"""ToolRegistry——工具的注册、查找、列表。参考 final/internal/tools/tools.py ToolExecutor。"""
from typing import Dict, List, Optional

from tools.base import Tool, CallResult


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_schemas(self) -> List[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def list_all(self) -> List[Tool]:
        return list(self._tools.values())
