# Hello-Agents 知识索引

> Datawhale 社区《从零开始构建智能体》教程
> 在线阅读：https://datawhalechina.github.io/hello-agents/
> GitHub：https://github.com/datawhalechina/Hello-Agents
>
> AI 使用指引：需要某个 Agent 知识时，搜索本章索引定位到对应章节后，去 ./docs/chapter{N}/ 读文档，去 ./code/chapter{N}/ 读代码。Co-creation 项目的源码在 ./Co-creation-projects/{name}/ 下可直接参考。

---

## 一、核心教程（16 章）

### 第一部分：基础篇

#### chapter1: 初识智能体
- **文档**: docs/chapter1/
- **代码**: code/chapter1/ (`FirstAgentTest.ipynb` / `.py`)
- Agent 的基本概念——从"有问必答的工具"到"自主行动的智能体"
- 核心要素：环境 / 传感器 / 执行器 / 自主性
- 演进脉络：简单反射 → 基于模型反射 → 基于目标 → 基于效用

#### chapter2: 智能体发展史
- **文档**: docs/chapter2/
- **代码**: code/chapter2/ (`ELIZA.py`)
- 回溯 Agent 发展：符号主义（物理符号系统假说/专家系统）→ 分布式 AI → 进化智能体 → 基于学习的智能体
- 理解现代 Agent 形态的历史渊源

#### chapter3: 大语言模型基础
- **文档**: docs/chapter3/
- **代码**: code/chapter3/ (`N_gram.py`, `Word_Embedding.py`, `Transformer.py`, `BPE.py`, `Qwen.py`)
- 语言模型演进：N-gram → RNN → Transformer
- Transformer 架构详解（Attention 机制、位置编码等）
- LLM 如何获得知识储备与推理能力

### 第二部分：单体智能体

#### chapter4: 智能体经典范式构建
- **文档**: docs/chapter4/
- **代码**: code/chapter4/ (`llm_client.py`, `tools.py`, `ReAct.py`, `Plan_and_solve.py`, `Reflection.py`)
- **三种经典范式从零实现**：
  - **ReAct**：Thought → Action → Observation 循环（边想边做）
  - **Plan-and-Solve**：先拆解计划再逐步执行（先规划后执行）
  - **Reflection**：执行后自我反思、迭代修正（自我反思修正）

#### chapter5: 基于低代码平台的智能体搭建
- **文档**: docs/chapter5/
- **代码**: code/chapter5/（Coze yml / n8n json / Dify zip 配置导出）
- Coze / Dify / n8n 三大低代码平台对比与实操
- 适合快速验证想法、非开发者参与的场景

### 第三部分：高级篇

#### chapter6: 框架开发实践
- **文档**: docs/chapter6/
- **代码**: code/chapter6/ (`AutoGenDemo/`, `AgentScopeDemo/`, `CAMEL/`, `Langgraph/`)
- 主流 Agent 框架对比与使用：AutoGen（多智能体对话）、AgentScope（应用开发）、CAMEL（角色扮演）、LangGraph（有向图工作流）

#### chapter7: 构建你的 Agent 框架（HelloAgents）
- **文档**: docs/chapter7/
- **代码**: code/chapter7/（HelloAgents 框架核心 + 测试脚本）
- **从零构建自己的框架 HelloAgents**：模型层、工具层、智能体层三层架构
- 核心组件：SimpleAgent、ReActAgent、PlanAndSolveAgent、ReflectionAgent

#### chapter8: 记忆与检索
- **文档**: docs/chapter8/
- **代码**: code/chapter8/（11 个演示脚本：Memory/RAG/QA 全链路）
- 认知科学 → 记忆系统：工作记忆、长期记忆
- RAG 检索管道（MarkItDown 解析 → 分块 → Embedding → 检索引擎）
- 记忆巩固（Consolidation）机制

