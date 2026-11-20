> 状态：D3 已完成（2026-10-24 收口），D4.2 判据修订后 95.0% 待定口径 | 更新：2026-10-24

# design — NTU 选课助手

> 正本只写拍板后的结论；过程稿在 `02-提示词设计.md` 等编号文档。

## 系统架构

RAG 开卷模式（不微调）：官方数据 → 课程卡片 → 混合检索 → Agent 引用作答。三层：

- **数据层**：原始 jsonl（WIS 目录 / CCA 官网页 / WIS 课表）→ 统一课程卡片 `course_cards.jsonl` → `RAGStore`（SQLite，版本化原文 + BM25）+ 向量索引缓存
- **检索层**：`HybridSearch` = BM25（RAGStore）⊕ 余弦（VectorSearchBackend，智谱 embedding OpenAI 兼容）→ RRF 融合 → `RAGTool` 暴露给 Agent
- **Agent 层**：D2 单 ReActAgent（`src/agent.py`）→ **D3 三 Agent 已落地**（`src/team.py`，代码编排 + Reflection ≤3 轮，详见下节）

选型理由：RAG 天然支持课程数据年度更新（换 version 重导入即可）、RetrievalResult 自带 source 溯源，符合反幻觉与可验证要求。

## Agent 划分与职责（D3 已落地，2026-10-24 收口）

| Agent | 职责 | 落地 |
|---|---|---|
| D2 course_qa（单 Agent，已验收） | ReAct 循环调 rag_search 作答；三板斧 + ExactCodeGuard 双保险 | `src/agent.py` |
| Planner（规划） | 计划生成（`generate_plan` function calling，≤5 步）+ **身份理解 `assumed_identity`**（模型结合"用户原话 + 对话历史 + 库覆盖事实"自己判断，输出 level/programme/confidence）；代码只做事后校验（库外项目不允许自称 certain、含课码时忽略身份）与"需要身份但层次未知 → 反问" | `src/team.py` |
| Retrieval（检索） | ReActAgent 按计划执行 rag_search（含 level 过滤）+ 4 个校验工具，产出初稿（只重组工具返回）→ **编排层 `_polish_draft` 单轮精炼**（溯源声明 + 组合逻辑总述；A/B 实验证实 ReAct 循环内写不出总述属信息流压制非模型上限，故精炼放在循环外） | `src/team.py` |
| Reviewer（审查） | Reflection ≤3 轮四项审查；**双轨判定**：代码机械审查（来源覆盖/学位规则引用/身份一致性）+ LLM 审查（查不到明说等语义项），任一 FAIL 打回（引用草稿原句）；轮次耗尽放行但附审查标注 | `src/team.py` `mechanical_review` |

**协作机制（框架源码核实结论）**：hello-agents 1.0.1 无 AgentTeam；真实多 Agent 协作 = Python 编排层组合多个 Agent 实例、显式拼 prompt 传递上下文（框架 PlanSolveAgent/ReflectionAgent 同款模式）。三 Agent 间无消息总线，Planner 计划/Retrieval 草稿/Reviewer 意见均由 `CourseAdvisorTeam` 编排，全程可测试。

**D3 代码护栏**（"代码管必须"哲学第三/四次实证）：
- **出路 1 重构（2026-10-24，用户拍板）**：删除所有"改写型"护栏（挂起态窄解析 `resolve_reply`、`_normalize_claim` 身份声明改写、计划补 level），改为"原话 + 完整对话历史透传，模型自己理解身份"。保留的护栏只做**过滤**：①需要身份但层次未知 → 反问；②库外项目不允许自称 certain（`_programme_known` 事后校验）；③含课码的属性查询忽略身份理解；④终审验真（来源覆盖 / 来源真实性 URL 白名单 / 学位规则引用 / 越权校验 / 占位符残留）
- 计划清洗 `_sanitize_steps`：query 含课程码的 search 步 level 置空（防属性查询被误过滤成"未查到"假阴性——D2 基线 8 回归中实证的退化）
- 计划补全 `_augment_steps`：用户点名课码未被计划覆盖时自动前置无过滤检索
- 精炼护栏 `_polish_draft`：初稿在干净单轮上下文精炼（总述为唯一创作任务）；推荐类总述特征词缺失自动重试 1 次（`_has_synthesis`）
- 机械审查 `mechanical_review`：纯 LLM 审查对坏草稿误判 PASS 的直接对策

## 校验工具（D3 落地，requirements Must 第 5 条）

`src/validators.py` `DegreeAuditTool`（expandable，注册后展开 4 子工具），学位规则以 decisions.md 2026-10-22 拍板的 CCA Option1/Option2 为准（来源 URL 随结论输出）：

