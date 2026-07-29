# 第八章：记忆与检索摘要

> 来源：`docs/chapter8/第八章 记忆与检索.md`  
> 用途：为后续搭建自己的 Agent 记忆系统提供设计参考。

## 1. 本章核心目标

第八章围绕两个能力展开：

1. **Memory System（记忆系统）**：让 Agent 能保存、检索、整合、遗忘历史交互、用户偏好、经验和知识。
2. **RAG（Retrieval-Augmented Generation，检索增强生成）**：让 Agent 在回答前从外部知识库检索相关内容，降低幻觉、补充最新或专业知识。

核心思想是：

- LLM 本身是无状态的，无法跨会话自动记住用户信息。
- LLM 内置知识静态且有截止时间，需要外部知识库补充。
- 记忆系统解决“我和用户经历过什么、学到了什么”。
- RAG 系统解决“外部文档里有什么可用知识”。
- 两者结合后，可以构建具有长期上下文、个性化和知识检索能力的 Agent。

## 2. 智能体为什么需要记忆

LLM/Agent 的常见限制：

1. **对话遗忘**：模型 API 调用默认无状态，重启或新会话后不知道之前内容。
2. **上下文窗口有限**：长对话早期信息可能被截断。
3. **个性化不足**：无法长期记住用户偏好、身份、任务背景。
4. **经验不可积累**：无法把过去成功/失败经验用于后续决策。
5. **知识有限**：训练数据有时间截止点，专业领域知识不一定完整。

因此，Agent 需要一个外部记忆层，将短期上下文、长期经历、抽象知识和外部文档分别管理。

## 3. 记忆系统的认知模型

本章借鉴人类记忆系统，将 Agent 记忆分为多层：

| 人类记忆 | Agent 中的对应设计 | 特点 |
|---|---|---|
| 感觉记忆 | 感知记忆 Perceptual Memory | 图像、音频、文件等多模态信息 |
| 工作记忆 | Working Memory | 当前会话上下文，短期、快速、容量有限 |
| 情景记忆 | Episodic Memory | 具体事件、交互经历、时间线 |
| 语义记忆 | Semantic Memory | 抽象知识、用户偏好、规则、概念 |

记忆生命周期包括：

1. **Encoding 编码**：把输入转换成可存储结构，如文本、向量、元数据。
2. **Storage 存储**：写入内存、SQLite、向量库或图数据库。
3. **Retrieval 检索**：根据查询找相关记忆。
4. **Consolidation 整合**：把重要短期记忆提升为长期记忆。
5. **Forgetting 遗忘**：清理过期、低重要性或超容量的记忆。

## 4. HelloAgents 记忆系统架构

文档中设计了四层记忆架构：

```text
HelloAgents 记忆系统
├── 基础设施层
│   ├── MemoryManager：统一调度和协调
│   ├── MemoryItem：标准化记忆项
│   ├── MemoryConfig：配置管理
│   └── BaseMemory：记忆基类接口
├── 记忆类型层
│   ├── WorkingMemory：工作记忆
│   ├── EpisodicMemory：情景记忆
│   ├── SemanticMemory：语义记忆
│   └── PerceptualMemory：感知记忆
├── 存储后端层
│   ├── QdrantVectorStore：向量存储
│   ├── Neo4jGraphStore：图存储
│   └── SQLiteDocumentStore：文档存储
└── 嵌入服务层
    ├── DashScopeEmbedding：云端嵌入
    ├── LocalTransformerEmbedding：本地嵌入
    └── TFIDFEmbedding：轻量兜底
```

设计原则：

- `MemoryTool` 作为 Agent 调用记忆能力的统一工具入口。
- `MemoryManager` 负责底层调度不同记忆类型。
- 不同记忆类型使用不同存储和检索策略。
- 嵌入服务统一封装，方便切换云端、本地或 TF-IDF。

## 5. 四种记忆类型总结

### 5.1 Working Memory：工作记忆

定位：当前会话的短期上下文。

特点：

