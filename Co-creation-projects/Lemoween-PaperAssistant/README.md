# 论文撰写助手（PaperAssistant）

基于 [HelloAgents](https://github.com/jjyaoao/HelloAgents) 框架构建的多智能体论文撰写助手。它能够根据给定的研究主题，自动完成**章节规划 → 文献检索 → PDF 下载 → RAG 索引 → 章节撰写 → 论文审校 → 最终汇总**的全流程，输出一份结构化的 Markdown 格式论文。



------

## 核心特性

- **多智能体协作**：五个专职 Agent 分工完成规划、检索、撰写、审校、汇总
- **学术来源限定**：所有文献来自 arXiv、Semantic Scholar、CrossRef、OpenAlex 等学术数据库，杜绝网页链接
- **真实文献支撑**：通过 [Paper Search MCP](https://github.com/openags/paper-search-mcp) 下载论文全文，经 RAG 索引供撰写时调用
- **检索增强生成（RAG）**：论文库基于 Qdrant 向量库构建，支持语义检索、MQE 多查询扩展与 HyDE 假设文档嵌入
- **结构化笔记**：使用 HelloAgents 的 `NoteTool` 保存章节草稿、大纲与终稿，支持跨会话恢复
- **多层次记忆**：使用 `MemoryTool` 管理工作记忆、情景记忆与语义记忆
- **工具调用追踪**：所有工具调用通过 `ToolCallTracker` 记录，便于调试与审计
- **引用格式规范**：支持 GB/T 7714引用风格

------

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户：输入研究主题                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  PaperAssistant    │ 协调器
                    │  (Orchestrator)    │
                    └─────────┬──────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       │                      │                      │
  ┌────▼─────┐          ┌─────▼────┐          ┌─────▼────┐
  │ Planner  │   →      │ Searcher │   →      │  Writer  │
  │ 章节规划  │          │ 文献检索  │          │ 章节撰写  │
  └──────────┘          └─────┬────┘          └─────┬────┘
                              │                      │
                              │ 下载 PDF              │ 检索论文原文
                              │                      │
                     ┌────────▼──────┐      ┌────────▼─────┐
                     │ PaperLibrary  │◄─────│ search_paper │
                     │  (RAGTool)    │      │   _library   │
                     └────────┬──────┘      └──────────────┘
                              │
                  ┌───────────▼───────────┐
                  │  Reviewer → Assembler │
                  │  审校    →  汇总成稿   │
                  └───────────────────────┘
```



**五个专职 Agent**：

| Agent                 | 职责                                  | 工具                                                    |
| :-------------------- | :------------------------------------ | :------------------------------------------------------ |
| PaperPlannerAgent     | 将研究主题拆解为 3-5 个章节           | `NoteTool`                                              |
| LiteratureSearchAgent | 检索学术论文、下载 PDF、加入 RAG 索引 | `Paper Search MCP` + `RAGTool`                          |
| SectionWriterAgent    | 撰写章节正文，引用文献                | `search_paper_library` + `format_citation` + `NoteTool` |
| PaperReviewAgent      | 审校论文的逻辑、引用、术语一致性      | `NoteTool`                                              |
| ReportAssemblerAgent  | 汇总章节生成最终论文                  | `NoteTool`                                              |

------

## 环境要求

| 组件                          | 版本   | 用途                                 |
| :---------------------------- | :----- | :----------------------------------- |
| Python                        | ≥ 3.10 | 运行环境                             |
| uv                            | ≥ 0.4  | 管理 Paper Search MCP 依赖           |
| Ollama 或其他 OpenAI 兼容 LLM | 任意   | 提供 LLM 能力                        |
| Qdrant                        | ≥ 1.7  | RAG 向量存储（本地 Docker 或云服务） |
| Neo4j                         | ≥ 5.x  | 语义记忆图存储（可选，可禁用）       |



------

## 安装步骤

### 1. 安装 Python 依赖

```
# 推荐使用虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```



### 2. 安装 uv（用于运行 Paper Search MCP）



```
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```



```
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```



### 3. 安装 spaCy 语言模型



```
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm
```



### 4. 预装 Paper Search MCP（强烈推荐）

为了避免每次调用都重新解析依赖，强烈建议**预装到专属 venv**：

```
# 在项目根目录
uv venv .venv-paper-search

# Windows
uv pip install --python .venv-paper-search `
  -i https://pypi.tuna.tsinghua.edu.cn/simple `
  "mcp<2" paper-search-mcp

# Linux/macOS
uv pip install --python .venv-paper-search \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  "mcp<2" paper-search-mcp
```

**注意**：`paper-search-mcp` 目前依赖 `mcp<2`，必须显式 pin 版本，否则会因 `mcp 2.x` 中 `fastmcp` 重命名而启动失败。

------

## 配置说明

在项目根目录创建 `.env` 文件：

```
cp .env.example .env
```



### 完整 `.env` 示例

```
# ============================================================
# LLM 配置（由 HelloAgentsLLM 自动检测，参数优先，环境变量兜底）
# ============================================================

# --- 例 1：本地 Ollama ---
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL_ID=qwen2.5:7b

# --- 例 2：DeepSeek 云端 ---
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
# LLM_MODEL_ID=deepseek-chat

# --- 例 3：OpenAI ---
# OPENAI_API_KEY=sk-xxxxxxxxxxxx
# LLM_MODEL_ID=gpt-4o-mini

# ============================================================
# Qdrant 向量数据库（RAGTool + MemoryTool 使用）
# ============================================================
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=hello_agents_vectors
QDRANT_VECTOR_SIZE=384
QDRANT_DISTANCE=cosine
QDRANT_TIMEOUT=30

# ============================================================
# Neo4j 图数据库（MemoryTool 的 semantic memory 使用）
# ============================================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j
NEO4J_MAX_CONNECTION_LIFETIME=3600
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=60

# ============================================================
# Embedding 服务（RAGTool 与 MemoryTool 的向量化后端）
# 若 EMBED_API_KEY 留空，会自动回退到本地 sentence-transformers
# ============================================================
EMBED_MODEL_TYPE=dashscope
EMBED_MODEL_NAME=text-embedding-v3
EMBED_API_KEY=your_dashscope_api_key
EMBED_BASE_URL=

# ============================================================
# Paper Search MCP（openags/paper-search-mcp）
# 推荐：使用预装 venv 的 Python 解释器启动
# ============================================================
PAPER_SEARCH_MCP_COMMAND=.venv-paper-search\Scripts\python,-m,paper_search_mcp.server
PAPER_SEARCH_MCP_PREFIX=papersearch

# 备选：使用 uvx 直接运行（首次较慢，每次调用需重新解析依赖）
# PAPER_SEARCH_MCP_COMMAND=uvx,--with,mcp<2,paper-search-mcp

# 可选 API Key（提升速率与覆盖率，不配也能用）
# PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY=
# PAPER_SEARCH_MCP_CORE_API_KEY=
# PAPER_SEARCH_MCP_UNPAYWALL_EMAIL=you@example.com

# ============================================================
# 论文设置
# ============================================================
PAPER_TYPE=conference           # conference / journal / thesis
CITATION_STYLE=gb7714           # gb7714 / apa
TARGET_SECTIONS=5
TARGET_WORDS_PER_SECTION=1000
MAX_REFERENCES_PER_SECTION=5
MAX_REVIEW_ROUNDS=2

# ============================================================
# 论文库
# ============================================================
PDF_DOWNLOAD_ENABLED=true
MAX_PDF_SIZE_MB=50
PAPER_LIBRARY_PATH=./workspace/paper_library

# ============================================================
# 笔记与记忆
# ============================================================
ENABLE_NOTES=true
NOTES_WORKSPACE=./workspace/paper_notes
ENABLE_MEMORY=true
MEMORY_USER_ID=paper_author

# ============================================================
# 其他
# ============================================================
STRIP_THINKING_TOKENS=true
```



### 配置说明

| 变量                         | 含义                                             |
| :--------------------------- | :----------------------------------------------- |
| `LLM_*` / `*_API_KEY`        | LLM 连接信息，由 `HelloAgentsLLM` 自动检测       |
| `QDRANT_URL`                 | Qdrant 向量库地址，RAG 索引与记忆系统的核心依赖  |
| `NEO4J_*`                    | Neo4j 图数据库，只有启用 `semantic` 记忆时才需要 |
| `EMBED_*`                    | 文本嵌入服务，留空则回退本地模型                 |
| `PAPER_SEARCH_MCP_COMMAND`   | MCP 服务器启动命令，逗号分隔                     |
| `TARGET_SECTIONS`            | 论文目标章节数                                   |
| `MAX_REFERENCES_PER_SECTION` | 每章最多检索的论文数                             |
| `PAPER_LIBRARY_PATH`         | 论文库路径，存放 PDF 与 RAG 索引                 |

------

## 使用方法

### 基本用法

```
python main.py "大语言模型在学术写作辅助中的应用与挑战"
```



### 快速测试（减少耗时）

在 `.env` 中临时调整：

```
TARGET_SECTIONS=3
TARGET_WORDS_PER_SECTION=200
MAX_REFERENCES_PER_SECTION=3
```



然后运行：

```
python main.py "大语言模型在学术写作辅助中的应用与挑战"
```



### 使用自定义主题

```
python main.py "联邦学习在医疗影像中的应用"
python main.py "量子机器学习的最新进展"
```



------

## 输出产物

运行完成后，产物位于 `workspace/` 目录下：

```
workspace/
├── output/
│   ├── paper_<主题>.md              # 最终论文（Markdown）
│   └── review_<主题>.md             # 审校意见
├── paper_notes/                     # NoteTool 工作区
│   ├── note_xxx_0.md                # 章节 1 笔记（task_state）
│   ├── note_xxx_1.md                # 章节 2 笔记
│   └── note_xxx_N.md                # 论文终稿（conclusion）
├── paper_memory/                    # MemoryTool 数据
│   └── memory.db
└── paper_library/                   # RAGTool 论文库
    ├── pdfs/                        # 下载的论文 PDF
    │   ├── 2502.00632v2.pdf
    │   ├── 2404.00027v5.pdf
    │   └── ...
    └── rag/
        └── index_manifest.json      # 索引清单
```



### 论文输出格式

最终论文为 Markdown 格式，包含：

- **标题**：由规划 Agent 生成
- **摘要**：200-300 字，概括研究背景、方法、主要发现
- **正文**：引言、相关工作、方法、实验/分析、结论等章节
- **参考文献**：统一格式，DOI 可追溯

------

## 项目结构

```
PaperAssistant/
├── README.md                          # 本文档
├── requirements.txt                   # Python 依赖
├── .env.example                       # 环境变量模板
├── main.py                            # 入口脚本
├── config.py                          # 应用层配置
├── models.py                          # 数据模型
├── prompts.py                         # 提示词模板
├── utils.py                           # 通用工具函数
├── agent.py                           # 协调器
│
├── tools/                             # 工具层
│   ├── __init__.py
│   ├── citation_tool.py               # 引用格式化
│   ├── paper_library_tool.py          # 论文库检索/问答
│   └── mcp_paper_search.py            # Paper Search MCP 工厂
│
├── services/                          # 服务层
│   ├── __init__.py
│   ├── paper_library.py               # 论文库服务（包装 RAGTool）
│   ├── planner.py                     # 章节规划服务
│   ├── writer.py                      # 章节撰写服务
│   ├── reviewer.py                    # 论文审校服务
│   ├── assembler.py                   # 论文汇总服务
│   └── tool_events.py                 # 工具调用追踪
│
└── agents/                            # Agent 层
    ├── __init__.py
    └── literature_search.py           # 文献检索 Agent
```





------

## 许可证

本项目采用 MIT License 授权。



------

## 作者

- **GitHub**：[@Lemoween](https://github.com/Lemoween)
- **Email**：lemoween@163.com



------

## 致谢

感谢Datawhale社区和Hello-Agents项目！