# Mini Agent Runtime

一个最小可用的 AI Agent 运行终端，实现 ReAct 循环、工具调用、会话管理和优雅降级。

## 特性

- **ReAct 循环**：Thought → Action → Observation → Final Answer，自动决定对话还是调工具
- **3 个内置工具**：calculator（安全计算）、search_web（Tavily 真实搜索，三级降级）、get_time（系统时间）
- **终端 REPL**：Claude Code 风格交互，rich 面板渲染
- **会话管理**：`/switch` 切换独立会话，SQLite 持久化历史
- **工具 Harness**：重试 + 超时保护（Windows/Linux 兼容）
- **优雅降级**：无 API Key → Mock 模式，SQLite 不可用 → 内存模式，API 故障 → 自动回退 Mock

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动（Mock 模式，无需 API Key）
python main.py
```

## 配置 LLM API

设置环境变量接入真实 LLM（兼容 OpenAI 接口标准的任意服务）：

```bash
export MINI_AGENT_API_URL="https://api.deepseek.com/v1/chat/completions"
export MINI_AGENT_API_KEY="sk-your-key"
export MINI_AGENT_MODEL="deepseek-v4-flash"  # 可选，默认 gpt-3.5-turbo
```

不配置则自动使用内置 MockClient，也能完整演示 ReAct 流程。

## 配置搜索 API

search_web 支持 Tavily 真实搜索，三级降级：**Tavily → LLM 知识库 → Mock 字典**

```bash
export MINI_AGENT_SEARCH_API_KEY="tvly-your-key"
```

不配置则自动降级到 LLM 回答或 Mock。

## 终端命令

| 命令 | 说明 |
|------|------|
| `/switch <名称>` | 创建或切换会话 |
| `/sessions` | 列出所有会话 |
| `/clear` | 清除当前会话历史 |
| `/help` | 显示帮助 |
| `/exit` | 退出 |

## 架构

```
CLI (main.py)
    │
    ▼
Runtime ─── Agent / AgentLoop / Executor
    │              ▲
    ├──────────────┤
    ▼              │
Capability ─── LLM / Parser / Tools / Context / Memory / Harness / Session
    │              ▲
    ├──────────────┤
    ▼              │
Infrastructure ─── SQLite
```

- **协议层**：`Message` + `AgentAction` 统一类型，隔离 Runtime 与 LLM 实现细节
- **分层间**：下层不知上层，Runtime 只依赖接口抽象，不绑定 ReAct 正则、OpenAI SDK 或工具函数

## 测试

```bash
python -m pytest tests/ -v
```

## 依赖

- Python 3.11+
- requests
- rich

## 可扩展性

| 扩展方向 | 接入方式 | 说明 |
|--------|---------|------|
| 新工具 | 实现 `Tool` + `ToolRegistry.register()` | 定义 JSON Schema 和 handler，注册即用 |
| 新 LLM | 实现 `LLMClient` 接口 | 只需 `chat(messages) -> str`，MockClient 即按此模式 |
| 新 Parser | 实现 `OutputParser` 接口 | 替换 ReAct 为其他决策格式，Runtime 无感知 |
| 新存储 | 替换 `SQLiteStorage` | 实现 `save_message/load_messages` 接口即可，如 MySQL、PostgreSQL |
| 新 Harness | 替换 `ToolHarness` | 自定义重试/超时策略，不影响 Loop |

核心原则：**Runtime 只依赖接口抽象**（`LLMClient`、`OutputParser`、`ToolRegistry` 等），不绑定具体实现。新增能力只需实现接口 + 注入 `Agent` 构造函数。

## License

MIT
