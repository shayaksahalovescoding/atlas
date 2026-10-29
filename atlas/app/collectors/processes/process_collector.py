import asyncio
import os
from datetime import datetime

import psutil

from atlas.app.collectors.base import BaseCollector
from atlas.app.core.events.event_types import EventType, EventPriority
from atlas.app.twin.entities.runtime import Process
from atlas.app.twin.relationships.relationship import RelationshipType, ConfidenceLevel
from atlas.app.security.redaction.secret_redactor import redact_command_line


APPLICATION_MAPPINGS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "code.exe": "Visual Studio Code",
    "devenv.exe": "Visual Studio",
    "explorer.exe": "Windows Explorer",
    "spotify.exe": "Spotify",
    "discord.exe": "Discord",
    "slack.exe": "Slack",
    "teams.exe": "Microsoft Teams",
    "outlook.exe": "Microsoft Outlook",
    "word.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "powerpnt.exe": "Microsoft PowerPoint",
    "notepad.exe": "Notepad",
    "notepad++.exe": "Notepad++",
    "docker.exe": "Docker Desktop",
    "com.docker.proxy.exe": "Docker Desktop",
    "com.docker.backend.exe": "Docker Desktop",
    "WindowsTerminal.exe": "Windows Terminal",
    "wt.exe": "Windows Terminal",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
    "python.exe": "Python",
    "pythonw.exe": "Python",
    "node.exe": "Node.js",
    "java.exe": "Java",
    "javaw.exe": "Java",
    "steam.exe": "Steam",
    "obs64.exe": "OBS Studio",
    "vlc.exe": "VLC Media Player",
    "winrar.exe": "WinRAR",
    "7zg.exe": "7-Zip",
    "git.exe": "Git",
    "svchost.exe": "Windows Service Host",
    "csrss.exe": "Client Server Runtime",
    "lsass.exe": "Local Security Authority",
    "services.exe": "Service Control Manager",
    "dwm.exe": "Desktop Window Manager",
    "taskhostw.exe": "Task Host Window",
    "RuntimeBroker.exe": "Runtime Broker",
    "SearchHost.exe": "Windows Search",
    "StartMenuExperienceHost.exe": "Start Menu",
    "ShellExperienceHost.exe": "Shell Experience Host",
    "SystemSettings.exe": "Windows Settings",
    "WmiPrvSE.exe": "WMI Provider Host",
}

SYSTEM_PROCESSES = {
    "system", "idle", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "fontdrvhost.exe", "dwm.exe", "svchost.exe",
    "lsaiso.exe", "sgrmbroker.exe", "memory compression",
}


