# 找实习助手 Agent 开发进度

更新时间：2026-06-13

## 当前状态

- 项目已从 Hello-Agents 第十四章 deepresearch 改造为“找实习助手 Agent”。
- 后端核心接口保持兼容：`/research`、`/research/stream`、`/applications`。
- 前端支持结构化求职画像、岗位推荐清单、排序筛选、来源可信度、信息完整度、推荐优先级、待确认项、搜索质量诊断和本地投递状态管理。
- 最终行动报告已升级为 6 章结构：今天优先投递、推荐理由、简历修改清单、7 天投递计划、风险与待确认项、来源与搜索诊断。
- 最新一轮重点已完成：稳定性门槛和轻量投递行动管理。

## 已完成

- v2.0 第一步：结构化求职画像表单。
- v2.0 第二步：岗位清单排序、筛选和可信度展示。
- v2.0 第三步：行动报告结构升级。
- 本地岗位保存与投递状态管理已落地。
- LLM 调用已统一通过 `BaseLLMClient` 入口，真实模型由 `RealLLMClient` 和 `HelloAgentsCompatibleLLM` 适配。
- 已支持 `LLM_MODE=real|fake|dry_run|replay`。
- 已支持 `.llm_cache/` 本地 LLM 调用缓存。
- 已支持 dry-run 模式和 `MAX_AGENT_STEPS` 最大步数限制。
- 已支持运行日志 `logs/run_{run_id}.json` 和 replay 模式。
- 已新增基础测试覆盖 prompt 构造、fake LLM、cache、dry-run、parser 和 replay。

## 关键决策

- `/research`、`/research/stream`、`/applications` 的 payload 继续保持兼容。
- 开发和测试优先使用 fake、dry-run、cache、replay，减少真实 LLM API 调用。
- 招聘信息必须保留来源并提醒用户核验。
- 匹配分、可信度和推荐优先级只作为辅助判断，不代表录用概率。
- 本地缓存、运行日志、运行数据和密钥全部通过 `.gitignore` 排除。

## 最近一次任务记录

### 2026-06-13：稳定性门槛与轻量投递行动管理

修改文件：

- 更新 `backend/src/agent.py`：内部 HelloAgents Agent 显式使用 `Config(trace_enabled=False)`，避免重复 trace、敏感信息副本和文件句柄泄漏。
- 更新 `backend/src/main.py`、`backend/src/services/applications.py`：保持三个核心路由兼容，为投递记录增加渠道、投递日期、下一步、待跟进日期、简历版本和放弃原因；日期严格使用 `YYYY-MM-DD`，旧 JSON 读取时自动补空字段。
- 新增 `backend/tests/test_api_contracts.py` 并扩展存储和 fake runtime 测试：覆盖同步响应、SSE `done/error` 终态、配置错误、applications CRUD、部分更新、主动清空、旧数据兼容和 trace 关闭。
- 更新前端 API 类型、normalizer、保存 composable 和 `JobWorkbench.vue`：增加完整投递行动表单，以及“今天待跟进”“已逾期”标签和汇总；拒绝、放弃状态不显示过期提醒。
- 新增 `frontend/src/utils/applicationTracking.ts`：集中处理浏览器本地日期和跟进状态判断。

验证结果：

- 后端全量测试通过：`Ran 81 tests`，`OK`；未调用真实 LLM 或搜索。
- 前端 `npm run build` 通过。
- 固定日期用例已覆盖今天、逾期、未来、空日期、拒绝和放弃状态。
- 本地前后端健康检查通过；内置浏览器当前不可用，未完成可视化点击核验。
- 全量测试中不再出现 hello_agents trace 的 `ResourceWarning`。

发现的问题与处理：

- FastAPI `on_event` 和当前 Starlette `TestClient` 依赖仍输出弃用警告，不影响本轮功能与测试结果；后续可单独迁移 lifespan 并同步测试客户端依赖。
- 跟进提示仅基于浏览器本地日期进行展示，不通知、不自动排序、不自动执行跟进。

下一步计划：

- 后续优先清理 FastAPI 启动事件与测试客户端的弃用警告，再考虑轻量导出或复盘能力。

### 2026-06-13：LLM 运行日志、严格回放与流式终态审查修复

修改文件：

- 更新 `backend/src/services/run_log.py`：运行日志升级为 schema v2，原始用户输入、完整 prompt 和工具输入改存长度与 SHA-256；日志写入改为锁内原子替换，目录不可写时降级为告警并停止本次落盘。
- 更新 `backend/src/agent.py`：流式致命异常和任务线程异常写入运行日志；严格 replay 使用工具输入哈希，并兼容旧日志中的原始工具输入格式。
- 更新 `backend/tests/test_run_log.py` 和 `backend/tests/test_agent_fake_runtime.py`：覆盖日志隐私、不可写降级、并发完整性、cache 严格 replay、禁止真实 LLM/搜索、流式终态、同步/流式步数一致性和旧日志兼容。

