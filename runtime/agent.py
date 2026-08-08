"""Agent——依赖注入 + 装配。"""
from runtime.loop import AgentLoop
from runtime.state import AgentState
from runtime.executor import Executor
from memory.short_term import ShortTermMemory
from llm.client import LLMClient
from llm.parser import OutputParser
from tools.registry import ToolRegistry
from context.manager import ContextManager
from harness.runner import ToolHarness


class Agent:
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

    def run(self, user_input: str, state: AgentState,
            memory: ShortTermMemory) -> str:
        loop = AgentLoop(
            self._llm, self._parser, self._tools,
            self._context, self._harness, self._executor,
        )
        return loop.run(user_input, state, memory)
