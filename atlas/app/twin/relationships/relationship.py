import enum
import uuid
from datetime import datetime
from typing import Optional


class RelationshipType(enum.Enum):
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    BELONGS_TO = "belongs_to"
    CONTAINS = "contains"
    USES = "uses"
    USED_BY = "used_by"
    DEPENDS_ON = "depends_on"
    DEPENDED_BY = "depended_by"
    OWNS = "owns"
    OWNED_BY = "owned_by"
    SUPPORTS = "supports"
    SUPPORTED_BY = "supported_by"
    RUNS_ON = "runs_on"
    HOSTS = "hosts"
    COMMUNICATES_WITH = "communicates_with"
    LOADS = "loads"
    LOADED_BY = "loaded_by"
    INSTALLED_ON = "installed_on"
    PART_OF = "part_of"
    HAS_PART = "has_part"
    MONITORS = "monitors"
    TRIGGERS = "triggers"
    CAUSED_BY = "caused_by"
    RELATED_TO = "related_to"
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"
    CONNECTED_TO = "connected_to"
    INSTANCE_OF = "instance_of"


class ConfidenceLevel(enum.Enum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


class Relationship:
    __slots__ = (
        "id", "relationship_type", "source_id", "target_id",
        "source_type", "target_type", "confidence", "confidence_score",
        "created_at", "updated_at", "evidence_source", "metadata"
    )

    def __init__(self, relationship_type, source_id, target_id,
                 source_type="", target_type="",
                 confidence=ConfidenceLevel.CONFIRMED,
                 confidence_score=1.0,
                 evidence_source="",
                 relationship_id=None):
        self.id = relationship_id or str(uuid.uuid4())
        self.relationship_type = relationship_type
        self.source_id = source_id
        self.target_id = target_id
        self.source_type = source_type
        self.target_type = target_type
        self.confidence = confidence
        self.confidence_score = confidence_score
        now = datetime.now().isoformat()
        self.created_at = now
        self.updated_at = now
        self.evidence_source = evidence_source
        self.metadata = {}

    def to_dict(self):
        return {
            "id": self.id,
            "relationship_type": self.relationship_type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "evidence_source": self.evidence_source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data):
        rel = cls(
            relationship_type=RelationshipType(data["relationship_type"]),
            source_id=data["source_id"],
            target_id=data["target_id"],
            source_type=data.get("source_type", ""),
            target_type=data.get("target_type", ""),
            confidence=ConfidenceLevel(data.get("confidence", "confirmed")),
            confidence_score=data.get("confidence_score", 1.0),
            evidence_source=data.get("evidence_source", ""),
            relationship_id=data.get("id"),
        )
        rel.created_at = data.get("created_at", rel.created_at)
        rel.updated_at = data.get("updated_at", rel.updated_at)
        rel.metadata = data.get("metadata", {})
        return rel

    def __repr__(self):
        return f"Rel({self.source_id[:8]}-[{self.relationship_type.value}]->{self.target_id[:8]})"

    def __eq__(self, other):
        if isinstance(other, Relationship):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)