验证结果：

- 后端全量测试通过：`Ran 71 tests`，`OK`。
- 已验证 cache 生成的新日志可以严格 replay，replay 不调用真实 LLM 或搜索。
- 已验证成功 SSE 日志记录 `final_answer`，致命异常记录 `error`；工作线程失败可记录错误并继续生成最终报告。
- 未修改前端，因此未运行 `npm run build`。

发现的问题与处理：

- 原实现会保存原始求职输入、完整 prompt 和工具输入，且并发线程可能竞争写同一 JSON；现已最小化输入并串行原子写入。
- 原实现中运行日志目录不可写会中断 fake/dry-run；现已改为非致命降级。
- LLM 响应、搜索结果和最终报告为保证 replay 仍保留原文，可能包含模型或搜索结果回显的用户信息，日志文件仍应视为敏感本地数据。

下一步计划：

- 继续保留 hello_agents trace `ResourceWarning` 为已知依赖问题；后续可单独调查资源关闭行为，不与本次日志修复混合。

### 2026-06-13：准备新对话开发交接 Prompt

本次结果：

- 未修改业务代码；整理了供新 Codex 对话使用的开发交接 prompt。
- 交接内容要求先阅读 `AGENTS.md`、`PROGRESS.md` 和相关代码，再检查当前未提交改动，禁止随意 revert。
- 建议新对话先验证上一轮 LLM client、fake/cache/dry-run/replay 和运行日志改造，再选择最小、可验证的下一步继续开发。

测试结果：

- 本次只做交接整理和进度文档更新，未运行后端或前端测试。

下一步计划：

- 在新对话中完成工作区审查和后端全量测试，然后继续推进稳定性、日志隐私或调试体验改进。

### 2026-06-12：将 AGENTS.md 调整为中英混合规则文档

修改文件：

- 更新 `AGENTS.md`：保留中文项目语境说明，将硬性进度规则、开发约束和最终回复前 checklist 改为英文 `MUST / MUST NOT` 风格，方便 Codex 更稳定遵循。
- 更新 `PROGRESS.md`：记录本次文档规则调整。

测试结果：

- 本次只修改文档，未运行后端或前端测试。

发现的问题：

- 无新增问题。

下一步计划：

- 后续任务继续按 `AGENTS.md` 要求，在最终回复前更新 `PROGRESS.md` 并写明 `Progress updated: yes`。

### 2026-06-12：建立长期进度记录机制

修改文件：

- 更新 `.gitignore`：显式放行根目录 `AGENTS.md` 和 `PROGRESS.md`，避免被上层忽略规则吞掉。
- 新增 `AGENTS.md`：写入长期生效的协作规则、进度更新规则和任务完成前 checklist。
- 新增 `PROGRESS.md`：作为唯一根目录进度记录入口。
- 删除 `doc/internship_agent_progress.md`：旧进度内容已迁移为简洁版根目录记录，避免重复维护。

测试结果：

- 本次只修改文档，未运行后端或前端测试。

发现的问题：

- 旧 `doc/internship_agent_progress.md` 内容较长，且在默认 PowerShell 输出中可能出现编码乱码；已改为根目录简洁进度文档。

下一步计划：

- 后续每次任务结束前都更新本文件。
- 下一轮代码改动优先继续使用 fake/dry-run/replay 降低调试成本。

## 最近验证

- 后端全量测试最近通过：

```text
Ran 81 tests
OK
```

- 上述测试包含 fake/cache/dry-run/replay、日志隐私与并发写入、流式终态、API 契约、投递行动字段和旧数据兼容验证。
- 前端本轮已通过 `npm run build`，跟进日期状态已用固定日期脚本验证。

## 已知问题与风险

- FastAPI `on_event` 和当前 Starlette `TestClient` 依赖会输出弃用警告，后续应单独升级处理。
- 运行日志已不保存原始用户输入、完整 prompt 和工具输入，但 LLM 响应、搜索结果和最终报告可能回显用户信息，仍需作为敏感本地数据保护。
- 真实招聘信息更新较快，用户必须打开来源链接核验岗位、薪资、地点、截止日期和投递入口。
- 真实 LLM/search 链路可能触发 429 或网络波动；开发阶段优先使用 fake、dry-run、cache 和 replay。
- 仍不做自动投递、不登录招聘平台、不批量联系 HR、不绕过平台规则。

## 下一步

- 在后续功能或修复任务中持续补充 fake/cache/replay 覆盖。
- 需要真实链路验证时，先用 dry-run 检查 prompt 和任务数量，再切到 real 模式。
- 可在不引入自动任务的前提下，后续增加投递记录导出或阶段复盘视图。
