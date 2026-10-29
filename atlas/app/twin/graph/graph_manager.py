import threading
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from atlas.app.twin.entities.base import Entity, EntityState
from atlas.app.twin.relationships.relationship import Relationship, RelationshipType, ConfidenceLevel

logger = logging.getLogger("atlas.graph")


class GraphManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._outgoing: Dict[str, Dict[str, Relationship]] = defaultdict(dict)
        self._incoming: Dict[str, Dict[str, Relationship]] = defaultdict(dict)
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._name_index: Dict[str, Set[str]] = {}

    def add_entity(self, entity: Entity) -> bool:
        with self._lock:
            if entity.id in self._entities:
                return False
            self._entities[entity.id] = entity
            self._type_index[entity.entity_type].add(entity.id)
            name_lower = entity.name.lower()
            if name_lower not in self._name_index:
                self._name_index[name_lower] = set()
            self._name_index[name_lower].add(entity.id)
            return True

    def update_entity(self, entity_id: str, **kwargs) -> bool:
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                return False
            old_name = entity.name.lower()
            changed = entity.update(**kwargs)
            if changed:
                new_name = entity.name.lower()
                if old_name != new_name:
                    if old_name in self._name_index:
                        self._name_index[old_name].discard(entity_id)
                    if new_name not in self._name_index:
                        self._name_index[new_name] = set()
                    self._name_index[new_name].add(entity_id)
            return changed

    def remove_entity(self, entity_id: str) -> Optional[Entity]:
        with self._lock:
            entity = self._entities.pop(entity_id, None)
            if entity is None:
                return None
            self._type_index[entity.entity_type].discard(entity_id)
            name_lower = entity.name.lower()
            if name_lower in self._name_index:
                self._name_index[name_lower].discard(entity_id)
            rel_ids_to_remove = []
            for rel_id in list(self._outgoing.get(entity_id, {}).keys()):
                rel_ids_to_remove.append(rel_id)
            for rel_id in list(self._incoming.get(entity_id, {}).keys()):
                rel_ids_to_remove.append(rel_id)
            for rel_id in set(rel_ids_to_remove):
                self._remove_relationship_internal(rel_id)
            return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with self._lock:
            return self._entities.get(entity_id)

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        with self._lock:
            ids = self._type_index.get(entity_type, set())
            return [self._entities[eid] for eid in ids if eid in self._entities]

    def get_entities_by_name(self, name: str) -> List[Entity]:
        with self._lock:
            ids = self._name_index.get(name.lower(), set())
            return [self._entities[eid] for eid in ids if eid in self._entities]

    def find_entity(self, entity_type: str = None, **properties) -> List[Entity]:
        with self._lock:
            candidates = self._entities.values()
            if entity_type:
                ids = self._type_index.get(entity_type, set())
                candidates = [self._entities[eid] for eid in ids if eid in self._entities]
            results = []
            for entity in candidates:
                match = True
                for key, value in properties.items():
                    if entity.properties.get(key) != value:
                        match = False
                        break
                if match:
                    results.append(entity)
            return results

    def add_relationship(self, relationship: Relationship) -> bool:
        with self._lock:
            if relationship.id in self._relationships:
                return False
            if relationship.source_id not in self._entities:
                return False
            if relationship.target_id not in self._entities:
                return False
            self._relationships[relationship.id] = relationship
            self._outgoing[relationship.source_id][relationship.id] = relationship
            self._incoming[relationship.target_id][relationship.id] = relationship
            return True

    def remove_relationship(self, relationship_id: str) -> Optional[Relationship]:
        with self._lock:
            return self._remove_relationship_internal(relationship_id)

    def _remove_relationship_internal(self, relationship_id: str) -> Optional[Relationship]:
        rel = self._relationships.pop(relationship_id, None)
        if rel is None:
            return None
        if rel.source_id in self._outgoing:
            self._outgoing[rel.source_id].pop(relationship_id, None)
        if rel.target_id in self._incoming:
            self._incoming[rel.target_id].pop(relationship_id, None)
        return rel

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        with self._lock:
            return self._relationships.get(relationship_id)

    def get_outgoing(self, entity_id: str, rel_type: RelationshipType = None) -> List[Relationship]:
        with self._lock:
            rels = list(self._outgoing.get(entity_id, {}).values())
            if rel_type:
                rels = [r for r in rels if r.relationship_type == rel_type]
            return rels

    def get_incoming(self, entity_id: str, rel_type: RelationshipType = None) -> List[Relationship]:
        with self._lock:
            rels = list(self._incoming.get(entity_id, {}).values())
            if rel_type:
                rels = [r for r in rels if r.relationship_type == rel_type]
            return rels

    def get_neighbors(self, entity_id: str, rel_type: RelationshipType = None,
                      direction: str = "both") -> List[Tuple[Entity, Relationship]]:
        with self._lock:
            results = []
            if direction in ("both", "outgoing"):
                for rel in self.get_outgoing(entity_id, rel_type):
                    target = self._entities.get(rel.target_id)
                    if target:
                        results.append((target, rel))
            if direction in ("both", "incoming"):
                for rel in self.get_incoming(entity_id, rel_type):
                    source = self._entities.get(rel.source_id)
                    if source:
                        results.append((source, rel))
            return results

    def get_subgraph(self, entity_id: str, max_depth: int = 3) -> Tuple[Dict[str, Entity], List[Relationship]]:
        with self._lock:
            visited = set()
            entities = {}
            relationships = []
            queue = [(entity_id, 0)]
            while queue:
                current_id, depth = queue.pop(0)
                if current_id in visited or depth > max_depth:
                    continue
                visited.add(current_id)
                entity = self._entities.get(current_id)
                if entity:
                    entities[current_id] = entity
                if depth < max_depth:
                    for rel in self.get_outgoing(current_id):
                        relationships.append(rel)
                        if rel.target_id not in visited:
                            queue.append((rel.target_id, depth + 1))
                    for rel in self.get_incoming(current_id):
                        relationships.append(rel)
                        if rel.source_id not in visited:
                            queue.append((rel.source_id, depth + 1))
            return entities, relationships

    def find_path(self, source_id: str, target_id: str, max_depth: int = 10) -> Optional[List[Tuple[str, Relationship]]]:
        with self._lock:
            if source_id not in self._entities or target_id not in self._entities:
                return None
            visited = set()
            queue = [(source_id, [])]
            while queue:
                current, path = queue.pop(0)
                if current == target_id:
                    return path
                if current in visited or len(path) >= max_depth:
                    continue
                visited.add(current)
                for rel in self.get_outgoing(current):
                    if rel.target_id not in visited:
                        queue.append((rel.target_id, path + [(rel.target_id, rel)]))
                for rel in self.get_incoming(current):
                    if rel.source_id not in visited:
                        queue.append((rel.source_id, path + [(rel.source_id, rel)]))
            return None

    def get_impact_graph(self, entity_id: str, max_depth: int = 5) -> Dict:
        with self._lock:
            impact = {"entity_id": entity_id, "directly_affected": [], "indirectly_affected": [], "total_affected": 0}
            visited = set()
            queue = [(entity_id, 0)]
            while queue:
                current_id, depth = queue.pop(0)
                if current_id in visited or depth > max_depth:
                    continue
                visited.add(current_id)
                dependents = self.get_incoming(current_id, RelationshipType.DEPENDS_ON)
                children = self.get_incoming(current_id, RelationshipType.CHILD_OF)
                owned = self.get_outgoing(current_id, RelationshipType.OWNS)
                for rel in dependents + children + owned:
                    affected_id = rel.source_id if rel.source_id != current_id else rel.target_id
                    if affected_id not in visited:
                        affected = self._entities.get(affected_id)
                        if affected:
                            entry = {
                                "entity": affected.to_dict(),
                                "relationship": rel.relationship_type.value,
                                "confidence": rel.confidence.value,
                                "depth": depth + 1,
                            }
                            if depth == 0:
                                impact["directly_affected"].append(entry)
                            else:
                                impact["indirectly_affected"].append(entry)
                            queue.append((affected_id, depth + 1))
            impact["total_affected"] = len(impact["directly_affected"]) + len(impact["indirectly_affected"])
            return impact

    def search(self, query: str, entity_type: str = None, limit: int = 50) -> List[Entity]:
        with self._lock:
            query_lower = query.lower()
            results = []
            candidates = self._entities.values()
            if entity_type:
                ids = self._type_index.get(entity_type, set())
                candidates = [self._entities[eid] for eid in ids if eid in self._entities]
            for entity in candidates:
                if query_lower in entity.name.lower():
                    results.append(entity)
                    continue
                for val in entity.properties.values():
                    if isinstance(val, str) and query_lower in val.lower():
                        results.append(entity)
                        break
                if len(results) >= limit:
                    break
            return results[:limit]

    @property
    def entity_count(self):
        return len(self._entities)

    @property
    def relationship_count(self):
        return len(self._relationships)

    def get_stats(self):
        with self._lock:
            type_counts = {t: len(ids) for t, ids in self._type_index.items() if ids}
            return {
                "entity_count": self.entity_count,
                "relationship_count": self.relationship_count,
                "total_entities": self.entity_count,
                "total_relationships": self.relationship_count,
                "entity_types": type_counts,
                "active_entities": sum(
                    1 for e in self._entities.values() if e.state == EntityState.ACTIVE
                ),
            }

    def clear(self):
        with self._lock:
            self._entities.clear()
            self._relationships.clear()
            self._outgoing.clear()
            self._incoming.clear()
            self._type_index.clear()
            self._name_index.clear()

    def get_all_entities(self) -> List[Entity]:
        with self._lock:
            return list(self._entities.values())

    def get_all_relationships(self) -> List[Relationship]:
        with self._lock:
            return list(self._relationships.values())

    def find_or_create_relationship(self, rel_type, source_id, target_id,
                                     source_type="", target_type="",
                                     confidence=ConfidenceLevel.CONFIRMED,
                                     evidence_source="") -> Relationship:
        with self._lock:
            for rel in self._outgoing.get(source_id, {}).values():
                if (rel.relationship_type == rel_type and
                    rel.target_id == target_id):
                    rel.updated_at = datetime.now().isoformat()
                    return rel
            rel = Relationship(
                relationship_type=rel_type,
                source_id=source_id,
                target_id=target_id,
                source_type=source_type,
                target_type=target_type,
                confidence=confidence,
                evidence_source=evidence_source,
            )
            self.add_relationship(rel)
            return rel
