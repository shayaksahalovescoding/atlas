import json
import logging
from datetime import datetime
from typing import Dict, List

from atlas.app.storage.sqlite.database import Database

logger = logging.getLogger("atlas.security.audit")


class AuditLog:
    def __init__(self, db: Database):
        self._db = db

    def log(self, action: str, actor: str = "system", target: str = "",
            details: Dict = None, result: str = ""):
        try:
            with self._db.transaction() as conn:
                conn.execute(
                    "INSERT INTO audit_log (timestamp, action, actor, target, details, result) VALUES (?, ?, ?, ?, ?, ?)",
                    (datetime.now().isoformat(), action, actor, target,
                     json.dumps(details or {}), result)
                )
        except Exception as e:
            logger.error(f"Audit log error: {e}")

    def log_ai_action(self, tool_name: str, arguments: Dict, result: str = ""):
        self.log(
            action=f"ai_tool_call:{tool_name}",
            actor="ai",
            target=tool_name,
            details={"arguments": arguments},
            result=result[:500],
        )

    def log_user_action(self, action: str, details: Dict = None):
        self.log(action=action, actor="user", details=details)

    def get_recent(self, count: int = 100) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
            (count,)
        )
        return [dict(r) for r in rows]

    def get_by_action(self, action: str, count: int = 50) -> List[Dict]:
        rows = self._db.fetchall(
            "SELECT * FROM audit_log WHERE action LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{action}%", count)
        )
        return [dict(r) for r in rows]
