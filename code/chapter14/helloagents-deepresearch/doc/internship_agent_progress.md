# 找实习助手 Agent 开发进度

更新时间：2026-06-08

## 当前目标

基于 Hello-Agents 第十四章 deepresearch 项目，先完成一个后端可用的“找实习助手”MVP。

当前阶段重点不是重做前端或新增复杂数据结构，而是让后端流程稳定输出求职语境结果：

- 生成 3-5 个找实习任务。
- 搜索岗位、JD、投递渠道和简历优化相关信息。
- 输出岗位分析总结。
- 生成《找实习行动报告》。

## 已完成

- 已完成第十四章源码独立项目整理，目录为 `helloagents-deepresearch`。
- 已修复后端基础运行问题：
  - `pyproject.toml` 打包配置。
  - `.env` 加载。
  - Windows GBK 控制台 emoji 编码报错。
  - 非流式 `run` 未真正迭代任务执行的问题。
- 已新增本地兼容文件：
  - `backend/src/tool_aware_agent.py`
  - `backend/src/note_tool.py`
  - `backend/src/search_tool.py`
- 已将核心 Prompt 改为找实习语境：
  - Planner：求职任务规划。
  - Summarizer：岗位/JD/渠道/简历建议总结。
  - Reporter：找实习行动报告。
- 已完成后端输出稳定化：
  - Planner 会稳定生成 3-5 个任务。
  - Planner 解析失败时会 fallback 到 4 个默认任务。
  - 默认任务包括：岗位搜索、JD要求分析、投递渠道梳理、简历优化建议。
  - Reporter 会确保最终报告以 `# 找实习行动报告` 开头。
  - Agent 名称、流式状态、最终笔记标题和标签已改为求职语境。
- 已新增 Planner 单元测试，覆盖合法 JSON、解析失败、任务补齐、任务截断、字段兜底。
- 已修复任务 1/4 易失败的问题：
  - 流式任务默认串行执行，降低多个总结任务同时调用 LLM 导致超时的概率。
  - 搜索上下文默认不抓取整页内容，并将每个来源上下文限制降到 800 token。
  - Planner 会为岗位/JD/渠道/简历类任务自动补充招聘相关关键词，减少搜到技术教程的概率。
- 已修复最终报告生成失败的问题：
  - Reporter 会先截断过长的任务总结和来源，降低最终汇总 prompt 过长导致失败的概率。
  - 如果最终报告 LLM 调用超时、报错或返回空内容，后端会用已有任务摘要和来源生成兜底版《找实习行动报告》。
  - 最终报告笔记保存失败不再中断接口返回，避免“报告已生成但前端收不到”的情况。
- 已修复岗位搜索结果被面经/教程带偏的问题：
  - 岗位搜索任务会优先保留招聘平台、校招官网、岗位详情页、JD/投递页。
  - 明显的面经、面试题、教程、博客、提示词案例、学习资源、开源项目类结果会被过滤掉。
  - 如果首轮岗位搜索没有合格 JD 链接，后端会自动追加“岗位详情、职位描述、任职要求、投递入口、招聘官网、-面经、-教程、-博客、-提示词”等关键词重搜一次。
- 已完成前端产品化实用增强：
  - 前端主文案已从“深度研究助手”切换为“找实习助手”。
  - 输入区改为“求职目标”，并新增 Java 后端、AI 应用、前端实习 3 个一键示例。
  - 结果区改为“岗位/JD/渠道来源”“岗位分析”“找实习行动报告”等求职语境文案。
  - 任务状态新增 `failed` 的中文显示“失败”。
  - 新增“复制当前来源”和“复制报告”操作。
