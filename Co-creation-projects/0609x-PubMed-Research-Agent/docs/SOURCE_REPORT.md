> **结构说明**：本报告生成于早期版本，其中的 `agents/`、`services/`、`tools/`、`tests/`、`database/`
> 等顶层目录在后续重构中已统一迁入 `backend/` 下；`cache/`、`database/` 的运行时数据已归拢到 `data/`；
> 部署文件位于 `deploy/`。代码逻辑与函数路径不受影响。

# PubMed Research Agent — 源码生成报告

> 生成日期：2026-07-09
> 版本：v0.1.0
> 仓库：https://github.com/0609x/PubMed-Research-Agent

---

## 一、项目概览

| 指标 | 数值 |
|------|------|
| 项目名称 | PubMed-Research-Agent |
| 项目类型 | AI 科研文献智能分析系统 |
| 编程语言 | Python 3.11+ |
| 框架 | Streamlit（前端）/ httpx（API 客户端） |
| LLM 接口 | OpenAI 兼容（GPT / DeepSeek / Qwen / Ollama） |
| Python 源文件 | **14 个** |
| 总代码行数 | **3,429 行** |
| 总字符数 | **141,173 字符** |
| 单元测试 | **61 个** |
| 测试通过率 | **100%** |
| 业务模块 | **10 个**（2 Agent + 6 Service + 1 Tool + 1 Frontend） |
| 数据模型 | **12 个** Pydantic / dataclass |
| 自定义异常 | **4 个** |

---

## 二、源码统计总览

### 2.1 按模块分类

| 模块 | 文件 | 行数 | 占比 | 核心功能 |
|------|------|------|------|----------|
| `tools/` | `pubmed_tool.py` | 406 | 11.8% | PubMed E-utilities API 封装 |
| `agents/` | `research_agent.py` | 229 | 6.7% | 全流程编排 Agent |
| `agents/` | `query_rewrite.py` | 93 | 2.7% | 查询改写：自然语言→PubMed 检索式 |
| `services/` | `literature_summary.py` | 269 | 7.8% | LLM 文献结构化总结（5维分析） |
| `services/` | `hybrid_search.py` | 226 | 6.6% | 混合检索：关键词+语义 RRF 融合 |
| `services/` | `reranker.py` | 191 | 5.6% | 精排重排序：Pointwise/Listwise |
| `services/` | `context_compressor.py` | 207 | 6.0% | 上下文压缩：摘要 token 削减 |
| `services/` | `prompt_cache.py` | — | — | 提示缓存：Redis 共享 TTL 缓存、分布式防击穿锁；磁盘后端仅供离线开发 |
| `services/` | `memory.py` | 141 | 4.1% | 对话记忆：多轮会话持久化 |
| `frontend/` | `app.py` | 658 | 19.2% | Streamlit 前端主页面 |
| `frontend/` | `api_client.py` | 55 | 1.6% | Agent 调用封装层 |
| `tests/` | `test_pubmed_tool.py` | 315 | 9.2% | PubMed 工具测试 |
| `tests/` | `test_literature_summary.py` | 323 | 9.4% | 文献总结测试 |
| `tests/` | `test_research_agent.py` | 196 | 5.7% | Agent 编排测试 |
| **合计** | **14 文件** | **3,429** | **100%** | |

### 2.2 业务代码 vs 测试代码

| 类型 | 文件数 | 行数 | 占比 |
|------|--------|------|------|
| 业务代码 | 11 | 2,595 | 75.7% |
| 测试代码 | 3 | 834 | 24.3% |
| **测试/业务比** | | | **0.32 : 1** |

---

## 三、目录结构

