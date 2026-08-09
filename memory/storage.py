"""SQLite 持久化——sessions / messages / tool_call_logs 三表。"""
import json
import logging
import sqlite3
import uuid
from typing import List, Optional

from protocol.message import Message, Role
from runtime.state import ToolCallLog

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_name TEXT,
    tool_call_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tool_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    params TEXT,
    result TEXT,
    success INTEGER DEFAULT 1,
    duration_ms REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
"""


class SQLiteStorage:
    def __init__(self, db_path: str = "mini_agent.db"):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.executescript(DDL)
            self._conn.commit()
        except Exception as e:
            logger.warning("SQLite 初始化失败: %s，降级为内存模式", e)
            self._conn = None

    @property
    def available(self) -> bool:
        return self._conn is not None

    def ensure_session(self, name: str) -> str:
        """Get or create a session row, return its id."""
        if not self._conn:
            return str(uuid.uuid4())[:8]
        cur = self._conn.execute("SELECT id FROM sessions WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            self._conn.execute(
                "UPDATE sessions SET updated_at = datetime('now') WHERE name = ?",
                (name,),
            )
            self._conn.commit()
            return row[0]
        sid = str(uuid.uuid4())[:8]
        self._conn.execute(
            "INSERT INTO sessions (id, name) VALUES (?, ?)", (sid, name))
        self._conn.commit()
        return sid

    def save_message(self, session_id: str, msg: Message) -> None:
        if not self._conn:
            return
        try:
            self._conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_name, tool_call_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, msg.role.value, msg.content,
                 msg.tool_name, msg.tool_call_id),
            )
            self._conn.commit()
        except Exception as e:
            logger.debug("保存消息失败: %s", e)

    def load_messages(self, session_id: str, limit: int = 50) -> List[Message]:
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(
                "SELECT role, content, tool_name, tool_call_id FROM messages "
                "WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit),
            )
            return [
                Message(
                    role=Role(row[0]),
                    content=row[1],
                    tool_name=row[2],
                    tool_call_id=row[3],
                )
                for row in cur.fetchall()
            ]
        except Exception as e:
            logger.debug("加载消息失败: %s", e)
            return []

    def save_tool_call(self, session_id: str, log: ToolCallLog) -> None:
        if not self._conn:
            return
        try:
            self._conn.execute(
                "INSERT INTO tool_call_logs (session_id, tool_name, params, result, "
                "success, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, log.tool_name, json.dumps(log.params, ensure_ascii=False),
                 log.result, 1 if log.success else 0, log.duration_ms),
            )
            self._conn.commit()
        except Exception as e:
            logger.debug("保存工具调用日志失败: %s", e)

    def delete_session(self, name: str) -> bool:
        """Delete a session and its messages/logs (cascade). Returns True if deleted."""
        if not self._conn:
            return False
        try:
            cur = self._conn.execute("DELETE FROM sessions WHERE name = ?", (name,))
            self._conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.debug("删除会话失败: %s", e)
            return False

    def list_sessions(self) -> List[dict]:
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(
                "SELECT name, created_at, updated_at FROM sessions ORDER BY updated_at DESC")
            return [
                {"name": r[0], "created_at": r[1], "updated_at": r[2]}
                for r in cur.fetchall()
            ]
        except Exception:
            return []

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
