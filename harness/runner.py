"""ToolHarness——工具执行：重试 + 超时保护（Windows 兼容，用 ThreadPoolExecutor）。"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass

from tools.base import Tool, CallResult

logger = logging.getLogger(__name__)


@dataclass
class HarnessConfig:
    max_retries: int = 3
    retry_delay_ms: int = 200
    tool_timeout_ms: int = 10000


class ToolHarness:
    def __init__(self, config: HarnessConfig):
        self.config = config

    def execute(self, tool: Tool, params: dict) -> CallResult:
        last_error = ""
        for attempt in range(self.config.max_retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(tool.handler, dict(params))
                    content = str(future.result(
                        timeout=self.config.tool_timeout_ms / 1000))
                logger.info(
                    "工具 %s 调用成功 (attempt %d/%d) params=%s",
                    tool.name, attempt + 1, self.config.max_retries, params,
                )
                return CallResult(success=True, content=content)
            except FutureTimeoutError:
                last_error = f"工具 {tool.name} 执行超时（{self.config.tool_timeout_ms}ms）"
                logger.warning(
                    "工具 %s 超时 (attempt %d/%d)",
                    tool.name, attempt + 1, self.config.max_retries,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "工具 %s 执行异常 (attempt %d/%d): %s",
                    tool.name, attempt + 1, self.config.max_retries, e,
                )
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay_ms / 1000)

        logger.error("工具 %s 所有重试已耗尽: %s", tool.name, last_error)
        return CallResult(success=False, content="", error=last_error)
