# Hello-Agents 教程 — 章节摘要

## chapter1: 初识智能体
介绍智能体的基本概念、核心要素（环境、传感器、执行器、自主性），以及传统智能体的演进脉络——从简单反射智能体到基于模型的反射智能体、基于目标的智能体、基于效用的智能体，为后续学习奠定基础。

## chapter1 code
- `FirstAgentTest.ipynb` / `FirstAgentTest.py` — 第一个智能体交互测试，演示 Thought-Action-Observation 循环

---

## chapter2: 智能体发展史
回溯智能体的发展历程，从符号主义（物理符号系统假说、专家系统）到分布式智能体，再到进化智能体和基于学习的智能体，展示了"问题驱动"的迭代演进路线。

## chapter2 code
- `ELIZA.py` — ELIZA 经典对话程序实现，展示早期基于模式匹配的智能体原型

---

## chapter3: 大语言模型基础
聚焦大语言模型的核心原理，从 N-gram 统计语言模型到 RNN、再到 Transformer 架构，系统讲解语言模型如何获得强大的知识储备与推理能力。

## chapter3 code
- `N_gram.py` — N-gram 统计语言模型实现
- `Word_Embedding.py` — 词嵌入（Word Embedding）示例
- `Transformer.py` — Transformer 架构实现
- `BPE.py` — BPE（Byte Pair Encoding）分词算法
- `Qwen.py` — 与 Qwen 大语言模型交互演示

---

## chapter4: 智能体经典范式构建
从零实现 ReAct（边想边做）、Plan-and-Solve（先规划后执行）、Reflection（自我反思修正）三种经典智能体范式，通过亲手编码深入理解每种范式的工作机制与设计思想。

## chapter4 code
- `llm_client.py` — LLM 客户端封装
- `tools.py` — 智能体工具定义（计算器、搜索等）
- `ReAct.py` — ReAct 范式实现
- `Plan_and_solve.py` — Plan-and-Solve 范式实现
- `Reflection.py` — Reflection 范式实现

---

## chapter5: 基于低代码平台的智能体搭建
介绍如何使用 Coze、Dify、n8n 三个低代码平台快速搭建智能体应用，降低技术门槛、提升开发效率，实现可视化调试与一键部署。

## chapter5 code
- `超级智能个人助手.yml` — Coze 平台工作流配置
- `HelloAgent_n8nCase.json` — n8n 工作流配置
- `Chatflow-AI_news-draft-9211.zip` — Dify 聊天流配置

---

## chapter6: 框架开发实践
探讨如何利用 AutoGen、AgentScope、CAMEL、LangGraph 等主流智能体框架高效构建多智能体协作系统，实现模块化、可扩展的框架驱动开发模式。

## chapter6 code
- `AutoGenDemo/` — AutoGen 多智能体对话协作示例
- `AgentScopeDemo/` — AgentScope 多智能体应用开发示例
- `CAMEL/` — CAMEL 角色扮演框架示例
- `Langgraph/` — LangGraph 有向图工作流示例

---

## chapter7: 构建你的 Agent 框架
从零开始逐步构建 HelloAgents 框架，设计整体架构（模型层、工具层、智能体层），实现 SimpleAgent、ReActAgent、PlanAndSolveAgent、ReflectionAgent 等核心组件，完成从框架使用者到构建者的跃迁。

## chapter7 code
- `my_llm.py` — LLM 客户端封装
- `my_simple_agent.py` — SimpleAgent 基础智能体
- `my_react_agent.py` — ReActAgent 实现
- `my_calculator_tool.py` — 计算器工具
- `my_advanced_search.py` — 高级搜索工具
- `test_*.py` — 各组件测试脚本

---

## chapter8: 记忆与检索
为 HelloAgents 框架引入记忆系统（Memory System）和检索增强生成（RAG），从认知科学角度理解人类记忆层次，实现工作记忆、长期记忆、RAG 检索管道。

## chapter8 code
- `01_MemoryTool_Basic_Operations.py` — 记忆工具基本操作
- `02_MemoryTool_Architecture.py` — 记忆工具架构
- `03_WorkingMemory_Implementation.py` — 工作记忆实现
- `04_RAGTool_MarkItDown_Pipeline.py` — MarkItDown RAG 管道
- `05_RAGTool_Advanced_Search.py` — 高级搜索
- `06_Memory_Consolidation_Demo.py` — 记忆巩固演示
- `07_RAGTool_Intelligent_QA.py` — 智能问答
- `08_Agent_Tool_Integration.py` — 智能体工具集成
- `09_Memory_Types_Deep_Dive.py` — 记忆类型深入
- `10_RAG_Pipeline_Complete.py` — 完整 RAG 管道
- `11_Q&A_Assistant.py` — 问答助手

---

## chapter9: 上下文工程
提出上下文工程（Context Engineering）概念，在 HelloAgents 框架中实现 GSSC（Gather-Select-Structure-Compress）流水线，通过 ContextBuilder、NoteTool、TerminalTool 系统化地管理模型输入上下文。

## chapter9 code
- `01_context_builder_basic.py` — ContextBuilder 基础使用
- `02_context_builder_with_agent.py` — ContextBuilder + 智能体
- `03_note_tool_operations.py` — NoteTool 笔记工具操作
- `04_note_tool_integration.py` — NoteTool 与智能体集成
- `05_terminal_tool_examples.py` — TerminalTool 终端工具示例
- `06_three_day_workflow.py` — 三天工作流完整演示
- `codebase_maintainer.py` — 代码库维护工具
- `project/main.py` — 项目完整入口
- `codebase/` — 示例代码库模块