- 已完成结构化岗位清单与匹配评分工作台：
  - 后端新增 `JobItem`，并在 `SummaryState`、`SummaryStateOutput` 中增加 `job_items`。
  - 新增 `JobExtractionService`，从岗位搜索/JD任务的公开搜索结果中抽取最多 8 个岗位条目。
  - 匹配评分基于当前求职目标进行第一版 LLM 评分；信息不足时 `match_score=null`，并提示点开来源确认。
  - 抽取失败时只会从可靠招聘/JD/投递来源生成最小岗位条目；没有可靠来源时返回空 `job_items`，避免生成伪岗位。
  - `/research` 响应新增 `job_items`，`/research/stream` 新增 `job_items` 事件，`final_report` 事件附带最终岗位列表。
  - 前端新增“推荐岗位清单”工作台，支持岗位列表、匹配分、来源链接、JD要求、技术栈、匹配理由、简历建议和风险展示。
  - 无可靠岗位时会提示“暂未找到可靠岗位/JD链接”，不再展示只有“未确认”的伪岗位卡片。
- 已完成搜索质量闭环与诊断面板：
  - 后端会为岗位搜索/JD任务生成 `search_diagnostics`，统计原始结果数、可靠岗位数、过滤数量和过滤原因。
  - 岗位搜索首轮无可靠来源时，会追加平台/官网定向 query 再搜一次。
  - `/research` 响应、`/research/stream` 事件和 `final_report` 事件均已兼容输出搜索诊断。
  - 搜索诊断会保存到 `backend/data/search_diagnostics/{run_id}.json`，方便手动对比不同搜索引擎的结果质量。
  - 前端新增“搜索质量诊断”模块，展示搜索后端、可靠来源比例、过滤原因和下一步建议。
- 已完成 429 限流容错修复：
  - 新增 `services/llm_resilience.py`，统一识别 `429`、`rate limit`、`速率限制`、`code 1302`。
  - Planner、Summarizer、JobExtraction、Reporter 的主要 LLM 调用已接入限流重试。
  - 默认重试 2 次，等待 5 秒、10 秒，并通过单进程最小调用间隔降低连续打爆账号限额的概率。
  - Summarizer 流式生成遇到 429 且重试耗尽时，会输出以 `## 任务总结` 开头的兜底摘要，任务仍可完成。
  - Reporter 遇到 429 且重试耗尽时，继续使用后端兜底版《找实习行动报告》。
- 已完成代码审查安全与稳定性修复：
  - 后端 CORS 已从 `allow_origins=["*"]` 改为读取 `CORS_ALLOW_ORIGINS`，默认仅允许本地 Vite 常用端口。
  - 项目根目录新增 `.gitignore`，排除 `.env`、虚拟环境、运行笔记、诊断数据、`node_modules` 和构建产物。
  - 修复 `main.py` 重复 stderr 日志 handler，避免 ERROR 日志重复输出。
  - `NoteTool` 增加 workspace 路径边界检查，降低未来路径处理调整带来的风险。
  - 未实现搜索后端会明确提示“已降级为 DuckDuckGo”，不再静默或英文提示。
  - `job_items` SSE 输出前会使用锁内快照，避免并发合并时读到半更新状态。
  - 前端已移除未使用的 `axios` 依赖，并更新 lockfile。
- 已完成本地岗位保存与投递状态管理：
  - 后端新增 `services/applications.py`，使用 `backend/data/applications.json` 保存岗位和投递状态。
  - 新增辅助接口：`GET /applications`、`POST /applications`、`PATCH /applications/{item_id}`、`DELETE /applications/{item_id}`。
  - 投递状态限定为：待投递、已投递、笔试、面试、拒绝、Offer、放弃。
  - 保存岗位按来源链接生成稳定 ID；同一来源重复保存会更新岗位信息并保留已有状态。
  - 前端岗位工作台新增“保存岗位”“更新保存”“移除”、状态下拉、备注输入和“已保存岗位”清单。
  - 初始页会显示已保存岗位入口，刷新页面后可继续查看本地跟踪清单。
  - 新增 `test_applications.py`，覆盖保存、去重、状态更新、状态校验和删除。
