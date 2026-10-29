import logging
from typing import Dict, List

from atlas.app.monitoring.metrics.metrics_engine import MetricsEngine
from atlas.app.monitoring.baselines.baseline_engine import BaselineEngine
from atlas.app.monitoring.anomaly.anomaly_detector import AnomalyDetector
from atlas.app.monitoring.incidents.incident_engine import IncidentEngine
from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.core.events.event_bus import EventBus

logger = logging.getLogger("atlas.reasoning.context")


class ContextBuilder:
    def __init__(self, graph: GraphManager, metrics: MetricsEngine,
                 baselines: BaselineEngine, anomaly_detector: AnomalyDetector,
                 incident_engine: IncidentEngine, event_bus: EventBus):
        self._graph = graph
        self._metrics = metrics
        self._baselines = baselines
        self._anomaly_detector = anomaly_detector
        self._incident_engine = incident_engine
        self._event_bus = event_bus

    def build_system_context(self, question: str = "") -> Dict:
        context = {
            "system_health": self._get_system_health(),
            "active_anomalies": self._get_active_anomalies(),
            "top_resource_consumers": self._get_top_consumers(),
            "recent_events": self._get_recent_events(),
            "active_incidents": self._get_active_incidents(),
            "baselines": self._get_baseline_summary(),
            "twin_stats": self._graph.get_stats(),
        }

        if question:
            context["relevant_entities"] = self._get_relevant_entities(question)
            context["candidate_hypotheses"] = self._generate_quick_hypotheses(context)

        return context

    def build_entity_context(self, entity_id: str) -> Dict:
        entity = self._graph.get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found"}

        neighbors = self._graph.get_neighbors(entity_id)
        outgoing = self._graph.get_outgoing(entity_id)
        incoming = self._graph.get_incoming(entity_id)

        context = {
            "entity": entity.to_dict(),
            "relationships": {
                "outgoing": [{"target": self._graph.get_entity(r.target_id).name if self._graph.get_entity(r.target_id) else r.target_id, "type": r.relationship_type.value} for r in outgoing],
                "incoming": [{"source": self._graph.get_entity(r.source_id).name if self._graph.get_entity(r.source_id) else r.source_id, "type": r.relationship_type.value} for r in incoming],
            },
        }

        if entity.entity_type == "process":
            pid = entity.properties.get("pid")
            if pid:
                context["cpu_history"] = self._metrics.get_process_history(pid, "cpu", 30)
                context["memory_history"] = self._metrics.get_process_history(pid, "memory", 30)

        return context

    def _get_system_health(self) -> Dict:
        current = self._metrics.get_current()
        machines = self._graph.get_entities_by_type("machine")
        machine = machines[0] if machines else None

        return {
            "cpu_percent": current.get("cpu_percent", 0),
            "memory_percent": current.get("memory_percent", 0),
            "memory_used_bytes": current.get("memory_used_bytes", 0),
            "memory_available_bytes": current.get("memory_available_bytes", 0),
            "swap_percent": current.get("swap_percent", 0),
            "disk_read_bytes_sec": current.get("disk_read_bytes_sec", 0),
            "disk_write_bytes_sec": current.get("disk_write_bytes_sec", 0),
            "net_sent_bytes_sec": current.get("net_sent_bytes_sec", 0),
            "net_recv_bytes_sec": current.get("net_recv_bytes_sec", 0),
            "process_count": current.get("process_count", 0),
            "uptime": machine.properties.get("uptime_seconds", 0) if machine else 0,
        }

    def _get_active_anomalies(self) -> List[Dict]:
        anomalies = self._anomaly_detector.get_active_anomalies()
        return [{
            "type": a.properties.get("anomaly_type", ""),
            "description": a.properties.get("description", ""),
            "score": a.properties.get("score", 0),
            "severity": a.properties.get("severity", ""),
            "current_value": a.properties.get("current_value", 0),
            "baseline_value": a.properties.get("baseline_value", 0),
        } for a in anomalies]

    def _get_top_consumers(self, count=10) -> List[Dict]:
        processes = self._graph.get_entities_by_type("process")
        by_memory = sorted(processes, key=lambda p: p.properties.get("memory_bytes", 0), reverse=True)[:count]
        return [{
            "name": p.name,
            "pid": p.properties.get("pid", 0),
            "cpu_percent": p.properties.get("cpu_percent", 0),
            "memory_bytes": p.properties.get("memory_bytes", 0),
            "memory_percent": p.properties.get("memory_percent", 0),
        } for p in by_memory]

    def _get_recent_events(self, count=20) -> List[Dict]:
        events = self._event_bus.get_recent_events(count)
        return [e.to_dict() for e in events]

    def _get_active_incidents(self) -> List[Dict]:
        incidents = self._incident_engine.get_active_incidents()
        return [{
            "name": i.name,
            "severity": i.properties.get("severity", ""),
            "description": i.properties.get("description", ""),
            "started_at": i.properties.get("started_at", ""),
        } for i in incidents]

    def _get_baseline_summary(self) -> Dict:
        return self._baselines.get_all_baselines()

    def _get_relevant_entities(self, question: str) -> List[Dict]:
        keywords = question.lower().split()
        results = []
        seen = set()
        for word in keywords:
            if len(word) < 3:
                continue
            for entity in self._graph.search(word, limit=5):
                if entity.id not in seen:
                    seen.add(entity.id)
                    results.append({
                        "id": entity.id,
                        "type": entity.entity_type,
                        "name": entity.name,
                    })
        return results[:20]

    def _generate_quick_hypotheses(self, context: Dict) -> List[Dict]:
        hypotheses = []
        health = context.get("system_health", {})

        if health.get("memory_percent", 0) > 80:
            hypotheses.append({
                "hypothesis": "Memory pressure",
                "score": min(health["memory_percent"] / 100, 1.0),
                "evidence": [f"RAM at {health['memory_percent']:.0f}%"],
            })

        if health.get("cpu_percent", 0) > 80:
            hypotheses.append({
                "hypothesis": "CPU saturation",
                "score": min(health["cpu_percent"] / 100, 1.0),
                "evidence": [f"CPU at {health['cpu_percent']:.0f}%"],
            })

        if health.get("swap_percent", 0) > 50:
            hypotheses.append({
                "hypothesis": "Excessive paging",
                "score": min(health["swap_percent"] / 100, 1.0),
                "evidence": [f"Swap at {health['swap_percent']:.0f}%"],
            })

        disk_io = health.get("disk_read_bytes_sec", 0) + health.get("disk_write_bytes_sec", 0)
        if disk_io > 100 * 1024 * 1024:
            hypotheses.append({
                "hypothesis": "Disk I/O saturation",
                "score": min(disk_io / (500 * 1024 * 1024), 1.0),
                "evidence": [f"Disk I/O at {disk_io / (1024*1024):.0f} MB/s"],
            })

        anomalies = context.get("active_anomalies", [])
        for a in anomalies:
            hypotheses.append({
                "hypothesis": a.get("description", "Unknown anomaly"),
                "score": a.get("score", 0.5),
                "evidence": [f"Active anomaly: {a.get('type', '')}"],
            })

        hypotheses.sort(key=lambda h: h["score"], reverse=True)
        return hypotheses[:5]