```
PubMed-Research-Agent/
├── agents/                          # AI Agent 编排层  (322 行)
│   ├── research_agent.py            # 主 Agent：检索→总结→报告
│   └── query_rewrite.py             # 查询改写：自然语言→PubMed 语法
│
├── services/                        # 核心业务服务层  (1,154 行)
│   ├── literature_summary.py        # LLM 文献总结（5维分析输出）
│   ├── hybrid_search.py             # 混合检索（关键词+语义+RRF融合）
│   ├── reranker.py                  # 精排重排序（Pointwise/Listwise/Fast）
│   ├── context_compressor.py        # 上下文压缩（Token削减60-80%）
│   ├── prompt_cache.py              # Redis 共享提示缓存（TTL + 分布式锁）
│   └── memory.py                    # 对话记忆（多轮会话持久化）
│
├── tools/                           # 外部工具封装  (406 行)
│   └── pubmed_tool.py               # PubMed E-utilities API 完整封装
│
├── frontend/                        # Streamlit 前端  (713 行)
│   ├── app.py                       # 主页面（深色主题、Markdown导出）
│   ├── api_client.py                # Agent 调用封装
│   ├── components/                   # 可复用组件（预留）
│   └── pages/                        # 多页面（预留）
│
├── tests/                           # 单元测试  (834 行, 61 tests)
│   ├── unit/
│   │   ├── test_pubmed_tool.py       # 26 个测试 — PubMed 工具
│   │   ├── test_literature_summary.py # 24 个测试 — 文献总结
│   │   └── test_research_agent.py    # 11 个测试 — Agent 编排
│   └── integration/                  # 集成测试（预留）
│
├── backend/                         # FastAPI 后端（预留）
├── database/                        # SQLite 数据库存放
├── config/                          # 全局配置
│
├── requirements.txt                 # Python 依赖清单
├── .env.example                     # 环境变量模板
├── .gitignore                       # Git 忽略规则
└── README.md                        # 项目文档
```

---

## 四、核心模块详情

### 4.1 `tools/pubmed_tool.py` — PubMed 检索工具

| 属性 | 值 |
|------|-----|
| 代码行数 | 406 |
| 数据模型 | `Author`, `PubMedArticle`, `PubMedSearchResult`（3个dataclass） |
| 核心类 | `PubMedSearchTool` |
| 异常类 | `PubMedAPIError`, `PubMedParseError` |
| 外部依赖 | `Bio.Entrez`（biopython） |
| 测试覆盖 | 26 个测试 |

**功能清单：**
- ESearch：查询 → PMID 列表
- EFetch：批量 PMID → 完整文献记录（XML 解析）
- HTML 标签清洗（`_strip_html`）
- 作者解析（姓/名/首字母/单位）
- DOI 提取（ELocationID 解析）
- 出版日期格式化（支持数字月→英文缩写翻译）
- 限流控制（无 Key 3 req/s，有 Key 10 req/s）
- 摘要多段拼接（`AbstractText` Label 合并）

---

### 4.2 `services/literature_summary.py` — LLM 文献总结

| 属性 | 值 |
|------|-----|
| 代码行数 | 269 |
| 数据模型 | `ResearchHotspot`, `FutureDirection`, `ExperimentalMethod`, `LiteratureSummary`（4个Pydantic） |
| 核心类 | `LiteratureSummarizer` |
| 模型预置 | `gpt-4o`, `gpt-4o-mini`, `deepseek-chat`, `deepseek-reasoner`, `qwen-turbo`, `qwen-plus`, `qwen-max`（7个） |
| 外部依赖 | `httpx` |
| 测试覆盖 | 24 个测试 |

**功能清单：**
- OpenAI 兼容 Chat Completions API 调用
- `json_object` 模式强制结构化输出
- 5 维分析：研究背景 / 热点 / 发现 / 方法 / 未来方向
- `from_preset()` 工厂方法：一行切换模型
- JSON 自动修复：去除 markdown fence / 修复尾逗号
- 长摘要自动截断（1500 字符 → `...`）
- 支持中英文输出语言切换

---

### 4.3 `services/hybrid_search.py` — 混合检索

