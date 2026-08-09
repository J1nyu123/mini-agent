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

## 演示

<video src="test.mp4" controls width="100%"></video>

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
| `/delete <名称>` | 删除会话 |
| `/sessions` | 列出所有会话 |
| `/clear` | 清除当前会话历史 |
| `/compress` | 压缩对话历史 |
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

## Prompt 与问题解决记录
### 设计方案
Prompt 与问题："在保持第一版功能闭环不变的前提下，将 Agent 改造成面向未来扩展的 Runtime 架构，整体架构建议保持清晰的分层结构。"

Prompt 与问题："用统一协议解耦 Runtime 与模型格式"

Prompt 与问题："基础设施降级，不会阻塞整个进程"

Prompt 与问题："这个方案有 harness 吗？加入工具调用重试，超时如何解决"

Prompt 与问题："/switch 创建独立 AgentState + ShortTermMemory 对，SQLite 持久化历史。后续补充 /delete 删除会话（级联清除消息和日志）、/clear 清除当前、/compress 压缩历史"

Prompt 与问题："ShortTerm 存消息，Context 决定发什么"

Prompt 与问题："终端交互使用 rich 面板渲染：工具调用 trace 用 [>>]/[!!] 绿色/红色面板，最终回答用 [Answer] 青色面板。>/ 命令行模式。"
### 问题解决
Prompt 与问题："现在几点" → 400 错误	ReAct 格式的 role:"tool" 缺 tool_call_id，DeepSeek 校验不通过	
解决：改用 role:"user" + Observation: 前缀

Prompt 与问题："现在几点" → 404 / SSL 错误	API 地址写成平台网页而非接口端点	
解决：修正为 api.deepseek.com/v1/chat/completions

Prompt 与问题："你好" → SSL 连接断开	
解决：网络代理干扰 HTTPS 握手	OpenAIClient 加 try/except 兜底，任何异常回退 MockClient

Prompt 与问题："增加主动压缩的 / 命令"
解决：加 /compress 手动触发 + compress_threshold 自动触发

## 架构设计题

### 模块一：Context / Performance
Q：一个 session 连续聊了 200 轮，context 快爆了。你会怎么做压缩？如何确保压缩后的对话仍然流畅？
A：
- 在上下文装配时，我会对不同类型的上下文定义 Token 预算与截断优先级（优先级1：绝对保护，不压缩，不截断；优先级2：只保留近 $N$ 轮对话；优先级3：按得分淘汰截断）
- 在 ReAct 或 TaskGraph 执行过程中，占用 Token 最多的是工具调用的返回结果，我会采用“写入即压缩” 的策略，将型提炼出来的结构化核心结论压入 Task 环形缓冲区
- 召回阶段使用`声明式硬过滤`筛掉 80%~90% 的无关记忆
- 删除衰减和过期的记忆

### 模块二：Memory
Q：和聊天 Agent 熟悉半个月后，用户问了一个以前问过的问题。Agent 如何做 memory 召回更合理？
A：
- 我会在设计记忆系统的时候，在记忆存入的时候加入衰减和初始重要度以及对该记忆进行分类，重要度用于保证这个问题的记忆在衰减之后不会被埋没，分类用于快速检索
- 在召回时，使用多路并行检索，第一路：短期历史，虽然半个月以前的早被移出了，但还是要拉取上下文，确定用户提问的语境。第二路：长期语义记忆，计算当前 Query 的 Embedding，使用声明式过滤产生少量优质候选，计算向量相似度和综合得分（综合得分由相似度和重要性得分加权），通过阈值筛选的放入最终的召回结果。
- 还可以设计知识图谱存记忆，在存入时构建关系边和时序边。在召回时拿去相似度高的记忆种子，在知识图谱中找出关联的邻居，对邻居记忆打分。对所有记忆合并去重，排序，TopK 截断，排序时 种子记忆排前面，拓展记忆排后面。

