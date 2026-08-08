"""Agent 动作协议——Parser 输出的统一格式。Runtime 只认这个类型。"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    FINAL_ANSWER = "final_answer"


@dataclass
class AgentAction:
    type: ActionType
    thought: str = ""
    tool_name: str = ""
    tool_params: dict = field(default_factory=dict)
    final_answer: str = ""
    raw_output: str = ""
