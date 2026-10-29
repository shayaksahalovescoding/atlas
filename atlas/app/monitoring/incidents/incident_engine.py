import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from atlas.app.core.events.event_bus import EventBus
from atlas.app.core.events.event_types import Event, EventType, EventPriority
from atlas.app.twin.entities.monitoring import Incident, IncidentSeverity, IncidentStatus, Anomaly
from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.monitoring.metrics.metrics_engine import MetricsEngine
from atlas.app.storage.sqlite.repositories import IncidentRepository

logger = logging.getLogger("atlas.monitoring.incidents")


class IncidentEngine:
    def __init__(self, event_bus: EventBus, graph: GraphManager,
                 metrics: MetricsEngine, incident_repo: IncidentRepository = None):
        self._event_bus = event_bus
        self._graph = graph
        self._metrics = metrics
        self._incident_repo = incident_repo
        self._active_incidents: Dict[str, Incident] = {}
        self._incident_count = 0

        self._event_bus.subscribe(EventType.ANOMALY_DETECTED, self._on_anomaly)
        self._event_bus.subscribe(EventType.CRASH_DETECTED, self._on_crash)

    async def _on_anomaly(self, event: Event):
        score = event.metadata.get("score", 0)
        if score < 0.5:
            return

        anomaly_type = event.metadata.get("type", "")
        description = event.metadata.get("description", "")
        anomaly_key = f"anomaly_{anomaly_type}"

        if anomaly_key in self._active_incidents:
            incident = self._active_incidents[anomaly_key]
            timeline = incident.properties.get("timeline", [])
            timeline.append({
                "timestamp": event.timestamp,
                "event": "anomaly_update",
                "details": description,
                "score": score,
            })
            incident.update(timeline=timeline, occurrence_count=incident.properties.get("occurrence_count", 1) + 1)
            return

        self._create_incident(
            name=f"Anomaly: {description[:100]}",
            incident_type=anomaly_type,
            description=description,
            severity=IncidentSeverity.HIGH if score > 0.8 else IncidentSeverity.MEDIUM,
            key=anomaly_key,
            event=event,
        )

    async def _on_crash(self, event: Event):
        app_name = event.metadata.get("application", "")
        if not app_name or not str(app_name).strip() or str(app_name).strip().isdigit():
            desc = event.metadata.get("description", "")
            source = event.metadata.get("source", "")
            import re
            m = re.search(r'([a-zA-Z0-9_\-\.]+\.exe)', desc, re.IGNORECASE)
            if m:
                app_name = m.group(1)
            elif source and "reporting" not in source.lower():
                app_name = source
            else:
                app_name = "Unknown Application"
        crash_key = f"crash_{app_name}"

        if crash_key in self._active_incidents:
            incident = self._active_incidents[crash_key]
            timeline = incident.properties.get("timeline", [])
            timeline.append({
                "timestamp": event.timestamp,
                "event": "crash_repeat",
                "details": event.metadata.get("description", ""),
            })
            count = incident.properties.get("occurrence_count", 1) + 1
            incident.update(timeline=timeline, occurrence_count=count)
            if count >= 3:
                incident.update(severity=IncidentSeverity.HIGH.value)
            return

        self._create_incident(
            name=f"Application Crash: {app_name}",
            incident_type="crash",
            description=f"{app_name} crashed",
            severity=IncidentSeverity.MEDIUM,
            key=crash_key,
            event=event,
        )

    def _create_incident(self, name, incident_type, description, severity, key, event):
        current_metrics = self._metrics.get_current()
        context_before = {
            "metrics": current_metrics,
            "process_count": len(self._graph.get_entities_by_type("process")),
            "active_anomalies": len(self._graph.get_entities_by_type("anomaly")),
        }

        incident = Incident(name=name, source="incident_engine")
        incident.properties.update({
            "severity": severity.value,
            "status": IncidentStatus.ACTIVE.value,
            "incident_type": incident_type,
            "description": description,
            "started_at": event.timestamp,
            "context_before": context_before,
            "context_during": {"event": event.to_dict()},
            "timeline": [{
                "timestamp": event.timestamp,
                "event": "incident_created",
                "details": description,
            }],
            "affected_entity_ids": [event.entity_id] if event.entity_id else [],
            "occurrence_count": 1,
        })

        self._graph.add_entity(incident)
        self._active_incidents[key] = incident
        self._incident_count += 1

        if self._incident_repo:
            try:
                self._incident_repo.save(incident)
            except Exception as e:
                logger.error(f"Failed to save incident: {e}")

        self._event_bus.publish_sync(Event(
            event_type=EventType.INCIDENT_CREATED,
            timestamp=datetime.now().isoformat(),
            source="incident_engine",
            entity_id=incident.id,
            entity_type="incident",
            metadata={"name": name, "severity": severity.value},
            priority=EventPriority.HIGH,
        ))

        logger.warning(f"Incident created: {name} (severity: {severity.value})")

    def resolve_incident(self, key):
        incident = self._active_incidents.pop(key, None)
        if incident:
            now = datetime.now().isoformat()
            incident.update(
                status=IncidentStatus.RESOLVED.value,
                resolved_at=now,
            )
            timeline = incident.properties.get("timeline", [])
            timeline.append({"timestamp": now, "event": "resolved"})
            incident.update(timeline=timeline)

            context_after = {
                "metrics": self._metrics.get_current(),
                "process_count": len(self._graph.get_entities_by_type("process")),
            }
            incident.update(context_after=context_after)

            if self._incident_repo:
                self._incident_repo.save(incident)

    def get_active_incidents(self) -> List[Incident]:
        return list(self._active_incidents.values())

    def get_all_incidents(self) -> List[Incident]:
        incidents = list(self._active_incidents.values())
        if self._incident_repo:
            recent = self._incident_repo.get_recent(50)
            for data in recent:
                if not any(i.id == data["id"] for i in incidents):
                    inc = Incident(name=data["name"])
                    inc.id = data["id"]
                    inc.properties = data.get("data", {})
                    incidents.append(inc)
        return incidents

    def get_stats(self):
        return {
            "active": len(self._active_incidents),
            "total": self._incident_count,
        }
