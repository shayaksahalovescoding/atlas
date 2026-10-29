import sys
import asyncio
import threading
import logging
import signal
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, Signal, QObject

from atlas.ui.themes.dark_theme import apply_theme
from atlas.ui.main_window import MainWindow
from atlas.app.core.config.settings import Settings
from atlas.app.core.events.event_bus import EventBus
from atlas.app.core.logging.logger import setup_logging
from atlas.app.core.state.app_state import AppState
from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.storage.sqlite.database import Database
from atlas.app.storage.sqlite.repositories import (
    EntityRepository, RelationshipRepository, MetricRepository,
    SnapshotRepository, IncidentRepository
)
from atlas.app.storage.cache.cache import LRUCache
from atlas.app.collectors.collector_manager import CollectorManager
from atlas.app.monitoring.metrics.metrics_engine import MetricsEngine
from atlas.app.monitoring.baselines.baseline_engine import BaselineEngine
from atlas.app.monitoring.anomaly.anomaly_detector import AnomalyDetector
from atlas.app.monitoring.incidents.incident_engine import IncidentEngine
from atlas.app.twin.snapshots.snapshot_engine import SnapshotEngine
from atlas.app.model.ollama.ollama_provider import OllamaProvider
from atlas.app.reasoning.context.context_builder import ContextBuilder
from atlas.app.reasoning.hypotheses.hypothesis_engine import HypothesisEngine
from atlas.app.reasoning.counterfactual.counterfactual_engine import CounterfactualEngine
from atlas.app.agent.tools.tool_registry import ToolRegistry
from atlas.app.agent.tools.inspection_tools import register_inspection_tools
from atlas.app.agent.runtime.agent_runtime import AgentRuntime
from atlas.app.security.permissions.permission_manager import PermissionManager

logger = logging.getLogger("atlas")


class AsyncLoopThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop = None
        self._ready_event = threading.Event()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready_event.set()
        self.loop.run_forever()
        try:
            pending = [t for t in asyncio.all_tasks(self.loop) if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            self.loop.close()

    def wait_ready(self):
        self._ready_event.wait()

    def run_coroutine(self, coro):
        if self.loop and self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        return None

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait(3000)


class AtlasOrchestrator(QObject):
    ai_response_ready = Signal(str)
    ai_query_error = Signal(str)

    def __init__(self):
        super().__init__()
        self._app = None
        self._window = None
        self._async_thread = None
        self._settings = None
        self._event_bus = None
        self._graph = None
        self._db = None
        self._collectors = None
        self._metrics = None
        self._baselines = None
        self._anomaly_detector = None
        self._incident_engine = None
        self._snapshot_engine = None
        self._ai_provider = None
        self._context_builder = None
        self._hypothesis_engine = None
        self._counterfactual = None
        self._agent = None
        self._tool_registry = None
        self._permissions = None
        self._update_timer = None
        self._snapshot_timer = None
        self._ai_connected = False

    def initialize(self):
        self._async_thread = AsyncLoopThread()
        self._async_thread.start()
        self._async_thread.wait_ready()

        data_dir = Path("atlas_data")
        data_dir.mkdir(exist_ok=True)

        setup_logging(str(data_dir / "logs"))

        self._settings = Settings()
        self._event_bus = EventBus()
        self._graph = GraphManager()

        self._db = Database(str(data_dir / "atlas.db"))

        self._entity_repo = EntityRepository(self._db)
        self._rel_repo = RelationshipRepository(self._db)
        self._metric_repo = MetricRepository(self._db)
        self._snapshot_repo = SnapshotRepository(self._db)
        self._incident_repo = IncidentRepository(self._db)

        self._collectors = CollectorManager(self._event_bus, self._graph, self._settings)
        self._metrics = MetricsEngine(self._event_bus, self._graph, self._metric_repo)
        self._baselines = BaselineEngine()
        self._anomaly_detector = AnomalyDetector(
            self._event_bus, self._graph, self._metrics, self._baselines
        )
        self._incident_engine = IncidentEngine(
            self._event_bus, self._graph, self._metrics, self._incident_repo
        )
        self._snapshot_engine = SnapshotEngine(self._graph, self._snapshot_repo)

        self._ai_provider = OllamaProvider(
            host=self._settings.ollama.host,
            model=self._settings.ollama.model,
        )
        self._context_builder = ContextBuilder(
            self._graph, self._metrics, self._baselines,
            self._anomaly_detector, self._incident_engine, self._event_bus
        )
        self._hypothesis_engine = HypothesisEngine(
            self._graph, self._metrics, self._baselines
        )
        self._counterfactual = CounterfactualEngine(self._graph)
        self._permissions = PermissionManager()

        self._tool_registry = ToolRegistry()
        register_inspection_tools(
            self._tool_registry, self._graph, self._metrics,
            self._anomaly_detector, self._incident_engine,
            self._snapshot_engine, self._context_builder,
            self._counterfactual, self._event_bus
        )

        self._agent = AgentRuntime(
            self._ai_provider, self._context_builder,
            self._hypothesis_engine, self._counterfactual,
            self._tool_registry, self._event_bus
        )

        logger.info("ATLAS core initialized")

    def start_collection(self):
        if self._async_thread:
            self._async_thread.run_coroutine(self._async_start())

    async def _async_start(self):
        await self._event_bus.start()
        await self._collectors.start()
        await self._metrics.start(interval=self._settings.get_sampling_intervals().get("metrics", 10))
        try:
            connected = await self._ai_provider.health_check()
            self._ai_connected = connected
            if connected:
                logger.info("Ollama connected")
            else:
                logger.warning("Ollama not available, running in deterministic mode")
        except Exception as e:
            self._ai_connected = False
            logger.warning(f"Ollama connection check failed: {e}")

    def create_ui(self, qt_app):
        self._app = qt_app
        apply_theme(qt_app)

        self._window = MainWindow()
        self._window.query_submitted.connect(self._on_query)
        self._window.show()

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(2000)

        self._snapshot_timer = QTimer()
        self._snapshot_timer.timeout.connect(self._take_snapshot)
        self._snapshot_timer.start(3600000)

        return self._window

    def _update_ui(self):
        try:
            self._update_overview()
            self._update_status_bar()
            self._run_anomaly_detection()
        except Exception as e:
            logger.error(f"UI update error: {e}")

    def _update_overview(self):
        current = self._metrics.get_current()
        cpu = current.get("cpu_percent", 0)
        mem = current.get("memory_percent", 0)

        net_sent = current.get("net_sent_bytes_sec", 0)
        net_recv = current.get("net_recv_bytes_sec", 0)
        net_mbps = (net_sent + net_recv) / (1024 * 1024)

        disk_usage = 0
        partitions = self._graph.get_entities_by_type("partition")
        if partitions:
            disk_usage = max(p.properties.get("usage_percent", 0) for p in partitions)

        gpus = self._graph.get_entities_by_type("gpu")
        gpu_usage = 0

        self._window.overview.update_metrics(cpu, mem, gpu_usage, disk_usage, net_mbps)

        stats = self._graph.get_stats()
        event_count = len(self._event_bus.get_recent_events(100))
        self._window.overview.update_twin_stats(
            stats.get("entity_count", 0),
            stats.get("relationship_count", 0),
            event_count
        )

        anomalies = self._anomaly_detector.get_active_anomalies()
        self._window.overview.update_anomalies([{
            "description": a.properties.get("description", ""),
            "severity": a.properties.get("severity", "low"),
        } for a in anomalies])

        health = "healthy"
        if cpu > 90 or mem > 90:
            health = "critical"
        elif cpu > 70 or mem > 80:
            health = "warning"

        self._window.overview.update_health(health, self._ai_connected, True)

        processes = self._graph.get_entities_by_type("process")
        top = sorted(processes, key=lambda p: p.properties.get("memory_bytes", 0), reverse=True)[:8]
        self._window.overview.update_consumers([{
            "name": p.name,
            "cpu_percent": p.properties.get("cpu_percent", 0),
            "memory_bytes": p.properties.get("memory_bytes", 0),
        } for p in top])

        proc_data = []
        from atlas.app.collectors.processes.process_collector import APPLICATION_MAPPINGS
        for p in processes:
            proc_data.append({
                "entity_id": p.id,
                "name": p.name,
                "pid": p.properties.get("pid", 0),
                "cpu_percent": p.properties.get("cpu_percent", 0),
                "memory_bytes": p.properties.get("memory_bytes", 0),
                "thread_count": p.properties.get("thread_count", 0),
                "status": p.properties.get("status", ""),
                "application": APPLICATION_MAPPINGS.get(p.name, ""),
            })
        proc_data.sort(key=lambda x: x["memory_bytes"], reverse=True)
        self._window.process_view.update_processes(proc_data)

        apps = self._graph.get_entities_by_type("application")
        app_data = sorted([{
            "entity_id": a.id,
            "name": a.name,
            "version": a.properties.get("version", ""),
        } for a in apps], key=lambda x: x["name"].lower())
        self._window.application_view.update_applications(app_data)

        services = self._graph.get_entities_by_type("service")
        svc_data = sorted([{
            "entity_id": s.id,
            "name": s.name,
            "display_name": s.properties.get("display_name", s.name),
            "service_name": s.properties.get("service_name", ""),
            "status": s.properties.get("status", ""),
        } for s in services], key=lambda x: x["display_name"].lower())
        self._window.service_view.update_services(svc_data)

        net_kbps_sent = net_sent / 1024
        net_kbps_recv = net_recv / 1024
        self._window.network_view.update_throughput(net_kbps_sent, net_kbps_recv)

        adapters = self._graph.get_entities_by_type("network_adapter")
        self._window.network_view.update_adapters([{
            "name": a.name,
            "is_up": a.properties.get("is_up", False),
            "ipv4_addresses": a.properties.get("ipv4_addresses", []),
            "speed_mbps": a.properties.get("speed_mbps", 0),
        } for a in adapters])

        connections = self._graph.get_entities_by_type("network_connection")
        self._window.network_view.update_connections([{
            "process_name": c.properties.get("process_name", ""),
            "protocol": c.properties.get("protocol", ""),
            "local_address": c.properties.get("local_address", ""),
            "local_port": c.properties.get("local_port", 0),
            "remote_address": c.properties.get("remote_address", ""),
            "remote_port": c.properties.get("remote_port", 0),
            "status": c.properties.get("status", ""),
            "pid": c.properties.get("pid", 0),
        } for c in connections[:200]])

        active_incidents = self._incident_engine.get_active_incidents()
        all_incidents = self._incident_engine.get_all_incidents()
        self._window.incidents_view.update_incidents(
            [{"name": i.name, "severity": i.properties.get("severity", ""),
              "started_at": i.properties.get("started_at", ""),
              "description": i.properties.get("description", "")} for i in active_incidents],
            [{"name": i.name, "status": i.properties.get("status", "")} for i in all_incidents]
        )

        events = self._event_bus.get_recent_events(100)
        self._window.timeline_view.update_events([e.to_dict() for e in events])

        self._window.machine_view.update_machine(self._graph)

    def _update_status_bar(self):
        current = self._metrics.get_current()
        stats = self._graph.get_stats()
        self._window.update_status_bar(
            entities=stats.get("entity_count", 0),
            rels=stats.get("relationship_count", 0),
            cpu=current.get("cpu_percent", 0),
            ram=current.get("memory_percent", 0),
            ai_connected=self._ai_connected,
            mode=self._settings.monitoring_mode.value,
        )

    def _run_anomaly_detection(self):
        if self._async_thread and self._anomaly_detector:
            self._async_thread.run_coroutine(self._anomaly_detector.detect())

    def _take_snapshot(self):
        try:
            self._snapshot_engine.create_snapshot(trigger="scheduled")
        except Exception as e:
            logger.error(f"Snapshot error: {e}")

    def _on_query(self, question):
        if not self._async_thread:
            self._handle_query_error("Async runtime is not running.")
            return

        future = self._async_thread.run_coroutine(self._process_query(question))
        if future:
            def on_done(fut):
                try:
                    fut.result()
                except Exception as e:
                    logger.error(f"Query execution error: {e}", exc_info=True)
                    self.ai_query_error.emit(str(e))
            future.add_done_callback(on_done)
        else:
            self._handle_query_error("Failed to submit query to async loop.")

    async def _process_query(self, question):
        try:
            result = await self._agent.process_query(question)
            answer = result.get("answer", "No response available.")
            self.ai_response_ready.emit(answer)
        except Exception as e:
            logger.error(f"Error in _process_query: {e}", exc_info=True)
            self.ai_query_error.emit(str(e))

    def _handle_query_error(self, error):
        self._window.ai_chat.add_message(f"Error: {error}", is_user=False)
        self._window.ai_chat.set_thinking(False)

    def update_graph_view(self):
        entities = []
        all_entities = {}
        for etype in ["machine", "cpu", "gpu", "memory", "partition", "network_adapter",
                       "application", "service", "project"]:
            for e in self._graph.get_entities_by_type(etype):
                entities.append({"id": e.id, "name": e.name, "entity_type": e.entity_type})
                all_entities[e.id] = e

        top_procs = sorted(
            self._graph.get_entities_by_type("process"),
            key=lambda p: p.properties.get("memory_bytes", 0),
            reverse=True
        )[:30]
        for p in top_procs:
            entities.append({"id": p.id, "name": p.name, "entity_type": "process"})
            all_entities[p.id] = p

        entity_ids = {e["id"] for e in entities}
        relationships = []
        for eid in entity_ids:
            for rel in self._graph.get_outgoing(eid):
                if rel.target_id in entity_ids:
                    relationships.append({
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "relationship_type": rel.relationship_type.value,
                    })

        self._window.graph_view.update_graph(entities, relationships)

    def shutdown(self):
        logger.info("ATLAS shutting down")
        if self._update_timer:
            self._update_timer.stop()
        if self._snapshot_timer:
            self._snapshot_timer.stop()

        try:
            self._snapshot_engine.create_snapshot(trigger="shutdown")
        except Exception as e:
            logger.error(f"Shutdown snapshot error: {e}")

        if self._async_thread:
            future = self._async_thread.run_coroutine(self._async_shutdown())
            if future:
                try:
                    future.result(timeout=5.0)
                except Exception as e:
                    logger.error(f"Async shutdown error: {e}")
            self._async_thread.stop()

        if self._db:
            self._db.close()

        logger.info("ATLAS shutdown complete")

    async def _async_shutdown(self):
        if self._collectors:
            await self._collectors.stop()
        if self._metrics:
            await self._metrics.stop()
        if self._event_bus:
            await self._event_bus.stop()
        if self._ai_provider:
            await self._ai_provider.close()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ATLAS")
    app.setOrganizationName("ATLAS")

    orchestrator = AtlasOrchestrator()
    orchestrator.initialize()

    window = orchestrator.create_ui(app)

    orchestrator.ai_response_ready.connect(lambda text: (
        window.ai_chat.add_message(text, is_user=False),
        window.ai_chat.set_thinking(False),
    ))
    orchestrator.ai_query_error.connect(lambda err: (
        window.ai_chat.add_message(f"Error: {err}", is_user=False),
        window.ai_chat.set_thinking(False),
    ))

    orchestrator.start_collection()

    QTimer.singleShot(10000, orchestrator.update_graph_view)

    def on_close():
        orchestrator.shutdown()

    app.aboutToQuit.connect(on_close)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