---

## chapter10: 智能体通信协议
为 HelloAgents 引入 MCP（模型上下文协议）、A2A（智能体间协议）、ANP（智能体网络协议）三种通信协议，实现智能体与工具、智能体间的标准化通信与大规模协作。

## chapter10 code
- `01_TestConnect.py` — 基础连接测试
- `02_Connect2MCP.py` — 连接 MCP 服务
- `03_GitHubMCP.py` — GitHub MCP 集成
- `04_MCPTransport.py` — MCP 传输层
- `05_UseMCPToolInAgent.py` — 智能体中使用 MCP 工具
- `06_MultiAgentDocumentAssist.py` — 多智能体文档协作
- `07_SimpleA2AAgent.py` — 简单 A2A 智能体
- `08_CustomA2AAgent.py` — 自定义 A2A 智能体
- `09_A2A_*.py` — A2A 完整实现（客户端、服务端、网络）
- `10_*.py` — ANP 初始化、任务分发、负载均衡、协商
- `14_weather_mcp_server.py` / `14_weather_agent.py` — 天气 MCP 服务端与智能体
- `weather-mcp-server/` — 独立天气 MCP 服务

---

## chapter11: Agentic-RL
介绍基于强化学习的智能体训练（Agentic RL），从 LLM 训练全景图出发，逐步深入到 SFT 监督微调、GRPO 群组相对策略优化，构建完整的智能体训练 pipeline。

## chapter11 code
- `00_quick_test.py` — 快速测试
- `01_dataset_loading.py` — 数据集加载
- `02_reward_functions.py` — 奖励函数定义
- `03_lora_configuration.py` — LoRA 微调配置
- `04_sft_training.py` — SFT 监督微调
- `05_grpo_training.py` — GRPO 强化学习训练
- `06_complete_pipeline.py` — 完整训练流程
- `07_model_evaluation.py` — 模型评估
- `08_distributed_training.py` — 分布式训练
- `accelerate_configs/` — 分布式训练配置（DDP、DeepSpeed）

---

## chapter12: 智能体性能评估
为 HelloAgents 增加性能评估系统，引入 BFCL（工具调用评估）、GAIA（通用 AI 助手评估）、LLM-as-Judge 和胜率评估等多种评估方法，实现对智能体能力的客观量化。

## chapter12 code
- `01_basic_agent_example.py` — 基础智能体示例
- `02_bfcl_quick_start.py` — BFCL 快速入门
- `03_bfcl_custom_evaluation.py` — BFCL 自定义评估
- `04_run_bfcl_evaluation.py` — 运行 BFCL 评估
- `05_gaia_quick_start.py` — GAIA 快速入门
- `06_gaia_best_practices.py` — GAIA 最佳实践
- `07_data_generation_complete_flow.py` — 数据生成完整流程
- `08_data_generation_llm_judge.py` — LLM-as-Judge 评估
- `09_data_generation_win_rate.py` — 胜率评估
- `data_generation/` — 数据生成与评估工具集
- `template_output/` — 评估结果输出

---

## chapter13: 智能旅行助手
构建一个完整的智能旅行助手应用（Vue3 + FastAPI 前后端分离架构），实现智能行程规划、地图可视化、预算计算、行程编辑和 PDF/图片导出功能。

## chapter13 code
- `helloagents-trip-planner/backend/` — FastAPI 后端，含 LLM 服务、高德地图服务、Unsplash 图片服务、旅行规划 Agent
- `helloagents-trip-planner/frontend/` — Vue3 + TypeScript 前端，含行程规划、地图展示、预算管理等页面

---

## chapter14: 自动化深度研究智能体
构建一个自动化深度研究助手，具备问题剖析、多轮信息采集（多搜索 API）、反思与总结能力，实现从开放主题到结构化研究报告的自动生成。

## chapter14 code
- `helloagents-deepresearch/backend/` — FastAPI 后端，含 Planner（规划）、Search（搜索）、Summarizer（总结）、Reporter（报告生成）等模块
- `helloagents-deepresearch/frontend/` — Vue3 + TypeScript 前端，全屏模态对话框 UI，Markdown 结果展示

---

## chapter15: 构建赛博小镇
将智能体技术与 Godot 游戏引擎结合，构建 AI 小镇。NPC 拥有独立的记忆系统、性格设定和好感度系统，玩家可用自然语言与 NPC 自由对话与互动。

## chapter15 code
- `Helloagents-AI-Town/helloagents-ai-town/` — Godot 4.5 游戏前端（角色、场景、UI、音效、动画）
- `Helloagents-AI-Town/backend/` — FastAPI 后端（NPC Agent 管理、记忆系统、好感度系统、对话日志）
- 配套文档：SETUP_GUIDE.md, MEMORY_SYSTEM_GUIDE.md, AFFINITY_SYSTEM_GUIDE.md, DIALOGUE_LOG_GUIDE.md

---

## chapter16: 毕业设计
指导读者独立设计并实现自己的多智能体应用，以开源项目形式通过 Pull Request 提交到社区共创仓库，完成从学习者到智能体系统构建者的最终跃迁。

## chapter16 code
- `共创路径.md` — 毕业设计指导文档，说明选题方向、项目命名规范、提交方式和评审流程