- 纯内存存储，访问速度快。
- 容量有限，例如默认 50 条。
- 使用 TTL 自动清理，例如 60 分钟。
- 适合保存当前任务中的临时状态、刚刚提到的问题、短期上下文。

典型内容：

- “用户刚才问了 Python 函数的问题”。
- “当前任务是分析第八章文档”。
- “本轮对话中用户希望输出中文摘要”。

检索策略：

- TF-IDF + 关键词匹配。
- 综合考虑语义相似度、时间衰减、重要性。

评分思想：

```text
最终得分 = 相关性 × 时间衰减 × 重要性权重
重要性权重 = 0.8 + importance × 0.4
```

适合自己实现时先做成最小版本：一个内存列表 + max_size + timestamp + search。

### 5.2 Episodic Memory：情景记忆

定位：长期保存具体事件和经历。

特点：

- 记录“发生过什么”。
- 带有时间戳、session_id、event_type、上下文元数据。
- 支持按时间线或主题检索。
- 可用于复盘、生成学习报告、回顾历史任务。

典型内容：

- “2026-07-25 用户要求总结 docs/chapter8”。
- “用户加载了某个 PDF 文档”。
- “用户完成了某次学习任务”。

推荐元数据：

```python
{
    "session_id": "session_20260725_153000",
    "event_type": "document_loaded | qa_interaction | task_completed",
    "timestamp": "...",
    "importance": 0.7
}
```

存储方案：

- SQLite 保存结构化事件。
- Qdrant 保存向量，支持语义检索。

评分思想：

```text
最终得分 = (向量相似度 × 0.8 + 时间近因性 × 0.2) × 重要性权重
```

### 5.3 Semantic Memory：语义记忆

定位：长期保存抽象知识、用户偏好、规则、概念。

特点：

- 记录“什么是真的/重要的”。
- 比情景记忆更抽象，不一定绑定某个具体事件。
- 适合保存用户长期偏好、领域知识、项目规则、Agent 行为准则。
- 可结合向量数据库和知识图谱。

典型内容：

- “用户偏好中文解释”。
- “Python 是解释型、面向对象的编程语言”。
- “Agent 需要在回答前优先检索用户相关记忆”。

存储方案：

- Qdrant：语义相似检索。
- Neo4j：实体和关系图谱，例如 用户 - 偏好 - 中文摘要。

检索策略：

- 向量检索 + 图检索混合。
- 向量用于语义相似度。
- 图用于关系推理、多跳查询和概念关联。

评分思想：

```text
最终得分 = (向量相似度 × 0.7 + 图相似度 × 0.3) × 重要性权重
```

### 5.4 Perceptual Memory：感知记忆

定位：保存多模态感知数据。

特点：

- 支持文本、图片、音频等。
- 不同模态可使用不同编码器。
- 各模态向量空间可能维度不同，因此适合分集合存储。

典型内容：

- 用户上传的代码截图。
- 用户上传的音频笔记。
- 文档中的图片、表格、视觉内容说明。

存储建议：

```text
perceptual_text
perceptual_image
perceptual_audio
```

评分思想类似情景记忆：

```text
最终得分 = (向量相似度 × 0.8 + 时间近因性 × 0.2) × 重要性权重
```

## 6. MemoryTool 核心操作

`MemoryTool` 是统一入口，通过 `execute(action, **kwargs)` 调用不同动作。

### 6.1 add：添加记忆

作用：把内容写入指定记忆类型。

关键参数：

- `content`：记忆内容。
- `memory_type`：`working | episodic | semantic | perceptual`。
- `importance`：重要性，通常 0.0-1.0。
- `metadata`：额外上下文，如 session_id、timestamp、event_type、file_path、modality。

示例：

```python
memory_tool.execute(
    "add",
    content="用户是一名 Python 开发者，关注 Agent 记忆系统",
    memory_type="semantic",
    importance=0.8
)
```

### 6.2 search：搜索记忆

作用：根据查询从记忆系统中找相关内容。

关键参数：

