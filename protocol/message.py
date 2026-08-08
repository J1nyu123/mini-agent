"""内部消息协议——不绑定任何具体 LLM SDK 的消息格式。"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: Role
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
