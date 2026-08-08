"""OutputParser 抽象 + ReActParser。"""
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List

from protocol.action import AgentAction, ActionType

logger = logging.getLogger(__name__)


class OutputParser(ABC):
    @abstractmethod
    def parse(self, raw: str, tools_schema: List[dict]) -> AgentAction:
        ...


class ReActParser(OutputParser):
    RE_THOUGHT = re.compile(
        r'Thought:\s*(.+?)(?=\n(?:Action|Final\s*Answer)|\Z)', re.S | re.I)
    RE_ACTION = re.compile(r'Action:\s*(\S+)', re.I)
    RE_ACTION_INPUT = re.compile(
        r'Action\s*Input:\s*(\{(?:[^{}]|"(?:[^"\\]|\\.)*")*\})', re.S | re.I)
    RE_FINAL = re.compile(
        r'Final\s*Answer:\s*(.+?)\s*$', re.S | re.I)

    def parse(self, raw: str, tools_schema: List[dict]) -> AgentAction:
        text = raw.strip()
        tool_names = {t["name"] for t in tools_schema}

        thought = ""
        m = self.RE_THOUGHT.search(text)
        if m:
            thought = m.group(1).strip()

        action_m = self.RE_ACTION.search(text)
        input_m = self.RE_ACTION_INPUT.search(text)

        if action_m:
            tool_name = action_m.group(1).strip()
            if tool_name in tool_names:
                params = {}
                if input_m:
                    try:
                        params = json.loads(input_m.group(1))
                    except json.JSONDecodeError:
                        logger.warning("ReActParser: JSON 解析失败 %s", input_m.group(1))
                return AgentAction(
                    type=ActionType.TOOL_CALL,
                    thought=thought,
                    tool_name=tool_name,
                    tool_params=params,
                    raw_output=text,
                )
            else:
                logger.warning(
                    "ReActParser: 工具 '%s' 未注册，降级为 Final Answer", tool_name)

        final_m = self.RE_FINAL.search(text)
        final_answer = final_m.group(1).strip() if final_m else text

        return AgentAction(
            type=ActionType.FINAL_ANSWER,
            thought=thought,
            final_answer=final_answer,
            raw_output=text,
        )
