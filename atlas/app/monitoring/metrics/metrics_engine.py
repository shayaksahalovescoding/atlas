import time
import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import psutil

from atlas.app.core.events.event_bus import EventBus
from atlas.app.core.events.event_types import Event, EventType, EventPriority
from atlas.app.storage.sqlite.repositories import MetricRepository
from atlas.app.twin.graph.graph_manager import GraphManager

logger = logging.getLogger("atlas.monitoring.metrics")


class RingBuffer:
    def __init__(self, max_size=3600):
        self._buffer = deque(maxlen=max_size)

    def append(self, timestamp, value):
        self._buffer.append((timestamp, value))

    def get_all(self):
        return list(self._buffer)

    def get_recent(self, count=60):
        items = list(self._buffer)
        return items[-count:]

    def get_since(self, since_ts):
        return [(ts, v) for ts, v in self._buffer if ts >= since_ts]

    @property
    def latest(self):
        if self._buffer:
            return self._buffer[-1]
        return None

    def __len__(self):
        return len(self._buffer)


class MetricsEngine:
    def __init__(self, event_bus: EventBus, graph: GraphManager,
                 metric_repo: MetricRepository = None):
        self._event_bus = event_bus
        self._graph = graph
        self._metric_repo = metric_repo
        self._running = False
        self._task = None
        self._buffers: Dict[str, RingBuffer] = {}
        self._sampling_interval = 10
        self._adaptive_interval = 10
        self._anomaly_mode = False
        self._collection_count = 0
        self._last_disk_io = None
        self._last_net_io = None
        self._last_io_time = None
        self._process_buffers: Dict[str, Dict[str, RingBuffer]] = {}

        for name in ["cpu_percent", "memory_percent", "memory_used_bytes",
                      "memory_available_bytes", "swap_percent",
                      "disk_read_bytes_sec", "disk_write_bytes_sec",
                      "net_sent_bytes_sec", "net_recv_bytes_sec",
                      "process_count", "handle_count"]:
            self._buffers[name] = RingBuffer()

    async def start(self, interval=10):
        self._sampling_interval = interval
        self._adaptive_interval = interval
        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info(f"Metrics engine started, interval={interval}s")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics engine stopped")

    async def _collection_loop(self):
        while self._running:
            try:
                await asyncio.get_event_loop().run_in_executor(None, self._collect)
                self._collection_count += 1

                if self._metric_repo and self._collection_count % 6 == 0:
                    self._persist_metrics()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}", exc_info=True)

            await asyncio.sleep(self._adaptive_interval)

    def _collect(self):
        now = datetime.now().isoformat()
        ts = time.time()

        cpu = psutil.cpu_percent(interval=0)
        self._buffers["cpu_percent"].append(ts, cpu)

        vm = psutil.virtual_memory()
        self._buffers["memory_percent"].append(ts, vm.percent)
        self._buffers["memory_used_bytes"].append(ts, vm.used)
        self._buffers["memory_available_bytes"].append(ts, vm.available)

        swap = psutil.swap_memory()
        self._buffers["swap_percent"].append(ts, swap.percent)

        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        if self._last_disk_io and self._last_io_time:
            dt = ts - self._last_io_time
            if dt > 0:
                dr = (disk_io.read_bytes - self._last_disk_io.read_bytes) / dt
                dw = (disk_io.write_bytes - self._last_disk_io.write_bytes) / dt
                self._buffers["disk_read_bytes_sec"].append(ts, dr)
                self._buffers["disk_write_bytes_sec"].append(ts, dw)

                ns = (net_io.bytes_sent - self._last_net_io.bytes_sent) / dt
                nr = (net_io.bytes_recv - self._last_net_io.bytes_recv) / dt
                self._buffers["net_sent_bytes_sec"].append(ts, ns)
                self._buffers["net_recv_bytes_sec"].append(ts, nr)

        self._last_disk_io = disk_io
        self._last_net_io = net_io
        self._last_io_time = ts

        pids = psutil.pids()
        self._buffers["process_count"].append(ts, len(pids))

        self._collect_process_metrics(ts)
        self._update_app_state(cpu, vm)
        self._adapt_sampling(cpu, vm.percent)

    def _collect_process_metrics(self, ts):
        top_processes = []
        for proc in self.graph.get_entities_by_type("process"):
            pid = proc.properties.get("pid", 0)
            if not pid:
                continue
            pid_key = str(pid)
            if pid_key not in self._process_buffers:
                self._process_buffers[pid_key] = {
                    "cpu": RingBuffer(360),
                    "memory": RingBuffer(360),
                }
            cpu = proc.properties.get("cpu_percent", 0)
            mem = proc.properties.get("memory_bytes", 0)
            self._process_buffers[pid_key]["cpu"].append(ts, cpu)
            self._process_buffers[pid_key]["memory"].append(ts, mem)

    def _update_app_state(self, cpu, vm):
        from atlas.app.core.state.app_state import AppState
        state = AppState()
        state.cpu_usage = cpu
        state.memory_usage = vm.percent
        try:
            partitions = psutil.disk_partitions(all=False)
            if partitions:
                usage = psutil.disk_usage(partitions[0].mountpoint)
                state.disk_usage = usage.percent
        except Exception:
            pass

    def _adapt_sampling(self, cpu, memory_pct):
        if cpu > 90 or memory_pct > 90:
            if not self._anomaly_mode:
                self._anomaly_mode = True
                self._adaptive_interval = max(1, self._sampling_interval // 5)
                logger.info(f"Adaptive sampling: increased to {self._adaptive_interval}s")
        else:
            if self._anomaly_mode:
                self._anomaly_mode = False
                self._adaptive_interval = self._sampling_interval
                logger.info(f"Adaptive sampling: restored to {self._adaptive_interval}s")

    def _persist_metrics(self):
        if not self._metric_repo:
            return
        now = datetime.now().isoformat()
        batch = []
        for name, buffer in self._buffers.items():
            latest = buffer.latest
            if latest:
                batch.append({
                    "metric_name": name,
                    "value": latest[1],
                    "timestamp": now,
                    "unit": self._get_unit(name),
                })
        if batch:
            try:
                self._metric_repo.save_batch(batch)
            except Exception as e:
                logger.error(f"Failed to persist metrics: {e}")

    def _get_unit(self, name):
        if "percent" in name:
            return "%"
        if "bytes" in name:
            return "bytes"
        if "count" in name:
            return "count"
        return ""

    def get_current(self):
        result = {}
        for name, buffer in self._buffers.items():
            latest = buffer.latest
            result[name] = latest[1] if latest else 0
        return result

    def get_history(self, metric_name, count=60):
        buffer = self._buffers.get(metric_name)
        if buffer:
            return buffer.get_recent(count)
        return []

    def get_process_history(self, pid, metric="cpu", count=60):
        pid_key = str(pid)
        if pid_key in self._process_buffers:
            buffer = self._process_buffers[pid_key].get(metric)
            if buffer:
                return buffer.get_recent(count)
        return []

    @property
    def graph(self):
        return self._graph

    def get_stats(self):
        return {
            "collections": self._collection_count,
            "interval": self._adaptive_interval,
            "anomaly_mode": self._anomaly_mode,
            "buffers": {k: len(v) for k, v in self._buffers.items()},
            "tracked_processes": len(self._process_buffers),
        }
