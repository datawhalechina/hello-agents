# MCP Tasks：让长时间工具调用可轮询、可恢复

> 本文解读 MCP Tasks 扩展及其在 2026-07-28 MCP 规范中的变化，聚焦一个具体问题：部署、批处理或长时间研究等工具调用可能超过一次 HTTP 请求的等待时间，客户端断线后也需要继续取得结果。内容是对 Hello-Agents 第十章 MCP 部分的增补，不替代现有章节。

## 一、为什么需要 Task 句柄

一次普通的 <code>tools/call</code> 请求通常要等工具执行完才返回结果。对快速查询很合适；对模型推理、批量处理、云部署、长时间检索等工作，长连接会遇到网关超时、客户端断线和重复提交等问题。

MCP Tasks 把调用的执行状态单独表示为一个有期限的 Task。服务端可以在工作完成前返回 <code>taskId</code>，客户端之后用这个 ID 查询状态和最终结果。Task 是协议层的工作句柄；它不负责替服务端实现队列、工作进程、重试策略或业务上的任务编排。

~~~mermaid
sequenceDiagram
    participant C as MCP 客户端
    participant S as MCP 服务端
    participant W as 工具工作进程
    C->>S: tools/call + Tasks 扩展能力
    S->>W: 持久化任务并启动工作
    S-->>C: resultType=task, taskId, pollIntervalMs
    loop 直到终态
        C->>S: tasks/get(taskId)
        S-->>C: working / input_required / completed / failed
        C->>C: 按 pollIntervalMs 等待
    end
~~~

客户端声明支持 Tasks 后，服务端仍可以对某次调用返回普通结果，也可以返回 Task 句柄。是否异步由服务端按调用决定；支持扩展不等于要求所有工具都走异步。

## 二、2026-07-28 规范中的生命周期

MCP 2026-07-28 将 Tasks 从实验性的核心能力迁移到扩展 <code>io.modelcontextprotocol/tasks</code>。这让 Tasks 可以独立演进。不要把旧实验版 API 和新扩展版请求体混在一起：新版客户端在请求的 <code>_meta.io.modelcontextprotocol/clientCapabilities.extensions</code> 中声明该扩展；服务端可通过 <code>server/discover</code> 暴露自己的扩展能力。

### 1. 创建任务

客户端发出 <code>tools/call</code>，并在该请求的 <code>_meta</code> 中声明 Tasks 扩展。服务端判断这次工作是否适合异步处理。如果返回 Task，结果的 <code>resultType</code> 为 <code>task</code>，其中包括随机生成的 <code>taskId</code>、当前状态、保留时长 <code>ttlMs</code> 和建议轮询间隔 <code>pollIntervalMs</code>。

服务端必须先把任务持久化到可查询的存储，再返回这个 ID；否则客户端可能收到 ID 后马上查询，却发现任务不存在。客户端也应该把 ID 保存到可恢复的状态中，断线或进程重启后才能继续查询。服务端可以在 TTL 到期后清理任务。

### 2. 查询、等待和完成

客户端调用 <code>tasks/get</code> 获取 Task 快照，并遵循响应里的 <code>pollIntervalMs</code> 继续轮询。常见状态如下：

| 状态 | 含义 | 客户端动作 |
| --- | --- | --- |
| <code>working</code> | 工具仍在执行 | 等待建议间隔后再次查询 |
| <code>input_required</code> | 服务端需要补充输入 | 读取 <code>inputRequests</code>，用 <code>tasks/update</code> 提交对应回答 |
| <code>completed</code> | 调用已完成 | 从 <code>result</code> 读取与原同步调用相同形状的结果 |
| <code>failed</code> | 执行中出现 JSON-RPC 错误 | 从 <code>error</code> 读取错误信息 |
| <code>cancelled</code> | 任务已取消 | 结束等待 |

<code>tasks/get</code> 是轮询基础流程。服务器也可以通过 <code>subscriptions/listen</code> 为客户端推送 <code>notifications/tasks</code>；每条通知包含完整 Task 状态。通知是可选优化，客户端不应因为没有通知而失去恢复能力。

### 3. 取消是协作式请求

<code>tasks/cancel</code> 用于表达取消意图。服务端会确认收到请求，但取消处理是最终一致的：确认返回时任务可能仍显示 <code>working</code>，也可能在取消生效前已经完成。规范不保证每次取消都能中止底层工作。客户端是否还要继续轮询，应由产品需求决定。

### 4. 错误状态和工具错误结果不同

这里有一个容易写错的区别：

- 如果执行过程出现 JSON-RPC 错误，Task 状态为 <code>failed</code>，并附带 <code>error</code>。
- 如果工具正常返回了 <code>CallToolResult</code>，即使其中 <code>isError: true</code>，Task 仍是 <code>completed</code>，原工具结果放在 <code>result</code> 中。

前者表示协议或调用执行失败；后者表示工具完成了调用，但把业务错误作为结果返回。

## 三、它如何和现有 MCP 教程衔接

Hello-Agents[第十章智能体通信协议](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/%E7%AC%AC%E5%8D%81%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE.md)已经讲解 MCP 客户端、工具调用和传输方式。Tasks 延伸的是同一条 MCP 工具调用链：把“请求必须等到结果”扩展成“先拿句柄，再取状态和结果”。

