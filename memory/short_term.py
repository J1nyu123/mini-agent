"""短期记忆——deque 滑动窗口。参考 final/internal/memory/memory.py ShortTerm，
改用 protocol.Message 替代 dict，去掉 timestamp 字段。"""
from collections import deque
from typing import List

from protocol.message import Message, Role


class ShortTermMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max(1, max_turns)
        self._messages: deque[Message] = deque(maxlen=max_turns * 2)

    def add(self, msg: Message) -> None:
        self._messages.append(msg)

    def get_all(self) -> List[Message]:
        return list(self._messages)

    def get_recent(self, n: int) -> List[Message]:
        messages = list(self._messages)
        return messages[-n:] if n > 0 else []

    def clear(self) -> None:
        self._messages.clear()

    def count(self) -> int:
        return len(self._messages)
