# PaperMind · 论文创新点发现 Agent

> 一个面向研究生的多 Agent 协作系统：批量阅读本地 PDF 论文 → 漏斗式信息收敛 → 识别研究空白 → 生成 2-3 个可落地的创新点与完整实验方案。

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)

---

## ✨ 项目亮点

- 🧠 **Plan-and-Execute + Reflexion**：Controller 动态规划执行路径，关键步骤自校验，置信度低自动回退
- 🤝 **多 Agent 协作**：1 个 Controller + 6 个专职 Agent（Parser / Extractor / Indexer / GapAnalyzer / InnovationGenerator / ExperimentDesigner）+ 1 个 Evaluator
- 🛠 **DeepSeek Function Calling**：`tool_choice="auto"`，模型自主选工具（10+ 工具）
- 🔍 **RAG 全链路**：BGE-m3 Embedding + Chroma 向量库 + BM25 关键词 → 混合搜索
- 💾 **双层 Memory**：会话级对话记忆 + 跨会话长期知识记忆（向量库 + JSON 元数据）
- 📊 **评估体系**：输出三维评分（新颖性 / 可行性 / 显著性）+ 工具调用成功率 + 自校验置信度
- 🪜 **七步漏斗式主链路**：严格遵循 `plan.docx` 信息收敛架构
- 🛡 **稳定性设计**：单篇失败隔离、JSON 容错、工具重试降级、超时控制

---

## 🏗 系统架构

```
                ┌─────────────────────────────────────┐
                │   Controller (Plan-and-Execute)     │
                └──────────────┬──────────────────────┘
                               │  动态调度
        ┌──────────────┬───────┼────────┬─────────────┐
        ▼              ▼       ▼        ▼             ▼
  ┌──────────┐  ┌──────────┐ ... ┌──────────┐  ┌──────────────┐
  │  Parser  │  │ Extractor│     │  Gap    │  │  Evaluator   │
  └──────────┘  └──────────┘     │ Analyzer│  └──────────────┘
                                 └──────────┘
        ▲              ▲                       ▲
        │              │   Reflexion 自校验     │
        └──────────────┴───────────────────────┘

七步漏斗主链路：
  ① PDF 解析  →  ② 结构化抽取  →  ③ 向量索引
   →  ④ 跨论文 Gap 识别  →  ⑤ 创新点生成
   →  ⑥ 实验方案设计   →  ⑦ 整合研究报告
```

---

## 📂 目录结构

```
paper-agent-trae/
├── backend/                  # FastAPI 后端
│   ├── agents/               # Controller + 6 专职 Agent
│   ├── tools/                # Function Calling 工具集（10+ 工具）
│   ├── rag/                  # Embedding + Chroma + BM25 混合搜索
│   ├── memory/               # 对话记忆 + 长期知识记忆
│   ├── orchestrator/         # 工作流编排 + Reflexion
│   ├── evaluator/            # 评估体系（质量评分 + 调用追踪）
│   ├── api/                  # FastAPI 异步接口
│   ├── models/               # Pydantic Schema
│   └── config.py             # 全局配置
├── frontend/                 # React + Vite 前端
│   ├── src/
│   │   ├── components/       # 报告视图 / 进度条 / 评估面板
│   │   ├── App.tsx
│   │   └── api.ts
│   └── package.json
├── data/                     # 向量库 / 缓存 / 报告（运行时生成）
├── .env.example              # 环境变量样例
├── .gitignore
├── run_backend.py            # 启动入口
└── plan.docx                 # 漏斗式架构原始设计文档
```

---

## 🚀 快速开始

### 1. 克隆与配置

