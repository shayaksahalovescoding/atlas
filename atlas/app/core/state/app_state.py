import enum
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("atlas.state")


class SubsystemStatus(enum.Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"
    STOPPED = "stopped"


class SystemHealth(enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AppState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.subsystems: Dict[str, SubsystemStatus] = {}
        self.subsystem_errors: Dict[str, str] = {}
        self.ollama_connected = False
        self.ollama_model = ""
        self.monitoring_active = False
        self.twin_entity_count = 0
        self.twin_relationship_count = 0
        self.twin_event_count = 0
        self.active_anomaly_count = 0
        self.active_incident_count = 0
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.gpu_usage = 0.0
        self.disk_usage = 0.0
        self.network_bytes_sent = 0
        self.network_bytes_recv = 0
        self.uptime_seconds = 0
        self.boot_time = None
        self.started_at = datetime.now().isoformat()
        self.last_snapshot = None
        self.last_reconciliation = None

    def set_subsystem_status(self, name: str, status: SubsystemStatus, error: str = None):
        self.subsystems[name] = status
        if error:
            self.subsystem_errors[name] = error
        elif name in self.subsystem_errors:
            del self.subsystem_errors[name]

    def get_overall_health(self) -> SystemHealth:
        if not self.subsystems:
            return SystemHealth.UNKNOWN
        statuses = list(self.subsystems.values())
        if any(s == SubsystemStatus.ERROR for s in statuses):
            critical_systems = {"process_collector", "metrics_engine", "storage"}
            error_systems = {k for k, v in self.subsystems.items() if v == SubsystemStatus.ERROR}
            if error_systems & critical_systems:
                return SystemHealth.CRITICAL
            return SystemHealth.WARNING
        if any(s == SubsystemStatus.DEGRADED for s in statuses):
            return SystemHealth.WARNING
        if all(s == SubsystemStatus.RUNNING for s in statuses):
            return SystemHealth.HEALTHY
        return SystemHealth.UNKNOWN

    def to_dict(self):
        return {
            "health": self.get_overall_health().value,
            "subsystems": {k: v.value for k, v in self.subsystems.items()},
            "errors": dict(self.subsystem_errors),
            "ollama_connected": self.ollama_connected,
            "ollama_model": self.ollama_model,
            "monitoring_active": self.monitoring_active,
            "twin": {
                "entities": self.twin_entity_count,
                "relationships": self.twin_relationship_count,
                "events": self.twin_event_count,
            },
            "anomalies": self.active_anomaly_count,
            "incidents": self.active_incident_count,
            "resources": {
                "cpu": self.cpu_usage,
                "memory": self.memory_usage,
                "gpu": self.gpu_usage,
                "disk": self.disk_usage,
            },
            "started_at": self.started_at,
            "last_snapshot": self.last_snapshot,
        }

    @classmethod
    def reset(cls):
        cls._instance = None
