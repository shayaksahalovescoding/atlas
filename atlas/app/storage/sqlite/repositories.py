import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from atlas.app.twin.entities.base import Entity, EntityState
from atlas.app.twin.relationships.relationship import Relationship, RelationshipType, ConfidenceLevel
from atlas.app.storage.sqlite.database import Database

logger = logging.getLogger("atlas.storage.repos")


class EntityRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, entity: Entity):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO entities
                   (id, entity_type, name, state, created_at, updated_at, first_seen, last_seen, source, properties)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entity.id, entity.entity_type, entity.name, entity.state.value,
                 entity.created_at, entity.updated_at, entity.first_seen, entity.last_seen,
                 entity.source, json.dumps(entity.properties))
            )
        entity.mark_clean()

    def save_batch(self, entities: List[Entity]):
        params = [
            (e.id, e.entity_type, e.name, e.state.value,
             e.created_at, e.updated_at, e.first_seen, e.last_seen,
             e.source, json.dumps(e.properties))
            for e in entities
        ]
        self._db.executemany(
            """INSERT OR REPLACE INTO entities
               (id, entity_type, name, state, created_at, updated_at, first_seen, last_seen, source, properties)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            params
        )
        for e in entities:
            e.mark_clean()

    def get(self, entity_id: str) -> Optional[Entity]:
        row = self._db.fetchone("SELECT * FROM entities WHERE id = ?", (entity_id,))
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_by_type(self, entity_type: str, state: str = None) -> List[Entity]:
        if state:
            rows = self._db.fetchall(
                "SELECT * FROM entities WHERE entity_type = ? AND state = ?",
                (entity_type, state)
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM entities WHERE entity_type = ?",
                (entity_type,)
            )
        return [self._row_to_entity(r) for r in rows]

    def search(self, query: str, entity_type: str = None, limit: int = 50) -> List[Entity]:
        pattern = f"%{query}%"
        if entity_type:
            rows = self._db.fetchall(
                "SELECT * FROM entities WHERE entity_type = ? AND (name LIKE ? OR properties LIKE ?) LIMIT ?",
                (entity_type, pattern, pattern, limit)
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM entities WHERE name LIKE ? OR properties LIKE ? LIMIT ?",
                (pattern, pattern, limit)
            )
        return [self._row_to_entity(r) for r in rows]

    def delete(self, entity_id: str):
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))

    def count(self, entity_type: str = None) -> int:
        if entity_type:
            row = self._db.fetchone(
                "SELECT COUNT(*) as cnt FROM entities WHERE entity_type = ?", (entity_type,)
            )
        else:
            row = self._db.fetchone("SELECT COUNT(*) as cnt FROM entities")
        return row["cnt"] if row else 0

    def _row_to_entity(self, row) -> Entity:
        entity = Entity(
            entity_type=row["entity_type"],
            name=row["name"],
            entity_id=row["id"],
            source=row["source"],
        )
        entity.state = EntityState(row["state"])
        entity.created_at = row["created_at"]
        entity.updated_at = row["updated_at"]
        entity.first_seen = row["first_seen"]
        entity.last_seen = row["last_seen"]
        entity.properties = json.loads(row["properties"]) if row["properties"] else {}
        entity._dirty = False
        return entity


class RelationshipRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, rel: Relationship):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO relationships
                   (id, relationship_type, source_id, target_id, source_type, target_type,
                    confidence, confidence_score, created_at, updated_at, evidence_source, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rel.id, rel.relationship_type.value, rel.source_id, rel.target_id,
                 rel.source_type, rel.target_type, rel.confidence.value,
                 rel.confidence_score, rel.created_at, rel.updated_at,
                 rel.evidence_source, json.dumps(rel.metadata))
            )

    def save_batch(self, relationships: List[Relationship]):
        params = [
            (r.id, r.relationship_type.value, r.source_id, r.target_id,
             r.source_type, r.target_type, r.confidence.value,
             r.confidence_score, r.created_at, r.updated_at,
             r.evidence_source, json.dumps(r.metadata))
            for r in relationships
        ]
        self._db.executemany(
            """INSERT OR REPLACE INTO relationships
               (id, relationship_type, source_id, target_id, source_type, target_type,
                confidence, confidence_score, created_at, updated_at, evidence_source, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            params
        )

    def get_by_source(self, source_id: str) -> List[Relationship]:
        rows = self._db.fetchall(
            "SELECT * FROM relationships WHERE source_id = ?", (source_id,)
        )
        return [self._row_to_rel(r) for r in rows]

    def get_by_target(self, target_id: str) -> List[Relationship]:
        rows = self._db.fetchall(
            "SELECT * FROM relationships WHERE target_id = ?", (target_id,)
        )
        return [self._row_to_rel(r) for r in rows]

    def delete(self, relationship_id: str):
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))

    def count(self) -> int:
        row = self._db.fetchone("SELECT COUNT(*) as cnt FROM relationships")
        return row["cnt"] if row else 0

    def _row_to_rel(self, row) -> Relationship:
        rel = Relationship(
            relationship_type=RelationshipType(row["relationship_type"]),
            source_id=row["source_id"],
            target_id=row["target_id"],
            source_type=row["source_type"],
            target_type=row["target_type"],
            confidence=ConfidenceLevel(row["confidence"]),
            confidence_score=row["confidence_score"],
            evidence_source=row["evidence_source"],
            relationship_id=row["id"],
        )
        rel.created_at = row["created_at"]
        rel.updated_at = row["updated_at"]
        rel.metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        return rel


class EventRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, event_type, timestamp, source, entity_id=None, entity_type=None,
             metadata=None, priority=1):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT INTO events (event_type, timestamp, source, entity_id, entity_type, metadata, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_type, timestamp, source, entity_id, entity_type,
                 json.dumps(metadata or {}), priority)
            )

    def save_batch(self, events):
        params = [
            (e.get("event_type", ""), e.get("timestamp", ""), e.get("source", ""),
             e.get("entity_id"), e.get("entity_type"),
             json.dumps(e.get("metadata", {})), e.get("priority", 1))
            for e in events
        ]
        self._db.executemany(
            """INSERT INTO events (event_type, timestamp, source, entity_id, entity_type, metadata, priority)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            params
        )

    def get_recent(self, count=100, event_type=None, since=None) -> List[Dict]:
        sql = "SELECT * FROM events"
        params = []
        conditions = []
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(count)
        rows = self._db.fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_by_entity(self, entity_id: str, limit: int = 100) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT * FROM events WHERE entity_id = ? ORDER BY timestamp DESC LIMIT ?",
            (entity_id, limit)
        )
        return [dict(r) for r in rows]

    def count(self, since=None) -> int:
        if since:
            row = self._db.fetchone(
                "SELECT COUNT(*) as cnt FROM events WHERE timestamp >= ?", (since,)
            )
        else:
            row = self._db.fetchone("SELECT COUNT(*) as cnt FROM events")
        return row["cnt"] if row else 0


class MetricRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, metric_name, value, timestamp, unit="", target_entity_id="",
             target_entity_type="", tags=None):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT INTO metrics (metric_name, value, unit, target_entity_id,
                   target_entity_type, timestamp, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (metric_name, value, unit, target_entity_id, target_entity_type,
                 timestamp, json.dumps(tags or {}))
            )

    def save_batch(self, metrics):
        params = [
            (m["metric_name"], m["value"], m.get("unit", ""),
             m.get("target_entity_id", ""), m.get("target_entity_type", ""),
             m["timestamp"], json.dumps(m.get("tags", {})))
            for m in metrics
        ]
        self._db.executemany(
            """INSERT INTO metrics (metric_name, value, unit, target_entity_id,
               target_entity_type, timestamp, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            params
        )

    def get_history(self, metric_name, since=None, until=None, entity_id=None,
                    limit=1000) -> List[Dict]:
        sql = "SELECT * FROM metrics WHERE metric_name = ?"
        params = [metric_name]
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        if until:
            sql += " AND timestamp <= ?"
            params.append(until)
        if entity_id:
            sql += " AND target_entity_id = ?"
            params.append(entity_id)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self._db.fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_latest(self, metric_name, entity_id=None) -> Optional[Dict]:
        if entity_id:
            row = self._db.fetchone(
                "SELECT * FROM metrics WHERE metric_name = ? AND target_entity_id = ? ORDER BY timestamp DESC LIMIT 1",
                (metric_name, entity_id)
            )
        else:
            row = self._db.fetchone(
                "SELECT * FROM metrics WHERE metric_name = ? ORDER BY timestamp DESC LIMIT 1",
                (metric_name,)
            )
        return dict(row) if row else None

    def get_aggregate(self, metric_name, since, until=None, entity_id=None) -> Dict:
        sql = "SELECT AVG(value) as avg_val, MIN(value) as min_val, MAX(value) as max_val, COUNT(*) as cnt FROM metrics WHERE metric_name = ? AND timestamp >= ?"
        params = [metric_name, since]
        if until:
            sql += " AND timestamp <= ?"
            params.append(until)
        if entity_id:
            sql += " AND target_entity_id = ?"
            params.append(entity_id)
        row = self._db.fetchone(sql, tuple(params))
        if row:
            return {"avg": row["avg_val"], "min": row["min_val"], "max": row["max_val"], "count": row["cnt"]}
        return {"avg": 0, "min": 0, "max": 0, "count": 0}


class SnapshotRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, snapshot_id, snapshot_time, trigger, entity_count,
             relationship_count, data):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO snapshots
                   (id, snapshot_time, trigger, entity_count, relationship_count, data)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (snapshot_id, snapshot_time, trigger, entity_count,
                 relationship_count, json.dumps(data))
            )

    def get(self, snapshot_id) -> Optional[Dict]:
        row = self._db.fetchone("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,))
        if row:
            result = dict(row)
            result["data"] = json.loads(result["data"]) if result["data"] else {}
            return result
        return None

    def get_recent(self, count=10) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT id, snapshot_time, trigger, entity_count, relationship_count FROM snapshots ORDER BY snapshot_time DESC LIMIT ?",
            (count,)
        )
        return [dict(r) for r in rows]

    def get_closest(self, timestamp) -> Optional[Dict]:
        row = self._db.fetchone(
            "SELECT * FROM snapshots WHERE snapshot_time <= ? ORDER BY snapshot_time DESC LIMIT 1",
            (timestamp,)
        )
        if row:
            result = dict(row)
            result["data"] = json.loads(result["data"]) if result["data"] else {}
            return result
        return None


class IncidentRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, incident):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO incidents
                   (id, name, severity, status, incident_type, description,
                    started_at, resolved_at, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (incident.id, incident.name,
                 incident.properties.get("severity", "medium"),
                 incident.properties.get("status", "active"),
                 incident.properties.get("incident_type", ""),
                 incident.properties.get("description", ""),
                 incident.properties.get("started_at", incident.created_at),
                 incident.properties.get("resolved_at", ""),
                 json.dumps(incident.properties))
            )

    def get_active(self) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT * FROM incidents WHERE status IN ('active', 'investigating') ORDER BY started_at DESC"
        )
        return [self._parse_row(r) for r in rows]

    def get_recent(self, count=20) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT * FROM incidents ORDER BY started_at DESC LIMIT ?", (count,)
        )
        return [self._parse_row(r) for r in rows]

    def _parse_row(self, row) -> Dict:
        result = dict(row)
        result["data"] = json.loads(result["data"]) if result["data"] else {}
        return result


class AnomalyRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, anomaly):
        with self._db.transaction() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO anomalies
                   (id, anomaly_type, severity, score, description,
                    affected_entity_id, detected_at, resolved_at, is_active, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (anomaly.id, anomaly.properties.get("anomaly_type", ""),
                 anomaly.properties.get("severity", "low"),
                 anomaly.properties.get("score", 0.0),
                 anomaly.properties.get("description", ""),
                 anomaly.properties.get("affected_entity_id", ""),
                 anomaly.properties.get("detected_at", anomaly.created_at),
                 anomaly.properties.get("resolved_at", ""),
                 1 if anomaly.properties.get("is_active", True) else 0,
                 json.dumps(anomaly.properties))
            )

    def get_active(self) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT * FROM anomalies WHERE is_active = 1 ORDER BY score DESC"
        )
        return [self._parse_row(r) for r in rows]

    def _parse_row(self, row) -> Dict:
        result = dict(row)
        result["data"] = json.loads(result["data"]) if result["data"] else {}
        return result
