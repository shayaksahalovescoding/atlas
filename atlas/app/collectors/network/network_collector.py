import asyncio
import logging
from datetime import datetime

import psutil

from atlas.app.collectors.base import BaseCollector
from atlas.app.core.events.event_types import EventType
from atlas.app.twin.entities.runtime import NetworkConnection as NetConnEntity
from atlas.app.twin.relationships.relationship import RelationshipType

logger = logging.getLogger("atlas.collectors.network")


class NetworkCollector(BaseCollector):
    def __init__(self, event_bus, graph):
        super().__init__("network_collector", event_bus, graph)
        self._known_connections = {}
        self._prev_io = None

    async def collect(self):
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        self._collect_connections()
        self._update_adapter_stats()

    def _collect_connections(self):
        current = set()
        try:
            connections = psutil.net_connections(kind='inet')
        except (psutil.AccessDenied, PermissionError):
            connections = []
            try:
                connections = psutil.net_connections(kind='tcp')
            except Exception:
                pass

        for conn in connections:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
            conn_key = f"{laddr}-{raddr}-{conn.pid or 0}"
            current.add(conn_key)

            if conn_key not in self._known_connections:
                proc_name = ""
                if conn.pid:
                    try:
                        proc_name = psutil.Process(conn.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                entity = NetConnEntity(
                    name=f"{proc_name or 'Unknown'}:{conn.laddr.port if conn.laddr else 0}",
                    source=self.name
                )
                entity.properties.update({
                    "local_address": conn.laddr.ip if conn.laddr else "",
                    "local_port": conn.laddr.port if conn.laddr else 0,
                    "remote_address": conn.raddr.ip if conn.raddr else "",
                    "remote_port": conn.raddr.port if conn.raddr else 0,
                    "protocol": "tcp" if conn.type == 1 else "udp",
                    "status": conn.status if hasattr(conn, 'status') else "",
                    "pid": conn.pid or 0,
                    "process_name": proc_name,
                    "family": "IPv4" if conn.family.value == 2 else "IPv6",
                })
                self.graph.add_entity(entity)
                self._known_connections[conn_key] = entity.id

                if conn.pid:
                    procs = self.graph.find_entity("process", pid=conn.pid)
                    if procs:
                        self.graph.find_or_create_relationship(
                            RelationshipType.OWNS, procs[0].id, entity.id,
                            "process", "network_connection",
                            evidence_source=self.name
                        )

        gone = set(self._known_connections.keys()) - current
        for conn_key in gone:
            entity_id = self._known_connections.pop(conn_key, None)
            if entity_id:
                self.graph.remove_entity(entity_id)

    def _update_adapter_stats(self):
        try:
            io = psutil.net_io_counters(pernic=True)
        except Exception:
            return

        for adapter_name, counters in io.items():
            adapters = self.graph.find_entity("network_adapter", name=adapter_name)
            if not adapters:
                continue
            adapter = adapters[0]
            self.graph.update_entity(adapter.id,
                bytes_sent=counters.bytes_sent,
                bytes_recv=counters.bytes_recv,
            )

    def get_connections_by_process(self, pid):
        results = []
        for entity in self.graph.get_entities_by_type("network_connection"):
            if entity.properties.get("pid") == pid:
                results.append(entity)
        return results
