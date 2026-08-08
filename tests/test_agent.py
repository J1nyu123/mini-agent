"""26 test cases covering tools, parser, agent loop, session, harness, degradation."""
import time
from protocol.message import Message, Role
from protocol.action import ActionType
from runtime.state import AgentState
from memory.short_term import ShortTermMemory
from tools.base import Tool
from harness.runner import ToolHarness, HarnessConfig
from memory.storage import SQLiteStorage
from session.manager import SessionManager
from llm.parser import ReActParser
from llm.client import MockClient
from runtime.executor import Executor, ExecutorConfig
from runtime.agent import Agent


TOOLS_SCHEMA = [
    {"name": "calculator", "description": "", "input_schema": {}},
    {"name": "search_web", "description": "", "input_schema": {}},
    {"name": "get_time", "description": "", "input_schema": {}},
]


# ── 工具注册 ──────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_get(self, tools):
        assert tools.get("calculator") is not None
        assert tools.get("search_web") is not None
        assert tools.get("get_time") is not None
        assert tools.get("nonexistent") is None

    def test_list_schemas(self, tools):
        schemas = tools.list_schemas()
        assert len(schemas) == 3
        for s in schemas:
            assert "name" in s
            assert "description" in s
            assert "input_schema" in s


# ── 内置工具 ──────────────────────────────────────────────────────────────

class TestBuiltinTools:
    def test_calculator_basic(self, tools):
        t = tools.get("calculator")
        assert t.handler({"expression": "2+3"}) == "5"
        assert t.handler({"expression": "10*5+2"}) == "52"

    def test_calculator_sqrt(self, tools):
        t = tools.get("calculator")
        assert t.handler({"expression": "sqrt(16)"}) == "4.0"

    def test_calculator_unsafe_blocked(self, tools):
        t = tools.get("calculator")
        result = t.handler({"expression": "__import__('os').system('dir')"})
        assert "不允许的字符" in result

    def test_search_web_found(self, tools):
        t = tools.get("search_web")
        result = t.handler({"query": "Python 是什么"})
        assert "Python" in result

    def test_search_web_not_found(self, tools):
        t = tools.get("search_web")
        result = t.handler({"query": "xyzunknown"})
        assert "模拟" in result

    def test_get_time(self, tools):
        t = tools.get("get_time")
        result = t.handler({})
        assert len(result) > 0
        assert ":" in result


# ── Parser ────────────────────────────────────────────────────────────────

class TestReActParser:
    def test_parse_tool_call(self, parser):
        raw = ("Thought: 计算数学\n"
               "Action: calculator\n"
               "Action Input: {\"expression\": \"100*3\"}")
        a = parser.parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.TOOL_CALL
        assert a.tool_name == "calculator"
        assert a.tool_params == {"expression": "100*3"}
        assert a.thought == "计算数学"

    def test_parse_final_answer(self, parser):
        raw = "Thought: 已经知道答案了\nFinal Answer: 答案是 300"
        a = parser.parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.FINAL_ANSWER
        assert "300" in a.final_answer

    def test_parse_plain_text_fallback(self, parser):
        a = parser.parse("你好，有什么可以帮你的", TOOLS_SCHEMA)
        assert a.type == ActionType.FINAL_ANSWER

    def test_parse_unknown_tool_fallback(self, parser):
        raw = ("Action: nonexistent_tool\n"
               "Action Input: {\"x\": 1}")
        a = parser.parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.FINAL_ANSWER


# ── MockClient ─────────────────────────────────────────────────────────────

class TestMockClient:
    def test_direct_chat(self):
        client = MockClient()
        raw = client.chat([Message(role=Role.USER, content="你好")])
        a = ReActParser().parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.FINAL_ANSWER
        assert len(a.final_answer) > 0

    def test_tool_routing_calculator(self):
        client = MockClient()
        raw = client.chat([Message(role=Role.USER, content="计算 3+5")])
        a = ReActParser().parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.TOOL_CALL
        assert a.tool_name == "calculator"

    def test_tool_routing_search(self):
        client = MockClient()
        raw = client.chat([Message(role=Role.USER, content="搜索 Go语言")])
        a = ReActParser().parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.TOOL_CALL
        assert a.tool_name == "search_web"

    def test_tool_routing_time(self):
        client = MockClient()
        raw = client.chat([Message(role=Role.USER, content="几点了")])
        a = ReActParser().parse(raw, TOOLS_SCHEMA)
        assert a.type == ActionType.TOOL_CALL
        assert a.tool_name == "get_time"


