import enum


class EventType(enum.Enum):
    PROCESS_STARTED = "process_started"
    PROCESS_STOPPED = "process_stopped"
    PROCESS_UPDATED = "process_updated"
    APPLICATION_OPENED = "application_opened"
    APPLICATION_CLOSED = "application_closed"
    APPLICATION_INSTALLED = "application_installed"
    APPLICATION_UNINSTALLED = "application_uninstalled"
    APPLICATION_UPDATED = "application_updated"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    SERVICE_STATE_CHANGED = "service_state_changed"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_RENAMED = "file_renamed"
    NETWORK_CHANGED = "network_changed"
    NETWORK_CONNECTION_OPENED = "network_connection_opened"
    NETWORK_CONNECTION_CLOSED = "network_connection_closed"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_REMOVED = "device_removed"
    CRASH_DETECTED = "crash_detected"
    RESOURCE_ANOMALY = "resource_anomaly"
    BOOT_COMPLETED = "boot_completed"
    CONFIGURATION_CHANGED = "configuration_changed"
    UPDATE_DETECTED = "update_detected"
    STARTUP_CHANGED = "startup_changed"
    DRIVER_CHANGED = "driver_changed"
    METRIC_COLLECTED = "metric_collected"
    SNAPSHOT_CREATED = "snapshot_created"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_RESOLVED = "incident_resolved"
    ANOMALY_DETECTED = "anomaly_detected"
    ANOMALY_RESOLVED = "anomaly_resolved"
    TWIN_ENTITY_ADDED = "twin_entity_added"
    TWIN_ENTITY_UPDATED = "twin_entity_updated"
    TWIN_ENTITY_REMOVED = "twin_entity_removed"
    TWIN_RELATIONSHIP_ADDED = "twin_relationship_added"
    TWIN_RELATIONSHIP_REMOVED = "twin_relationship_removed"
    SYSTEM_HEALTH_CHANGED = "system_health_changed"
    COLLECTOR_ERROR = "collector_error"
    COLLECTOR_RECOVERED = "collector_recovered"
    AI_QUERY_STARTED = "ai_query_started"
    AI_QUERY_COMPLETED = "ai_query_completed"
    AI_QUERY_FAILED = "ai_query_failed"


class EventPriority(enum.IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Event:
    __slots__ = (
        "event_type", "timestamp", "source", "entity_id",
        "entity_type", "metadata", "priority", "event_id"
    )

    _counter = 0

    def __init__(self, event_type, timestamp, source, entity_id=None,
                 entity_type=None, metadata=None, priority=EventPriority.NORMAL):
        Event._counter += 1
        self.event_id = Event._counter
        self.event_type = event_type
        self.timestamp = timestamp
        self.source = source
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.metadata = metadata or {}
        self.priority = priority

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "timestamp": self.timestamp,
            "source": self.source,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "metadata": self.metadata,
            "priority": self.priority.value if isinstance(self.priority, EventPriority) else self.priority,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            event_type=EventType(data["event_type"]) if isinstance(data.get("event_type"), str) else data.get("event_type"),
            timestamp=data.get("timestamp"),
            source=data.get("source"),
            entity_id=data.get("entity_id"),
            entity_type=data.get("entity_type"),
            metadata=data.get("metadata", {}),
            priority=EventPriority(data["priority"]) if isinstance(data.get("priority"), int) else EventPriority.NORMAL,
        )

    def __repr__(self):
        return f"Event({self.event_type.value}, entity={self.entity_id}, src={self.source})"