- `query`：查询文本。
- `limit`：返回数量。
- `memory_type` 或 `memory_types`：限定记忆类型。
- `min_importance`：过滤低重要性记忆。

示例：

```python
memory_tool.execute(
    "search",
    query="用户偏好和学习目标",
    memory_types=["semantic", "episodic"],
    limit=5,
    min_importance=0.5
)
```

### 6.3 summary：生成摘要

作用：生成当前记忆概览，便于查看系统知道什么。

适合用于：

- 调试记忆系统。
- 启动 Agent 时构建系统上下文。
- 生成用户画像或学习报告。

### 6.4 forget：遗忘记忆

作用：清理不重要、过期或超容量的记忆。

三种策略：

1. `importance_based`：删除重要性低于阈值的记忆。
2. `time_based`：删除超过指定时间的记忆。
3. `capacity_based`：容量超限时删除低优先级记忆。

示例：

```python
memory_tool.execute("forget", strategy="importance_based", threshold=0.2)
memory_tool.execute("forget", strategy="time_based", max_age_days=30)
```

### 6.5 consolidate：整合记忆

作用：把重要的短期记忆转为长期记忆。

常见路径：

```text
working -> episodic
情景中的高价值知识 -> semantic
```

示例：

```python
memory_tool.execute(
    "consolidate",
    from_type="working",
    to_type="episodic",
    importance_threshold=0.7
)
```

## 7. RAG 系统摘要

RAG 解决的是外部知识检索问题。

基本流程：

```text
外部文档 -> 文本提取 -> 分块 -> 向量化 -> 向量数据库 -> 查询检索 -> 注入 Prompt -> LLM 生成回答
```

HelloAgents 的 RAG 系统设计为：

```text
RAGTool 统一接口
  ↓
应用层：智能问答、搜索、知识库管理
  ↓
处理层：文档解析、Markdown 转换、分块、向量化
  ↓
存储层：Qdrant 向量库、文档存储
  ↓
基础层：嵌入模型、LLM、数据库
```

## 8. 文档处理与分块策略

本章使用 MarkItDown 将不同格式文档统一转换为 Markdown。

支持格式包括：

- PDF
- Word
- Excel
- PowerPoint
- 图片 OCR
- 音频转录
- TXT / CSV / JSON / XML / HTML
- 代码文件

统一转 Markdown 的好处：

- 后续处理流程一致。
- 可以利用 Markdown 标题层级做结构化分块。
- 更容易保留章节、段落和上下文。

分块策略：

1. 根据 Markdown 标题 `# / ## / ###` 识别层级。
2. 按段落保持语义完整性。
3. 估算 token 长度控制 chunk 大小。
4. 使用 overlap 保持上下文连续。
5. 每个 chunk 保留 `heading_path`、start/end、document_id 等元数据。

推荐参数：

```python
chunk_size = 1000
chunk_overlap = 200
```

## 9. 嵌入模型与向量存储

嵌入模型用于把文本转为向量。

本章提供三类方案：

| 方案 | 优点 | 缺点 | 适用场景 |
|---|---|---|---|
| DashScope / 百炼 API | 效果较好，云端维护 | 需要 API Key，有成本 | 生产或效果优先 |
| Local Transformer | 可离线，成本低 | 需要本地模型和算力 | 私有部署、离线应用 |
| TF-IDF | 轻量，无模型依赖 | 语义理解弱 | 兜底、简单原型 |

向量数据库使用 Qdrant：

- 存储 chunk embedding。
- 支持相似度检索。
- 可通过 namespace / collection 隔离不同用户或知识库。

## 10. 高级 RAG 检索策略

### 10.1 MQE：多查询扩展

Multi-Query Expansion 的思想：一个问题可以有多种表达，生成多个语义等价或互补查询并一起检索。

例：

```text
原始问题：如何学习 Python？
扩展查询：
- Python 入门教程
- Python 学习方法
- Python 编程指南
```

适合：

- 用户表达模糊。
- 文档用词和用户问题不一致。
- 希望提高召回率。

### 10.2 HyDE：假设文档嵌入

