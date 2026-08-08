"""AgentLoop——核心 ReAct 循环。只依赖接口抽象，不直接依赖 ReAct 正则、工具函数或 LLM SDK。"""
import logging
import time
from datetime import datetime

from protocol.message import Message, Role
from protocol.action import ActionType, AgentAction
from memory.short_term import ShortTermMemory
from runtime.state import AgentState, ToolCallLog
from runtime.executor import Executor
from tools.registry import ToolRegistry
from tools.base import Tool, CallResult
from harness.runner import ToolHarness
from context.manager import ContextManager
from llm.client import LLMClient
from llm.parser import OutputParser

logger = logging.getLogger(__name__)


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        parser: OutputParser,
        tools: ToolRegistry,
        context: ContextManager,
        harness: ToolHarness,
        executor: Executor,
    ):
        self._llm = llm
        self._parser = parser
        self._tools = tools
        self._context = context
        self._harness = harness
        self._executor = executor

    def run(
        self,
        user_input: str,
        state: AgentState,
        memory: ShortTermMemory,
    ) -> str:
        memory.add(Message(role=Role.USER, content=user_input))
        state.task_status = "running"
        state.turn_count = 0
        state.tool_calls = []
        state.last_error = ""

        while not self._executor.should_stop(state):
            messages = self._context.build(memory, self._tools.list_schemas())

            raw = self._llm.chat(messages)
            logger.debug("LLM raw output:\n%s", raw)

            action = self._parser.parse(raw, self._tools.list_schemas())

            if action.type == ActionType.FINAL_ANSWER:
                memory.add(Message(role=Role.ASSISTANT, content=action.final_answer))
                state.task_status = "done"
                return action.final_answer

            if action.type == ActionType.TOOL_CALL:
                tool = self._tools.get(action.tool_name)
                if tool is None:
                    obs = f"错误：工具 '{action.tool_name}' 不存在"
                    memory.add(Message(role=Role.USER, content=f"Observation: {obs}",
                                       tool_name=action.tool_name))
                    state.turn_count += 1
                    continue

                t0 = time.perf_counter()
                result = self._harness.execute(tool, action.tool_params)
                elapsed = (time.perf_counter() - t0) * 1000

                obs = result.content if result.success else f"工具调用失败: {result.error}"
                memory.add(Message(role=Role.USER, content=f"Observation: {obs}",
                                   tool_name=action.tool_name))

                state.tool_calls.append(ToolCallLog(
                    tool_name=action.tool_name,
                    params=action.tool_params,
                    result=result.content if result.success else result.error,
                    success=result.success,
                    duration_ms=round(elapsed, 2),
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                ))
                state.turn_count += 1
                continue

        state.task_status = "error"
        state.last_error = "达到最大轮次上限"
        fallback = "已达到最大轮次上限，请简化问题后重试。"
        memory.add(Message(role=Role.ASSISTANT, content=fallback))
        return fallback