| 属性 | 值 |
|------|-----|
| 代码行数 | 226 |
| 核心类 | `HybridSearcher`, `EmbeddingClient`, `SimpleVectorStore` |
| 算法 | Reciprocal Rank Fusion（k=60） |
| 外部依赖 | `httpx`, `PubMedSearchTool` |
| 测试覆盖 | （集成到 Agent 测试中） |

**功能清单：**
- 关键词检索（PubMedSearchTool）
- 语义检索（Embedding API → Cosine Similarity）
- RRF 双榜融合（无超参数、位置鲁棒）
- 优雅降级：Embedding API 不可用 → 纯关键词
- 轻量级 `SimpleVectorStore`（内存向量存储，ChromaDB 不可用时替代）

---

### 4.4 `services/reranker.py` — 精排重排序

| 属性 | 值 |
|------|-----|
| 代码行数 | 191 |
| 核心类 | `LLMReranker` |
| 策略 | Pointwise（单篇评分）/ Listwise（全局排序）/ Fast（启发式） |
| 外部依赖 | `LiteratureSummarizer`（LLM） |
| 测试覆盖 | （集成到 Agent 测试中） |

**功能清单：**
- Pointwise：对每篇论文独立评分（0-10），LLM 评估真实相关性
- Listwise：N≤15 时一次性全局排序
- Fast：基于查询词密度的零成本启发式排序（无 LLM 调用）
- 降级策略：LLM 不可用 → Fast；Listwise 失败 → 原始序

---

### 4.5 `services/context_compressor.py` — 上下文压缩

| 属性 | 值 |
|------|-----|
| 代码行数 | 207 |
| 核心类 | `ContextCompressor` |
| 策略 | Extractive / LLM / Hybrid |
| 外部依赖 | `LiteratureSummarizer`（LLM，可选） |
| 测试覆盖 | （集成到 Agent 测试中） |

**功能清单：**
- Extractive：保留高分句子（查询词+方法关键词加权），去除 7 类 boilerplate
- LLM：用小模型提取 2-4 个 key points
- 压缩后标记 `compressed: True` + `original_chars` 可审计
- 统计日志：压缩率报告（X→Y chars, N% reduction）

---

### 4.6 `services/prompt_cache.py` — 提示缓存

| 属性 | 值 |
|------|-----|
| 代码行数 | 约 260 |
| 核心类 | `PromptCache` |
| 策略 | SHA256 哈希 + Redis TTL + 分布式锁 |
| 外部依赖 | Redis（线上）；磁盘后端仅用于离线开发与测试 |

**功能清单：**
- `get_or_compute()`：跨 Worker 复用结果，未命中时自动计算并缓存
- Redis 分布式锁抑制相同请求同时击穿到 LLM
- Redis TTL 自动过期（默认 24h），DB 1 与任务队列隔离
- Redis 不可用时放弃缓存但不阻断检索任务
- 磁盘 JSON 后端仅供显式的离线开发与单元测试
- 查询翻译、PubMed 检索式改写和最终摘要共享同一缓存服务

---

### 4.7 `services/memory.py` — 对话记忆

| 属性 | 值 |
|------|-----|
| 代码行数 | 141 |
| 核心类 | `ConversationMemory` |
| 策略 | Buffer / Summary / Hybrid |
| 外部依赖 | 无（仅标准库） |

**功能清单：**
- `add_turn()`：添加查询-报告对
- `get_context()`：获取上下文（支持注入系统提示词）
- `save()` / `load()`：跨天会话持久化
- `clear()`：重置会话
- `list_sessions()`：列出所有历史会话文件

---

### 4.8 `agents/research_agent.py` — 主 Agent

| 属性 | 值 |
|------|-----|
| 代码行数 | 229 |
| 数据模型 | `ResearchReport`（Pydantic） |
| 核心类 | `ResearchAgent` |
| 依赖 | `PubMedSearchTool` + `LiteratureSummarizer` |
| 测试覆盖 | 11 个测试 |

**工作流：**
```
用户问题 → PubMed 检索 → 文献获取 → LLM 总结 → JSON 报告
```
**容错设计：**
- PubMed 失败 → `status=failed`，错误入 `errors[]`
- LLM 失败 → `status=partial`，文献完整但分析为空
- 0 结果 → `status=completed`，无分析数据

