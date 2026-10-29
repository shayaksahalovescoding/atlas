import asyncio
import logging
import signal
from typing import Callable, List, Optional
from datetime import datetime

from atlas.app.core.state.app_state import AppState, SubsystemStatus

logger = logging.getLogger("atlas.lifecycle")


class Subsystem:
    def __init__(self, name, initializer, finalizer=None, priority=0, required=False):
        self.name = name
        self.initializer = initializer
        self.finalizer = finalizer
        self.priority = priority
        self.required = required
        self.instance = None


class AppLifecycle:
    def __init__(self):
        self._subsystems: List[Subsystem] = []
        self._state = AppState()
        self._shutdown_event = asyncio.Event()
        self._started = False

    def register(self, name, initializer, finalizer=None, priority=0, required=False):
        sub = Subsystem(name, initializer, finalizer, priority, required)
        self._subsystems.append(sub)
        self._subsystems.sort(key=lambda s: s.priority)
        self._state.set_subsystem_status(name, SubsystemStatus.INITIALIZING)
        return sub

    async def start(self):
        logger.info("ATLAS starting up...")
        for sub in self._subsystems:
            try:
                logger.info(f"Initializing {sub.name}...")
                self._state.set_subsystem_status(sub.name, SubsystemStatus.INITIALIZING)
                result = sub.initializer()
                if asyncio.iscoroutine(result):
                    result = await result
                sub.instance = result
                self._state.set_subsystem_status(sub.name, SubsystemStatus.RUNNING)
                logger.info(f"{sub.name} initialized successfully")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to initialize {sub.name}: {error_msg}", exc_info=True)
                self._state.set_subsystem_status(sub.name, SubsystemStatus.ERROR, error_msg)
                if sub.required:
                    logger.critical(f"Required subsystem {sub.name} failed, aborting startup")
                    await self.shutdown()
                    raise RuntimeError(f"Required subsystem {sub.name} failed: {error_msg}")
        self._started = True
        logger.info("ATLAS startup complete")

    async def shutdown(self):
        logger.info("ATLAS shutting down...")
        for sub in reversed(self._subsystems):
            if sub.finalizer:
                try:
                    logger.info(f"Shutting down {sub.name}...")
                    result = sub.finalizer()
                    if asyncio.iscoroutine(result):
                        await result
                    self._state.set_subsystem_status(sub.name, SubsystemStatus.STOPPED)
                    logger.info(f"{sub.name} shut down")
                except Exception as e:
                    logger.error(f"Error shutting down {sub.name}: {e}", exc_info=True)
        self._shutdown_event.set()
        self._started = False
        logger.info("ATLAS shutdown complete")

    async def wait_for_shutdown(self):
        await self._shutdown_event.wait()

    def get_subsystem(self, name):
        for sub in self._subsystems:
            if sub.name == name:
                return sub.instance
        return None

    @property
    def is_started(self):
        return self._started

    def health_report(self):
        return {
            "overall": self._state.get_overall_health().value,
            "subsystems": {
                sub.name: {
                    "status": self._state.subsystems.get(sub.name, SubsystemStatus.INITIALIZING).value,
                    "error": self._state.subsystem_errors.get(sub.name),
                    "required": sub.required,
                }
                for sub in self._subsystems
            }
        }
