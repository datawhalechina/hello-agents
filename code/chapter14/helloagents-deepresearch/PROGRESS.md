# 找实习助手 Agent 开发进度

更新时间：2026-06-13

## 当前状态

- 项目已从 Hello-Agents 第十四章 deepresearch 改造为“找实习助手 Agent”。
- 后端核心接口保持兼容：`/research`、`/research/stream`、`/applications`。
- 前端支持结构化求职画像、岗位推荐清单、排序筛选、来源可信度、信息完整度、推荐优先级、待确认项、搜索质量诊断和本地投递状态管理。
- 最终行动报告已升级为 6 章结构：今天优先投递、推荐理由、简历修改清单、7 天投递计划、风险与待确认项、来源与搜索诊断。
- 最新一轮重点已完成：低成本、可测试、可回放 Agent 架构。

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
Ran 64 tests
OK
```

- 上述测试来自低成本、可测试、可回放 Agent 架构改造完成后的验证。
- 前端本轮未修改；最近一次涉及前端的改动已通过 `npm run build`。

## 已知问题与风险

- 测试过程中仍可见 hello_agents trace 文件相关 `ResourceWarning`，目前不影响测试通过。
- 真实招聘信息更新较快，用户必须打开来源链接核验岗位、薪资、地点、截止日期和投递入口。
- 真实 LLM/search 链路可能触发 429 或网络波动；开发阶段优先使用 fake、dry-run、cache 和 replay。
- 仍不做自动投递、不登录招聘平台、不批量联系 HR、不绕过平台规则。

## 下一步

- 在后续功能或修复任务中持续补充 fake/cache/replay 覆盖。
- 需要真实链路验证时，先用 dry-run 检查 prompt 和任务数量，再切到 real 模式。
- 后续可考虑把运行日志中的敏感用户输入做脱敏处理。
