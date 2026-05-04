# AgentPlatformBase - 双智能体任务平台

`AgentPlatformBase` 是一个面向 Hello-Agents 第 16 章毕业项目的轻量智能体平台。它用 FastAPI 提供统一后端，用浏览器前端承载对话入口，并接入两个有明确业务价值的智能体：搜索员 `deep_research` 和资讯员 `rss_digest`。

## 核心功能

- 统一智能体注册表：后端通过 `AgentRegistry` 管理不同智能体。
- 后台任务执行：长任务默认后台运行，前端轮询任务状态，不阻塞输入框。
- 搜索员：内置 DeepResearchAgent，生成调研报告并保留运行产物和长期笔记。
- 资讯员：拉取 RSS、抽取正文、调用 LLM 生成中文摘要，并渲染 HTML 简报。
- 数据分区：所有智能体数据统一放在 `data/{agent_id}/`，便于清理和提交时忽略。

## 项目结构

```text
agent_platform_base/
  backend/
    agents/
      adapters/
        deep_research.py
        rss_digest.py
      base.py
      profiles.py
      registry.py
    memory/
    tasks/
    main.py
    config.py
    maintenance.py
    events.py
    models.py

  frontend/
    index.html
    styles.css
    app.js

  agents/
    deep_research/
      README.md
      src/
        agent.py
        config.py
        services/
    rss_digest/
      src/rss_digest/
      config/
      scripts/
      main.py
      README.md

  data/
    deep_research/
      runs/
      notes/
    rss_digest/
      runs/
      state/

  .env.example
  requirements.txt
  smoke_test.py
```

目录规则：

- `backend/`：平台后端，只放 API、任务、注册表、适配器和平台公共逻辑。
- `frontend/`：单页前端工作台。
- `agents/{agent_id}/`：具体智能体代码、配置和脚本。
- `data/{agent_id}/runs/`：可清理的运行产物。
- `data/{agent_id}/notes/`：长期保留的知识和笔记，仅有需要的智能体才创建。
- `data/{agent_id}/state/`：持久状态，例如 RSS 去重数据库。

## 技术栈

- Python 3.10+
- FastAPI / Uvicorn
- Pydantic
- hello-agents / OpenAI SDK / Tavily / DDGS
- Requests / Python 标准库 RSS 与 HTML 解析
- 原生 HTML、CSS、JavaScript

## 快速开始

```powershell
cd Co-creation-projects\huailishang-AgentPlatformBase
python -m pip install -r requirements.txt
python main.py
```

访问：

- 前端工作台：http://127.0.0.1:8016/app/
- API 文档：http://127.0.0.1:8016/docs
- 健康检查：http://127.0.0.1:8016/health

## 使用示例

前端输入框必须用 `@` 指定智能体：

```text
@deep_research 调研 AI Agent 平台架构
@rss_digest 今日简报
@rss_digest 强制刷新今日简报
```

如果当天已经生成 RSS HTML 简报，普通 `@rss_digest 今日简报` 会直接返回已有简报，避免重复拉取和重复消耗 LLM。输入包含“强制”“重新生成”“刷新”或 `force/refresh` 时会重新运行 RSS pipeline。

## 运行机制

```text
POST /tasks
POST /tasks/{task_id}/run        默认后台启动，立即返回 running
GET  /tasks/{task_id}            前端轮询直到 completed / failed
```

同步调试可以使用：

```text
POST /tasks/{task_id}/run?background=false
```

任务完成后会在 `artifacts.elapsed_seconds` 记录总耗时。RSS 和 DeepResearch 还会记录更细的阶段耗时，便于后续优化。

## RSS 默认配置

```env
RSS_SOURCE_LIMIT=10
RSS_ENTRIES_PER_SOURCE=5
RSS_MAX_NEW_ARTICLES_PER_RUN=50
RSS_MAX_SUMMARY_ARTICLES_PER_RUN=10
RSS_AI_MAX_CONCURRENCY=2
RSS_RELEVANCE_THRESHOLD=65
RSS_MAX_DIGEST_ARTICLES=12
```

RSS 后台日志只保留阶段级进度和最终统计，逐个 feed、逐篇文章、逐条摘要的过程日志不再打印到后台。

## 清理策略

清理逻辑在 `backend/maintenance.py`，长任务调用时惰性触发：

- `RESEARCH_RUN_RETENTION_DAYS=7`：删除超过 7 天的搜索员运行产物。
- `RSS_DIGEST_RETENTION_DAYS=7`：删除超过 7 天的 RSS HTML 简报。
- `RSS_CACHE_RETENTION_DAYS=7`：删除超过 7 天的 RSS 原始 HTML、正文抽取和翻译缓存。
- 不自动删除 `data/deep_research/notes`。
- 不自动删除 `data/rss_digest/state/articles.json`。

## 自检

```powershell
cd Co-creation-projects\huailishang-AgentPlatformBase
python smoke_test.py
```

通过时输出：

```text
chapter16 platform smoke test passed
```

## 提交说明

按第 16 章要求，最终提交版会整理到：

```text
Co-creation-projects/huailishang-AgentPlatformBase/
```

提交版不包含 `.env`、运行数据、缓存、视频、大模型文件或其它大文件，确保项目体积满足 5MB 要求。

## 项目亮点

- 平台层和智能体层分离，后续新增智能体只需要实现适配器并注册 profile。
- 长耗时任务后台执行，前端体验不会被 RSS 抓取或 DeepResearch 调研阻塞。
- RSS 使用轻量增量策略，默认每次最多处理 10 个源、50 篇正文、10 篇摘要，避免一次调用过慢。
- 运行产物和长期知识统一归档到 `data/{agent_id}/`，提交时可以整体忽略。

## 效果评估

- `smoke_test.py` 覆盖健康检查、智能体列表、dry run、批量保护和任务执行基本链路。
- 提交目录体积约 143KB，不包含运行数据和密钥，满足 5MB 限制。
- RSS 后台日志已收敛为阶段级统计，避免逐篇文章刷屏。

## 后续计划

- 为 `deep_research` 增加更完整的前端报告查看页。
- 为 RSS 简报增加前端筛选、收藏和历史归档入口。
- 将任务事件持久化到 SQLite，支持服务重启后的任务历史查询。

## 作者

- GitHub 用户名目录：`huailishang-AgentPlatformBase`
- 项目路径：`Co-creation-projects/huailishang-AgentPlatformBase/`

## 许可证

本项目用于 Hello-Agents 课程毕业设计提交，遵循仓库根目录许可证约束。
