# 找实习助手 Agent 改造计划

## 1. 改造目标

把当前第十四章的“深度研究助手”改造成“半自动找实习助手”。

原项目主线是：

```text
研究主题 -> 任务规划 -> 搜索资料 -> 任务总结 -> 最终报告
```

找实习助手可以复用这条主线：

```text
求职目标 -> 求职任务规划 -> 搜索岗位/渠道/JD -> 岗位分析 -> 求职行动报告
```

第一版不要做自动登录、自动投递、自动填写表单。先做一个能帮用户找岗位、分析 JD、判断匹配度、生成投递建议的半自动助手。

## 2. MVP 范围

### 输入

- 求职方向：后端、前端、算法、AI 应用、数据分析等。
- 城市偏好：上海、杭州、北京、远程等。
- 技术栈：Java、Python、Vue、FastAPI、LLM、RAG 等。
- 简历文本或个人背景。
- 到岗时间、实习周期。
- 公司类型偏好：大厂、创业公司、AI 公司、远程团队等。

第一版可以先继续使用原来的 `topic` 字段，让用户用自然语言输入完整求职目标，例如：

```text
我想找 2026 暑期 Java 后端实习，城市上海/杭州，会 Spring Boot、MySQL、Redis，有一个 RAG 项目。
```

等后端跑通后，再把前端输入改成结构化表单。

### 输出

- 候选实习岗位列表。
- 每个岗位的 JD 摘要。
- 技能匹配度与匹配理由。
- 推荐投递优先级。
- 简历修改建议。
- 最终找实习行动报告。

## 3. 原项目模块映射

| 当前深度研究项目 | 找实习助手中的角色 |
| --- | --- |
| `DeepResearchAgent` | `InternshipAgent`，整体流程调度器 |
| `PlanningService` | 求职任务规划服务 |
| `SearchService` | 岗位/公司/投递渠道搜索服务 |
| `SummarizationService` | 岗位分析与 JD 总结服务 |
| `ReportingService` | 求职行动报告生成服务 |
| `TodoItem` | 搜索任务或求职任务 |
| `SummaryState` | 找实习过程状态 |

第一阶段建议先保留现有文件名，只改内部 prompt 和逻辑。等功能稳定后，再考虑系统性重命名。

## 4. 阶段一：改 Prompt，先让输出方向变成求职

优先修改：

```text
backend/src/prompts.py
```

把三个角色从通用研究场景改成求职场景：

```text
研究规划专家 -> 求职规划专家
任务总结专家 -> 岗位分析专家
报告撰写专家 -> 求职行动报告专家
```

### Planner Prompt 目标

输入求职目标后，稳定输出 4 个左右的求职任务：

```json
{
  "tasks": [
    {
      "title": "岗位搜索",
      "intent": "搜索符合目标方向和城市的实习岗位",
      "query": "2026 暑期实习 Java 后端 上海 杭州 招聘"
    },
    {
      "title": "JD要求分析",
      "intent": "总结目标岗位常见技能要求",
      "query": "Java 后端 实习 JD Spring Boot MySQL Redis"
    },
    {
      "title": "公司渠道梳理",
      "intent": "查找企业官网、校招、内推和实习发布渠道",
      "query": "Java 后端 实习 内推 校招 官网"
    },
    {
      "title": "简历优化建议",
      "intent": "根据岗位要求分析简历需要突出哪些内容",
      "query": "Java 后端实习 简历 项目经历 优化"
    }
  ]
}
```

### Summarizer Prompt 目标

任务总结不再写泛泛的研究总结，而是围绕：

- 岗位信息。
- 公司和渠道。
- JD 技能要求。
- 用户背景与岗位要求的差距。
- 可执行的准备建议。

### Reporter Prompt 目标

最终报告结构改成：

```text
# 找实习行动报告

## 1. 求职目标概览
方向、城市、技术栈、约束条件。

## 2. 推荐岗位清单
按优先级列出岗位和来源。

## 3. 岗位匹配分析
每个岗位的匹配分、优势、短板。

## 4. 简历修改建议
针对高优先级岗位给出修改方向。

## 5. 投递计划
今天投哪些、这周投哪些、需要准备什么。

## 6. 风险提醒
岗位过期、信息不完整、技术短板、城市不匹配等。
```

## 5. 阶段二：改 Planner

重点文件：

```text
backend/src/services/planner.py
```

当前 `planner.py` 的职责是：

```text
研究主题 -> TodoItem 列表
```

改造后职责是：

```text
求职目标 -> 求职任务列表
```

优先要保证：

- 任务数量稳定在 3-5 个。
- 每个任务都有明确的 `title`、`intent`、`query`。
- `query` 适合直接用于搜索实习岗位或求职信息。
- 如果模型输出解析失败，fallback 也不要只给一个“基础背景梳理”，而是给 4 个默认求职任务。

建议 fallback 改成：

```text
1. 岗位搜索
2. JD要求分析
3. 投递渠道梳理
4. 简历优化建议
```

## 6. 阶段三：改搜索层

重点文件：

```text
backend/src/services/search.py
backend/src/search_tool.py
```

第一版继续使用 DuckDuckGo / Tavily，不要急着爬 Boss、实习僧、牛客。

推荐搜索来源：

