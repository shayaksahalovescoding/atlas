import logging
from typing import Dict

from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.monitoring.metrics.metrics_engine import MetricsEngine
from atlas.app.monitoring.anomaly.anomaly_detector import AnomalyDetector
from atlas.app.monitoring.incidents.incident_engine import IncidentEngine
from atlas.app.twin.snapshots.snapshot_engine import SnapshotEngine
from atlas.app.reasoning.context.context_builder import ContextBuilder
from atlas.app.reasoning.counterfactual.counterfactual_engine import CounterfactualEngine
from atlas.app.agent.tools.tool_registry import ToolRegistry
from atlas.app.core.events.event_bus import EventBus

logger = logging.getLogger("atlas.agent.tools.inspection")


def register_inspection_tools(registry: ToolRegistry, graph: GraphManager,
                               metrics: MetricsEngine, anomaly_detector: AnomalyDetector,
                               incident_engine: IncidentEngine,
                               snapshot_engine: SnapshotEngine,
                               context_builder: ContextBuilder,
                               counterfactual: CounterfactualEngine,
                               event_bus: EventBus):

    def inspect_system():
        return context_builder.build_system_context()

    registry.register(
        "inspect_system",
        "Get the current system state overview including CPU, memory, disk, network, anomalies, and top consumers",
        {"type": "object", "properties": {}, "required": []},
        inspect_system
    )

    def inspect_process(identifier: str = ""):
        if not identifier:
            processes = graph.get_entities_by_type("process")
            processes.sort(key=lambda p: p.properties.get("memory_bytes", 0), reverse=True)
            return [{"name": p.name, "pid": p.properties.get("pid"), "cpu": p.properties.get("cpu_percent", 0), "memory_mb": round(p.properties.get("memory_bytes", 0) / (1024*1024), 1)} for p in processes[:30]]
        entity = graph.get_entity(identifier)
        if not entity:
            try:
                pid = int(identifier)
                results = graph.find_entity("process", pid=pid)
                if results:
                    entity = results[0]
            except (ValueError, TypeError):
                results = graph.search(identifier, "process")
                if results:
                    entity = results[0]
        if entity:
            return context_builder.build_entity_context(entity.id)
        return {"error": "Process not found"}

    registry.register(
        "inspect_process",
        "Inspect a specific process by PID, name, or entity ID. Returns details, relationships, and metrics history.",
        {"type": "object", "properties": {"identifier": {"type": "string", "description": "Process PID, name, or entity ID"}}, "required": []},
        inspect_process
    )

    def inspect_application(name: str = ""):
        if not name:
            apps = graph.get_entities_by_type("application")
            return [{"name": a.name, "version": a.properties.get("version", "")} for a in apps[:50]]
        results = graph.search(name, "application")
        if results:
            return context_builder.build_entity_context(results[0].id)
        return {"error": "Application not found"}

    registry.register(
        "inspect_application",
        "Inspect an installed application by name. Returns details, processes, dependencies, and metrics.",
        {"type": "object", "properties": {"name": {"type": "string", "description": "Application name"}}, "required": []},
        inspect_application
    )

    def inspect_service(name: str = ""):
        if not name:
            services = graph.get_entities_by_type("service")
            return [{"name": s.name, "status": s.properties.get("status", ""), "startup": s.properties.get("startup_type", "")} for s in services[:50]]
        results = graph.find_entity("service", service_name=name)
        if not results:
            results = graph.search(name, "service")
        if results:
            return context_builder.build_entity_context(results[0].id)
        return {"error": "Service not found"}

    registry.register(
        "inspect_service",
        "Inspect a Windows service by name. Returns status, dependencies, dependents, and associated processes.",
        {"type": "object", "properties": {"name": {"type": "string", "description": "Service name"}}, "required": []},
        inspect_service
    )

    def get_recent_events(count: int = 20, event_type: str = ""):
        events = event_bus.get_recent_events(count)
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        return [e.to_dict() for e in events]

    registry.register(
        "get_recent_events",
        "Get recent system events. Optionally filter by event type.",
        {"type": "object", "properties": {"count": {"type": "integer"}, "event_type": {"type": "string"}}, "required": []},
        get_recent_events
    )

    def get_anomaly_report():
        anomalies = anomaly_detector.get_active_anomalies()
        return [{"type": a.properties.get("anomaly_type"), "description": a.properties.get("description"), "score": a.properties.get("score"), "severity": a.properties.get("severity")} for a in anomalies]

    registry.register(
        "get_anomaly_report",
        "Get all currently active anomalies with scores and evidence.",
        {"type": "object", "properties": {}, "required": []},
        get_anomaly_report
    )

    def get_dependency_graph(entity_id: str, depth: int = 3):
        entities, relationships = graph.get_subgraph(entity_id, max_depth=depth)
        return {"entities": [e.to_dict() for e in entities.values()], "relationships": [r.to_dict() for r in relationships]}

    registry.register(
        "get_dependency_graph",
        "Get the dependency subgraph around an entity. Returns connected entities and relationships.",
        {"type": "object", "properties": {"entity_id": {"type": "string"}, "depth": {"type": "integer"}}, "required": ["entity_id"]},
        get_dependency_graph
    )

    def get_resource_history(metric_name: str, count: int = 60):
        history = metrics.get_history(metric_name, count)
        return [{"timestamp": ts, "value": round(v, 2)} for ts, v in history]

    registry.register(
        "get_resource_history",
        "Get historical values for a metric (cpu_percent, memory_percent, etc.)",
        {"type": "object", "properties": {"metric_name": {"type": "string"}, "count": {"type": "integer"}}, "required": ["metric_name"]},
        get_resource_history
    )

    def compare_system_states(hours_ago: int = 24):
        return snapshot_engine.get_what_changed(since_hours=hours_ago)

    registry.register(
        "compare_system_states",
        "Compare current system state with a previous state. Shows what changed.",
        {"type": "object", "properties": {"hours_ago": {"type": "integer"}}, "required": []},
        compare_system_states
    )

    def simulate_process_termination(identifier: str):
        return counterfactual.simulate_process_termination(identifier)

    registry.register(
        "simulate_process_termination",
        "Simulate what would happen if a process is terminated. Returns impact analysis.",
        {"type": "object", "properties": {"identifier": {"type": "string"}}, "required": ["identifier"]},
        simulate_process_termination,
        requires_confirmation=False
    )

    def simulate_service_disable(name: str):
        return counterfactual.simulate_service_disable(name)

    registry.register(
        "simulate_service_disable",
        "Simulate what would happen if a service is disabled. Returns dependency impact.",
        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        simulate_service_disable,
        requires_confirmation=False
    )

    def search_entities(query: str, entity_type: str = ""):
        results = graph.search(query, entity_type if entity_type else None)
        return [{"id": e.id, "type": e.entity_type, "name": e.name} for e in results]

    registry.register(
        "search_entities",
        "Search across all entities (processes, applications, services, files, etc.)",
        {"type": "object", "properties": {"query": {"type": "string"}, "entity_type": {"type": "string"}}, "required": ["query"]},
        search_entities
    )

    def get_incident_timeline(incident_id: str = ""):
        if incident_id:
            entity = graph.get_entity(incident_id)
            if entity:
                return entity.properties.get("timeline", [])
            return {"error": "Incident not found"}
        incidents = incident_engine.get_active_incidents()
        return [{"id": i.id, "name": i.name, "severity": i.properties.get("severity"), "started_at": i.properties.get("started_at")} for i in incidents]

    registry.register(
        "get_incident_timeline",
        "Get the timeline of an incident or list active incidents.",
        {"type": "object", "properties": {"incident_id": {"type": "string"}}, "required": []},
        get_incident_timeline
    )
