SCHEMA_VERSION = 5

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    properties TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_state ON entities(state);
CREATE INDEX IF NOT EXISTS idx_entities_updated ON entities(updated_at);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    relationship_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    source_type TEXT DEFAULT '',
    target_type TEXT DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'confirmed',
    confidence_score REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    evidence_source TEXT DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_rel_source_type ON relationships(source_id, relationship_type);
CREATE INDEX IF NOT EXISTS idx_rel_target_type ON relationships(target_id, relationship_type);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    entity_id TEXT,
    entity_type TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_id);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT DEFAULT '',
    target_entity_id TEXT DEFAULT '',
    target_entity_type TEXT DEFAULT '',
    timestamp TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_entity ON metrics(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name_ts ON metrics(metric_name, timestamp);

CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    snapshot_time TEXT NOT NULL,
    trigger TEXT DEFAULT '',
    entity_count INTEGER DEFAULT 0,
    relationship_count INTEGER DEFAULT 0,
    data TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(snapshot_time);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'active',
    incident_type TEXT DEFAULT '',
    description TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    resolved_at TEXT DEFAULT '',
    data TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_started ON incidents(started_at);

CREATE TABLE IF NOT EXISTS anomalies (
    id TEXT PRIMARY KEY,
    anomaly_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'low',
    score REAL NOT NULL DEFAULT 0.0,
    description TEXT DEFAULT '',
    affected_entity_id TEXT DEFAULT '',
    detected_at TEXT NOT NULL,
    resolved_at TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    data TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_anomalies_active ON anomalies(is_active);
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_anomalies_entity ON anomalies(affected_entity_id);

CREATE TABLE IF NOT EXISTS config_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_type TEXT NOT NULL,
    category TEXT DEFAULT '',
    path TEXT DEFAULT '',
    old_value TEXT DEFAULT '',
    new_value TEXT DEFAULT '',
    detected_at TEXT NOT NULL,
    affected_entity_id TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_config_detected ON config_changes(detected_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'system',
    target TEXT DEFAULT '',
    details TEXT NOT NULL DEFAULT '{}',
    result TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
"""