#### chapter9: 上下文工程（Context Engineering）
- **文档**: docs/chapter9/
- **代码**: code/chapter9/（6+ 脚本：ContextBuilder / NoteTool / TerminalTool）
- **关键概念**：GSSC 流水线（Gather-Select-Structure-Compress）
- 工具：ContextBuilder（上下文组装）、NoteTool（笔记管理）、TerminalTool（终端交互）
- 三天工作流完整演示

#### chapter10: 智能体通信协议
- **文档**: docs/chapter10/
- **代码**: code/chapter10/（14+ 脚本：MCP / A2A / ANP 全实现）
- **三大协议**：
  - **MCP**（Model Context Protocol）：智能体 ↔ 工具/服务的标准化接口
  - **A2A**（Agent-to-Agent）：智能体间的直接通信与协作
  - **ANP**（Agent Network Protocol）：大规模智能体网络的任务分发/负载均衡/协商
- 实战：GitHub MCP 集成、天气 MCP 服务、多智能体文档协作

#### chapter11: Agentic-RL（强化学习训练）
- **文档**: docs/chapter11/
- **代码**: code/chapter11/（完整训练 pipeline：数据→SFT→GRPO→评估）
- LLM 训练全景 → SFT 监督微调（LoRA）→ GRPO 群组相对策略优化
- 奖励函数设计、分布式训练（DDP/DeepSpeed）

#### chapter12: 智能体性能评估
- **文档**: docs/chapter12/
- **代码**: code/chapter12/（BFCL / GAIA / LLM-as-Judge / 胜率评估）
- **三大评估方法**：
  - **BFCL**（Berkeley Function Calling Leaderboard）：工具调用能力评估
  - **GAIA**（General AI Assistants）：通用 AI 助手能力评估
  - **LLM-as-Judge + 胜率评估**：主观质量评估
- 数据生成与评估工具集

### 第四部分：实战篇

#### chapter13: 智能旅行助手
- **文档**: docs/chapter13/
- **代码**: code/chapter13/ (helloagents-trip-planner/ — Vue3 + FastAPI)
- 完整前后端分离应用：行程规划、地图可视化（高德）、预算计算、PDF/图片导出
- 多智能体协作架构

#### chapter14: 自动化深度研究智能体
- **文档**: docs/chapter14/
- **代码**: code/chapter14/ (helloagents-deepresearch/ — Vue3 + FastAPI)
- 自动 Deep Research：问题剖析 → 多轮信息采集（多搜索 API）→ 反思 → 结构化报告
- 模块：Planner / Search / Summarizer / Reporter

#### chapter15: 构建赛博小镇
- **文档**: docs/chapter15/
- **代码**: code/chapter15/ (Helloagents-AI-Town/ — Godot 4.5 + FastAPI)
- Agent + 游戏引擎：NPC 独立记忆系统、性格设定、好感度系统
- 自然语言自由对话与互动

### 第五部分：展望篇

#### chapter16: 毕业设计
- **文档**: docs/chapter16/
- **代码**: code/chapter16/ (`共创路径.md`)
- 独立设计多智能体应用 → 以 PR 提交到社区共创仓库
- 选题方向、命名规范、评审流程

---

## 二、社区共创项目（34 个）

> 位置：`Co-creation-projects/{name}/`
> 技术栈高度集中在 HelloAgents 框架（SimpleAgent / ReActAgent / PlanAndSolveAgent / ReflectionAgent）

### 数据分析类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| 1zrj-DataAnalysisAgent | 数据分析助手，自动生成报告 | HelloAgents, pandas, matplotlib |
| alexrunner-DataAnalysisAgent | 商品销售分析，Plan-and-Solve + ReAct 混合 | HelloAgents, pandas |
| healer-666-Academic-Data-Agent | 科研数据分析 + PDF 主表提取 | HelloAgents Scientific ReAct, pdfplumber |
| czxgg0630-ProductAnalysisAgent | 竞品分析系统，两种 Agent 范式可选 | HelloAgents, Tavily, DuckDuckGo |

