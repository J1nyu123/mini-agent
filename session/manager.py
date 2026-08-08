"""SessionManager——会话的创建、切换、列表 + SQLite 持久化。"""
import logging
from typing import List, Optional, Tuple

from memory.short_term import ShortTermMemory
from memory.storage import SQLiteStorage
from runtime.state import AgentState, ToolCallLog
from protocol.message import Message

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, storage: SQLiteStorage, max_turns: int = 10):
        self._storage = storage
        self._max_turns = max_turns
        self._current_name: str = "默认"
        self._states: dict[str, AgentState] = {}
        self._memories: dict[str, ShortTermMemory] = {}

        # Pre-create default session
        self.get_or_create("默认")

    def get_or_create(self, name: str) -> Tuple[AgentState, ShortTermMemory]:
        if name not in self._states:
            sid = self._storage.ensure_session(name)
            state = AgentState(session_id=sid)
            memory = ShortTermMemory(max_turns=self._max_turns)

            for msg in self._storage.load_messages(sid, limit=self._max_turns * 2):
                memory.add(msg)

            self._states[name] = state
            self._memories[name] = memory

        return self._states[name], self._memories[name]

    def switch(self, name: str) -> None:
        self._current_name = name
        self.get_or_create(name)

    def current(self) -> Tuple[AgentState, ShortTermMemory]:
        return self.get_or_create(self._current_name)

    def current_name(self) -> str:
        return self._current_name

    def list_names(self) -> List[dict]:
        return self._storage.list_sessions()

    def save_message(self, name: str, msg: Message) -> None:
        state, _ = self.get_or_create(name)
        self._storage.save_message(state.session_id, msg)

    def save_tool_call(self, name: str, log: ToolCallLog) -> None:
        state, _ = self.get_or_create(name)
        self._storage.save_tool_call(state.session_id, log)

    def close(self) -> None:
        self._storage.close()
