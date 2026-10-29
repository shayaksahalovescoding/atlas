import abc
import time
import logging
import asyncio
from typing import Optional
from datetime import datetime

from atlas.app.core.events.event_bus import EventBus
from atlas.app.core.events.event_types import Event, EventType, EventPriority
from atlas.app.twin.graph.graph_manager import GraphManager

logger = logging.getLogger("atlas.collectors")


class BaseCollector(abc.ABC):
    def __init__(self, name, event_bus: EventBus, graph: GraphManager):
        self.name = name
        self.event_bus = event_bus
        self.graph = graph
        self.logger = logging.getLogger(f"atlas.collectors.{name}")
        self._running = False
        self._healthy = True
        self._error = None
        self._last_collection = None
        self._collection_count = 0
        self._error_count = 0
        self._total_time_ms = 0
        self._task = None

    @abc.abstractmethod
    async def collect(self):
        pass

    async def initialize(self):
        self.logger.info(f"Initializing {self.name}")
        self._running = True

    async def shutdown(self):
        self.logger.info(f"Shutting down {self.name}")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def run_collection(self):
        start = time.perf_counter()
        try:
            await self.collect()
            self._healthy = True
            self._error = None
            self._collection_count += 1
            self._last_collection = datetime.now().isoformat()
        except Exception as e:
            self._error_count += 1
            self._error = str(e)
            self._healthy = False
            self.logger.error(f"Collection error in {self.name}: {e}", exc_info=True)
            try:
                await self.event_bus.publish(Event(
                    event_type=EventType.COLLECTOR_ERROR,
                    timestamp=datetime.now().isoformat(),
                    source=self.name,
                    metadata={"error": str(e)},
                    priority=EventPriority.HIGH,
                ))
            except Exception:
                pass
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            self._total_time_ms += elapsed

    async def start_periodic(self, interval_seconds: int):
        self._task = asyncio.create_task(self._periodic_loop(interval_seconds))

    async def _periodic_loop(self, interval):
        while self._running:
            await self.run_collection()
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    def emit_event(self, event_type, entity_id=None, entity_type=None, metadata=None,
                   priority=EventPriority.NORMAL):
        event = Event(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            source=self.name,
            entity_id=entity_id,
            entity_type=entity_type,
            metadata=metadata or {},
            priority=priority,
        )
        self.event_bus.publish_sync(event)
        return event

    def get_health(self):
        avg_ms = (self._total_time_ms / self._collection_count) if self._collection_count > 0 else 0
        return {
            "name": self.name,
            "healthy": self._healthy,
            "running": self._running,
            "error": self._error,
            "collections": self._collection_count,
            "errors": self._error_count,
            "last_collection": self._last_collection,
            "avg_collection_ms": round(avg_ms, 1),
        }
