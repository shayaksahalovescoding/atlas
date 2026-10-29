import asyncio
import logging
from typing import Dict, List

from atlas.app.core.config.settings import Settings
from atlas.app.core.events.event_bus import EventBus
from atlas.app.twin.graph.graph_manager import GraphManager
from atlas.app.collectors.base import BaseCollector
from atlas.app.collectors.hardware.hardware_collector import HardwareCollector
from atlas.app.collectors.processes.process_collector import ProcessCollector
from atlas.app.collectors.services.service_collector import ServiceCollector
from atlas.app.collectors.applications.application_collector import ApplicationCollector
from atlas.app.collectors.filesystem.filesystem_collector import FilesystemCollector
from atlas.app.collectors.network.network_collector import NetworkCollector
from atlas.app.collectors.events.event_collector import EventCollector

logger = logging.getLogger("atlas.collectors.manager")


class CollectorManager:
    def __init__(self, event_bus: EventBus, graph: GraphManager, settings: Settings):
        self._event_bus = event_bus
        self._graph = graph
        self._settings = settings
        self._collectors: Dict[str, BaseCollector] = {}
        self._tasks: List[asyncio.Task] = []
        self._running = False

    def _create_collectors(self):
        cfg = self._settings.collectors

        if cfg.hardware_enabled:
            self._collectors["hardware"] = HardwareCollector(self._event_bus, self._graph)

        if cfg.process_enabled:
            self._collectors["processes"] = ProcessCollector(
                self._event_bus, self._graph, self._settings.privacy
            )

        if cfg.service_enabled:
            self._collectors["services"] = ServiceCollector(self._event_bus, self._graph)

        if cfg.application_enabled:
            self._collectors["applications"] = ApplicationCollector(self._event_bus, self._graph)

        if cfg.filesystem_enabled:
            self._collectors["filesystem"] = FilesystemCollector(
                self._event_bus, self._graph,
                watch_paths=cfg.filesystem_watch_paths
            )

        if cfg.network_enabled:
            self._collectors["network"] = NetworkCollector(self._event_bus, self._graph)

        if cfg.event_log_enabled:
            self._collectors["events"] = EventCollector(self._event_bus, self._graph)

    async def start(self):
        logger.info("Starting collector manager")
        self._create_collectors()
        self._running = True

        for name, collector in self._collectors.items():
            try:
                await collector.initialize()
                logger.info(f"Collector {name} initialized")
            except Exception as e:
                logger.error(f"Failed to initialize collector {name}: {e}", exc_info=True)

        logger.info("Running initial discovery...")
        for name, collector in self._collectors.items():
            try:
                await collector.run_collection()
                logger.info(f"Initial collection complete: {name}")
            except Exception as e:
                logger.error(f"Initial collection failed for {name}: {e}", exc_info=True)

        intervals = self._settings.get_sampling_intervals()

        interval_map = {
            "hardware": intervals.get("metrics", 10),
            "processes": intervals.get("processes", 10),
            "services": intervals.get("services", 60),
            "applications": intervals.get("applications", 120),
            "filesystem": intervals.get("filesystem", 30),
            "network": intervals.get("network", 10),
            "events": intervals.get("metrics", 10) * 6,
        }

        for name, collector in self._collectors.items():
            interval = interval_map.get(name, 30)
            task = asyncio.create_task(self._collection_loop(name, collector, interval))
            self._tasks.append(task)
            logger.info(f"Scheduled {name} every {interval}s")

    async def _collection_loop(self, name, collector, interval):
        while self._running:
            try:
                await asyncio.sleep(interval)
                if self._running:
                    await collector.run_collection()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Collection loop error for {name}: {e}", exc_info=True)
                await asyncio.sleep(interval)

    async def stop(self):
        logger.info("Stopping collector manager")
        self._running = False

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        for name, collector in self._collectors.items():
            try:
                await collector.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")

        logger.info("Collector manager stopped")

    def get_health(self):
        return {name: c.get_health() for name, c in self._collectors.items()}

    def get_collector(self, name) -> BaseCollector:
        return self._collectors.get(name)

    async def force_collection(self, collector_name=None):
        if collector_name:
            collector = self._collectors.get(collector_name)
            if collector:
                await collector.run_collection()
        else:
            for collector in self._collectors.values():
                await collector.run_collection()
