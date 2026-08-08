"""AgentState——每个请求的运行时状态。"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ToolCallLog:
    tool_name: str
    params: dict
    result: str
    success: bool
    duration_ms: float
    timestamp: str


@dataclass
class AgentState:
    session_id: str
    turn_count: int = 0
    tool_calls: List[ToolCallLog] = field(default_factory=list)
    task_status: str = "idle"
    last_error: str = ""