### 代码/开发工具类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| jjyaoao-CodeReviewAgent | Python 代码审查 + 质量报告 | HelloAgents, Python AST |
| chen070808-ProgrammingTutor | 编程学习助手（路径规划/出题/评审） | HelloAgents, A2A 协作 |
| lll0807-CodeTutorAgent | 编程导师（RAG 出题 + 记忆回顾） | HelloAgents A2A, RAG |
| YYHDBL-HelloCodeAgentCli | 本地 Code Agent CLI（类似 Claude Code） | HelloAgents, GSSC 上下文, 多层记忆 |

### 金融/科研类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| kkkano-FinReportAgent | 金融研报生成（Yahoo Finance + 搜索） | HelloAgents ReAct, yfinance |
| Apricity-InnocoreAI | 科研全流程自动化（4 Agent 协作） | HelloAgents, FastAPI, Qdrant/Redis |
| zjzhou-SREOnCallAgent | SRE 值班助手（告警分诊/根因/复盘） | HelloAgents, FastAPI |

### 创意/娱乐类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| afei-GuessWhoAmI | 猜人物游戏，Agent 扮演角色 | FastAPI, hello_agents, Tavily |
| laoyouf-aistory | 多文体故事生成器 | HelloAgents |
| lgs-only-NovelGenerator | 小说辅助创作（大纲+章节+管理系统） | HelloAgents, FastAPI |
| megg-ops-roleplay_agent | 沉浸式角色扮演对话 | OpenAI SDK |
| melxy1997-ColumnWriter | 专栏写作系统（规划→撰写→评审→优化） | HelloAgents, MCP, Tavily |

### 教育/写作类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| angelen-SoftwareDevHelper | 软件开发学习助手（出题/测试/打分） | HelloAgents, FastAPI |
| xujikai-SentenceExpandAgent | 英语写作教练（记者提问法扩写） | Vue3, FastAPI, HelloAgents |
| Yixiang-Wu-LearningAgent | 个性化学习助手（三层 Agent 架构） | HelloAgents, pytest |

### 生活助手类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| allen2000-FashionDailyDress | 天气 + 穿衣建议（三 Agent 协作） | hello-agents, fastmcp, Gradio |
| AstrumPush-Smart-Recipe-Agent | 菜谱搜索系统（多 Agent 协作） | hello_agents, MCP |
| bichchibui5-hub-EmailSmartAssistant | 智能邮件处理（分类/回复/提醒） | HelloAgents ReAct, imaplib |
| jack6249-GiftGeniusAgent | 智能送礼助手（军师→猎人→编辑） | HelloAgents, Tavily, MCP |
| pamdla-MindEchoAgent | 情绪音乐推荐（深度情绪识别） | hello-agents, gradio |
| Shawnxyxy-HealthRecordAgent | 健康档案助手（报告解读/饮食推荐） | HelloAgents, Milvus, SQLite |
| lh2021739-pixel-Personal_Info_Signaling_System | 日报→维度提取→自动修正搜索主题 | Python, LLM, tkinter |

### 平台/通用工具类
| 项目 | 描述 | 技术栈 |
|------|------|--------|
| 939147533-DatabaseAgent | 自然语言 → SQL 查询 | HelloAgents ReAct, Oracle |
| haoye2-UnivesalAgent | 通用智能体（多引擎搜索+终端执行） | HelloAgents, ModelScope |
| huailishang-AgentPlatformBase | 双 Agent 任务平台（搜索 + RSS 摘要） | FastAPI, hello-agents |
| tino-chen-HelloClaw | 个性化 AI Agent（身份定制+记忆） | Hello-Agents, Vue3 |
| usernamedadad-AutoFlow | 自然语言 → Mermaid 流程图 | HelloAgents, FastAPI, React |
| JJason-DeepCastAgent | 自动化播客生成（研究→脚本→语音） | HelloAgents, FastAPI, Vue3 |
| meiguanxiHXX-historyReviewAgent | 多角色历史辩论智能体 | FastAPI, OpenRouter |

