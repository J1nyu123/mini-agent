"""Tool 定义——JSON Schema 标准参数格式。参考 final/internal/tools/tools.py Tool/CallResult。"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CallResult:
    success: bool
    content: str
    error: str = ""


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], str]
