import asyncio
import logging
from datetime import datetime, timedelta

from atlas.app.collectors.base import BaseCollector
from atlas.app.core.events.event_types import EventType, EventPriority

logger = logging.getLogger("atlas.collectors.events")

try:
    import win32evtlog
    import win32evtlogutil
    import win32con
    _evtlog_available = True
except ImportError:
    _evtlog_available = False
    logger.warning("win32evtlog not available")


CRASH_EVENT_IDS = {1000, 1001, 1002}
SERVICE_EVENT_IDS = {7036, 7040, 7045}
BOOT_EVENT_IDS = {6005, 6006, 6008, 6009, 6013}
UPDATE_EVENT_IDS = {19, 20, 43}
DRIVER_EVENT_IDS = {7026, 7000}
BLUESCREEN_EVENT_IDS = {1001}


class EventCollector(BaseCollector):
    def __init__(self, event_bus, graph):
        super().__init__("event_collector", event_bus, graph)
        self._last_check = {}
        self._processed_records = set()

    async def collect(self):
        if not _evtlog_available:
            return
        await asyncio.get_event_loop().run_in_executor(None, self._collect_sync)

    def _collect_sync(self):
        self._read_log("Application")
        self._read_log("System")

    def _read_log(self, log_name):
        try:
            handle = win32evtlog.OpenEventLog(None, log_name)
        except Exception as e:
            self.logger.error(f"Failed to open {log_name} log: {e}")
            return

        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        cutoff = datetime.now() - timedelta(hours=24)

        try:
            events_read = 0
            max_events = 500

            while events_read < max_events:
                events = win32evtlog.ReadEventLog(handle, flags, 0)
                if not events:
                    break

                for event in events:
                    events_read += 1
                    if events_read > max_events:
                        break

                    try:
                        event_time = event.TimeGenerated
                        if hasattr(event_time, 'timestamp'):
                            event_dt = datetime.fromtimestamp(event_time.timestamp())
                        else:
                            event_dt = datetime(
                                event_time.year, event_time.month, event_time.day,
                                event_time.hour, event_time.minute, event_time.second
                            )
                    except Exception:
                        continue

                    if event_dt < cutoff:
                        events_read = max_events
                        break

                    record_key = f"{log_name}_{event.RecordNumber}"
                    if record_key in self._processed_records:
                        continue
                    self._processed_records.add(record_key)

                    if len(self._processed_records) > 10000:
                        self._processed_records = set(list(self._processed_records)[-5000:])

                    event_id = event.EventID & 0xFFFF
                    source_name = event.SourceName
                    event_type = event.EventType

                    strings = event.StringInserts or []
                    description = ' '.join(str(s) for s in strings[:3]) if strings else ""

                    if event_id in CRASH_EVENT_IDS and log_name == "Application":
                        app_name = strings[0] if strings else "Unknown"
                        self.emit_event(
                            EventType.CRASH_DETECTED,
                            metadata={
                                "application": app_name,
                                "event_id": event_id,
                                "source": source_name,
                                "description": description[:500],
                                "timestamp": event_dt.isoformat(),
                            },
                            priority=EventPriority.HIGH,
                        )

                    elif event_id in BOOT_EVENT_IDS and log_name == "System":
                        self.emit_event(
                            EventType.BOOT_COMPLETED,
                            metadata={
                                "event_id": event_id,
                                "source": source_name,
                                "description": description[:500],
                                "timestamp": event_dt.isoformat(),
                            },
                        )

                    elif event_id in SERVICE_EVENT_IDS and log_name == "System":
                        svc_name = strings[0] if strings else ""
                        self.emit_event(
                            EventType.SERVICE_STATE_CHANGED,
                            metadata={
                                "service_name": svc_name,
                                "event_id": event_id,
                                "description": description[:500],
                                "timestamp": event_dt.isoformat(),
                            },
                        )

                    elif event_id in UPDATE_EVENT_IDS and log_name == "System":
                        self.emit_event(
                            EventType.UPDATE_DETECTED,
                            metadata={
                                "event_id": event_id,
                                "source": source_name,
                                "description": description[:500],
                                "timestamp": event_dt.isoformat(),
                            },
                        )

                    elif event_type in (win32evtlog.EVENTLOG_ERROR_TYPE,) and log_name == "Application":
                        self.emit_event(
                            EventType.CRASH_DETECTED,
                            metadata={
                                "event_id": event_id,
                                "source": source_name,
                                "description": description[:500],
                                "severity": "error",
                                "timestamp": event_dt.isoformat(),
                            },
                        )

        except Exception as e:
            self.logger.error(f"Error reading {log_name} log: {e}", exc_info=True)
        finally:
            try:
                win32evtlog.CloseEventLog(handle)
            except Exception:
                pass
