import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.storage.sqlite.repositories import SnapshotRepository

logger = logging.getLogger("atlas.twin.snapshots")


class SnapshotEngine:
    def __init__(self, graph: GraphManager, snapshot_repo: SnapshotRepository = None):
        self._graph = graph
        self._snapshot_repo = snapshot_repo
        self._last_snapshot = None

    def create_snapshot(self, trigger="scheduled") -> Dict:
        now = datetime.now().isoformat()
        snapshot_id = str(uuid.uuid4())

        hardware = {}
        for etype in ["cpu", "gpu", "memory", "storage_device", "partition", "network_adapter", "battery"]:
            entities = self._graph.get_entities_by_type(etype)
            hardware[etype] = [e.to_dict() for e in entities]

        software = {}
        for etype in ["application", "service", "startup_entry"]:
            entities = self._graph.get_entities_by_type(etype)
            software[etype] = [{"id": e.id, "name": e.name, "properties": e.properties} for e in entities]

        processes = []
        for p in self._graph.get_entities_by_type("process"):
            processes.append({
                "name": p.name,
                "pid": p.properties.get("pid"),
                "cpu_percent": p.properties.get("cpu_percent", 0),
                "memory_bytes": p.properties.get("memory_bytes", 0),
            })

        services = []
        for s in self._graph.get_entities_by_type("service"):
            services.append({
                "name": s.name,
                "status": s.properties.get("status", ""),
                "startup_type": s.properties.get("startup_type", ""),
            })

        resource_summary = {}
        for etype in ["cpu", "memory"]:
            entities = self._graph.get_entities_by_type(etype)
            if entities:
                e = entities[0]
                resource_summary[etype] = {
                    "usage_percent": e.properties.get("usage_percent", 0),
                }

        partitions = self._graph.get_entities_by_type("partition")
        for part in partitions:
            mount = part.properties.get("mount_point", "")
            resource_summary[f"disk_{mount}"] = {
                "usage_percent": part.properties.get("usage_percent", 0),
                "free_bytes": part.properties.get("free_bytes", 0),
            }

        data = {
            "hardware": hardware,
            "software": software,
            "processes": processes[:100],
            "services": services,
            "resource_summary": resource_summary,
            "anomalies": [a.to_dict() for a in self._graph.get_entities_by_type("anomaly")],
        }

        config_str = json.dumps(software, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()

        snapshot = {
            "id": snapshot_id,
            "snapshot_time": now,
            "trigger": trigger,
            "entity_count": self._graph.entity_count,
            "relationship_count": self._graph.relationship_count,
            "configuration_hash": config_hash,
            "data": data,
        }

        if self._snapshot_repo:
            self._snapshot_repo.save(
                snapshot_id, now, trigger,
                self._graph.entity_count, self._graph.relationship_count,
                data
            )

        self._last_snapshot = snapshot
        logger.info(f"Snapshot created: {snapshot_id[:8]} ({trigger})")
        return snapshot

    def compare_snapshots(self, snapshot_a: Dict, snapshot_b: Dict) -> Dict:
        changes = {
            "time_a": snapshot_a.get("snapshot_time", ""),
            "time_b": snapshot_b.get("snapshot_time", ""),
            "added": [],
            "removed": [],
            "changed": [],
            "resource_changes": {},
            "summary": {},
        }

        data_a = snapshot_a.get("data", {})
        data_b = snapshot_b.get("data", {})

        for category in ["application", "service", "startup_entry"]:
            items_a = {item["name"]: item for item in data_a.get("software", {}).get(category, [])}
            items_b = {item["name"]: item for item in data_b.get("software", {}).get(category, [])}

            added = set(items_b.keys()) - set(items_a.keys())
            removed = set(items_a.keys()) - set(items_b.keys())

            for name in added:
                changes["added"].append({"category": category, "name": name})
            for name in removed:
                changes["removed"].append({"category": category, "name": name})

            for name in items_a.keys() & items_b.keys():
                if items_a[name].get("properties") != items_b[name].get("properties"):
                    changes["changed"].append({"category": category, "name": name})

        res_a = data_a.get("resource_summary", {})
        res_b = data_b.get("resource_summary", {})
        for key in set(res_a.keys()) | set(res_b.keys()):
            val_a = res_a.get(key, {}).get("usage_percent", 0)
            val_b = res_b.get(key, {}).get("usage_percent", 0)
            if abs(val_a - val_b) > 5:
                changes["resource_changes"][key] = {
                    "before": val_a,
                    "after": val_b,
                    "delta": val_b - val_a,
                }

        proc_count_a = len(data_a.get("processes", []))
        proc_count_b = len(data_b.get("processes", []))

        changes["summary"] = {
            "total_added": len(changes["added"]),
            "total_removed": len(changes["removed"]),
            "total_changed": len(changes["changed"]),
            "process_count_delta": proc_count_b - proc_count_a,
            "entity_count_delta": snapshot_b.get("entity_count", 0) - snapshot_a.get("entity_count", 0),
        }

        return changes

    def get_latest_snapshot(self) -> Optional[Dict]:
        if self._last_snapshot:
            return self._last_snapshot
        if self._snapshot_repo:
            recent = self._snapshot_repo.get_recent(1)
            if recent:
                full = self._snapshot_repo.get(recent[0]["id"])
                return full
        return None

    def get_snapshot_at(self, timestamp) -> Optional[Dict]:
        if self._snapshot_repo:
            return self._snapshot_repo.get_closest(timestamp)
        return None

    def get_what_changed(self, since_hours=24) -> Dict:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=since_hours)).isoformat()

        old_snapshot = self.get_snapshot_at(cutoff)
        new_snapshot = self.get_latest_snapshot()

        if not old_snapshot:
            return {"message": "No historical snapshot available for comparison"}
        if not new_snapshot:
            new_snapshot = self.create_snapshot(trigger="comparison")

        return self.compare_snapshots(old_snapshot, new_snapshot)
