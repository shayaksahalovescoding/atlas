import os
import sys
import json
import time
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from functools import wraps


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "component"):
            log_entry["component"] = record.component
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        msg = f"{color}{ts} [{record.levelname:>8}] {record.name}: {record.getMessage()}{self.RESET}"
        if hasattr(record, "duration_ms"):
            msg += f" ({record.duration_ms:.1f}ms)"
        return msg


def setup_logging(log_dir, debug=False):
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("atlas")
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(ConsoleFormatter())
    root.addHandler(console)

    log_file = Path(log_dir) / "atlas.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredFormatter())
    root.addHandler(file_handler)

    error_file = Path(log_dir) / "atlas_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root.addHandler(error_handler)

    return root


def timed(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger = logging.getLogger("atlas.timing")
            logger.debug(
                f"{func.__qualname__} completed",
                extra={"duration_ms": elapsed, "component": func.__module__}
            )

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger = logging.getLogger("atlas.timing")
            logger.debug(
                f"{func.__qualname__} completed",
                extra={"duration_ms": elapsed, "component": func.__module__}
            )

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def get_logger(name):
    return logging.getLogger(f"atlas.{name}")
