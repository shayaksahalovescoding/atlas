import asyncio
import logging
from datetime import datetime

from atlas.app.collectors.base import BaseCollector
from atlas.app.collectors.windows.wmi_provider import WMIProvider
from atlas.app.core.events.event_types import EventType
from atlas.app.twin.entities.software import Service
from atlas.app.twin.relationships.relationship import RelationshipType

logger = logging.getLogger("atlas.collectors.services")

try:
    import win32service
    import win32con
    _win32_available = True
except ImportError:
    _win32_available = False
    logger.warning("win32service not available")


class ServiceCollector(BaseCollector):
    def __init__(self, event_bus, graph):
        super().__init__("service_collector", event_bus, graph)
        self._wmi = WMIProvider()
        self._known_services = {}

    async def collect(self):
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        services_data = self._get_services()
        current_names = set()

        for svc_data in services_data:
            svc_name = svc_data.get("name", "")
            if not svc_name:
                continue
            current_names.add(svc_name)
            display_name = svc_data.get("display_name", svc_name)

            if svc_name in self._known_services:
                entity_id = self._known_services[svc_name]
                old_entity = self.graph.get_entity(entity_id)
                old_status = old_entity.properties.get("status", "") if old_entity else ""
                new_status = svc_data.get("status", "")

                self.graph.update_entity(entity_id,
                    status=new_status,
                    pid=svc_data.get("pid", 0),
                )

                if old_status != new_status and old_status and new_status:
                    if new_status.lower() in ("running", "started"):
                        self.emit_event(EventType.SERVICE_STARTED,
                            entity_id=entity_id, entity_type="service",
                            metadata={"service_name": svc_name, "display_name": display_name})
                    elif new_status.lower() in ("stopped",):
                        self.emit_event(EventType.SERVICE_STOPPED,
                            entity_id=entity_id, entity_type="service",
                            metadata={"service_name": svc_name, "display_name": display_name})
                    else:
                        self.emit_event(EventType.SERVICE_STATE_CHANGED,
                            entity_id=entity_id, entity_type="service",
                            metadata={"service_name": svc_name, "old": old_status, "new": new_status})
            else:
                service = Service(name=display_name, source=self.name)
                service.properties.update({
                    "service_name": svc_name,
                    "display_name": display_name,
                    "status": svc_data.get("status", ""),
                    "startup_type": svc_data.get("startup_type", ""),
                    "executable_path": svc_data.get("path", ""),
                    "pid": svc_data.get("pid", 0),
                    "description": svc_data.get("description", ""),
                    "account": svc_data.get("account", ""),
                    "service_type": svc_data.get("service_type", ""),
                    "dependencies": [],
                    "dependents": [],
                })
                self.graph.add_entity(service)
                self._known_services[svc_name] = service.id

                machines = self.graph.get_entities_by_type("machine")
                if machines:
                    self.graph.find_or_create_relationship(
                        RelationshipType.RUNS_ON, service.id, machines[0].id,
                        "service", "machine", evidence_source=self.name
                    )

        self._build_dependencies()

    def _get_services(self):
        return self._wmi.get_services()

    def _build_dependencies(self):
        if not _win32_available:
            return
        try:
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        except Exception:
            return

        for svc_name, entity_id in self._known_services.items():
            try:
                handle = win32service.OpenService(scm, svc_name, win32service.SERVICE_QUERY_CONFIG)
                config = win32service.QueryServiceConfig(handle)
                deps = config[6] if config[6] else []
                if isinstance(deps, str):
                    deps = [d for d in deps.split('\0') if d]

                dep_names = []
                for dep in deps:
                    dep_name = dep.lstrip('+')
                    dep_names.append(dep_name)
                    if dep_name in self._known_services:
                        self.graph.find_or_create_relationship(
                            RelationshipType.DEPENDS_ON, entity_id, self._known_services[dep_name],
                            "service", "service", evidence_source=self.name
                        )

                self.graph.update_entity(entity_id, dependencies=dep_names)
                win32service.CloseServiceHandle(handle)
            except Exception:
                continue

        try:
            win32service.CloseServiceHandle(scm)
        except Exception:
            pass

    def get_service_by_name(self, service_name):
        entity_id = self._known_services.get(service_name)
        if entity_id:
            return self.graph.get_entity(entity_id)
        return None

    def get_service_dependencies(self, service_name):
        entity_id = self._known_services.get(service_name)
        if not entity_id:
            return {"dependencies": [], "dependents": []}
        deps = self.graph.get_outgoing(entity_id, RelationshipType.DEPENDS_ON)
        dependents = self.graph.get_incoming(entity_id, RelationshipType.DEPENDS_ON)
        return {
            "dependencies": [self.graph.get_entity(r.target_id) for r in deps],
            "dependents": [self.graph.get_entity(r.source_id) for r in dependents],
        }
