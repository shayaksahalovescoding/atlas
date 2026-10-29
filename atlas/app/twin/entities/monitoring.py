import enum
from atlas.app.twin.entities.base import Entity


class IncidentSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(enum.Enum):
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AnomalyType(enum.Enum):
    CPU_SPIKE = "cpu_spike"
    MEMORY_LEAK = "memory_leak"
    MEMORY_PRESSURE = "memory_pressure"
    DISK_IO_SATURATION = "disk_io_saturation"
    DISK_SPACE_LOW = "disk_space_low"
    NETWORK_ANOMALY = "network_anomaly"
    PROCESS_CRASH = "process_crash"
    SERVICE_FAILURE = "service_failure"
    BOOT_DEGRADATION = "boot_degradation"
    RESOURCE_LEAK = "resource_leak"
    UNUSUAL_PROCESS = "unusual_process"
    REPEATED_CRASH = "repeated_crash"
    THERMAL_THROTTLE = "thermal_throttle"
    HIGH_HANDLE_COUNT = "high_handle_count"
    PROCESS_EXPLOSION = "process_explosion"


class MetricSample(Entity):
    def __init__(self, name="Metric", **kwargs):
        super().__init__("metric_sample", name, **kwargs)
        self.properties.setdefault("metric_name", "")
        self.properties.setdefault("value", 0.0)
        self.properties.setdefault("unit", "")
        self.properties.setdefault("target_entity_id", "")
        self.properties.setdefault("target_entity_type", "")
        self.properties.setdefault("timestamp", "")
        self.properties.setdefault("tags", {})


class Incident(Entity):
    def __init__(self, name="Incident", **kwargs):
        super().__init__("incident", name, **kwargs)
        self.properties.setdefault("severity", IncidentSeverity.MEDIUM.value)
        self.properties.setdefault("status", IncidentStatus.ACTIVE.value)
        self.properties.setdefault("incident_type", "")
        self.properties.setdefault("description", "")
        self.properties.setdefault("affected_entity_ids", [])
        self.properties.setdefault("affected_entity_types", [])
        self.properties.setdefault("timeline", [])
        self.properties.setdefault("context_before", {})
        self.properties.setdefault("context_during", {})
        self.properties.setdefault("context_after", {})
        self.properties.setdefault("started_at", "")
        self.properties.setdefault("resolved_at", "")
        self.properties.setdefault("duration_seconds", 0)
        self.properties.setdefault("related_incident_ids", [])
        self.properties.setdefault("hypotheses", [])
        self.properties.setdefault("root_cause", "")
        self.properties.setdefault("occurrence_count", 1)


class Anomaly(Entity):
    def __init__(self, name="Anomaly", **kwargs):
        super().__init__("anomaly", name, **kwargs)
        self.properties.setdefault("anomaly_type", "")
        self.properties.setdefault("severity", IncidentSeverity.LOW.value)
        self.properties.setdefault("score", 0.0)
        self.properties.setdefault("description", "")
        self.properties.setdefault("metric_name", "")
        self.properties.setdefault("current_value", 0.0)
        self.properties.setdefault("baseline_value", 0.0)
        self.properties.setdefault("deviation", 0.0)
        self.properties.setdefault("affected_entity_id", "")
        self.properties.setdefault("affected_entity_type", "")
        self.properties.setdefault("detected_at", "")
        self.properties.setdefault("resolved_at", "")
        self.properties.setdefault("is_active", True)
        self.properties.setdefault("evidence", [])
        self.properties.setdefault("promoted_to_incident", False)
        self.properties.setdefault("incident_id", "")


class ConfigurationChange(Entity):
    def __init__(self, name="Config Change", **kwargs):
        super().__init__("configuration_change", name, **kwargs)
        self.properties.setdefault("change_type", "")
        self.properties.setdefault("category", "")
        self.properties.setdefault("path", "")
        self.properties.setdefault("old_value", "")
        self.properties.setdefault("new_value", "")
        self.properties.setdefault("detected_at", "")
        self.properties.setdefault("affected_entity_id", "")


class BootSession(Entity):
    def __init__(self, name="Boot Session", **kwargs):
        super().__init__("boot_session", name, **kwargs)
        self.properties.setdefault("boot_time", "")
        self.properties.setdefault("boot_duration_seconds", 0)
        self.properties.setdefault("startup_app_count", 0)
        self.properties.setdefault("startup_service_count", 0)
        self.properties.setdefault("previous_shutdown_type", "")
        self.properties.setdefault("resource_peak_cpu", 0.0)
        self.properties.setdefault("resource_peak_memory", 0.0)
        self.properties.setdefault("slow_services", [])
        self.properties.setdefault("errors_during_boot", [])
        self.properties.setdefault("comparison_to_previous", {})


class Snapshot(Entity):
    def __init__(self, name="Snapshot", **kwargs):
        super().__init__("snapshot", name, **kwargs)
        self.properties.setdefault("snapshot_time", "")
        self.properties.setdefault("trigger", "")
        self.properties.setdefault("entity_count", 0)
        self.properties.setdefault("relationship_count", 0)
        self.properties.setdefault("hardware_state", {})
        self.properties.setdefault("software_inventory", {})
        self.properties.setdefault("process_state", {})
        self.properties.setdefault("service_state", {})
        self.properties.setdefault("resource_summary", {})
        self.properties.setdefault("active_anomalies", [])
        self.properties.setdefault("configuration_hash", "")