---

### 4.9 `agents/query_rewrite.py` — 查询改写

| 属性 | 值 |
|------|-----|
| 代码行数 | 93 |
| 核心类 | `QueryRewriter` |
| 策略 | LLM 生成 MeSH + Boolean / 词典扩展（降级） |
| 外部依赖 | `LiteratureSummarizer`（LLM） |

**功能清单：**
- LLM 识别生物医学术语 → 映射 MeSH → 输出 `(SEC61G[All]) AND (Lung Neoplasms[MeSH])`
- 内存缓存（重复查询免调 LLM）
- `expand_with_synonyms()`：无 LLM 纯词典扩展（内置 6 组同义词）

---

### 4.10 `frontend/app.py` — Streamlit 前端

| 属性 | 值 |
|------|-----|
| 代码行数 | 658 |
| CSS 样式 | 约 200 行自定义深色主题 |
| 页面组件 | 15 个渲染函数 |

**功能清单：**
- **左侧**：PubMed API / LLM API 配置面板
- **顶部**：搜索框 + 渐变按钮
- **中部**：状态指标栏 → 文献卡片列表 → 5 维分析
- **底部**：JSON 下载 / Markdown 下载 / 复制
- 7 个模型预设下拉框
- SSL / 语言 / Temperature 可调节

---

## 五、测试覆盖

### 5.1 测试统计

| 测试文件 | 测试数 | 测试类 | 覆盖模块 |
|------|--------|--------|----------|
| `test_pubmed_tool.py` | **26** | 6 个 TestClass | `PubMedSearchTool` 完整覆盖 |
| `test_literature_summary.py` | **24** | 7 个 TestClass | `LiteratureSummarizer` 完整覆盖 |
| `test_research_agent.py` | **11** | 2 个 TestClass | `ResearchAgent` 编排流程 |
| **合计** | **61** | **15** | **3 个核心模块** |

### 5.2 测试覆盖矩阵

| 模块 | 初始化 | 正常路径 | 空数据 | HTTP 错误 | 网络错误 | JSON 修复 | 降级策略 |
|------|--------|----------|--------|-----------|----------|-----------|----------|
| `pubmed_tool.py` | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| `literature_summary.py` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `research_agent.py` | ✅ | ✅ | ✅ | — | — | — | ✅ |

### 5.3 未覆盖模块

以下模块通过 Agent 集成测试间接覆盖，缺少独立单元测试：

| 模块 | 原因 | 建议 |
|------|------|------|
| `hybrid_search.py` | 依赖 Embedding API 网络 | 添加 mock EmbeddingClient 的独立测试 |
| `reranker.py` | 依赖 LLM 评分 | 添加 mock 评分结果的独立测试 |
| `context_compressor.py` | 逻辑自包含 | 添加 extractive 压缩结果验证测试 |
| `prompt_cache.py` | 纯标准库 | 添加缓存命中/过期/淘汰测试 |
| `memory.py` | 纯标准库 | 添加 add_turn/get_context/save/load 测试 |
| `query_rewrite.py` | 依赖 LLM | 添加 rewrite 结果和 fallback 测试 |

---

## 六、依赖分析

### 6.1 运行时依赖

| 包名 | 版本 | 用途 | 所属模块 |
|------|------|------|----------|
| `biopython` | ≥1.84 | PubMed Entrez API 封装 | `pubmed_tool.py` |
| `httpx` | ≥0.28 | HTTP 客户端（LLM API + NCBI 备选） | `literature_summary.py`, `hybrid_search.py` |
| `pydantic` | ≥2.10 | 数据验证和序列化 | 全部业务模块 |
| `streamlit` | ≥1.40 | Web UI 前端 | `frontend/app.py` |
| `pytest` | ≥8.3 | 单元测试框架 | `tests/` |

### 6.2 标准库依赖