Hypothetical Document Embeddings 的思想：先让 LLM 生成一个“可能的答案段落”，再用这个答案去检索真实文档。

优势：

- 用“答案形态”匹配“文档形态”。
- 缩小问题和文档之间的语义鸿沟。
- 专业领域问题常有帮助。

适合：

- 技术文档问答。
- 专业概念检索。
- 用户问题很短但文档内容较长。

### 10.3 扩展检索框架

完整流程：

```text
原始 query
  -> MQE 生成多个 query
  -> HyDE 生成假设答案
  -> 对每个 query 执行向量检索
  -> 合并结果
  -> 去重
  -> 按分数排序
  -> 返回 top-k
```

建议：

- 一般查询：启用 MQE。
- 专业领域查询：MQE + HyDE。
- 性能敏感场景：基础检索或只启用 MQE。

## 11. Memory 与 RAG 的区别

| 维度 | Memory | RAG |
|---|---|---|
| 主要对象 | 用户交互、偏好、经历、抽象知识 | 外部文档、知识库、资料 |
| 解决问题 | Agent 记住过去 | Agent 查找外部知识 |
| 生命周期 | 随用户和会话持续演化 | 随知识库更新变化 |
| 典型存储 | 内存、SQLite、Qdrant、Neo4j | 文档库、Qdrant |
| 检索目标 | “我知道这个用户/任务的什么历史” | “文档中有什么相关内容” |
| 输出用途 | 个性化、上下文延续、复盘 | 准确问答、引用来源、知识补充 |

简单判断：

- 问题涉及用户历史、偏好、学习进度、之前做过什么：优先 Memory。
- 问题涉及某份文档、手册、论文、知识库内容：优先 RAG。
- 复杂助手通常同时使用二者。

## 12. 智能文档问答助手案例

本章最终案例是一个基于 Gradio 的 PDF 学习助手，整合 `MemoryTool` 和 `RAGTool`。

核心功能：

1. **加载文档**
   - RAGTool 处理 PDF。
   - MarkItDown 转 Markdown。
   - 分块、向量化、存入知识库。
   - MemoryTool 记录“加载了文档”到情景记忆。

2. **智能问答**
   - 用户问题先写入工作记忆。
   - RAGTool 用 MQE/HyDE 检索相关文档片段并回答。
   - 问答事件写入情景记忆。

3. **学习笔记**
   - 用户手动添加笔记。
   - 笔记写入语义记忆。

4. **学习回顾**
   - 从 Memory 中检索历史学习过程。

5. **学习报告**
   - 汇总 session_id、用户 ID、文档数量、提问次数、笔记数量、记忆摘要、RAG 状态。

## 13. 搭建自己 Agent 记忆系统的建议路线

### 13.1 最小可行版本

先实现简单但完整的闭环：

```text
MemoryItem 数据结构
  -> add_memory
  -> search_memory
  -> summarize_memory
  -> forget_memory
```

建议字段：

```python
{
    "id": "uuid",
    "content": "记忆内容",
    "memory_type": "working | episodic | semantic | perceptual",
    "importance": 0.5,
    "timestamp": "ISO 时间",
    "user_id": "用户 ID",
    "session_id": "会话 ID",
    "metadata": {}
}
```

### 13.2 第一阶段：工作记忆

目标：让 Agent 在当前会话内更稳定。

实现：

- 使用 Python list 或 dict。
- 限制最大容量。
- 记录 timestamp。
- 关键词检索即可。

### 13.3 第二阶段：长期事件记忆

目标：跨会话记住发生过的事。

实现：

- SQLite 存储 MemoryItem。
- 增加 `session_id`、`event_type`。
- 支持按时间和关键词查询。

### 13.4 第三阶段：语义记忆

目标：保存稳定知识和用户偏好。

实现：

- 可以先用 SQLite + embedding 字段或本地 JSON。
- 后续接 Qdrant 做向量检索。
- 对用户偏好、长期指令设置较高 importance。

### 13.5 第四阶段：记忆整合与遗忘

目标：避免记忆无限增长。

