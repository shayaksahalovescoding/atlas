import asyncio
import time
import logging
from collections import defaultdict
from typing import Callable, Optional, Set

from atlas.app.core.events.event_types import Event, EventType, EventPriority

logger = logging.getLogger("atlas.events")


class EventBus:
    def __init__(self, max_queue_size=10000):
        self._subscribers = defaultdict(list)
        self._global_subscribers = []
        self._queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._running = False
        self._task = None
        self._processed_count = 0
        self._dropped_count = 0
        self._event_history = []
        self._max_history = 5000
        self._paused = False

    def subscribe(self, event_type: EventType, callback: Callable, priority: int = 0):
        self._subscribers[event_type].append((priority, callback))
        self._subscribers[event_type].sort(key=lambda x: -x[0])

    def subscribe_all(self, callback: Callable, priority: int = 0):
        self._global_subscribers.append((priority, callback))
        self._global_subscribers.sort(key=lambda x: -x[0])

    def unsubscribe(self, event_type: EventType, callback: Callable):
        self._subscribers[event_type] = [
            (p, cb) for p, cb in self._subscribers[event_type] if cb != callback
        ]

    def unsubscribe_all(self, callback: Callable):
        self._global_subscribers = [
            (p, cb) for p, cb in self._global_subscribers if cb != callback
        ]

    async def publish(self, event: Event):
        if self._paused:
            return
        try:
            sort_key = (-event.priority.value, event.event_id)
            self._queue.put_nowait((sort_key, event))
        except asyncio.QueueFull:
            self._dropped_count += 1
            logger.warning(f"Event queue full, dropped event: {event}")

    def publish_sync(self, event: Event):
        if self._paused:
            return
        try:
            sort_key = (-event.priority.value, event.event_id)
            if getattr(self, "_loop", None) and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._queue.put_nowait, (sort_key, event))
            else:
                self._queue.put_nowait((sort_key, event))
        except (asyncio.QueueFull, Exception):
            self._dropped_count += 1

    async def start(self):
        if self._running:
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("EventBus started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._loop = None
        logger.info("EventBus stopped")

    async def _process_loop(self):
        while self._running:
            try:
                sort_key, event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            await self._dispatch(event)
            self._processed_count += 1

            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

    async def _dispatch(self, event: Event):
        callbacks = []
        for priority, cb in self._global_subscribers:
            callbacks.append(cb)
        for priority, cb in self._subscribers.get(event.event_type, []):
            callbacks.append(cb)

        for cb in callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}", exc_info=True)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    @property
    def queue_size(self):
        return self._queue.qsize()

    @property
    def processed_count(self):
        return self._processed_count

    @property
    def dropped_count(self):
        return self._dropped_count

    def get_recent_events(self, count=100, event_type=None, since=None):
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if since:
            events = [e for e in events if e.timestamp and e.timestamp >= since]
        return events[-count:]

    def get_stats(self):
        return {
            "queue_size": self.queue_size,
            "processed": self._processed_count,
            "dropped": self._dropped_count,
            "subscribers": sum(len(v) for v in self._subscribers.values()),
            "global_subscribers": len(self._global_subscribers),
            "history_size": len(self._event_history),
            "running": self._running,
            "paused": self._paused,
        }
