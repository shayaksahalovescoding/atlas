import asyncio
import os
import winreg
import logging
from datetime import datetime
from pathlib import Path

from atlas.app.collectors.base import BaseCollector
from atlas.app.core.events.event_types import EventType
from atlas.app.twin.entities.software import Application, StartupEntry, ScheduledTask
from atlas.app.twin.relationships.relationship import RelationshipType

logger = logging.getLogger("atlas.collectors.applications")

UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

STARTUP_REGISTRY_KEYS = [
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
]


class ApplicationCollector(BaseCollector):
    def __init__(self, event_bus, graph):
        super().__init__("application_collector", event_bus, graph)
        self._known_apps = {}
        self._known_startups = {}

    async def collect(self):
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        self._collect_installed_apps()
        self._collect_startup_entries()
        self._link_processes_to_apps()

    def _collect_installed_apps(self):
        current_apps = {}

        for hive, key_path in UNINSTALL_KEYS:
            try:
                key = winreg.OpenKey(hive, key_path)
            except OSError:
                continue

            try:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)

                        app_info = self._read_app_info(subkey, subkey_name)
                        if app_info and app_info.get("display_name"):
                            display_name = app_info["display_name"]
                            current_apps[display_name] = app_info

                        winreg.CloseKey(subkey)
                        i += 1
                    except OSError:
                        break
            finally:
                winreg.CloseKey(key)

        for display_name, info in current_apps.items():
            if display_name in self._known_apps:
                entity_id = self._known_apps[display_name]
                self.graph.update_entity(entity_id,
                    version=info.get("version", ""),
                )
            else:
                app = Application(name=display_name, source=self.name)
                app.properties.update({
                    "display_name": display_name,
                    "version": info.get("version", ""),
                    "publisher": info.get("publisher", ""),
                    "install_date": info.get("install_date", ""),
                    "install_location": info.get("install_location", ""),
                    "uninstall_string": info.get("uninstall_string", ""),
                    "size_bytes": info.get("size", 0),
                    "is_system": info.get("system_component", False),
                    "registry_key": info.get("registry_key", ""),
                })
                self.graph.add_entity(app)
                self._known_apps[display_name] = app.id

                machines = self.graph.get_entities_by_type("machine")
                if machines:
                    self.graph.find_or_create_relationship(
                        RelationshipType.INSTALLED_ON, app.id, machines[0].id,
                        "application", "machine", evidence_source=self.name
                    )

        new_apps = set(current_apps.keys()) - set(self._known_apps.keys())
        for name in new_apps:
            if name in self._known_apps:
                self.emit_event(EventType.APPLICATION_INSTALLED,
                    entity_id=self._known_apps[name], entity_type="application",
                    metadata={"name": name})

    def _read_app_info(self, key, subkey_name):
        info = {"registry_key": subkey_name}
        fields = {
            "DisplayName": "display_name",
            "DisplayVersion": "version",
            "Publisher": "publisher",
            "InstallDate": "install_date",
            "InstallLocation": "install_location",
            "UninstallString": "uninstall_string",
            "EstimatedSize": "size",
            "SystemComponent": "system_component",
        }
        for reg_name, dict_name in fields.items():
            try:
                value, _ = winreg.QueryValueEx(key, reg_name)
                if dict_name == "size" and isinstance(value, int):
                    value = value * 1024
                if dict_name == "system_component":
                    value = bool(value)
                info[dict_name] = value
            except OSError:
                continue

        if info.get("system_component") and not info.get("display_name"):
            return None
        return info

    def _collect_startup_entries(self):
        for hive, key_path in STARTUP_REGISTRY_KEYS:
            try:
                key = winreg.OpenKey(hive, key_path)
            except OSError:
                continue

            try:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        entry_key = f"{key_path}\\{name}"

                        if entry_key not in self._known_startups:
                            entry = StartupEntry(name=name, source=self.name)
                            entry.properties.update({
                                "command": str(value),
                                "location": key_path,
                                "enabled": True,
                                "type": "registry",
                            })
                            self.graph.add_entity(entry)
                            self._known_startups[entry_key] = entry.id

                            machines = self.graph.get_entities_by_type("machine")
                            if machines:
                                self.graph.find_or_create_relationship(
                                    RelationshipType.RUNS_ON, entry.id, machines[0].id,
                                    "startup_entry", "machine", evidence_source=self.name
                                )
                        i += 1
                    except OSError:
                        break
            finally:
                winreg.CloseKey(key)

        startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup_folder.exists():
            for item in startup_folder.iterdir():
                entry_key = f"startup_folder\\{item.name}"
                if entry_key not in self._known_startups and item.suffix in ('.lnk', '.exe', '.bat', '.cmd'):
                    entry = StartupEntry(name=item.stem, source=self.name)
                    entry.properties.update({
                        "command": str(item),
                        "location": str(startup_folder),
                        "enabled": True,
                        "type": "startup_folder",
                    })
                    self.graph.add_entity(entry)
                    self._known_startups[entry_key] = entry.id

    def _link_processes_to_apps(self):
        from atlas.app.collectors.processes.process_collector import APPLICATION_MAPPINGS

        processes = self.graph.get_entities_by_type("process")
        for proc in processes:
            if proc.properties.get("application_id"):
                continue
            exe_name = proc.name
            app_name = APPLICATION_MAPPINGS.get(exe_name, "")
            if app_name and app_name in self._known_apps:
                app_id = self._known_apps[app_name]
                self.graph.update_entity(proc.id, application_id=app_id)
                self.graph.find_or_create_relationship(
                    RelationshipType.BELONGS_TO, proc.id, app_id,
                    "process", "application", evidence_source=self.name
                )

    def get_app_by_name(self, name):
        entity_id = self._known_apps.get(name)
        if entity_id:
            return self.graph.get_entity(entity_id)
        results = self.graph.search(name, "application")
        return results[0] if results else None
