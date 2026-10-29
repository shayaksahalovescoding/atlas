import logging
from typing import Dict, List
from datetime import datetime

from atlas.app.monitoring.metrics.metrics_engine import MetricsEngine
from atlas.app.monitoring.baselines.baseline_engine import BaselineEngine
from atlas.app.twin.graph.graph_manager import GraphManager

logger = logging.getLogger("atlas.reasoning.hypotheses")


class Hypothesis:
    def __init__(self, name, description=""):
        self.name = name
        self.description = description
        self.supporting_evidence = []
        self.contradicting_evidence = []
        self.score = 0.0
        self.category = ""
        self.affected_entities = []

    def add_supporting(self, evidence, weight=1.0):
        self.supporting_evidence.append({"evidence": evidence, "weight": weight})
        self._recalculate()

    def add_contradicting(self, evidence, weight=1.0):
        self.contradicting_evidence.append({"evidence": evidence, "weight": weight})
        self._recalculate()

    def _recalculate(self):
        support = sum(e["weight"] for e in self.supporting_evidence)
        contra = sum(e["weight"] for e in self.contradicting_evidence)
        total = support + contra
        self.score = support / total if total > 0 else 0

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "score": round(self.score, 2),
            "category": self.category,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "affected_entities": self.affected_entities,
            "confidence": "high" if self.score > 0.8 else "medium" if self.score > 0.5 else "low",
        }


