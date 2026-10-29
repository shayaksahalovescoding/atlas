import logging
from typing import Dict, List

from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.twin.relationships.relationship import RelationshipType, ConfidenceLevel

logger = logging.getLogger("atlas.reasoning.counterfactual")


CONFIDENCE_LABELS = {
    "confirmed": "CONFIRMED",
    "likely": "LIKELY",
    "possible": "POSSIBLE",
    "unknown": "UNKNOWN",
}


class CounterfactualEngine:
    def __init__(self, graph: GraphManager):
        self._graph = graph

    def simulate_process_termination(self, pid_or_entity_id) -> Dict:
        process = self._find_process(pid_or_entity_id)
        if not process:
            return {"error": "Process not found"}

        impact = self._graph.get_impact_graph(process.id, max_depth=4)

        child_procs = self._graph.get_incoming(process.id, RelationshipType.CHILD_OF)
        children = []
        for rel in child_procs:
            child = self._graph.get_entity(rel.source_id)
            if child:
                children.append({
                    "name": child.name,
                    "pid": child.properties.get("pid"),
                    "confidence": CONFIDENCE_LABELS["confirmed"],
                })

        app_rel = self._graph.get_outgoing(process.id, RelationshipType.BELONGS_TO)
        affected_app = None
        if app_rel:
            app = self._graph.get_entity(app_rel[0].target_id)
            if app:
                app_procs = self._graph.get_incoming(app.id, RelationshipType.BELONGS_TO)
                remaining = len(app_procs) - 1
                affected_app = {
                    "name": app.name,
                    "will_close": remaining <= 0,
                    "remaining_processes": remaining,
                    "confidence": CONFIDENCE_LABELS["likely"],
                }

        connections = self._graph.get_outgoing(process.id, RelationshipType.OWNS)
        affected_connections = len(connections)

        memory = process.properties.get("memory_bytes", 0)
        cpu = process.properties.get("cpu_percent", 0)

        return {
            "process": {"name": process.name, "pid": process.properties.get("pid")},
            "child_processes_terminated": children,
            "affected_application": affected_app,
            "network_connections_closed": affected_connections,
            "memory_freed_bytes": memory,
            "cpu_freed_percent": cpu,
            "total_affected_entities": impact["total_affected"],
            "directly_affected": impact["directly_affected"],
            "indirectly_affected": impact["indirectly_affected"][:10],
            "warnings": self._get_warnings(process),
        }

    def simulate_service_disable(self, service_name_or_id) -> Dict:
        service = self._find_service(service_name_or_id)
        if not service:
            return {"error": "Service not found"}

        dependents = self._graph.get_incoming(service.id, RelationshipType.DEPENDS_ON)
        affected_services = []
        for rel in dependents:
            dep_svc = self._graph.get_entity(rel.source_id)
            if dep_svc:
                sub_deps = self._graph.get_incoming(dep_svc.id, RelationshipType.DEPENDS_ON)
                affected_services.append({
                    "name": dep_svc.name,
                    "service_name": dep_svc.properties.get("service_name", ""),
                    "status": dep_svc.properties.get("status", ""),
                    "cascade_count": len(sub_deps),
                    "confidence": rel.confidence.value.upper(),
                })

        dependencies = self._graph.get_outgoing(service.id, RelationshipType.DEPENDS_ON)
        dep_list = []
        for rel in dependencies:
            dep = self._graph.get_entity(rel.target_id)
            if dep:
                dep_list.append({"name": dep.name})

        impact = self._graph.get_impact_graph(service.id)

        svc_pid = service.properties.get("pid", 0)
        associated_processes = []
        if svc_pid:
            procs = self._graph.find_entity("process", pid=svc_pid)
            for p in procs:
                associated_processes.append({
                    "name": p.name,
                    "pid": svc_pid,
                    "memory_bytes": p.properties.get("memory_bytes", 0),
                })

        return {
            "service": {
                "name": service.name,
                "service_name": service.properties.get("service_name", ""),
                "status": service.properties.get("status", ""),
                "startup_type": service.properties.get("startup_type", ""),
            },
            "dependent_services_affected": affected_services,
            "dependencies": dep_list,
            "associated_processes": associated_processes,
            "total_affected": impact["total_affected"],
            "is_critical": self._is_critical_service(service),
            "warnings": self._get_service_warnings(service, affected_services),
        }

    def simulate_application_close(self, app_name_or_id) -> Dict:
        app = self._find_application(app_name_or_id)
        if not app:
            return {"error": "Application not found"}

        processes = self._graph.get_incoming(app.id, RelationshipType.BELONGS_TO)
        proc_details = []
        total_memory = 0
        total_cpu = 0

        for rel in processes:
            proc = self._graph.get_entity(rel.source_id)
            if proc and proc.entity_type == "process":
                mem = proc.properties.get("memory_bytes", 0)
                cpu = proc.properties.get("cpu_percent", 0)
                total_memory += mem
                total_cpu += cpu
                proc_details.append({
                    "name": proc.name,
                    "pid": proc.properties.get("pid"),
                    "memory_bytes": mem,
                    "cpu_percent": cpu,
                })

        connections = 0
        for rel in processes:
            proc = self._graph.get_entity(rel.source_id)
            if proc:
                conns = self._graph.get_outgoing(proc.id, RelationshipType.OWNS)
                connections += len([c for c in conns if self._graph.get_entity(c.target_id) and self._graph.get_entity(c.target_id).entity_type == "network_connection"])

        return {
            "application": {"name": app.name, "version": app.properties.get("version", "")},
            "processes_terminated": proc_details,
            "total_processes": len(proc_details),
            "memory_freed_bytes": total_memory,
            "cpu_freed_percent": total_cpu,
            "network_connections_closed": connections,
            "confidence": CONFIDENCE_LABELS["likely"],
        }

    def estimate_memory_recovery(self, entity_ids: List[str]) -> Dict:
        total = 0
        details = []
        for eid in entity_ids:
            entity = self._graph.get_entity(eid)
            if entity:
                mem = entity.properties.get("memory_bytes", 0)
                total += mem
                details.append({"name": entity.name, "memory_bytes": mem})
        return {
            "total_recoverable_bytes": total,
            "total_recoverable_mb": round(total / (1024 * 1024), 1),
            "details": details,
        }

    def _find_process(self, identifier):
        entity = self._graph.get_entity(identifier)
        if entity and entity.entity_type == "process":
            return entity
        try:
            pid = int(identifier)
            results = self._graph.find_entity("process", pid=pid)
            if results:
                return results[0]
        except (ValueError, TypeError):
            pass
        results = self._graph.search(str(identifier), "process")
        return results[0] if results else None

    def _find_service(self, identifier):
        entity = self._graph.get_entity(identifier)
        if entity and entity.entity_type == "service":
            return entity
        results = self._graph.find_entity("service", service_name=identifier)
        if results:
            return results[0]
        results = self._graph.search(str(identifier), "service")
        return results[0] if results else None

    def _find_application(self, identifier):
        entity = self._graph.get_entity(identifier)
        if entity and entity.entity_type == "application":
            return entity
        results = self._graph.search(str(identifier), "application")
        return results[0] if results else None

    def _get_warnings(self, process):
        warnings = []
        if process.properties.get("is_system"):
            warnings.append("This is a system process. Terminating it may cause system instability.")
        return warnings

    def _get_service_warnings(self, service, affected):
        warnings = []
        if self._is_critical_service(service):
            warnings.append("This is a critical Windows service. Disabling it may cause system instability.")
        if len(affected) > 5:
            warnings.append(f"This service has {len(affected)} dependent services. Disabling it will have widespread impact.")
        return warnings

    def _is_critical_service(self, service):
        critical = {"RpcSs", "DcomLaunch", "Dhcp", "Dnscache", "EventLog",
                     "PlugPlay", "Power", "SecurityHealthService", "Winmgmt",
                     "wuauserv", "WinDefend", "Schedule"}
        svc_name = service.properties.get("service_name", "")
        return svc_name in critical
