import logging
from datetime import datetime
from typing import Dict, List

from atlas.app.core.events.event_bus import EventBus
from atlas.app.core.events.event_types import Event, EventType, EventPriority
from atlas.app.monitoring.baselines.baseline_engine import BaselineEngine
from atlas.app.monitoring.metrics.metrics_engine import MetricsEngine
from atlas.app.twin.entities.monitoring import Anomaly, AnomalyType, IncidentSeverity
from atlas.app.twin.graph.graph_manager import GraphManager

logger = logging.getLogger("atlas.monitoring.anomaly")


class AnomalyDetector:
    def __init__(self, event_bus: EventBus, graph: GraphManager,
                 metrics: MetricsEngine, baselines: BaselineEngine):
        self._event_bus = event_bus
        self._graph = graph
        self._metrics = metrics
        self._baselines = baselines
        self._active_anomalies: Dict[str, Anomaly] = {}
        self._detection_count = 0

    async def detect(self):
        current = self._metrics.get_current()

        for name, value in current.items():
            self._baselines.update(name, value)

        anomalies = []
        anomalies.extend(self._check_cpu(current))
        anomalies.extend(self._check_memory(current))
        anomalies.extend(self._check_disk(current))
        anomalies.extend(self._check_network(current))
        anomalies.extend(self._check_process_anomalies())

        for anomaly in anomalies:
            self._detection_count += 1

        self._resolve_cleared(current)

    def _check_cpu(self, current):
        anomalies = []
        cpu = current.get("cpu_percent", 0)

        if cpu > 90:
            history = self._metrics.get_history("cpu_percent", 6)
            sustained = all(v > 85 for _, v in history) if len(history) >= 3 else False

            if sustained:
                anomaly = self._create_or_update_anomaly(
                    "cpu_sustained_high",
                    AnomalyType.CPU_SPIKE,
                    f"CPU sustained above 90% (current: {cpu:.0f}%)",
                    score=min(cpu / 100, 1.0),
                    severity=IncidentSeverity.HIGH if cpu > 95 else IncidentSeverity.MEDIUM,
                    current_value=cpu,
                    baseline_value=self._baselines.get_baseline("cpu_percent").mean if self._baselines.get_baseline("cpu_percent") else 0,
                )
                anomalies.append(anomaly)

        elif self._baselines.is_anomalous("cpu_percent", cpu, threshold=3.0):
            bl = self._baselines.get_baseline("cpu_percent")
            anomaly = self._create_or_update_anomaly(
                "cpu_deviation",
                AnomalyType.CPU_SPIKE,
                f"CPU usage ({cpu:.0f}%) significantly above baseline ({bl.mean:.0f}%)",
                score=min(abs(bl.z_score(cpu)) / 5, 1.0),
                severity=IncidentSeverity.LOW,
                current_value=cpu,
                baseline_value=bl.mean,
            )
            anomalies.append(anomaly)

        return anomalies

    def _check_memory(self, current):
        anomalies = []
        mem_pct = current.get("memory_percent", 0)

        if mem_pct > 90:
            anomaly = self._create_or_update_anomaly(
                "memory_pressure",
                AnomalyType.MEMORY_PRESSURE,
                f"Memory pressure: {mem_pct:.0f}% used",
                score=min(mem_pct / 100, 1.0),
                severity=IncidentSeverity.HIGH if mem_pct > 95 else IncidentSeverity.MEDIUM,
                current_value=mem_pct,
                baseline_value=self._baselines.get_baseline("memory_percent").mean if self._baselines.get_baseline("memory_percent") else 0,
            )
            anomalies.append(anomaly)

        history = self._metrics.get_history("memory_used_bytes", 30)
        if len(history) >= 10:
            values = [v for _, v in history]
            if len(values) >= 2:
                growth_rate = (values[-1] - values[0]) / max(len(values), 1)
                if growth_rate > 100 * 1024 * 1024:
                    anomaly = self._create_or_update_anomaly(
                        "memory_growth",
                        AnomalyType.MEMORY_LEAK,
                        f"Sustained memory growth detected: {growth_rate / (1024*1024):.0f} MB/sample",
                        score=min(growth_rate / (500 * 1024 * 1024), 1.0),
                        severity=IncidentSeverity.MEDIUM,
                        current_value=values[-1],
                        baseline_value=values[0],
                    )
                    anomalies.append(anomaly)

        return anomalies

    def _check_disk(self, current):
        anomalies = []

        for partition in self._graph.get_entities_by_type("partition"):
            usage = partition.properties.get("usage_percent", 0)
            if usage > 90:
                mount = partition.properties.get("mount_point", "")
                anomaly = self._create_or_update_anomaly(
                    f"disk_space_{mount}",
                    AnomalyType.DISK_SPACE_LOW,
                    f"Disk space low on {mount}: {usage:.0f}% used",
                    score=min(usage / 100, 1.0),
                    severity=IncidentSeverity.HIGH if usage > 95 else IncidentSeverity.MEDIUM,
                    current_value=usage,
                    affected_entity_id=partition.id,
                )
                anomalies.append(anomaly)

        disk_read = current.get("disk_read_bytes_sec", 0)
        disk_write = current.get("disk_write_bytes_sec", 0)
        total_io = disk_read + disk_write

        if self._baselines.is_anomalous("disk_read_bytes_sec", disk_read, threshold=3.0):
            bl = self._baselines.get_baseline("disk_read_bytes_sec")
            if bl and disk_read > 100 * 1024 * 1024:
                anomaly = self._create_or_update_anomaly(
                    "disk_io_high",
                    AnomalyType.DISK_IO_SATURATION,
                    f"Disk I/O above baseline: {disk_read / (1024*1024):.0f} MB/s read",
                    score=min(abs(bl.z_score(disk_read)) / 5, 1.0),
                    severity=IncidentSeverity.MEDIUM,
                    current_value=disk_read,
                    baseline_value=bl.mean,
                )
                anomalies.append(anomaly)

        return anomalies

    def _check_network(self, current):
        anomalies = []
        net_recv = current.get("net_recv_bytes_sec", 0)
        net_sent = current.get("net_sent_bytes_sec", 0)

        for metric_name, value in [("net_recv_bytes_sec", net_recv), ("net_sent_bytes_sec", net_sent)]:
            if self._baselines.is_anomalous(metric_name, value, threshold=4.0):
                bl = self._baselines.get_baseline(metric_name)
                if bl and value > 10 * 1024 * 1024:
                    direction = "download" if "recv" in metric_name else "upload"
                    anomaly = self._create_or_update_anomaly(
                        f"network_{direction}_high",
                        AnomalyType.NETWORK_ANOMALY,
                        f"Network {direction} above baseline: {value / (1024*1024):.1f} MB/s",
                        score=min(abs(bl.z_score(value)) / 5, 1.0),
                        severity=IncidentSeverity.LOW,
                        current_value=value,
                        baseline_value=bl.mean,
                    )
                    anomalies.append(anomaly)

        return anomalies

    def _check_process_anomalies(self):
        anomalies = []
        process_count = len(self._graph.get_entities_by_type("process"))

        bl = self._baselines.get_baseline("process_count")
        if bl and bl.is_anomalous(process_count, threshold=3.0) and process_count > bl.mean * 1.5:
            anomaly = self._create_or_update_anomaly(
                "process_explosion",
                AnomalyType.PROCESS_EXPLOSION,
                f"Unusual number of processes: {process_count} (baseline: {bl.mean:.0f})",
                score=min(abs(bl.z_score(process_count)) / 5, 1.0),
                severity=IncidentSeverity.MEDIUM,
                current_value=process_count,
                baseline_value=bl.mean,
            )
            anomalies.append(anomaly)

        return anomalies

    def _create_or_update_anomaly(self, key, anomaly_type, description, score,
                                   severity=IncidentSeverity.LOW,
                                   current_value=0, baseline_value=0,
                                   affected_entity_id=""):
        if key in self._active_anomalies:
            anomaly = self._active_anomalies[key]
            anomaly.update(
                score=score,
                description=description,
                current_value=current_value,
            )
            return anomaly

        anomaly = Anomaly(name=description, source="anomaly_detector")
        anomaly.properties.update({
            "anomaly_type": anomaly_type.value,
            "severity": severity.value,
            "score": score,
            "description": description,
            "current_value": current_value,
            "baseline_value": baseline_value,
            "deviation": current_value - baseline_value,
            "affected_entity_id": affected_entity_id,
            "detected_at": datetime.now().isoformat(),
            "is_active": True,
        })
        self._active_anomalies[key] = anomaly
        self._graph.add_entity(anomaly)

        self._event_bus.publish_sync(Event(
            event_type=EventType.ANOMALY_DETECTED,
            timestamp=datetime.now().isoformat(),
            source="anomaly_detector",
            entity_id=anomaly.id,
            entity_type="anomaly",
            metadata={"type": anomaly_type.value, "score": score, "description": description},
            priority=EventPriority.HIGH,
        ))

        return anomaly

    def _resolve_cleared(self, current):
        cpu = current.get("cpu_percent", 0)
        mem = current.get("memory_percent", 0)

        resolutions = {}
        if cpu < 70 and "cpu_sustained_high" in self._active_anomalies:
            resolutions["cpu_sustained_high"] = True
        if cpu < 70 and "cpu_deviation" in self._active_anomalies:
            resolutions["cpu_deviation"] = True
        if mem < 80 and "memory_pressure" in self._active_anomalies:
            resolutions["memory_pressure"] = True

        for key in resolutions:
            anomaly = self._active_anomalies.pop(key, None)
            if anomaly:
                anomaly.update(is_active=False, resolved_at=datetime.now().isoformat())
                self._event_bus.publish_sync(Event(
                    event_type=EventType.ANOMALY_RESOLVED,
                    timestamp=datetime.now().isoformat(),
                    source="anomaly_detector",
                    entity_id=anomaly.id,
                    entity_type="anomaly",
                    metadata={"type": anomaly.properties.get("anomaly_type", "")},
                ))

    def get_active_anomalies(self) -> List[Anomaly]:
        return list(self._active_anomalies.values())

    def get_stats(self):
        return {
            "active_anomalies": len(self._active_anomalies),
            "total_detections": self._detection_count,
            "baselines": len(self._baselines._baselines),
        }