| 工具 | 检查 | 数据边界 |
|---|---|---|
| check_schedule_conflict | 课程对时段重叠（聚合到课程对级，平行班只报组合数） | 仅课表库内课程（CSC 本科 2026 Sem1）；研究生课表官方不公开 → 如实报"无课表数据" |
| check_specialized_electives | 专选门数 ≥4 | 卡片 category 字段 |
| check_au_limit | Option1 通选 ≤18AU/专选 ≥12AU；Option2 通选 ≤12AU | 卡片 au 字段（EE6111 无 AU 值 → 明说未计入） |
| check_prerequisites | 先修是否满足/互斥同选/限修提示（转述卡片字段不推断） | 卡片 prerequisite/mutually_exclusive/not_available_to 字段 |

## MCP 接入（D3 Should 项已演示）

`scripts/mcp_server.py`（MCPServer，stdio）暴露 cca_degree_rules / cca_specialized_elective_list 两工具；`scripts/mcp_demo.py` 经框架 `MCPConnection.stdio` 挂载 → `register_tools(registry)` → `aexecute_tool` 调用，链路跑通。主流程 team.py 默认不挂（演示性质，避免自测依赖子进程）。**依赖版本线：mcp 2.x**（框架 mcp.py 的 `from mcp import Client` 对应 2.x；server 端 FastMCP 在 2.x 改名 MCPServer）。

## 提示词设计（已落地于 `02-提示词设计.md` + `src/team.py`，D3 v1）

- D3 三 Agent 五段式正稿与毛坯→正稿迭代记录见 02-提示词设计.md「D3 三 Agent 提示词正稿」
- D2 单 Agent v12 留档于 02 + `src/agent.py`（反幻觉三板斧 + ExactCodeGuard 双保险继续在 D3 生效）
- 选课建议必须走学位规则校验工具并引用其返回（机械审查强制）

## 数据与检索

- 三数据通道（细节见 `03-数据源侦察.md`）：WIS 本科目录 POST、CCA 官网静态页、WIS 课表 POST（完整浏览器载荷）
- **课程卡片**：单课整卡不切片（chunk_size=4000 保证 1 卡 = 1 chunk）；`document_id = course_code`，`version = 数据日期.内容摘要8位`（内容变 → 版本自动变，框架同版本原文不可变约束下可安全迭代）；字段 course_code/title/au/level/programme/category/semesters/prerequisite/mutually_exclusive/description/source_url
- **Embedding**：智谱 embedding-3（OpenAI 兼容，2048 维）。金标 15 条实测拍板（2026-10-22）：hybrid(e3) recall@5=1.00/MRR@5=0.92，全面优于 embedding-2（0.81/0.78）、单路向量 e3（0.83/0.80）、纯 BM25（0.53/0.50）
- **检索**：BM25 ⊕ 向量余弦 → RRF（框架 `HybridSearch`，rrf_k=60）；BM25 分词支持中文单字/双字；卡片标题行重复课程码（tf 提权）保证课程码查询命中
- **评估**：金标查询集（中英混合、预期课程码分级标注：10=必须命中/5=次级相关）→ 框架 `evaluate_retrieval`（recall@5 / MRR@5 / nDCG@5）；评估脚本 `scripts/eval_retrieval.py`，金标 `eval/golden_queries.json`
- **课表数据不进卡片**：冲突检测工具直接查 schedule jsonl，避免卡片膨胀

## D4 评估结论（2026-10-24，D4.1/D4.2）

- **D4 基线 12/20 = 60.0% → D4.1（v1 判据）17/20 = 85.0% → D4.2（v2 判据修订）19/20 = 95.0%**；D4.2 单轮耗时中位 33.41s / P90 105.95s / 整案最大 174.34s（Q19）；检索金标复核 hybrid(e3) recall@5=1.000 / MRR@5=0.878（阈值 0.90/0.85，达标）。
- 基线 7 条系统实质失败已全部修复：来源兜底（Q11/Q12 编造 URL）、空字段防编造（Q16 空描述、Q04 相近课先修嫁接）、身份 grounding（Q14 “机械工程”被模型映射成 CCA）、`programme_code` 短键边界（Q08 “cs”误中 Robotics→CSC）、`has_code` 护栏过宽（Q10 audit 类被清空身份）。定向复跑 7/7 PASS。
- D4.2 用户允许修订列表类判据（Q06/Q07/Q08 去固定锚点、保留结构判据：≥3 门/层次一致/项目归属/来源合法）；v1 保留在 `eval/e2e_queries.json`，v2 在 `eval/e2e_queries_v2.json`。**v1 85% 是预注册保守口径，v2 95% 不可直接比较。**
- D4.2 唯一 FAIL Q16（单次遗漏“简介未收录”），已加 description-intent 护栏，定向复跑 41.78s PASS，未再重跑全量；D4.3 候选。
- 架构含义：出路 1 的身份链路（Q17-Q20 4/4）有效，但“模型理解身份”必须配代码 grounding 校验；“含课码忽略身份”应收窄到单课属性查询；来源真实性、空字段、字段完整性不能只靠 Reviewer LLM。
- 详见 `04-评估报告.md`；代码↔教程章节映射见 `05-架构说明.md`。