实现策略：

- 工作记忆中 importance >= 0.7 的内容转入情景记忆。
- 情景记忆中反复出现或高度重要的内容抽象成语义记忆。
- 定期删除低重要性、过期、低访问频次的记忆。

### 13.6 第五阶段：加入 RAG

目标：让 Agent 能查外部文档。

实现：

- 文档转文本/Markdown。
- chunk + overlap。
- embedding。
- Qdrant 或本地向量索引。
- 查询时检索 top-k 文档片段并注入 prompt。

## 14. 推荐的记忆写入规则

构建自己的 Agent 时，不建议“什么都记”。可以采用以下规则：

应写入记忆：

- 用户明确要求记住的信息。
- 用户长期偏好、身份、目标。
- 当前任务中的关键决策。
- 已完成的重要事件。
- 反复出现的问题和解决经验。
- 用户手动保存的笔记。

不建议写入记忆：

- 临时闲聊。
- 一次性中间过程。
- 可从代码或文档重新读取的信息。
- 敏感信息，如密码、密钥、身份证、银行卡。
- 低价值重复内容。

## 15. 推荐的检索路由策略

可以在 Agent 回答前做一个简单路由：

```text
用户问题
  -> 是否涉及当前对话？查 working memory
  -> 是否涉及历史事件/学习进度？查 episodic memory
  -> 是否涉及用户偏好/规则/稳定知识？查 semantic memory
  -> 是否涉及外部文档/知识库？查 RAG
  -> 合并上下文
  -> 构造 prompt
  -> LLM 回答
```

示例判断：

| 用户问题 | 优先检索 |
|---|---|
| “我刚才问了什么？” | Working Memory |
| “我上次加载了什么文档？” | Episodic Memory |
| “我偏好什么格式的回答？” | Semantic Memory |
| “这篇 PDF 对 RAG 是怎么解释的？” | RAG |
| “结合我之前的笔记解释这个概念” | Semantic Memory + RAG |

## 16. 数据隔离建议

如果未来做多用户 Agent：

- 每条 MemoryItem 都带 `user_id`。
- 每个 session 带 `session_id`。
- Qdrant 中使用 metadata filter 过滤 `user_id`。
- RAG 中使用 `rag_namespace` 隔离知识库。
- Neo4j 中实体和关系也要带 user_id 或 namespace。
- 不同用户之间默认不可互相检索。

## 17. 本章最值得借鉴的设计点

1. **记忆作为工具，而不是新 Agent 类**：保持框架简单，方便注册到任何 Agent。
2. **统一 MemoryTool 接口**：所有操作都通过 `execute(action, **kwargs)`。
3. **分类型记忆**：不同信息进入不同生命周期和存储后端。
4. **重要性 importance**：用于检索排序、整合和遗忘。
5. **session_id + user_id**：支持会话追踪和多用户隔离。
6. **向量检索 + 图检索**：语义记忆既能相似匹配，也能关系推理。
7. **RAG 和 Memory 分工明确**：一个管理个人历史，一个管理外部知识。
8. **整合和遗忘机制**：避免记忆无限增长，使记忆更接近真实认知系统。

## 18. 后续实现可参考的目录结构

如果在 `MyAgent/Memory` 下实现自己的版本，可以参考：

```text
MyAgent/Memory/
├── base.py              # MemoryItem、MemoryConfig、BaseMemory
├── manager.py           # MemoryManager
├── working.py           # 工作记忆
├── episodic.py          # 情景记忆
├── semantic.py          # 语义记忆
├── storage.py           # SQLite / JSON / VectorStore 封装
├── embedding.py         # 嵌入模型封装
├── memory_tool.py       # Agent 可调用的记忆工具
└── rag_tool.py          # 可选：RAG 工具
```

建议先不要一次性实现 Qdrant、Neo4j、多模态等完整能力。可以先做：

```text
MemoryItem + JSON/SQLite 持久化 + 简单关键词搜索 + importance + session_id
```

跑通后再逐步加入 embedding、向量库、整合、遗忘和 RAG。