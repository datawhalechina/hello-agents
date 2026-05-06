# HelloAgents Optimized

> 基于 [HelloAgents](https://github.com/jjyaoao/HelloAgents) v0.2.9 的全面优化与功能扩展 —— 轻量级、可扩展的多智能体框架

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI-Compatible-green.svg)](https://platform.openai.com/docs/api-reference)

HelloAgents Optimized 在保留原项目"一切皆为工具"轻量级哲学的基础上，对核心架构、智能体范式、工具系统、记忆系统、上下文工程、评估系统、强化学习、课程学习等多个维度进行了全面增强，新增 **30+ 测试文件**确保代码质量。

> 📖 本项目是对 [Datawhale Hello-Agents 教程](https://github.com/datawhalechina/hello-agents/tree/main/docs) **前 12 章课后习题**的实践总结与系统化整理，涵盖从基础 Agent 构建到强化学习训练的完整学习路径。

---

## 目录

- [快速开始](#快速开始)
- [Agent 范式](#agent-范式)
- [核心优化亮点](#核心优化亮点)
- [项目结构](#项目结构)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 快速开始

### 系统要求

- **Python 3.10+**（必需）
- 支持的操作系统：Windows、macOS、Linux

### 环境配置

创建 `.env` 文件：

```bash
LLM_MODEL_ID=your-model-name
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=your-api-base-url
```

### 基本使用

```python
from hello_agents import SimpleAgent, HelloAgentsLLM

llm = HelloAgentsLLM()  # 自动检测 provider

agent = SimpleAgent(
    name="AI助手",
    llm=llm,
    system_prompt="你是一个有用的AI助手"
)

response = agent.run("你好！请介绍一下自己")
print(response)
```

### 流式输出

```python
for chunk in agent.stream_run("什么是人工智能？"):
    print(chunk, end="", flush=True)
```

---

## Agent 范式

| Agent | 说明 |
|-------|------|
| **SimpleAgent** | 基础对话智能体，智能工具调用检测 |
| **ReActAgent** | 推理与行动结合，适合需要外部信息的任务 |
| **ReflectionAgent** | 自我反思与迭代优化，适合代码生成、文档写作 |
| **PlanAndSolveAgent** | 问题分解规划与逐步执行 |
| **FunctionCallAgent** | 多轮工具调用，精细 tool_choice 控制 |
| **ToolAwareSimpleAgent** | 深度工具感知增强 |
| **TreeOfThoughtAgent** 🆕 | 树形思维推理（多分支 + BFS/DFS + 回溯） |

### 工具使用示例

```python
from hello_agents import ReActAgent, ToolRegistry, SearchTool, CalculatorTool

registry = ToolRegistry()
registry.register_tool(SearchTool())
registry.register_tool(CalculatorTool())

agent = ReActAgent(name="研究助手", llm=llm, tool_registry=registry, max_steps=5)
result = agent.run("搜索最新的GPT-4发展情况，并计算其参数量相比GPT-3的增长倍数")
```

---

## 核心优化亮点

### 1. 核心架构增强

- **对话管理系统**：`Conversation` + `ConversationManager`，支持消息分叉（fork/branch）、多会话管理、JSON 持久化
- **流式事件系统**：标准化 `StreamEvent` 数据模型（text / thought / action / tool_call / tool_result / status / error / done）
- **插件系统**：`Plugin` + `PluginRegistry`，6 个生命周期钩子，自动发现已安装插件
- **LLM 客户端**：提供商从 10 个扩展至 **12+ 个**，新增 custom 自定义提供商

### 2. 工具系统扩展（+5 个新工具）

| 新增工具 | 功能 |
|----------|------|
| **NoteOrganizer** | 自动笔记分类与去重 |
| **SecureTerminalTool** | 带审批流程的安全命令行执行 |
| **ApprovalManager** | 审批工作流系统 |
| **TaskDepManager** | 任务依赖关系管理 |
| **MultiJudgeTool** | 多裁判集成评估 |

### 3. 记忆系统重构

- **4 种模块化记忆类型**：Working / Episodic / Semantic / Perceptual
- **统一记忆管理器**：`MemoryManager`，支持遗忘清理、归档恢复
- **多存储后端**：SQLite + Qdrant 向量库 + Neo4j 图数据库
- **归档 + 安全擦除**：冷热存储策略、GDPR 合规辅助

### 4. 上下文工程增强

- **混合压缩器**：截断 / 滑动窗口 / LLM 摘要 / 延迟自适应
- **上下文评估器**：相关性 / 完整性 / Token 效率质量报告
- **智能检索路由**：意图分类 + 上下文分析 + 多策略路由

### 5. 评估系统完善

- **BFCL 扩展**：AST 匹配器、边缘用例样本、深度评估
- **GAIA 扩展**：智能评估器、多维度答案匹配、医疗领域评估
- **持续评估系统**：分层评估、定时调度、性能趋势检测、异常告警
- **报告生成**：开发者 / 产品经理 / 终端用户三层受众模板

### 6. 强化学习扩展

- **在线学习系统**：质量过滤 + 安全守卫 + 增量训练 + 用户反馈闭环
- **层级强化学习**：高/低层策略、层级 GRPO 训练器、课程任务生成
- **SFT 扩展**：监督微调数据集扩展

### 7. 课程学习系统 🆕

从简单任务逐步过渡到复杂任务，包含 `CurriculumPlanner`、`TaskGenerator`、`TransitionEvaluator`、`DifficultyAdapter`、`ProgressTracker`、`CurriculumTrainer`、`CurriculumVisualizer` 七大组件。

### 8. 解决方案

- **代码重构助手**（`solutions/code_refactor_assistant.py`）：集成 NoteTool + SecureTerminalTool + ApprovalManager 的自动化代码重构管理

---

## 项目结构

```
HelloAgents-Optimized/
├── hello_agents/            # 主包
│   ├── core/                # 核心组件（LLM、Agent基类、消息、配置）
│   │   ├── llm.py           # LLM 统一抽象层（12+ 提供商）
│   │   ├── agent.py         # Agent 基类
│   │   ├── conversation.py  # 对话管理 🆕
│   │   ├── conversation_manager.py  # 多会话管理 🆕
│   │   ├── stream.py        # 流式事件系统 🆕
│   │   └── plugin.py        # 插件系统 🆕
│   ├── agents/              # Agent 实现（7 种范式）
│   │   ├── simple_agent.py
│   │   ├── react_agent.py
│   │   ├── reflection_agent.py
│   │   ├── plan_solve_agent.py
│   │   ├── function_call_agent.py
│   │   ├── tool_aware_agent.py
│   │   └── tree_of_thought_agent.py  # 🆕
│   ├── tools/               # 工具系统（19 个内置工具）
│   │   ├── registry.py      # 工具注册表
│   │   ├── base.py          # 工具基类
│   │   ├── chain.py         # 工具链
│   │   ├── async_executor.py  # 并行工具执行
│   │   └── builtin/         # 内置工具
│   ├── memory/              # 记忆系统 🆕
│   │   ├── manager.py       # 统一记忆管理器
│   │   ├── types/           # 4 种记忆类型
│   │   ├── storage/         # 多存储后端
│   │   ├── archive.py       # 归档系统
│   │   ├── secure_wipe.py   # 安全擦除
│   │   └── rag/             # RAG 子系统
│   ├── context/             # 上下文工程 🆕
│   │   ├── compressor.py    # 混合压缩器
│   │   ├── evaluator.py     # 上下文评估器
│   │   └── retrieval_router.py  # 智能检索路由
│   ├── evaluation/          # 评估系统 🆕
│   ├── rl/                  # 强化学习 🆕
│   ├── curriculum/          # 课程学习 🆕
│   ├── reward_functions/    # 奖励函数 🆕
│   └── solutions/           # 解决方案 🆕
├── tests/                   # 30+ 测试文件
└── README.md
```

---

## 与原版对比

| 维度 | HelloAgents（原版） | HelloAgents Optimized |
|------|-------------------|----------------------|
| **Agent 范式** | 6 种 | **7 种**（+TreeOfThought） |
| **LLM 提供商** | 10 个 | **12+ 个** |
| **内置工具** | 14 个 | **19 个** |
| **插件系统** | ❌ | ✅ |
| **对话管理** | 简单消息列表 | 多会话 / 分叉 / 归档 |
| **流式事件** | 基础 | 标准化 StreamEvent |
| **记忆类型** | 混合 | 4 种模块化类型 |
| **记忆存储** | Qdrant / Neo4j | + SQLite / 归档 / 安全擦除 |
| **上下文工程** | GSSC 管道 | + 混合压缩 / 评估器 / 检索路由 |
| **评估系统** | BFCL / GAIA 基础 | + AST 匹配 / 医疗 GAIA / 持续评估 / 报告生成 |
| **强化学习** | SFT / GRPO / PPO | + 在线学习 / 层级 RL / SFT 扩展 |
| **课程学习** | ❌ | ✅ 完整系统 |
| **奖励函数** | 基础 | + 细粒度 / 防御奖励 |
| **解决方案** | ❌ | ✅ 代码重构助手 |
| **测试覆盖** | ❌ | **30+ 测试文件** |

---

## 许可证

本项目基于 [HelloAgents](https://github.com/jjyaoao/HelloAgents) 修改，采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可证。

- ✅ **署名**（Attribution）：使用时需注明原作者
- ✅ **相同方式共享**（ShareAlike）：修改后作品需使用相同许可证
- ⚠️ **非商业性使用**（NonCommercial）：不得用于商业目的

---

## 致谢

- 感谢 [Datawhale](https://github.com/datawhalechina) 提供的优秀开源教程，本项目的代码是对 [Hello-Agents 教程前 12 章](https://github.com/datawhalechina/hello-agents/tree/main/docs) 课后习题的系统化实现
- 感谢 [HelloAgents](https://github.com/jjyaoao/HelloAgents) 原项目的所有贡献者
- 感谢所有为智能体技术发展做出贡献的研究者和开发者

---

<div align="center">

**HelloAgents Optimized** — 让智能体开发更强大、更灵活 🚀

</div>