- 已完成前端拆分与流式恢复工程化收尾：
  - `frontend/src/App.vue` 已拆分为页面 shell，保留布局切换、composables 组合和组件接线。
  - 新增 `components/`、`composables/`、`types/`、`utils/` 分层，承接岗位工作台、任务工作区、报告块、保存岗位和复制逻辑。
  - SSE 软恢复已迁移到 `useResearchWorkflow`：断线自动重试一次，支持手动“重新尝试”，用户取消和后端业务错误不自动重试。
  - 本地岗位保存/投递状态管理已迁移到 `useSavedApplications`，复制报告/来源/笔记路径逻辑已迁移到 `useClipboardActions`。

## 当前状态

后端 MVP 主链路已经具备可验证基础：

```text
用户求职需求 -> 求职任务规划 -> 搜索 -> 岗位分析总结 -> 找实习行动报告
```

当前接口和数据结构仍保持兼容：

- API 仍使用 `topic` 作为输入字段。
- 输出仍包含 `todo_items` 和 `report_markdown`。
- 输出已兼容新增 `job_items`，旧前端或旧调用方可继续忽略该字段。
- 输出已兼容新增 `search_diagnostics`，用于解释岗位清单质量和空结果原因。
- 已新增 `JobItem`；暂未新增 `MatchResult`。
- 岗位保存与投递状态已通过本地 JSON 和辅助 API 落地，不影响现有 `/research` 与 `/research/stream` 兼容性。
- 本地 `backend/.env` 已存在且已被 `.gitignore` 排除；真实 LLM/search 密钥仅保留在本机配置中，不提交仓库。
- 端到端复测时使用真实 LLM 配置运行，进程环境覆盖 `FETCH_FULL_PAGE=False`、`TASK_CONCURRENCY=1` 和 `LLM_MIN_INTERVAL_SECONDS=2` 以保持稳定。
- LLM 限流容错默认生效，可通过 `.env` 调整：
  - `LLM_RETRY_ATTEMPTS=2`
  - `LLM_RETRY_BASE_DELAY=5`
  - `LLM_RETRY_MAX_DELAY=20`
  - `LLM_MIN_INTERVAL_SECONDS=2`
- CORS 白名单默认覆盖本地前端，可通过 `.env` 调整：
  - `CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174`

## 验证情况

已通过：

```powershell
cd D:\1-school\agent\14\helloagents-deepresearch\backend
.\.venv\Scripts\python.exe -B -m unittest discover -s tests
```

结果：

```text
Ran 45 tests
OK
```

另已完成后端关键模块导入检查。最近一次完整后端单元测试仍为 `Ran 45 tests OK`，测试日志中的 429/timeout/fallback 输出是兜底逻辑覆盖的预期现象。

前端构建已通过：

```powershell
cd D:\1-school\agent\14\helloagents-deepresearch\frontend
npm run build
```

结果：

```text
vue-tsc --noEmit && vite build
built successfully
```

前端拆分后的行为回归 smoke 已完成：

- 使用临时 mock 后端验证 `/healthz`、`/applications` 保存/更新/删除，以及 `/research/stream` 普通完成、断线恢复、手动重试和业务 error 事件形状。
- 前端 dev server 在 `http://127.0.0.1:5174` 返回 200，入口 `#app` 存在。
- 早期真实后端 smoke 已确认 `/healthz` 正常，`/research/stream` 能返回初始化状态和任务清单事件；后续完整 SSE 复测结果见下文。

真实链路 SSE 复测已在真实 LLM 配置下完成，最近一轮结果如下：

- 后端加载真实自定义 LLM 配置和 `TAVILY_API_KEY`，日志中 `api_key` 仅脱敏显示；本轮未发现 LLM `502`。
- `tavily`：约 242 秒收到 `done`，包含 `search_diagnostics`、`job_items` 和 `final_report`；日志中出现 429，但重试和兜底摘要完成了 SSE。
- `duckduckgo`：约 113 秒收到 `done`，包含 `search_diagnostics`、`job_items` 和 `final_report`；未出现 SSE `error`。
- `advanced`：约 118 秒收到 `done`，包含 `search_diagnostics`、`job_items` 和 `final_report`；未出现 SSE `error`。
- 最近三份诊断 JSON 已生成到 `backend/data/search_diagnostics/`：
  - `tavily`：岗位搜索 5/1 可靠来源，JD 要求分析 5/3。
  - `duckduckgo`：岗位搜索 5/2 可靠来源，JD 要求分析 5/2，简历优化建议 5/2。
  - `advanced`：岗位搜索 10/5 可靠来源，JD 要求分析 5/0，简历优化建议 5/4。
