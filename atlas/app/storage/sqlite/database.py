import sqlite3
import json
import logging
import shutil
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from atlas.app.storage.sqlite.schema import SCHEMA_SQL, SCHEMA_VERSION

logger = logging.getLogger("atlas.storage")


class Database:
    def __init__(self, db_path):
        self._db_path = db_path
        self._local = threading.local()
        self._write_lock = threading.Lock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self):
        conn = self._get_connection()
        conn.executescript(SCHEMA_SQL)
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        current = row[0] if row[0] is not None else 0
        if current < SCHEMA_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now().isoformat())
            )
            conn.commit()
        logger.info(f"Database initialized at {self._db_path}, schema v{SCHEMA_VERSION}")

    def _get_connection(self):
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection

    @contextmanager
    def connection(self):
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def transaction(self):
        with self._write_lock:
            conn = self._get_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute(self, sql, params=None):
        conn = self._get_connection()
        if params:
            return conn.execute(sql, params)
        return conn.execute(sql)

    def executemany(self, sql, params_list):
        with self._write_lock:
            conn = self._get_connection()
            conn.executemany(sql, params_list)
            conn.commit()

    def fetchone(self, sql, params=None):
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def fetchall(self, sql, params=None):
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    def backup(self, backup_path=None):
        if backup_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(Path(self._db_path).parent / f"atlas_backup_{ts}.db")
        with self._write_lock:
            conn = self._get_connection()
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
        logger.info(f"Database backed up to {backup_path}")
        return backup_path

    def restore(self, backup_path):
        with self._write_lock:
            if hasattr(self._local, "connection") and self._local.connection:
                self._local.connection.close()
                self._local.connection = None
            shutil.copy2(backup_path, self._db_path)
            self._initialize()
        logger.info(f"Database restored from {backup_path}")

    def cleanup(self, retention_days=None):
        if retention_days is None:
            return
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        with self.transaction() as conn:
            conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            logger.info(f"Cleaned up records older than {retention_days} days")

    def vacuum(self):
        with self._write_lock:
            conn = self._get_connection()
            conn.execute("VACUUM")
        logger.info("Database vacuumed")

    def get_stats(self):
        stats = {}
        for table in ["entities", "relationships", "events", "metrics", "snapshots", "incidents", "anomalies"]:
            try:
                row = self.fetchone(f"SELECT COUNT(*) as cnt FROM {table}")
                stats[table] = row["cnt"] if row else 0
            except Exception:
                stats[table] = 0
        db_file = Path(self._db_path)
        if db_file.exists():
            stats["file_size_mb"] = round(db_file.stat().st_size / (1024 * 1024), 2)
        return stats

    def close(self):
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    def reset(self):
        with self._write_lock:
            self.close()
            Path(self._db_path).unlink(missing_ok=True)
            self._initialize()
        logger.info("Database reset")
