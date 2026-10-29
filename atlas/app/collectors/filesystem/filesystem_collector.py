import asyncio
import os
import logging
from pathlib import Path
from datetime import datetime

from atlas.app.collectors.base import BaseCollector
from atlas.app.core.events.event_types import EventType
from atlas.app.twin.entities.filesystem import File, Directory, Project
from atlas.app.twin.relationships.relationship import RelationshipType

logger = logging.getLogger("atlas.collectors.filesystem")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _watchdog_available = True
except ImportError:
    _watchdog_available = False
    logger.warning("watchdog not available, filesystem watching disabled")

PROJECT_MARKERS = {
    ".git": "git",
    "package.json": "node",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "requirements.txt": "python",
    "setup.py": "python",
    "pyproject.toml": "python",
    "pom.xml": "java",
    "build.gradle": "java",
    ".sln": "dotnet",
    ".csproj": "dotnet",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
    "composer.json": "php",
    "Gemfile": "ruby",
}

IMPORTANT_DIRS = [
    os.path.expanduser("~"),
    os.path.expandvars("%PROGRAMFILES%"),
    os.path.expandvars("%PROGRAMFILES(X86)%"),
    os.path.expandvars("%APPDATA%"),
    os.path.expandvars("%LOCALAPPDATA%"),
]


class AtlasFileHandler(FileSystemEventHandler):
    def __init__(self, collector):
        self._collector = collector
        self._event_count = 0
        self._max_per_minute = 1000

    def on_created(self, event):
        if self._event_count < self._max_per_minute:
            self._event_count += 1
            self._collector.emit_event(
                EventType.FILE_CREATED,
                metadata={"path": event.src_path, "is_directory": event.is_directory}
            )

    def on_modified(self, event):
        if not event.is_directory and self._event_count < self._max_per_minute:
            self._event_count += 1
            self._collector.emit_event(
                EventType.FILE_MODIFIED,
                metadata={"path": event.src_path}
            )

    def on_deleted(self, event):
        if self._event_count < self._max_per_minute:
            self._event_count += 1
            self._collector.emit_event(
                EventType.FILE_DELETED,
                metadata={"path": event.src_path, "is_directory": event.is_directory}
            )

    def on_moved(self, event):
        if self._event_count < self._max_per_minute:
            self._event_count += 1
            self._collector.emit_event(
                EventType.FILE_RENAMED,
                metadata={"src_path": event.src_path, "dest_path": event.dest_path}
            )

    def reset_counter(self):
        self._event_count = 0


class FilesystemCollector(BaseCollector):
    def __init__(self, event_bus, graph, watch_paths=None):
        super().__init__("filesystem_collector", event_bus, graph)
        self._watch_paths = watch_paths or []
        self._observer = None
        self._handler = None
        self._known_projects = {}

    async def initialize(self):
        await super().initialize()
        if _watchdog_available and self._watch_paths:
            self._handler = AtlasFileHandler(self)
            self._observer = Observer()
            for path in self._watch_paths:
                if Path(path).exists():
                    self._observer.schedule(self._handler, path, recursive=True)
                    self.logger.info(f"Watching filesystem: {path}")
            self._observer.start()

    async def shutdown(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        await super().shutdown()

    async def collect(self):
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        self._discover_projects()
        self._collect_important_dirs()
        if self._handler:
            self._handler.reset_counter()

    def _discover_projects(self):
        home = Path.home()
        search_dirs = [home]

        common_project_dirs = [
            home / "Documents",
            home / "Projects",
            home / "repos",
            home / "dev",
            home / "source",
            home / "workspace",
            home / "code",
            home / "src",
            home / "GitHub",
        ]

        for d in common_project_dirs:
            if d.exists():
                search_dirs.append(d)

        for search_dir in search_dirs:
            try:
                for item in search_dir.iterdir():
                    if not item.is_dir():
                        continue
                    self._check_project(item)
            except (PermissionError, OSError):
                continue

    def _check_project(self, path):
        for marker, lang in PROJECT_MARKERS.items():
            marker_path = path / marker
            if marker_path.exists():
                proj_key = str(path)
                if proj_key in self._known_projects:
                    return

                project = Project(name=path.name, source=self.name)
                project.properties.update({
                    "path": str(path),
                    "project_type": lang,
                    "language": lang,
                    "vcs": "git" if (path / ".git").exists() else "",
                    "last_activity": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                })

                try:
                    file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                    project.properties["file_count"] = min(file_count, 99999)
                except (PermissionError, OSError):
                    project.properties["file_count"] = 0

                self.graph.add_entity(project)
                self._known_projects[proj_key] = project.id

                machines = self.graph.get_entities_by_type("machine")
                if machines:
                    self.graph.find_or_create_relationship(
                        RelationshipType.PART_OF, project.id, machines[0].id,
                        "project", "machine", evidence_source=self.name
                    )
                return

    def _collect_important_dirs(self):
        for dir_path in IMPORTANT_DIRS:
            try:
                p = Path(dir_path)
                if not p.exists():
                    continue
                existing = self.graph.find_entity("directory", path=str(p))
                if existing:
                    continue
                d = Directory(name=p.name, source=self.name)
                d.properties.update({
                    "path": str(p),
                    "directory_type": "system",
                })
                self.graph.add_entity(d)
            except (PermissionError, OSError):
                continue