class ProcessCollector(BaseCollector):
    def __init__(self, event_bus, graph, privacy_config=None):
        super().__init__("process_collector", event_bus, graph)
        self._known_pids = {}
        self._privacy_config = privacy_config
        self._excluded_apps = set()
        if privacy_config:
            self._excluded_apps = {a.lower() for a in privacy_config.excluded_applications}

    async def collect(self):
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        current_pids = {}
        for proc in psutil.process_iter(['pid', 'name', 'ppid', 'status', 'username',
                                          'create_time', 'cpu_percent', 'memory_info',
                                          'memory_percent', 'num_threads', 'exe',
                                          'cmdline', 'io_counters', 'num_handles']):
            try:
                info = proc.info
                pid = info['pid']
                if pid == 0:
                    continue
                current_pids[pid] = info

                exe_name = (info.get('name') or '').lower()
                if exe_name in self._excluded_apps:
                    continue

                app_name = APPLICATION_MAPPINGS.get(info.get('name', ''), '')
                is_system = exe_name in SYSTEM_PROCESSES

                cmd = ''
                if info.get('cmdline'):
                    cmd = redact_command_line(' '.join(info['cmdline'][:5]))

                mem_info = info.get('memory_info')
                io = info.get('io_counters')
                exe_path = info.get('exe') or ''

                start_time = ''
                if info.get('create_time'):
                    try:
                        start_time = datetime.fromtimestamp(info['create_time']).isoformat()
                    except (OSError, ValueError):
                        pass

                if pid in self._known_pids:
                    entity_id = self._known_pids[pid]
                    self.graph.update_entity(entity_id,
                        status=info.get('status', ''),
                        cpu_percent=info.get('cpu_percent', 0.0) or 0.0,
                        memory_bytes=mem_info.rss if mem_info else 0,
                        memory_percent=info.get('memory_percent', 0.0) or 0.0,
                        thread_count=info.get('num_threads', 0) or 0,
                        handle_count=info.get('num_handles', 0) or 0,
                        io_read_bytes=io.read_bytes if io else 0,
                        io_write_bytes=io.write_bytes if io else 0,
                        io_read_count=io.read_count if io else 0,
                        io_write_count=io.write_count if io else 0,
                    )
                else:
                    process = Process(
                        name=info.get('name', f'PID_{pid}'),
                        source=self.name
                    )
                    process.properties.update({
                        "pid": pid,
                        "ppid": info.get('ppid', 0),
                        "executable_path": exe_path,
                        "command_line": cmd,
                        "username": info.get('username', ''),
                        "start_time": start_time,
                        "status": info.get('status', ''),
                        "cpu_percent": info.get('cpu_percent', 0.0) or 0.0,
                        "memory_bytes": mem_info.rss if mem_info else 0,
                        "memory_percent": info.get('memory_percent', 0.0) or 0.0,
                        "thread_count": info.get('num_threads', 0) or 0,
                        "handle_count": info.get('num_handles', 0) or 0,
                        "io_read_bytes": io.read_bytes if io else 0,
                        "io_write_bytes": io.write_bytes if io else 0,
                        "io_read_count": io.read_count if io else 0,
                        "io_write_count": io.write_count if io else 0,
                        "priority": "",
                        "is_system": is_system,
                        "application_id": None,
                        "window_title": "",
                    })
                    self.graph.add_entity(process)
                    self._known_pids[pid] = process.id

                    self.emit_event(EventType.PROCESS_STARTED,
                        entity_id=process.id, entity_type="process",
                        metadata={"pid": pid, "name": info.get('name', ''), "application": app_name})

                    ppid = info.get('ppid', 0)
                    if ppid and ppid in self._known_pids:
                        self.graph.find_or_create_relationship(
                            RelationshipType.CHILD_OF, process.id, self._known_pids[ppid],
                            "process", "process", evidence_source=self.name
                        )

                    machines = self.graph.get_entities_by_type("machine")
                    if machines:
                        self.graph.find_or_create_relationship(
                            RelationshipType.RUNS_ON, process.id, machines[0].id,
                            "process", "machine", evidence_source=self.name
                        )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        gone_pids = set(self._known_pids.keys()) - set(current_pids.keys())
        for pid in gone_pids:
            entity_id = self._known_pids.pop(pid, None)
            if entity_id:
                entity = self.graph.get_entity(entity_id)
                if entity:
                    self.graph.update_entity(entity_id,
                        state="terminated", status="terminated")
                    self.emit_event(EventType.PROCESS_STOPPED,
                        entity_id=entity_id, entity_type="process",
                        metadata={"pid": pid, "name": entity.name})

    def get_process_tree(self, pid=None):
        tree = {}
        for entity in self.graph.get_entities_by_type("process"):
            p = entity.properties.get("pid", 0)
            pp = entity.properties.get("ppid", 0)
            if p not in tree:
                tree[p] = {"entity": entity, "children": []}
            if pp not in tree:
                tree[pp] = {"entity": None, "children": []}
            tree[pp]["children"].append(p)
        if pid:
            return tree.get(pid)
        return tree

    def get_top_consumers(self, metric="memory_bytes", count=10):
        processes = self.graph.get_entities_by_type("process")
        processes.sort(key=lambda p: p.properties.get(metric, 0), reverse=True)
        return processes[:count]