### 模块三：Task 
Q：用户给 Agent 下达任务：每天早上 9 点根据昨天聊天情况做复盘总结。你会怎么设计？
A：
设计成一个持久化的 Scheduled Task + 每次触发时动态构造上下文 + 创建一次普通 Agent Turn
1. 首先把`每天早上 9 点根据昨天聊天情况做复盘总结`,解析成一个结构化任务
2. 获取`昨天聊天情况`:标记聊天的起始时间，从数据库中取出这部分，剔除闲聊和无意义的确认词（如“好的”、“收到”）按以下结构整理，拼接成Prompt：
       ├── 昨天的对话
       ├── 用户提出的问题
       ├── Agent 完成的任务（包含工具调用记录等）
       ├── 未完成任务
       ├── 用户明确的计划
       └── 重要决策   
3. 可以选择将总结的内容写回记忆中，实现自我总结
4. 早上 9 点时，如果用户在 UI 界面上，通过 SSE / WebSocket 实时推送到前端，并且将总结内容作为上下文注入到上下文

### 模块四：Tool / Session Runtime
Q：Agent 工具有同步和异步两类。异步工具不能让用户一直等，但结果依然重要。你会如何设计异步工具执行和完成通知？
A：设计为 “异步任务挂起（Suspend） $\rightarrow$ 状态持久化 $\rightarrow$ 回调唤醒（Resume） $\rightarrow$ 记忆反哺与主动推送” 的完整闭环
1. 节点挂起：当 Agent 的节点识别到这是一个长耗时异步工具时，工具提交后立刻返回一个 jobID，TaskGraph 将该节点状态标记为挂起，Agent 主 Task 解绑当前 HTTP/SSE 链接，去处理其他请求
2. 状态落盘与上下文持久化：断点恢复能力，在数据库中插入一条记录：
AsyncJob{JobID: "job_123", NodeID: "n_5", TaskID: "task_888", UserID: "u_999", Status: "PENDING"}，将当前的 TaskMemBuffer 状态和 Prompt 前缀上下文快照持久化，等待后续唤醒
3. 完成通知：异步工具执行完毕后主动请求 Agent 的 Webhook 接口
4. 当获取到异步工具的最终执行结果后，提取异步结果并填入节点，将节点标记为完成以解除依赖阻塞，唤醒拓扑引擎继续往下执行。将执行结果追加至任务缓冲区，并在经过安全校验后提炼写入长期向量库与图数据库，实现知识落盘。依据用户实时在线状态，通过 SSE/WebSocket 弹窗通知在线用户，或通过邮件/消息推送通知离线用户。

### 模块五：Agent Runtime 架构对比
Q：Claude Code 的工具输出方式和国内 GLM / 豆包等 OpenAI-compatible function calling 有什么不同？他们各自这样设计的优缺点是什么？
A：
- Claude Code 的输出是是具体的 Shell 命令或修改指令，本地 CLI 监控捕获执行后直接输出结果。
优点：
1. 接近原生 Shell 操作，Claude 可以像人类程序员一样进行 grep -> find -> read -> edit -> test 这一连串流畅的链式操作，无需频繁交还控制权。
2. 支持 MCP（Model Context Protocol）协议，插件和工具的扩展不需要重新设计 JSON Schema，能动态加载本地/远程工具。
缺点：
1. 模型直接具备了执行 Bash 命令的能力，存在潜在的系统命令注入风险，极度依赖客户端的 Permission（权限审批）层防护。
2. 解析与容错机制复杂，模型输出格式稍微偏移，解析层必须做复杂的容错补偿。
3. 迁移与通用性较差，很难直接套用到其他轻量级开源模型上。

- OpenAI-compatible 的输出为通过 JSON Schema 定义好 functions。当模型需要调用时，强制产生一个 tool_call 的 JSON 响应（包含函数名与参数）。
优点：
1. 稳定性高，通过 JSON Schema 严格校验输入参数，不容易产生无效的语法错误，极少破坏代码数据类型。
2. 前后端与系统解耦
3. 生态兼容性极佳，由于 OpenAI 定义了事实上的标准（messages + tools），国内如 GLM、豆包、通义千问等模型可以直接无缝切入同一套 SDK 和 Agent 框架
缺点：
1. 调用工具频繁交互，Token 成本高
2. 灵活性受限于 Schema