```bash
git clone https://github.com/jphJack/PaperMind-Agent.git
cd PaperMind-Agent

# 复制环境变量样例
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 2. 启动后端

```bash
# 推荐 Python 3.12
pip install -r backend/requirements.txt
python run_backend.py
# 服务监听 http://0.0.0.0:8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
# 浏览器访问 http://localhost:5173
```

### 4. 使用流程

1. 在前端输入本地 PDF 文件夹路径
2. 点击「启动分析」
3. 实时查看七步漏斗的进度与中间产物
4. 分析完成后查看结构化研究报告 + 评估指标

---

## 🔧 核心工具集（Function Calling）

| 工具 | 功能 |
|---|---|
| `scan_folder` | 扫描目标文件夹收集 PDF |
| `parse_pdf` | PyMuPDF 解析 + 章节结构保留 |
| `extract_paper_structure` | 强制 JSON 输出固定 schema |
| `build_vector_index` | 章节分块 → BGE-m3 → Chroma 入库 |
| `hybrid_search` | 向量相似度 + BM25 关键词混合检索 |
| `analyze_gaps` | 跨论文综合分析，识别四类 Gap 信号 |
| `generate_innovations` | 创新点生成与三维评分筛选 |
| `design_experiments` | 生成可执行实验方案 |
| `web_search` | 近 1-2 年新颖性去重 |
| `save_memory` / `load_memory` | Memory 读写 |

---

## 📊 结构化抽取 Schema

每篇论文抽取为如下 JSON（节选）：

```json
{
  "title": "...",
  "task": "...",
  "method": "...",
  "key_contributions": ["..."],
  "datasets": ["..."],
  "metrics": ["..."],
  "results": "...",
  "limitations": ["..."],
  "future_work": ["..."],
  "source_sections": {
    "method": ["3.1", "3.2"],
    "limitations": ["6.2"]
  }
}
```

`source_sections` 字段保证所有结论可回溯到原文具体章节，避免 LLM 编造。

---

## 📈 评估体系

最终报告附带三类评估指标：

- **输出质量三维评分**：新颖性 / 可行性 / 显著性（0-10 分）
- **工具调用统计**：调用次数 / 成功率 / 平均耗时
- **Reflexion 置信度**：关键步骤的自校验置信度统计

---

## ⚙️ 环境变量

完整配置见 [`.env.example`](.env.example)，核心项：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（必填） | - |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-chat` |
| `EMBEDDING_MODEL` | 本地 Embedding 模型 | `BAAI/bge-m3` |
| `CHROMA_PATH` | 向量库路径 | `./data/chroma` |
| `CONFIDENCE_THRESHOLD` | Reflexion 置信度阈值 | `0.7` |
| `MAX_CONCURRENT_PAPERS` | 并发抽取数 | `5` |
| `TOOL_MAX_RETRIES` | 工具调用最大重试次数 | `3` |

---

## 🛣 七步漏斗式主链路

严格遵循 [`plan.docx`](plan.docx) 定义的漏斗式信息收敛架构：

1. **PDF 解析** — PyMuPDF + 章节结构保留
2. **单篇结构化抽取** — 固定 schema + source_sections 回溯
3. **向量索引构建** — BGE-m3 + Chroma
4. **跨论文综合分析 + Gap 识别** — 重复局限 / 方法空白 / 矛盾结论 / 未兑现未来工作
5. **创新点生成与筛选** — 方法组合 / 局限改进 / 跨域迁移 / 新场景应用
6. **实验方案设计** — 假设 / 数据 / 基线 / 指标 / 消融 / 步骤 / 风险
7. **整合输出** — Markdown 研究提案，含背景综述 / 创新点论证 / 实验方案 / 参考文献溯源

---

## 🛡 稳定性设计

- ✅ 单篇论文失败隔离，独立缓存可单独重跑
- ✅ Function Calling 强制 JSON + 程序层校验
- ✅ 工具调用 3 次重试 + 降级路径
- ✅ 单篇 / 单步超时阈值控制
- ✅ Controller 异常捕获与恢复

---

## 🧪 技术栈

**后端**：Python 3.12 · FastAPI · OpenAI SDK（兼容 DeepSeek）· ChromaDB · sentence-transformers · PyMuPDF · rank-bm25 · Pydantic · SSE

**前端**：React 18 · Vite 5 · TypeScript · react-markdown

**AI**：DeepSeek-chat · BAAI/bge-m3 Embedding

---

## 📄 License

MIT

---

## 🙋 关于

本项目为人工智能专业研究生的「Agent 开发深度理解」项目作品，旨在展示主流 Agent 工程能力（推理框架、多智能体协作、Function Calling、RAG、Memory、动态编排、评估体系）的完整落地。
