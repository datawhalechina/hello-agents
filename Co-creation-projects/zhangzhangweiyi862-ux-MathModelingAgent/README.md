# MathModelingAgent

> 一个面向数学建模任务的多智能体研究助手，通过赛题解析、数据审计、模型设计和报告汇总四个 Agent 协同完成结构化建模分析。

## 📝 项目简介

MathModelingAgent 是一个面向数学建模场景设计的轻量级多智能体应用。

项目针对数学建模过程中常见的“拿到题目后直接建模、数据边界不清、关键参数被默认补全、模型复杂化过早”等问题，将建模流程拆分为多个职责明确的智能体。

系统按照以下顺序运行：

ProblemAnalysisAgent
→ DataAuditAgent
→ ModelingAgent
→ ReportAgent

最终自动生成 Markdown 格式的建模分析报告。

本项目重点不是替代参赛者完成数学建模，而是辅助完成赛题理解、数据边界检查、Baseline 模型设计和报告整理。

---

## ✨ 核心功能

### 1. ProblemAnalysisAgent —— 赛题解析

负责：

- 提取问题背景
- 拆解核心任务
- 识别已知条件
- 识别待求量
- 提取决策变量候选
- 提取目标函数候选
- 分析关键约束
- 判断建模类型
- 发现信息缺口

---

### 2. DataAuditAgent —— 数据与信息审计

负责：

- 检查数据对象及角色
- 检查时间粒度
- 检查单位和量纲
- 检查缺失信息
- 检查异常值与数据对齐风险
- 明确决策时点的信息集
- 检查未来信息泄漏
- 给出 Gate 判断

Gate 包含：

- 通过，可以进入建模
- 有条件通过，需要明确假设
- 不通过，需要补充关键信息

---

### 3. ModelingAgent —— 数学模型设计

负责：

- 建立建模假设
- 定义参数与变量
- 建立 Baseline 模型
- 构造目标函数
- 构造约束条件
- 推荐求解方法
- 提出模型验证方案
- 在有依据时提出模型升级方向

当题目缺少关键参数时，ModelingAgent 不直接虚构数值，而使用符号参数保留模型结构。

---

### 4. ReportAgent —— 建模报告汇总

负责整合前三个 Agent 的结果，并生成结构化 Markdown 报告。

报告主要包含：

- 问题概述
- 核心建模任务
- 信息与数据边界
- 数据审计结论
- 建模假设
- 符号与变量
- Baseline 数学模型
- 目标函数
- 核心约束
- 求解方案
- 模型验证
- 当前限制
- 可升级方向
- 最终结论

---

## 🧠 多智能体工作流程

用户输入数学建模问题

↓

ProblemAnalysisAgent  
赛题理解与任务拆解

↓

DataAuditAgent  
数据、时间信息和未来信息泄漏审计

↓

ModelingAgent  
Baseline 模型与算法设计

↓

ReportAgent  
统一生成建模分析报告

↓

output/modeling_report.md

---

## 🛠️ 技术栈

- Python 3.10+
- OpenAI Compatible API
- Kimi 大语言模型
- openai Python SDK
- python-dotenv
- Markdown
- Git / GitHub

项目采用轻量级自定义多智能体流水线实现，设计思想来自 Hello-Agents 课程中的 Agent 分工、任务拆解与协作机制。

---

## 📁 项目结构

```text
MathModelingAgent/
│
├── main.py
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
└── src/
    ├── __init__.py
    ├── llm_client.py
    ├── problem_analysis_agent.py
    ├── data_audit_agent.py
    ├── modeling_agent.py
    └── report_agent.py