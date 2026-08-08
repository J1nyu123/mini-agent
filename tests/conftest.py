"""测试 fixtures。"""
import sys
import os
import pytest

# Ensure mini_agent package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.registry import ToolRegistry
from tools.builtin import builtin_tools
from llm.client import MockClient
from llm.parser import ReActParser
from context.manager import ContextManager
from harness.runner import ToolHarness, HarnessConfig
from runtime.executor import Executor, ExecutorConfig
from runtime.agent import Agent


@pytest.fixture
def tools():
    reg = ToolRegistry()
    for t in builtin_tools():
        reg.register(t)
    return reg


@pytest.fixture
def mock_client():
    return MockClient()


@pytest.fixture
def parser():
    return ReActParser()


@pytest.fixture
def context_mgr():
    template = "You are an AI assistant.\n\nTools: {tools_schema}\n\nUse ReAct format:\nThought: ...\nAction: tool_name\nAction Input: {{\"param\": \"value\"}}\n...or Final Answer: ..."
    return ContextManager(template)


@pytest.fixture
def harness():
    return ToolHarness(HarnessConfig(max_retries=2, retry_delay_ms=10, tool_timeout_ms=5000))


@pytest.fixture
def executor():
    return Executor(ExecutorConfig(max_turns=5))


@pytest.fixture
def agent(tools, mock_client, parser, context_mgr, harness, executor):
    return Agent(mock_client, parser, tools, context_mgr, harness, executor)