# ── Agent Loop ────────────────────────────────────────────────────────────

class TestAgentLoop:
    def test_chat_no_tool(self, agent):
        state = AgentState(session_id="t1")
        mem = ShortTermMemory(max_turns=5)
        answer = agent.run("你好", state, mem)
        assert len(answer) > 0
        assert state.task_status == "done"

    def test_single_tool(self, agent):
        state = AgentState(session_id="t2")
        mem = ShortTermMemory(max_turns=5)
        answer = agent.run("计算 2+8", state, mem)
        assert len(answer) > 0
        assert state.task_status == "done"
        assert len(state.tool_calls) >= 1

    def test_loop_max_turns(self, tools, mock_client, parser, context_mgr, harness):
        strict_exec = Executor(ExecutorConfig(max_turns=1))
        a = Agent(mock_client, parser, tools, context_mgr, harness, strict_exec)
        state = AgentState(session_id="t3")
        mem = ShortTermMemory(max_turns=5)
        answer = a.run("计算 1+1 再算 2+2 再算 3+3", state, mem)
        assert state.task_status == "error"
        assert "轮次上限" in answer


# ── Session 隔离 ───────────────────────────────────────────────────────────

class TestSessionIsolation:
    def test_independent_memories(self):
        storage = SQLiteStorage(":memory:")
        mgr = SessionManager(storage, max_turns=5)

        s1, m1 = mgr.get_or_create("A")
        s2, m2 = mgr.get_or_create("B")

        m1.add(Message(role=Role.USER, content="msg A"))
        m2.add(Message(role=Role.USER, content="msg B"))

        assert m1.count() == 1
        assert m2.count() == 1
        assert m1.get_all()[0].content == "msg A"
        assert m2.get_all()[0].content == "msg B"
        assert s1.session_id != s2.session_id


# ── Context 截断 ──────────────────────────────────────────────────────────

class TestContextTruncation:
    def test_deque_truncation(self):
        mem = ShortTermMemory(max_turns=3)
        for i in range(20):
            mem.add(Message(role=Role.USER, content=f"msg {i}"))
        # max_turns=3 -> maxlen=6
        assert mem.count() <= 6


# ── Harness ────────────────────────────────────────────────────────────────

class TestHarness:
    def test_retry_on_error(self):
        call_count = [0]

        def fail_then_ok(_params):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("临时故障")
            return "ok"

        h = ToolHarness(HarnessConfig(max_retries=3, retry_delay_ms=10, tool_timeout_ms=5000))
        tool = Tool(name="t", description="", input_schema={}, handler=fail_then_ok)
        result = h.execute(tool, {})
        assert result.success
        assert result.content == "ok"
        assert call_count[0] == 2

    def test_timeout(self):
        def slow(_params):
            time.sleep(10)
            return "never"

        h = ToolHarness(HarnessConfig(max_retries=2, retry_delay_ms=10, tool_timeout_ms=500))
        tool = Tool(name="t", description="", input_schema={}, handler=slow)
        result = h.execute(tool, {})
        assert not result.success
        assert "超时" in result.error

    def test_all_retries_exhausted(self):
        def always_fail(_params):
            raise RuntimeError("永远失败")

        h = ToolHarness(HarnessConfig(max_retries=2, retry_delay_ms=10, tool_timeout_ms=5000))
        tool = Tool(name="t", description="", input_schema={}, handler=always_fail)
        result = h.execute(tool, {})
        assert not result.success
        assert "永远失败" in result.error


# ── 降级 ───────────────────────────────────────────────────────────────────

class TestGracefulDegradation:
    def test_mock_client_used_when_no_key(self):
        from config import Config
        from llm.client import MockClient
        cfg = Config(llm_api_url="", llm_api_key="")
        assert not cfg.is_real_llm()
        client = MockClient()
        assert isinstance(client.chat([Message(role=Role.USER, content="hello")]), str)

    def test_sqlite_unavailable_no_crash(self):
        storage = SQLiteStorage("/invalid_path_xyz/test_unlikely.db")
        assert not storage.available
        msg = Message(role=Role.USER, content="test")
        storage.save_message("s1", msg)
        assert storage.load_messages("s1") == []
        # Cleanup is no-crash (close on unavailable storage)
        storage.close()