---

## 三、扩展专题（Extra-Chapter，12 篇）

> 位置：`Extra-Chapter/`

| 编号 | 主题 | 核心知识点 |
|------|------|-----------|
| Extra01 | **面试八股合集** | LLM/VLM/Agent 面试题（Transformer自注意力、RoPE、MHA/MQA/GQA、Scaling Laws、BPE/WordPiece、MoE、RLHF、RAG）+ 完整参考答案 |
| Extra02 | **上下文工程补充** | Context Engineering = 管理 LLM 上下文窗口的艺术与科学；"LLM=CPU，上下文窗=RAM"类比；"RAG is dead"讨论 |
| Extra03 | **Dify 智能体搭建保姆级教程** | Dify 插件安装、MCP 云端配置（ModelScope MCP 市场）、可视化搭建 |
| Extra04 | **Datawhale FAQ** | 多智能体并行调度策略、主流框架生态对比、Hello-Agents 定位 |
| Extra05 | **Agent Skills 与 MCP** | MCP（工具连接）vs Skill（高层能力封装）两种范式互补；Skill 应对复杂推理场景 |
| Extra06 | **GUI Agent 科普与实战** | GUI Agent（视觉感知+LLM 推理）vs RPA（固定脚本）；跨平台自主操作 |
| Extra07 | **环境配置指南** | Python 3.10+ / API 配置 / 天气+搜索工具链 |
| Extra08 | **如何写出好的 Skill** | Skill = 文件夹（指令+参考资料+脚本）；上半部触发条件 + 下半部操作步骤；AI 能力插件 |
| Extra09 | **Agent 开发踩坑与经验** | 工具设计 Goldilocks 区、提示词是控制面不是咒语、上下文是注意力调度问题、可观测性 |
| Extra10 | **Agent 自进化** | 四类闭环：内建上下文 → 技能资产化 → 外部监督/群体智能 → 参数/代码自修改；10 个代表项目（DSPy/EVOSKILL/OpenClaw 等） |
| Extra11 | **Web Agent 科普与实战** | Web Agent vs RPA vs GUI Agent 区别；三种感知策略（DOM/视觉/混合）；生产级推荐混合路线 |
| Extra12 | **旅行助手后训练实战** | 完整后训练闭环：产品协议→评测集→prompt→SFT 数据→LoRA→rerank；常见陷阱 |

---

## 四、补充章节

| 位置 | 内容 |
|------|------|
| `Additional-Chapter/N8N_INSTALL_GUIDE.md` | N8N Docker 安装教程 |
| `Additional-Chapter/NODEJS_INSTALL_GUIDE.md` | Node.js 安装指南 |

---

## 五、快速定位指南

**场景 → 读哪章：**

| 你想干什么 | 读这章 |
|------------|--------|
| Agent 概念入门 | chapter1、chapter2 |
| 理解 Transformer / LLM 原理 | chapter3 |
| 手写 ReAct / Plan-and-Solve / Reflection | chapter4 |
| 用 Dify/Coze/n8n 低代码搭 Agent | chapter5 |
| 选框架（AutoGen/LangGraph/AgentScope） | chapter6 |
| 从零写自己的 Agent 框架 | chapter7 |
| 给 Agent 加记忆和 RAG | chapter8 |
| 系统化管理上下文（Context Engineering） | chapter9 |
| MCP/A2A/ANP 通信协议 | chapter10 |
| 用 RL 训练 Agent（SFT→GRPO） | chapter11 |
| 评估 Agent 性能（BFCL/GAIA） | chapter12 |
| 做完整项目（旅行助手/深度研究/赛博小镇） | chapter13、chapter14、chapter15 |
| 看真实社区项目源码参考 | Co-creation-projects/ |
| 准备 Agent 岗位面试 | Extra01 |
| 学写 Hermes Skill | Extra08 |
| Agent 自进化思路 | Extra10 |