class HypothesisEngine:
    def __init__(self, graph: GraphManager, metrics: MetricsEngine,
                 baselines: BaselineEngine):
        self._graph = graph
        self._metrics = metrics
        self._baselines = baselines

    def generate_hypotheses(self, question: str = "") -> List[Hypothesis]:
        current = self._metrics.get_current()
        hypotheses = []

        hypotheses.append(self._check_memory_pressure(current))
        hypotheses.append(self._check_cpu_saturation(current))
        hypotheses.append(self._check_disk_io(current))
        hypotheses.append(self._check_swap_pressure(current))
        hypotheses.append(self._check_process_explosion(current))
        hypotheses.append(self._check_application_issues(current))

        hypotheses = [h for h in hypotheses if h is not None]
        hypotheses.sort(key=lambda h: h.score, reverse=True)
        return hypotheses

    def _check_memory_pressure(self, current) -> Hypothesis:
        h = Hypothesis("Memory Pressure", "System is running low on available RAM")
        h.category = "memory"

        mem_pct = current.get("memory_percent", 0)
        mem_avail = current.get("memory_available_bytes", 0)
        swap_pct = current.get("swap_percent", 0)

        if mem_pct > 85:
            h.add_supporting(f"RAM usage at {mem_pct:.0f}%", 0.8)
        elif mem_pct > 70:
            h.add_supporting(f"RAM usage at {mem_pct:.0f}%", 0.3)
        else:
            h.add_contradicting(f"RAM usage at {mem_pct:.0f}% (normal)", 0.5)

        if swap_pct > 30:
            h.add_supporting(f"Swap usage at {swap_pct:.0f}%", 0.6)
        else:
            h.add_contradicting(f"Swap usage low at {swap_pct:.0f}%", 0.3)

        mem_bl = self._baselines.get_baseline("memory_percent")
        if mem_bl and mem_bl.mean > 0:
            deviation = mem_pct - mem_bl.mean
            if deviation > 10:
                h.add_supporting(f"Memory {deviation:.0f}% above baseline ({mem_bl.mean:.0f}%)", 0.5)
            elif deviation < -5:
                h.add_contradicting(f"Memory below baseline", 0.3)

        top_mem = sorted(
            self._graph.get_entities_by_type("process"),
            key=lambda p: p.properties.get("memory_bytes", 0),
            reverse=True
        )[:5]
        for p in top_mem:
            mem_mb = p.properties.get("memory_bytes", 0) / (1024 * 1024)
            if mem_mb > 500:
                h.add_supporting(f"{p.name}: {mem_mb:.0f} MB", 0.3)
                h.affected_entities.append({"name": p.name, "memory_mb": round(mem_mb)})

        return h

    def _check_cpu_saturation(self, current) -> Hypothesis:
        h = Hypothesis("CPU Saturation", "CPU is heavily loaded")
        h.category = "cpu"

        cpu = current.get("cpu_percent", 0)
        if cpu > 90:
            h.add_supporting(f"CPU at {cpu:.0f}%", 0.9)
        elif cpu > 70:
            h.add_supporting(f"CPU at {cpu:.0f}%", 0.5)
        elif cpu > 50:
            h.add_supporting(f"CPU at {cpu:.0f}%", 0.2)
        else:
            h.add_contradicting(f"CPU at {cpu:.0f}% (normal)", 0.7)

        cpu_bl = self._baselines.get_baseline("cpu_percent")
        if cpu_bl and cpu > cpu_bl.mean + 2 * cpu_bl.std_dev:
            h.add_supporting(f"CPU significantly above baseline ({cpu_bl.mean:.0f}%)", 0.4)

        top_cpu = sorted(
            self._graph.get_entities_by_type("process"),
            key=lambda p: p.properties.get("cpu_percent", 0),
            reverse=True
        )[:5]
        for p in top_cpu:
            cpu_pct = p.properties.get("cpu_percent", 0)
            if cpu_pct > 10:
                h.add_supporting(f"{p.name}: {cpu_pct:.0f}% CPU", 0.3)
                h.affected_entities.append({"name": p.name, "cpu_percent": round(cpu_pct, 1)})

        return h

    def _check_disk_io(self, current) -> Hypothesis:
        h = Hypothesis("Disk I/O Saturation", "Disk is under heavy I/O load")
        h.category = "disk"

        read = current.get("disk_read_bytes_sec", 0)
        write = current.get("disk_write_bytes_sec", 0)
        total = read + write

        if total > 200 * 1024 * 1024:
            h.add_supporting(f"Disk I/O at {total / (1024*1024):.0f} MB/s", 0.8)
        elif total > 50 * 1024 * 1024:
            h.add_supporting(f"Disk I/O at {total / (1024*1024):.0f} MB/s", 0.4)
        else:
            h.add_contradicting(f"Disk I/O at {total / (1024*1024):.0f} MB/s (normal)", 0.6)

        for part in self._graph.get_entities_by_type("partition"):
            usage = part.properties.get("usage_percent", 0)
            if usage > 90:
                mount = part.properties.get("mount_point", "")
                h.add_supporting(f"Disk {mount} at {usage:.0f}% capacity", 0.5)

        return h

    def _check_swap_pressure(self, current) -> Hypothesis:
        h = Hypothesis("Excessive Paging", "System is heavily using swap/page file")
        h.category = "memory"

        swap = current.get("swap_percent", 0)
        if swap > 50:
            h.add_supporting(f"Swap usage at {swap:.0f}%", 0.8)
        elif swap > 20:
            h.add_supporting(f"Swap usage at {swap:.0f}%", 0.4)
        else:
            h.add_contradicting(f"Swap usage low at {swap:.0f}%", 0.7)

        mem = current.get("memory_percent", 0)
        if mem > 85:
            h.add_supporting(f"High RAM usage ({mem:.0f}%) driving swap", 0.5)

        return h

    def _check_process_explosion(self, current) -> Hypothesis:
        h = Hypothesis("Process Explosion", "Unusually high number of processes")
        h.category = "processes"

        count = current.get("process_count", 0)
        bl = self._baselines.get_baseline("process_count")

        if bl and bl.mean > 0:
            if count > bl.mean * 1.5:
                h.add_supporting(f"{count} processes (baseline: {bl.mean:.0f})", 0.7)
            else:
                h.add_contradicting(f"Process count ({count}) near baseline ({bl.mean:.0f})", 0.6)
        elif count > 300:
            h.add_supporting(f"High process count: {count}", 0.4)
        else:
            h.add_contradicting(f"Normal process count: {count}", 0.5)

        return h

    def _check_application_issues(self, current) -> Hypothesis:
        h = Hypothesis("Application-Specific Issue", "A specific application may be misbehaving")
        h.category = "application"

        processes = self._graph.get_entities_by_type("process")
        app_resources = {}
        for p in processes:
            app_id = p.properties.get("application_id")
            if app_id:
                if app_id not in app_resources:
                    app_resources[app_id] = {"cpu": 0, "memory": 0, "count": 0, "name": ""}
                app_resources[app_id]["cpu"] += p.properties.get("cpu_percent", 0)
                app_resources[app_id]["memory"] += p.properties.get("memory_bytes", 0)
                app_resources[app_id]["count"] += 1
                app = self._graph.get_entity(app_id)
                if app:
                    app_resources[app_id]["name"] = app.name

        for app_id, res in app_resources.items():
            mem_mb = res["memory"] / (1024 * 1024)
            if mem_mb > 2000:
                h.add_supporting(f"{res['name']}: {mem_mb:.0f} MB across {res['count']} processes", 0.5)
                h.affected_entities.append({"name": res["name"], "memory_mb": round(mem_mb)})
            if res["cpu"] > 50:
                h.add_supporting(f"{res['name']}: {res['cpu']:.0f}% CPU", 0.4)

        if not h.supporting_evidence:
            h.add_contradicting("No single application using excessive resources", 0.5)

        return h
