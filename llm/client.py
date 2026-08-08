"""LLM Client：OpenAIClient 参考 final/internal/llm/llm.py _call_chat，
MockClient 扩展自 _mock 使其能路由到 ReAct 工具调用。"""
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List

import requests

from protocol.message import Message, Role

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: List[Message]) -> str:
        ...


class OpenAIClient(LLMClient):
    def __init__(self, api_url: str, api_key: str, model: str,
                 temperature: float = 0.7, timeout: int = 60):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self._timeout = timeout
        self._mock = None  # 惰性创建，避免 MockClient 未定义

    def chat(self, messages: List[Message]) -> str:
        try:
            return self._call_api(messages)
        except Exception as e:
            logger.error("LLM API 调用失败: %s，回退到 Mock", e)
            if self._mock is None:
                self._mock = MockClient()
            return self._mock.chat(messages)

    def _call_api(self, messages: List[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in messages
            ],
            "temperature": self.temperature,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        resp = requests.post(
            self.api_url, headers=headers, json=payload,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API 返回 {resp.status_code}: {resp.text}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("LLM API 返回空 choices")
        return choices[0].get("message", {}).get("content", "")


class MockClient(LLMClient):
    def __init__(self):
        self._responses = {
            "你是谁": "我是一个智能 AI 助手，可以调用工具完成任务。",
        }

    def chat(self, messages: List[Message]) -> str:
        # 若历史中已有工具观察结果，则据此生成最终回答（模拟真实 LLM 的终止行为）
        for m in reversed(messages):
            if m.tool_name is not None and m.content:
                return (
                    f"Thought: 根据工具返回的结果，我已有足够信息回答用户。\n"
                    f"Final Answer: 工具返回：{m.content}"
                )

        user_msg = ""
        for m in reversed(messages):
            if m.role == Role.USER:
                user_msg = m.content
                break

        for keyword, response in self._responses.items():
            if keyword in user_msg:
                return response

        tool_keywords = {
            "计算": ("calculator", self._extract_calc_params),
            "算": ("calculator", self._extract_calc_params),
            "几点了": ("get_time", lambda _: {}),
            "时间": ("get_time", lambda _: {}),
            "几点": ("get_time", lambda _: {}),
            "搜索": ("search_web", self._extract_search_params),
            "查": ("search_web", self._extract_search_params),
            "什么是": ("search_web", self._extract_search_params),
        }

        for kw, (tool_name, param_fn) in tool_keywords.items():
            if kw in user_msg:
                params = param_fn(user_msg)
                return (
                    f"Thought: 用户想要使用 {tool_name} 工具\n"
                    f"Action: {tool_name}\n"
                    f"Action Input: {json.dumps(params, ensure_ascii=False)}"
                )

        return (
            f"Thought: 用户的问题可以直接回答\n"
            f"Final Answer: 收到：「{user_msg}」——这是模拟回复，配置真实 LLM API 后会更好。"
        )

    @staticmethod
    def _extract_calc_params(text: str) -> dict:
        expr = re.search(r'[\d+\-*/().\s]+', text)
        return {"expression": expr.group().strip() if expr else text}

    @staticmethod
    def _extract_search_params(text: str) -> dict:
        return {"query": text}
