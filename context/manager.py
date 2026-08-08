"""ContextManager——参考 final promptctx 的 ContextAssembler，简化为 system prompt 渲染 + STM 拼接。"""
import json
from typing import List

from protocol.message import Message, Role
from memory.short_term import ShortTermMemory


class ContextManager:
    def __init__(self, system_template: str):
        self._template = system_template

    def build(
        self,
        memory: ShortTermMemory,
        tools_schema: List[dict],
    ) -> List[Message]:
        schema_text = json.dumps(tools_schema, ensure_ascii=False, indent=2)
        system_content = self._template.replace("{tools_schema}", schema_text)

        messages: List[Message] = [
            Message(role=Role.SYSTEM, content=system_content)
        ]
        messages.extend(memory.get_all())
        return messages
