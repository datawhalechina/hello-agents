# Codebase Onboarding Agent：带对照评测的代码库问答示例

面向“这个功能在哪里实现、调用关系怎么走”的 Python 代码库问题，提供源码索引、混合检索、可选 ReAct 问答演示，以及一套可自动核对的证据检索评测。

这是一个课程项目的教学实现。重点是让检索改动能够单独测量，并保留没有通过既定门槛的结果。

## 实现范围

| 部分 | 当前实现 | 验证范围 |
|---|---|---|
| 索引 | Python AST 类、函数、方法与模块 docstring；内存符号表和向量矩阵 | 固定语料的源码坐标 |
| 检索 | BM25 + dense + 加权 RRF；可选一跳调用名扩展、查询改写 | 六臂的 top-5 证据排序 |
| 问答演示 | HelloAgents ReAct + 搜索、大纲、读符号、查潜在调用方四个只读工具 | 可选 LLM 路径，与 Part 4 分开 |
| 引用校验 | 检查 ID 存在且在本轮工具结果中出现；输出固定 commit 源码链接 | 引用 ID 有效率，不是断言的语义正确率 |

索引不持久化，也没有多用户服务、权限系统或持久化审计日志。原课程项目的 FastAPI、RabbitMQ、PostgreSQL/pgvector 服务未迁入本例。
没有与通用 Coding Agent 做统一条件的端到端比较；帮助新人 onboarding 仍是应用假设。

## 快速开始

使用 Python 3.12，在本项目目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest -v
python run_evaluation.py --check-reference
```

也可运行 `jupyter lab` 打开 `main.ipynb`，按顺序执行。`run_evaluation.py` 执行同一份 notebook 代码，始终跳过 LLM 演示。
首次运行需要联网下载语料与 embedding 模型，耗时取决于网络与 CPU。后续可用本地缓存；不需要 API Key。

模型固定为 `flax-sentence-embeddings/st-codesearch-distilroberta-base` 的 revision
`23d22ea4191fc9d006833d3b62694949f1ffebd1`，计算设备为 CPU。直接依赖固定于 `requirements.txt`，参考环境的完整包版本在 `reference/environment.txt`。
跨硬件或数值库仍可能产生排序差异。检查命令要求指标误差不超过 `1e-6`、排序与判定一致；失败时应对照环境与 provenance 排查，不能直接覆盖参考答案。

### 可选的 Agent 演示

```bash
cp .env.example .env
# 填写 LLM_API_KEY、LLM_MODEL_ID、LLM_BASE_URL，并设置 RUN_AGENT_DEMO=1
jupyter lab
```

在 notebook 中执行 Part 3。`agent_demo.py` 使用 HelloAgents 0.2.7 的 `custom_prompt`，确保引用规则进入实际 ReAct 提示词。
框架循环最多 14 步，包括结束动作；这不代表 token 或延迟上限。

```python
OBSERVED_IDS.clear()
answer = agent.run("How is basic auth attached to a prepared request?")
checked = verify_citations(str(answer), OBSERVED_IDS)
print(checked["answer"])
print(checked["citation_id_validity"])
for cid in checked["verified"]:
    print(source_url(BY_ID[cid]))