| 调用方式 | 调用返回 | 连接中断后的恢复 | 合适场景 |
| --- | --- | --- | --- |
| 普通同步 <code>tools/call</code> | 完成后的工具结果 | 通常需要重新调用或由客户端自行处理 | 快速、短时工具 |
| MCP Tasks 扩展 | 普通结果，或带 <code>taskId</code> 的 Task 快照 | 客户端持久化 ID 后可继续 <code>tasks/get</code> | 长时任务、间歇网络、人工等待 |
| Agent 规划循环 | Agent 自己选择下一步工具和停止条件 | 由 Agent 状态或运行时管理 | 多步计划和动态工具选择 |

Tasks 不会决定 Agent 下一步该做什么，也不是 Agentic RAG 或 A2A 的替代品。它只规定某次支持的工具调用怎样返回可延续的执行状态。目前扩展定义的 Task 增强执行支持 <code>tools/call</code>。

### Streamable HTTP 路由提示

2026-07-28 规范取消了 MCP 核心层的会话 ID，HTTP 请求包含 <code>MCP-Protocol-Version: 2026-07-28</code>，并使用 <code>Mcp-Method</code> 和 <code>Mcp-Name</code> 标头。对 <code>tasks/get</code>、<code>tasks/update</code>、<code>tasks/cancel</code>，<code>Mcp-Name</code> 应设置为 <code>taskId</code>，便于负载均衡器把请求路由到保存任务状态的服务实例。只在 JSON-RPC 请求体里传 Task ID，而忽略路由标头，可能导致请求落到没有该状态的实例。

## 四、实现时的工程边界

1. **先持久化，再返回 ID**：任务记录必须在工作线程或队列启动后仍可查询。真实部署应使用数据库或可恢复的任务存储，不能只放进单进程内存字典。
2. **轮询要尊重服务器提示**：按 <code>pollIntervalMs</code> 请求，设置客户端总超时、退避和停止条件，避免大量客户端高频轮询。
3. **考虑 TTL 与重启**：客户端重启后继续查询前，要考虑任务是否已过期；任务状态、结果保留策略应和业务要求一致。
4. **每次请求都验证身份**：<code>taskId</code> 应难以猜测，但规范仍要求对每次 Task 请求做身份和权限校验。不要把“拿到 taskId”当作唯一授权。
5. **取消不等于强制杀进程**：工具工作进程应检查取消信号并安全收尾；调用方需容忍任务在确认取消前已完成。
6. **区分终态**：JSON-RPC 错误才是 <code>failed</code>；工具结果中的 <code>isError</code> 仍是一次已完成的调用。
7. **核对版本和 SDK 支持**：截至 2026-10-18，核心 MCP 2026-07-28 版本已发布；Tasks 的 SEP-2663 状态为 Final，但扩展站点的完整规范页面仍标为 Draft。不同语言 SDK 的实现节奏可能不同，上线前应确认 SDK 和部署端支持的是扩展版，而不是 2025-11-25 的实验版。

新版不再提供 <code>tasks/list</code>。这减少了跨调用枚举其他用户 Task ID 的风险，但意味着客户端必须保存自己需要恢复的 ID。扩展规范还要求服务端对 Task ID 使用足够熵，并在每个 Task 请求重新进行授权检查。

## 五、最小运行示例

配套脚本 <code>code/extra14_mcp_tasks_demo.py</code> 使用 Python 标准库，启动一个仅监听本机的 JSON-RPC HTTP 小服务。客户端声明 Tasks 能力后调用 <code>tools/call</code>，拿到 Task ID，再按建议间隔调用 <code>tasks/get</code>；加上 <code>--no-extension</code> 参数可以观察同步兼容路径。

~~~bash
python code/extra14_mcp_tasks_demo.py
python code/extra14_mcp_tasks_demo.py --no-extension
~~~

异步模式的输出结构如下（端口、Task ID 和轮询次数会变化）：

~~~text
server returned resultType=task
task status=working
...
task status=completed
result=Report ready for: protocol migration
~~~

这份小程序刻意只覆盖 <code>tools/call</code>、Task 句柄和轮询，**不是符合性测试，也不是完整 MCP SDK 服务端**。它用进程内存保存 Task，不实现真正的持久化、认证、TTL 清理、<code>input_required</code>、<code>subscriptions/listen</code> 或正式扩展协商；这些边界在生产实现中不能省略。

## 参考资料

1. [Model Context Protocol 2026-07-28 规范发布说明](https://blog.modelcontextprotocol.io/posts/2026-07-28/)：无会话核心、扩展机制与 Tasks 迁移。
2. [MCP Tasks 扩展规范](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks)：Task 状态、能力声明、轮询、更新、取消、HTTP 路由与安全要求。该页面当前标记为 Draft。
3. [SEP-2663：Tasks Extension](https://tasks.extensions.modelcontextprotocol.io/seps/2663-tasks-extension)：扩展的设计动机及旧实验 API 的迁移背景。
4. Hello-Agents：[第十章智能体通信协议](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/%E7%AC%AC%E5%8D%81%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE.md)。

本文自行绘制流程图，未复制规范或课程中的原图。