- 前端 dev server 在 `http://127.0.0.1:5174` 返回 200，入口 `#app` 存在。
- 后端 `/applications` 替代 smoke 已通过：保存岗位、更新状态为 `Offer`、更新备注、删除岗位均成功，清单计数从 0 到 1 再回到 0。
- 内置浏览器通道仍不可用，未完成真实页面点击、复制和保存岗位的交互级自动化验证。

已确认本轮配置检查：

```text
backend/.env: exists locally
LLM_PROVIDER/LLM_MODEL_ID/LLM_API_KEY/LLM_BASE_URL: configured locally
TAVILY_API_KEY: configured locally
runtime FETCH_FULL_PAGE=False
runtime TASK_CONCURRENCY=1
runtime LLM_MIN_INTERVAL_SECONDS=2
```

本轮搜索质量小补丁已进入实现与验证：

- 优先修复真实 JD 被误判为教程/博客的问题，可信招聘详情 URL 会优先保留。
- 已移除“经验”作为硬负面词，避免 JD 中的“项目经验”“开发经验”导致岗位被误杀。
- 二次平台定向搜索补充 `site:zhipin.com/job_detail`、`site:shixiseng.com/intern` 和 `site:jobs.bytedance.com`，但仍只在首轮无可靠来源时重试一次。
- 搜索诊断建议已补充“可能误命中 JD 中的经验词”的提示；岗位清单为空时仍保持可靠空态，不生成伪岗位。
- 真实 LLM 无 `502` 端到端验收已完成；后续若频繁触发 429，可继续提高 `LLM_MIN_INTERVAL_SECONDS`。

未完成：

- `ruff` 未运行，因为当前后端虚拟环境未安装 `ruff`。
- 尚未使用可用浏览器通道对真实链路页面面板做点击、复制、保存岗位等交互级复测；当前已完成 dev server 和 `/applications` API 替代 smoke。
- 真实链路仍会触发 429 限流，但已确认重试和兜底摘要可完成 SSE；后续可按需调大调用间隔。
- 尚未将岗位保存清单升级为 SQLite 或多用户存储；当前适合单机本地开发和演示。

## 下一步

优先级建议：

1. 在可用浏览器通道中检查“复制当前来源”“复制报告”“复制笔记路径”和岗位保存/状态/备注/移除是否可用。
2. 启动前端，用真实求职输入人工检查任务清单、岗位/JD/渠道来源、岗位分析和最终报告是否正常展示。
3. 检查“搜索质量诊断”是否显示搜索后端、可靠来源数量、过滤原因和建议操作。
4. 检查“推荐岗位清单”是否只展示可靠招聘/JD来源；若为空，应显示诊断建议而不是伪岗位。
5. 若仍频繁触发 429，可临时提高 `LLM_MIN_INTERVAL_SECONDS` 或降低搜索/总结频率后重启后端。
6. 后续可考虑简历上传匹配、模型切换配置、真实浏览器自动化回归或将岗位库升级为 SQLite。

推荐测试输入：

```text
我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot、MySQL、Redis，有一个 RAG 项目。
```

## 风险与注意事项

- 招聘信息更新快，报告中必须保留来源链接，并提醒用户核验。
- 搜索结果可能来自公开摘要，不一定是最新 JD。
- 当前版本不做自动投递、登录招聘平台或绕过平台规则。
- 简历和个人背景可能包含隐私，后续做持久化和日志时需要脱敏。
- 匹配分析目前仍是 Markdown 文本，尚未结构化评分。
- 429 修复只能降低失败率，不能突破服务商账号本身的速率/额度限制。
