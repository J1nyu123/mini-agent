"""短期记忆——deque 滑动窗口 + 对话压缩。"""
import re
from collections import deque
from typing import List

from protocol.message import Message, Role


def generate_summary(llm, old_messages: List[Message], max_chars: int = 200) -> str:
    """调用 LLM 将历史对话压缩为一两句话的摘要。"""
    convo = "\n".join(
        f"[{m.role.value}]: {m.content[:max_chars]}" for m in old_messages
    )
    prompt = f"请用一两句话总结以下对话的要点，保留关键信息和上下文：\n\n{convo}"
    raw = llm.chat([Message(role=Role.USER, content=prompt)])
    m = re.search(r'Final\s*Answer:\s*(.+)', raw, re.S | re.I)
    return m.group(1).strip() if m else raw.strip()


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

    def compress(self, keep_recent_turns: int, summary: str) -> int:
        """用摘要替换旧消息，保留最近 N 轮。返回压缩掉的消息数。"""
        keep_count = max(1, keep_recent_turns) * 2
        all_msgs = list(self._messages)
        if len(all_msgs) <= keep_count:
            return 0
        old_count = len(all_msgs) - keep_count
        recent = all_msgs[-keep_count:]
        self._messages.clear()
        self._messages.append(
            Message(role=Role.SYSTEM, content=f"[对话历史摘要] {summary}")
        )
        for m in recent:
            self._messages.append(m)
        return old_count
