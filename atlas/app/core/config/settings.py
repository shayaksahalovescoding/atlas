import os
import json
import enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


class MonitoringMode(enum.Enum):
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    QUIET = "quiet"


SAMPLING_INTERVALS = {
    MonitoringMode.PERFORMANCE: {
        "metrics": 5,
        "processes": 5,
        "services": 30,
        "applications": 60,
        "filesystem": 10,
        "network": 5,
        "reconciliation": 300,
        "snapshots": 1800,
    },
    MonitoringMode.BALANCED: {
        "metrics": 10,
        "processes": 10,
        "services": 60,
        "applications": 120,
        "filesystem": 30,
        "network": 10,
        "reconciliation": 600,
        "snapshots": 3600,
    },
    MonitoringMode.QUIET: {
        "metrics": 30,
        "processes": 30,
        "services": 120,
        "applications": 300,
        "filesystem": 60,
        "network": 30,
        "reconciliation": 1200,
        "snapshots": 7200,
    },
}


@dataclass
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    timeout: int = 120
    max_retries: int = 3
    enabled: bool = True


@dataclass
class RetentionConfig:
    events_days: int = 30
    metrics_days: int = 14
    snapshots_days: int = 90
    incidents_days: int = 180
    audit_days: int = 365


@dataclass
class PrivacyConfig:
    excluded_applications: List[str] = field(default_factory=lambda: [
        "KeePass", "1Password", "LastPass", "Bitwarden",
    ])
    excluded_paths: List[str] = field(default_factory=list)
    redact_command_lines: bool = True
    redact_environment: bool = True
    monitor_clipboard: bool = False


@dataclass
class CollectorConfig:
    hardware_enabled: bool = True
    process_enabled: bool = True
    service_enabled: bool = True
    application_enabled: bool = True
    filesystem_enabled: bool = True
    network_enabled: bool = True
    event_log_enabled: bool = True
    filesystem_watch_paths: List[str] = field(default_factory=list)
    max_processes: int = 5000
    max_file_events_per_minute: int = 1000


@dataclass
class UIConfig:
    theme: str = "dark"
    graph_max_nodes: int = 500
    chart_history_minutes: int = 60
    refresh_rate_ms: int = 1000
    show_system_tray: bool = True


@dataclass
class Settings:
    app_name: str = "ATLAS"
    version: str = "1.0.0"
    data_dir: str = ""
    log_dir: str = ""
    config_dir: str = ""
    db_path: str = ""
    monitoring_mode: MonitoringMode = MonitoringMode.BALANCED
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    collectors: CollectorConfig = field(default_factory=CollectorConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    debug: bool = False
    first_run: bool = True

    def __post_init__(self):
        if not self.data_dir:
            self.data_dir = str(Path(os.environ.get("LOCALAPPDATA", "")) / "ATLAS")
        if not self.log_dir:
            self.log_dir = str(Path(self.data_dir) / "logs")
        if not self.config_dir:
            self.config_dir = str(Path(self.data_dir) / "config")
        if not self.db_path:
            self.db_path = str(Path(self.data_dir) / "atlas.db")

    def get_sampling_intervals(self) -> Dict[str, int]:
        return SAMPLING_INTERVALS[self.monitoring_mode]

    def ensure_directories(self):
        for d in [self.data_dir, self.log_dir, self.config_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)

    def save(self, path=None):
        if path is None:
            path = Path(self.config_dir) / "settings.json"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = self._to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path=None):
        settings = cls()
        if path is None:
            path = Path(settings.config_dir) / "settings.json"
        if Path(path).exists():
            with open(path) as f:
                data = json.load(f)
            settings._from_dict(data)
        return settings

    def _to_dict(self):
        return {
            "monitoring_mode": self.monitoring_mode.value,
            "debug": self.debug,
            "first_run": self.first_run,
            "data_dir": self.data_dir,
            "ollama": {
                "host": self.ollama.host,
                "model": self.ollama.model,
                "timeout": self.ollama.timeout,
                "max_retries": self.ollama.max_retries,
                "enabled": self.ollama.enabled,
            },
            "retention": {
                "events_days": self.retention.events_days,
                "metrics_days": self.retention.metrics_days,
                "snapshots_days": self.retention.snapshots_days,
                "incidents_days": self.retention.incidents_days,
                "audit_days": self.retention.audit_days,
            },
            "privacy": {
                "excluded_applications": self.privacy.excluded_applications,
                "excluded_paths": self.privacy.excluded_paths,
                "redact_command_lines": self.privacy.redact_command_lines,
                "redact_environment": self.privacy.redact_environment,
                "monitor_clipboard": self.privacy.monitor_clipboard,
            },
            "collectors": {
                "hardware_enabled": self.collectors.hardware_enabled,
                "process_enabled": self.collectors.process_enabled,
                "service_enabled": self.collectors.service_enabled,
                "application_enabled": self.collectors.application_enabled,
                "filesystem_enabled": self.collectors.filesystem_enabled,
                "network_enabled": self.collectors.network_enabled,
                "event_log_enabled": self.collectors.event_log_enabled,
                "filesystem_watch_paths": self.collectors.filesystem_watch_paths,
                "max_processes": self.collectors.max_processes,
                "max_file_events_per_minute": self.collectors.max_file_events_per_minute,
            },
            "ui": {
                "theme": self.ui.theme,
                "graph_max_nodes": self.ui.graph_max_nodes,
                "chart_history_minutes": self.ui.chart_history_minutes,
                "refresh_rate_ms": self.ui.refresh_rate_ms,
                "show_system_tray": self.ui.show_system_tray,
            },
        }

    def _from_dict(self, data):
        if "monitoring_mode" in data:
            self.monitoring_mode = MonitoringMode(data["monitoring_mode"])
        self.debug = data.get("debug", self.debug)
        self.first_run = data.get("first_run", self.first_run)
        if "data_dir" in data:
            self.data_dir = data["data_dir"]
        if "ollama" in data:
            o = data["ollama"]
            self.ollama = OllamaConfig(**o)
        if "retention" in data:
            self.retention = RetentionConfig(**data["retention"])
        if "privacy" in data:
            p = data["privacy"]
            self.privacy = PrivacyConfig(**p)
        if "collectors" in data:
            self.collectors = CollectorConfig(**data["collectors"])
        if "ui" in data:
            self.ui = UIConfig(**data["ui"])