- 公司官网招聘页。
- 企业校招官网。
- 牛客公开讨论。
- 学校就业网。
- GitHub 招聘帖。
- 公众号招聘信息。
- 招聘平台公开页。

推荐查询关键词：

```text
2026 暑期实习 Java 后端 上海 杭州 招聘
site:jobs.bytedance.com 实习 后端
site:campus.alibaba.com Java 实习
AI 应用开发 实习生 LLM RAG
后端开发 实习 JD Spring Boot MySQL Redis
```

搜索结果至少保留：

- 标题。
- 链接。
- 摘要。
- 来源平台。
- 抓取时间。

找实习信息更新很快，必须保留来源链接和时间。

## 7. 阶段四：新增岗位结构化模型

重点文件：

```text
backend/src/models.py
```

可以新增：

```python
@dataclass
class JobItem:
    company: str
    title: str
    location: str
    source_url: str
    requirements: list[str]
    responsibilities: list[str]
    tech_stack: list[str]
    duration: str | None = None
    deadline: str | None = None
    match_score: int | None = None
    match_reason: str | None = None
```

第一版可以先不完全落地 `JobItem`，先让总结和报告用 Markdown 输出岗位信息。等输出稳定后，再结构化。

## 8. 阶段五：增加匹配评分

可以新增：

```text
backend/src/services/matcher.py
```

第一版用 LLM 做规则化评分，不必马上写复杂算法。

建议评分维度：

| 维度 | 分值 |
| --- | --- |
| 技术栈匹配 | 30 |
| 项目经历匹配 | 25 |
| 城市与到岗时间匹配 | 20 |
| 学历/年级要求匹配 | 10 |
| 岗位成长价值 | 10 |
| 投递难度 | 5 |

输出示例：

```json
{
  "match_score": 82,
  "match_reason": "岗位要求 Java、Spring Boot、MySQL，与用户技能较匹配；如果简历中补充 Redis 和高并发项目会更有竞争力。",
  "resume_advice": [
    "突出后端项目中的接口设计和数据库设计",
    "补充 Spring Boot 项目部署经验",
    "把 RAG 项目包装成 AI 应用开发亮点"
  ]
}
```

## 9. 阶段六：改报告生成

重点文件：

```text
backend/src/services/reporter.py
```

把研究报告改成求职行动报告。

报告应该回答这些问题：

- 现在有哪些值得投的岗位？
- 哪些岗位最匹配？
- 为什么匹配？
- 简历应该怎么改？
- 接下来 1-7 天应该怎么投？
- 有哪些风险和不确定性？

报告不应该只总结搜索结果，而要给行动建议。

## 10. 阶段七：改前端文案和展示

重点文件：

```text
frontend/src/App.vue
frontend/src/services/api.ts
```

第一步只改文案：

| 当前文案 | 改成 |
| --- | --- |
| 深度研究助手 | 找实习助手 |
| 研究主题 | 求职目标 |
| 开始新研究 | 开始找实习 |
| 任务总结 | 岗位分析 |
| 最终报告 | 求职行动报告 |

第二步再改 UI：

- 左侧输入求职目标。
- 中间展示搜索任务进度。
- 右侧展示岗位卡片。
- 底部展示行动报告。

第一版可以继续复用原 UI，不要一开始重做界面。

## 11. 阶段八：增加投递状态管理

等岗位列表稳定后，再增加状态管理。

状态建议：

```text
待投递
已投递
笔试
面试
拒绝
Offer
放弃
```

第一版可以用本地 JSON 文件：

```text
data/jobs.json
data/applications.json
```

后续再换 SQLite。

## 12. 推荐开发顺序

```text
1. 改 prompts.py，让输出方向变成求职。
2. 改 planner.py，稳定生成 3-5 个求职任务。
3. 改 reporter.py，生成求职行动报告。
4. 改 summarizer.py，让任务总结偏向岗位、JD、技能和投递建议。
5. 改 models.py，增加 JobItem / MatchResult。
6. 新增 matcher.py，做岗位匹配评分。
7. 改 main.py，支持结构化求职输入。
8. 改前端文案。
9. 改前端展示岗位卡片。
10. 增加本地岗位状态持久化。
```

最小可用版本只需要完成前 4 步。

## 13. 第一版验收标准

输入一句求职目标后，系统应能做到：

- 生成 3-5 个求职任务。
- 每个任务能搜索到相关岗位、渠道或 JD 信息。
- 任务总结围绕岗位、技能、投递渠道和简历建议。
- 最终报告能给出明确投递建议。
- 报告里有来源链接。
- 用户看完报告后知道下一步该投哪些岗位、补哪些简历内容。

## 14. 风险与注意事项

- 招聘信息更新快，必须保留来源链接和抓取时间。
- 招聘平台可能有登录、反爬和访问限制，第一版不要强依赖爬虫。
- JD 信息可能不完整，未知字段要标记“不确定”。
- 自动投递风险高，应保留人工确认。
- 简历包含隐私信息，日志和笔记中要注意脱敏。
- 匹配评分有主观性，必须给出评分理由。

## 15. 当前最建议的第一步

先改：

```text
backend/src/prompts.py
```

原因：

- 改动小。
- 风险低。
- 能最快看到项目从“深度研究”转向“找实习”的效果。
- 不需要先重构数据结构和前端。

等 prompt 输出方向正确后，再逐步改 `planner.py`、`summarizer.py` 和 `reporter.py`。