```

引用 ID 按过滤前不同 ID 的集合计分，重复引用不增加权重，零引用记 0。不存在或本轮未出现的 ID 会被删除。
**真实 ID 也可能支持不了对应断言；删除引用标记不会修正正文。** 本例没有 LLM Judge 或人工答案正确性评分。

### 一次真实问答示例

以下摘自 2026-09-09 的 `gpt-5.4-mini` 实跑记录；无需配置 API 即可阅读。[完整记录](./reference/agent_smoke.json)保留原始回答与核查说明。

**问题**：重定向到不同主机时，Session 如何决定是否移除 `Authorization` 请求头？

**执行过程**：`search_code → Finish`，共 2 次模型调用，答案引用了以下两个源码位置：

- [sessions.py::SessionRedirectMixin.should_strip_auth](https://github.com/psf/requests/blob/414f0513c33883adf6f2b46901d4f0b38a455851/src/requests/sessions.py#L154-L184)
- [sessions.py::SessionRedirectMixin.resolve_redirects](https://github.com/psf/requests/blob/414f0513c33883adf6f2b46901d4f0b38a455851/src/requests/sessions.py#L186-L307)

**回答原文**：

> When a redirect points to a different hostname, `SessionRedirectMixin.should_strip_auth(old_url, new_url)` returns `True`, which means the `Authorization` header should be removed; it compares `urlparse(old_url).hostname` and `urlparse(new_url).hostname` and strips auth whenever they differ. There is one special case: it does not strip auth for an `http` -> `https` redirect when the old URL uses port 80 or no port and the new URL uses port 443 or no port, to preserve backward compatibility. During redirect processing, `resolve_redirects` is the code path that follows redirects and uses this decision. [sessions.py#7][sessions.py#8]

**核查结果**：两个引用 ID 均存在且在本轮工具结果中出现，引用 ID 有效率为 1.0。回答正确指出不同主机会移除认证头，但随后提到 HTTP→HTTPS 的例外时，漏写了“同一主机”这一前提，容易让人误以为跨主机也存在该例外。因此这次记录证明链路能够运行，不能当作完全正确的答案。

## 评测协议与参考结果

语料固定在 `psf/requests@414f0513c33883adf6f2b46901d4f0b38a455851`，仅索引 `src/requests`：19 个文件、320 个 chunk。
题集 10 道，L1/L2/L3 分别为 2/5/3 道；所有 gold 启动时必须恰好解析到一个 chunk。

`strict-anchor-v2` 精确匹配文件、符号、起始行；类块不替方法得分，同名方法不互相替代。重复结果不重复得分，gold 顺序不影响评分。
MRR 在前五条截断，记为 MRR@5。composite 是 Recall@5、MRR@5、nDCG@5 的等权均值。

| 臂 | 检索路径 |
|---|---|
| B2 | dense-only |
| B3 | BM25 + dense + RRF（K=60，dense:sparse=2:1） |
| B4 | B3 + 一跳调用名扩展与显式符号跳转，按来源/相关度排序后再次融合 |
| B3Q | 扩展查询给稀疏、稠密两路 |
| B3Qs | 只给稀疏路扩展查询 |
| B4Qs | B3Qs 的种子 + 与 B4 相同的扩展函数，显式跳转仍用原问题 |

前三臂进入主判据：B4 在 L2、L3 上都要比 B2、B3 高至少 0.05，四项全过才为 supported。
0.05 是工程门槛，不是统计显著性阈值。后三臂用于诊断，不改变主判定。

**Part 4 没有运行 ReAct，也没有生成或核验最终答案。它测的是证据检索与扩展。**

| 臂 | Recall@5 | MRR@5 | nDCG@5 | composite |
|---|---|---|---|---|
| B2 | 0.542 | 0.633 | 0.477 | 0.551 |
| B3 | 0.612 | 0.717 | 0.555 | 0.628 |
| B4 | 0.637 | 0.750 | 0.577 | 0.655 |
| B3Q | 0.662 | 0.662 | 0.546 | 0.623 |
| B3Qs | 0.662 | 0.725 | 0.571 | 0.653 |
| B4Qs | 0.587 | 0.750 | 0.537 | 0.625 |

| 层级 | 题数 | B2 | B3 | B4 | B4−B2 | B4−B3 |
|---|---|---|---|---|---|---|
| L2 | 5 | 0.630 | 0.659 | 0.630 | -0.000 | -0.030 |
| L3 | 3 | 0.345 | 0.424 | 0.563 | 0.217 | 0.139 |

**四项通过 2/4，判定 `unsupported`。** 表格保留三位小数，判定使用未舍入值。

| 层级 | 两路改写−B3 | 仅稀疏改写−B3 | 扩展−B3 | 两者组合−B3 |
|---|---|---|---|---|
| L2 | 0.034 | 0.087 | -0.030 | -0.074 |
| L3 | -0.012 | -0.012 | 0.139 | 0.209 |

### 如何解释

- L3 上 B4−B3 为 +0.139，表示这套扩展策略在三道 L3 题上的增益；B4−B2 的 +0.217 同时包含混合检索收益，不能全部归因给取证扩展。
- L2 上 B4−B3 为 −0.030。整体均值不能说明所有层级都受益，应查看 `reference/h1_report.json` 的逐题证据。
- 只改稀疏路的整体分数高于同时改两路，但这是当前词表与模型配置的结果，不能推广为“稠密检索不该改写”。句向量语义偏移仅是可能解释。
- B4Qs 在 L3 上优于单独组件，L2 上却更差，因此不能笼统地说“两个增强不叠加”。

同题集上的查询新增词数上限（`max_expand`）扫描：4 / 8 / 12 / 20 对应 composite 0.6721 / 0.6961 / 0.6526 / 0.6562。
默认仍为 12，扫描只是敏感性分析，没有把最高分当作未见数据收益。这里调整的是查询新增词数；B4 的一跳检索操作预算固定为 14，两者分别控制查询改写和证据扩展。

### 修订与数据边界

v2 修复方法 chunk 的缩进解析、同名符号误匹配和依赖 gold 顺序的 nDCG；统一 B4/B4Qs 扩展逻辑、稳定同分排序，并用未舍入数值判定。
旧版的 0.582 / 0.686 / 0.693 及 1/4 判定已废弃。新旧分数属于不同协议，不能用差值宣称能力提升。

本题集已经用于开发、配置选择和本次修复，不是独立 holdout，也不能把本轮修复称为新的独立预注册实验。
本例演示固定规则后运行与报告的流程；真正的确认性评测需提前冻结实现和判据，并另取未用于调试的题目。

## 文件与验证

- `main.ipynb`：四部分教学流程。
- `evaluation.py`：缩进解析、精确锚点指标、引用 ID 校验和全精度判定。
- `agent_demo.py`：可选 HelloAgents 适配。
- `test_evaluation.py`：评分边界与脚本化 LLM 的四工具集成测试，不调用真实模型。
- `reference/h1_report.json`：逐题排名、聚合、判定、模型 revision、题集与代码哈希；本地重跑写入 `results/`。

已通过 10 项测试和六臂本地执行。测试包含脚本化 LLM 的四工具往返，以及 GPT-5/普通模型的实际 HTTP JSON 参数序列化；测试不调用真实 API。

2026-09-09 使用 `gpt-5.4-mini` 实跑一条跨主机重定向问题：2 次模型调用（search_code → Finish）、2 个有效引用，记录见 `reference/agent_smoke.json`。
链路完成，但答案漏写了 HTTP→HTTPS 保留认证仅适用于同主机的限定，不能当作完全正确的回答或质量基准。
这也说明引用 ID 有效率为 1.0 不等于语义 groundedness 为 1.0。

实跑修复了 `.env` 显式路径、GPT-5 的 `max_completion_tokens` 参数，以及把完整答案写入单行 Finish 的提示词。适配层对 GPT-5/o 系列省略旧 `max_tokens` 和默认 temperature，其他模型使用 `max_tokens=4096`。

## 已知边界

- 仅 Python、单一仓库、10 道题；不能外推到其他语言、大型仓库或真实用户效果。
- 4 道 `graph_reverse` 题由已有调用关系反推，可能漏掉解析器看不到的链路，来源与难度混淆。
- 调用解析只匹配名字，不推断接收者类型；同名定义均为候选，可能误报。
- 精确 gold 不能覆盖所有合理证据；类块即使包含目标方法也不得分，这是刻意选择的严格口径。
- 步数上限不限制单步候选数量或读取 token；没有完整服务安全与权限设计。

## 与 Extra14 的关系

配套投稿 `Extra-Chapter/Extra14-垂直场景Agent的自建评测.md` 解释方法。
两份 PR 独立提交，不要求另一份先合并；本目录已包含运行所需文件。
章节中的 33 题、495 次执行、三轮重复与 B3.5 消融属于原课程项目的作者报告数据，不是本 notebook 的复现结果。

## 作者与许可证

作者：[@Odiethebest](https://github.com/Odiethebest)。感谢 Datawhale 与 Hello-Agents 社区。
许可证：CC BY-NC-SA 4.0。
