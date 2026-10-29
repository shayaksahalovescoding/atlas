import uuid
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional


class EntityState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"
    ERROR = "error"


class Entity:
    __slots__ = (
        "id", "entity_type", "name", "state", "created_at", "updated_at",
        "first_seen", "last_seen", "source", "properties", "_dirty"
    )

    def __init__(self, entity_type, name, entity_id=None, source="unknown"):
        self.id = entity_id or str(uuid.uuid4())
        self.entity_type = entity_type
        self.name = name
        self.state = EntityState.ACTIVE
        now = datetime.now().isoformat()
        self.created_at = now
        self.updated_at = now
        self.first_seen = now
        self.last_seen = now
        self.source = source
        self.properties = {}
        self._dirty = True

    def update(self, **kwargs):
        changed = False
        for k, v in kwargs.items():
            if k in self.__slots__ and k not in ("id", "entity_type", "created_at", "first_seen"):
                old = getattr(self, k, None)
                if old != v:
                    setattr(self, k, v)
                    changed = True
            else:
                old = self.properties.get(k)
                if old != v:
                    self.properties[k] = v
                    changed = True
        if changed:
            self.updated_at = datetime.now().isoformat()
            self.last_seen = self.updated_at
            self._dirty = True
        return changed

    def touch(self):
        self.last_seen = datetime.now().isoformat()

    def mark_clean(self):
        self._dirty = False

    @property
    def is_dirty(self):
        return self._dirty

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "name": self.name,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "source": self.source,
            "properties": dict(self.properties),
        }

    @classmethod
    def from_dict(cls, data):
        entity = cls(
            entity_type=data["entity_type"],
            name=data["name"],
            entity_id=data["id"],
            source=data.get("source", "unknown"),
        )
        entity.state = EntityState(data.get("state", "active"))
        entity.created_at = data.get("created_at", entity.created_at)
        entity.updated_at = data.get("updated_at", entity.updated_at)
        entity.first_seen = data.get("first_seen", entity.first_seen)
        entity.last_seen = data.get("last_seen", entity.last_seen)
        entity.properties = data.get("properties", {})
        entity._dirty = False
        return entity

    def __repr__(self):
        return f"{self.entity_type}({self.name}, id={self.id[:8]})"

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)