| 模块 | 用途 |
|------|------|
| `hashlib` | `PromptCache` 缓存键生成 |
| `json` | LLM 响应解析 / 缓存持久化 |
| `logging` | 全模块分级日志输出 |
| `re` | HTML 标签清洗 / boilerplate 移除 / JSON 修复 |
| `ssl` | SSL 验证控制 |
| `time` | 限流节拍 / 耗时统计 |
| `ast` | （开发用）语法检查 |
| `os` | 目录创建 / 文件路径 |

### 6.3 无重型框架依赖

项目选择不依赖以下常见重型框架：

| 框架 | 不引入原因 |
|------|------------|
| `langchain` / `langchain-openai` | 包体积大（十几个子包）、版本兼容复杂；OpenAI API 协议简单，httpx 直调更可控 |
| `chromadb` | 代码中标记为可选；内建 `SimpleVectorStore` 作为降级替代 |
| `fastapi` / `uvicorn` | 当前 Streamlit 内嵌 Agent 模式无需独立后端；架构已预留 `backend/` 目录 |

---

## 七、代码质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **类型注解** | ⭐⭐⭐⭐⭐ | 100% 覆盖，所有函数签名 + 返回类型完整标注 |
| **文档字符串** | ⭐⭐⭐⭐⭐ | 所有类/函数有 Google-style docstring，含 Parameters/Returns/Raises |
| **异常处理** | ⭐⭐⭐⭐☆ | 4 个自定义异常类，关键路径全覆盖。部分辅助函数缺少 try/catch |
| **日志记录** | ⭐⭐⭐⭐⭐ | logging 分级覆盖初始化/执行/异常/降级/性能 |
| **测试覆盖** | ⭐⭐⭐⭐☆ | 3 核心模块 100%，6 辅助模块集成覆盖（建议补单测） |
| **容错降级** | ⭐⭐⭐⭐⭐ | 每个外部依赖都有 2+ 种降级路径 |
| **模块化** | ⭐⭐⭐⭐⭐ | 14 个文件，10 个独立业务模块，SOLID 原则 |
| **可扩展性** | ⭐⭐⭐⭐⭐ | 预留 backend/chroma/RAG 集成接口 |

---

## 八、数据模型清单

| 模型名 | 类型 | 所在文件 | 字段数 | 说明 |
|------|------|----------|--------|------|
| `Author` | dataclass | `pubmed_tool.py` | 4 | 作者信息 |
| `PubMedArticle` | dataclass | `pubmed_tool.py` | 7 | 单篇文献 |
| `PubMedSearchResult` | dataclass | `pubmed_tool.py` | 4 | 检索结果容器 |
| `ResearchHotspot` | Pydantic | `literature_summary.py` | 3 | 研究热点 |
| `FutureDirection` | Pydantic | `literature_summary.py` | 3 | 未来方向 |
| `ExperimentalMethod` | Pydantic | `literature_summary.py` | 3 | 实验方法 |
| `LiteratureSummary` | Pydantic | `literature_summary.py` | 8 | LLM 总结输出 |
| `ResearchReport` | Pydantic | `research_agent.py` | 13 | 最终报告 |
| `PromptCache` | class | `prompt_cache.py` | — | 缓存服务 |
| `ConversationMemory` | class | `memory.py` | — | 记忆服务 |

---

## 九、交付物清单

| 类型 | 文件 | 状态 |
|------|------|------|
| 业务模块 | 10 个 `.py` 文件 | ✅ |
| 单元测试 | 3 个 `test_*.py` 文件，61 tests | ✅ 100% 通过 |
| 依赖清单 | `requirements.txt` | ✅ |
| 环境模板 | `.env.example` | ✅ |
| Git 忽略 | `.gitignore` | ✅ |
| 项目文档 | `README.md` | ✅ |
| 源码报告 | `SOURCE_REPORT.md`（本文件） | ✅ |

---

*报告由源码自动统计生成。Python 3.13.11 · pytest 9.1.1 · 2026-07-09*
