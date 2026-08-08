"""内置工具：calculator（新）/ search_web（复用 final mock）/ get_time（复用 final get_time）。"""
import math as _math
import time as _time

from tools.base import Tool

_SAFE_MATH_FUNCTIONS: dict = {
    "abs": abs, "round": round, "min": min, "max": max,
    "pow": pow, "sum": sum,
    "sqrt": _math.sqrt, "sin": _math.sin, "cos": _math.cos,
    "tan": _math.tan, "log": _math.log, "log10": _math.log10,
    "ceil": _math.ceil, "floor": _math.floor,
}


def _calculator_handler(params: dict) -> str:
    expression = params.get("expression", "").strip()
    if not expression:
        return "错误：请提供计算表达式"

    allowed = set(
        "0123456789+-*/.() ,%^<>!=|&~ abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    )
    for ch in expression:
        if ch not in allowed:
            return f"错误：表达式包含不允许的字符 '{ch}'"

    try:
        result = eval(expression, {"__builtins__": {}}, _SAFE_MATH_FUNCTIONS)
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"


def _mock_search_handler(params: dict) -> str:
    query = params.get("query", "")
    db = {
        "AI应用工程师": "AI 应用工程师是将 AI 技术落地到业务的工程师，需具备 ML 基础、API 开发、Prompt 工程等能力。",
        "Go语言": "Go 是 Google 开发的开源编程语言，适用于高并发服务端应用。",
        "Python": "Python 是一种解释型、面向对象的高级编程语言，广泛应用于数据科学、AI、Web 开发。",
    }
    for k, v in db.items():
        if k in query:
            return v
    return f"关于「{query}」的搜索结果（模拟）"


def _get_time_handler(params: dict) -> str:
    tz = params.get("timezone", "")
    if tz:
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime())


def builtin_tools() -> list:
    return [
        Tool(
            name="calculator",
            description="计算数学表达式。支持加减乘除、括号、幂运算、sqrt、sin、cos 等函数。",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2+3*4' 或 'sqrt(16)'",
                    }
                },
                "required": ["expression"],
            },
            handler=_calculator_handler,
        ),
        Tool(
            name="search_web",
            description="搜索互联网信息，返回相关知识说明。",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题",
                    }
                },
                "required": ["query"],
            },
            handler=_mock_search_handler,
        ),
        Tool(
            name="get_time",
            description="获取当前系统时间，支持可选时区参数。不提供时区则返回本地时间。",
            input_schema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "可选时区，如 Asia/Tokyo",
                    }
                },
                "required": [],
            },
            handler=_get_time_handler,
        ),
    ]
