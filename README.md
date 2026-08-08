# Mini Agent Runtime

一个最小可用的 AI Agent 运行终端，实现 ReAct 循环、工具调用、会话管理和优雅降级。

## 特性

- **ReAct 循环**：Thought → Action → Observation → Final Answer，自动决定对话还是调工具
- **3 个内置工具**：calculator（安全计算）、search_web（模拟搜索）、get_time（系统时间）
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

## License

MIT
