"""Mini Agent CLI——终端 REPL 入口。"""
import logging
import os
import sys

from config import Config
from runtime.agent import Agent
from runtime.executor import Executor, ExecutorConfig
from llm.client import MockClient, OpenAIClient
from llm.parser import ReActParser
from tools.registry import ToolRegistry
from tools.builtin import builtin_tools
from context.manager import ContextManager
from harness.runner import ToolHarness, HarnessConfig
from memory.storage import SQLiteStorage
from session.manager import SessionManager
from protocol.message import Message, Role

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_system_template() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "prompts", "system.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def create_llm_client(cfg: Config):
    if cfg.is_real_llm():
        try:
            return OpenAIClient(
                api_url=cfg.llm_api_url,
                api_key=cfg.llm_api_key,
                model=cfg.llm_model,
                temperature=cfg.temperature,
            )
        except Exception as e:
            logger.warning("LLM 连接失败，降级为 Mock: %s", e)
    return MockClient()


def print_banner(console):
    console.print("[bold cyan]Mini Agent Runtime[/bold cyan]")
    console.print("输入 [bold]/help[/bold] 查看命令，Ctrl+C 退出")
    console.print()


def print_help(console):
    console.print("[bold]可用命令：[/bold]")
    console.print("  [bold]/switch[/bold] <名称>   - 切换会话")
    console.print("  [bold]/sessions[/bold]        - 列出所有会话")
    console.print("  [bold]/clear[/bold]           - 清除当前会话历史")
    console.print("  [bold]/help[/bold]            - 显示帮助")
    console.print("  [bold]/exit[/bold]            - 退出程序")


def render_step(console, prefix: str, text: str, style: str):
    from rich.panel import Panel
    console.print(Panel(text, title=prefix, style=style))


def main():
    cfg = Config()

    llm = create_llm_client(cfg)

    tools = ToolRegistry()
    for t in builtin_tools(cfg=cfg, llm=llm):
        tools.register(t)

    parser = ReActParser()
    context_mgr = ContextManager(load_system_template())
    harness = ToolHarness(HarnessConfig(
        max_retries=cfg.max_retries,
        retry_delay_ms=cfg.retry_delay_ms,
        tool_timeout_ms=cfg.tool_timeout_ms,
    ))
    executor = Executor(ExecutorConfig(max_turns=cfg.max_turns))

    agent = Agent(llm, parser, tools, context_mgr, harness, executor)
    storage = SQLiteStorage(cfg.db_path)
    sessions = SessionManager(storage, max_turns=cfg.short_term_max_turns)

    from rich.console import Console
    console = Console()
    print_banner(console)

    try:
        while True:
            try:
                user_input = console.input("[bold green]>[/bold green] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]再见！[/dim]")
                break

            if not user_input:
                continue

            if user_input == "/exit":
                console.print("[dim]再见！[/dim]")
                break
            elif user_input == "/help":
                print_help(console)
                continue
            elif user_input == "/sessions":
                names = sessions.list_names()
                current = sessions.current_name()
                for n in names:
                    marker = " [bold cyan]*[/bold cyan]" if n["name"] == current else ""
                    console.print(f"  {n['name']}{marker}")
                continue
            elif user_input.startswith("/switch "):
                name = user_input[len("/switch "):].strip()
                if name:
                    sessions.switch(name)
                    console.print(f"[bold]已切换到「{name}」[/bold]")
                continue
            elif user_input == "/clear":
                _, mem = sessions.current()
                mem.clear()
                console.print("[dim]当前会话已清除[/dim]")
                continue

            # Normal chat input
            state, memory = sessions.current()
            sessions.save_message(sessions.current_name(),
                                  Message(role=Role.USER, content=user_input))

            answer = agent.run(user_input, state, memory)

            sessions.save_message(sessions.current_name(),
                                  Message(role=Role.ASSISTANT, content=answer))
            for log in state.tool_calls:
                sessions.save_tool_call(sessions.current_name(), log)

            # Render tool call traces
            for i, log in enumerate(state.tool_calls):
                icon = "[>>]" if log.success else "[!!]"
                details = (
                    f"参数: {log.params}\n"
                    f"耗时: {log.duration_ms}ms\n"
                    f"结果: {log.result}"
                )
                render_step(
                    console,
                    f"{icon} {log.tool_name}",
                    details,
                    "green" if log.success else "red",
                )

            # Render final answer
            render_step(console, "[Answer]", answer, "cyan")

    finally:
        sessions.close()


if __name__ == "__main__":
    main()
