import math
import time
import logging
from collections import deque
from typing import Dict, Optional

logger = logging.getLogger("atlas.monitoring.baselines")


class MetricBaseline:
    def __init__(self, window_size=360, ema_alpha=0.05):
        self._values = deque(maxlen=window_size)
        self._ema = None
        self._ema_alpha = ema_alpha
        self._count = 0
        self._sum = 0.0
        self._sum_sq = 0.0
        self._min = float('inf')
        self._max = float('-inf')

    def add(self, value):
        self._values.append(value)
        self._count += 1
        self._sum += value
        self._sum_sq += value * value

        if value < self._min:
            self._min = value
        if value > self._max:
            self._max = value

        if self._ema is None:
            self._ema = value
        else:
            self._ema = self._ema_alpha * value + (1 - self._ema_alpha) * self._ema

    @property
    def mean(self):
        if not self._values:
            return 0
        return sum(self._values) / len(self._values)

    @property
    def std_dev(self):
        if len(self._values) < 2:
            return 0
        m = self.mean
        variance = sum((x - m) ** 2 for x in self._values) / len(self._values)
        return math.sqrt(variance)

    @property
    def ema(self):
        return self._ema if self._ema is not None else 0

    @property
    def p95(self):
        if not self._values:
            return 0
        sorted_vals = sorted(self._values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def p99(self):
        if not self._values:
            return 0
        sorted_vals = sorted(self._values)
        idx = int(len(sorted_vals) * 0.99)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def z_score(self, value):
        sd = self.std_dev
        if sd == 0:
            return 0
        return (value - self.mean) / sd

    def is_anomalous(self, value, threshold=2.5):
        if len(self._values) < 10:
            return False
        return abs(self.z_score(value)) > threshold

    def deviation_from_baseline(self, value):
        if self.mean == 0:
            return 0
        return ((value - self.mean) / self.mean) * 100

    def to_dict(self):
        return {
            "mean": round(self.mean, 2),
            "std_dev": round(self.std_dev, 2),
            "ema": round(self.ema, 2),
            "p95": round(self.p95, 2),
            "p99": round(self.p99, 2),
            "min": self._min if self._min != float('inf') else 0,
            "max": self._max if self._max != float('-inf') else 0,
            "sample_count": len(self._values),
        }


class BaselineEngine:
    def __init__(self):
        self._baselines: Dict[str, MetricBaseline] = {}
        self._process_baselines: Dict[str, Dict[str, MetricBaseline]] = {}

    def update(self, metric_name, value):
        if metric_name not in self._baselines:
            self._baselines[metric_name] = MetricBaseline()
        self._baselines[metric_name].add(value)

    def update_process(self, pid, metric_name, value):
        pid_key = str(pid)
        if pid_key not in self._process_baselines:
            self._process_baselines[pid_key] = {}
        if metric_name not in self._process_baselines[pid_key]:
            self._process_baselines[pid_key][metric_name] = MetricBaseline(window_size=120)
        self._process_baselines[pid_key][metric_name].add(value)

    def get_baseline(self, metric_name) -> Optional[MetricBaseline]:
        return self._baselines.get(metric_name)

    def get_process_baseline(self, pid, metric_name) -> Optional[MetricBaseline]:
        pid_key = str(pid)
        if pid_key in self._process_baselines:
            return self._process_baselines[pid_key].get(metric_name)
        return None

    def is_anomalous(self, metric_name, value, threshold=2.5):
        baseline = self._baselines.get(metric_name)
        if baseline is None:
            return False
        return baseline.is_anomalous(value, threshold)

    def get_all_baselines(self):
        return {name: bl.to_dict() for name, bl in self._baselines.items()}

    def cleanup_stale_processes(self, active_pids):
        active = {str(p) for p in active_pids}
        stale = [pid for pid in self._process_baselines if pid not in active]
        for pid in stale:
            del self._process_baselines[pid]
