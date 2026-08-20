# MoneyMirrorAgent —— 面向年轻人的游戏化个人财务行为智能体

> 让账单成为一面镜子：先用可靠工具读懂真实消费，再由多智能体像游戏 NPC 一样一步步陪用户制定行动，**完成交流后才生成专属 Markdown 月报**。

## 📝 项目背景

MoneyMirrorAgent 面向年轻人的日常账单场景，将深夜外卖、周末体验消费、低额高频消费、长期订阅和储蓄目标转化为可执行的下一步。项目以 CSV 账单为输入：Python 工具负责金额与统计事实，Hello-Agents 驱动的大模型负责理解、引导、追问、人格文案、Quest 动态编排、Reflection 与最终报告。


## ✨ 核心能力

- **账单导入与标准化**：`CSVImportTool` 支持常见中英文列名、UTF-8/GB18030、正负金额、独立收入/支出列和常见日期格式。
- **记忆优先分类**：`SQLite Memory → 规则 → ReActAgent`。用户手动纠正商户分类后，同商户下次优先命中 Memory。
- **确定性消费分析**：收入、支出、结余、储蓄率、类别占比、日/周/月趋势、深夜/周末/工资到账后/高频小额模式均由 Python 计算。
- **异常与订阅检测**：使用 IQR、Z-score、中位数比例和周期性规则定位行为信号；订阅分析结合跨月稳定扣费、订阅分类与会员/续费/月卡语义等证据，大模型基于这些信号生成解释。
- **人格、目标、预算与 RPG Quest**：消费人格采用“特征向量 → JSON 配置评分 → 证据校验 → LLM 年轻化表达”；目标、预算和带 EXP 的任务均基于实际指标。
- **长期 Memory**：保存目标、分类修正、预算、Quest、成就、快照、Reflection 与最近引导对话。
- **分步 AI 引导**：用户输入会立即交给大模型并以流式方式返回；每轮围绕“观察 → 小建议 → 一个追问”展开。
- **最终 Markdown 报告**：用户结束引导后，LLM 综合已验证账单事实、Memory 和对话生成专属月报。

## 🤖 Agent 架构

```text
CSV bill
  ↓
MoneyMirrorCoordinator
  ├── TransactionAgent   ReActAgent：Memory/规则/低置信 LLM 分类
  ├── PatternAgent       PlanSolveAgent：规划 → Python 统计/异常/订阅工具
  ├── PersonaAgent       特征向量 → 配置化评分 → 证据校验 → LLM 表达
  ├── GoalAgent          PlanSolveAgent：目标投影 → 行动路径
  ├── QuestAgent         真实信号 → LLM 编排 → 可验证 RPG Quest
  ├── ReflectionAgent    计划 → 实际 → 偏差 → 下一周期策略
  └── ConversationAgent  用户输入 → 流式引导 → 最终 Markdown 报告
```

### 消费人格判定

PersonaAgent 从账单提取深夜、周末、高频小额、弹性消费、餐饮、订阅、学习连续性、储蓄、发薪日节奏、规划与冲动特征，形成标准化特征向量；随后读取 `src/config/personas.json` 中的原型权重、最低分与证据门槛，计算评分并输出通过校验的 Top-K 原型。当前原型覆盖夜行消费、周末体验与社交、高频小额、日常餐饮、数字订阅、学习成长、发薪日节奏、弹性体验、储蓄冲刺、稳健规划与清醒消费等不同消费风格。LLM 基于原型、评分和证据生成年轻化叙述。

### Hello-Agents 技术使用

- 使用官方 `ToolRegistry`、`ReActAgent`、`PlanSolveAgent`、`ReflectionAgent`、`SimpleAgent` 与 `ContextBuilder`。
- 八个确定性工具以 JSON adapter 注册到 `ToolRegistry`：`CSVImportTool`、`TransactionCategoryTool`、`StatisticsTool`、`AnomalyDetectionTool`、`BudgetCalculatorTool`、`GoalProjectionTool`、`SubscriptionDetectorTool`、`QuestProgressTool`。
- 使用 Context Engineering 分开传递 **Verified tool output** 与 **Long-term Memory**：已验证工具结果作为数值事实上下文，长期 Memory 作为个性化上下文。
- 低置信分类、个性化解释、Quest 动态编排、Reflection、分步对话与 Markdown 报告都通过 Hello-Agents 调用。


## 🧰 技术栈

- Python 3.10+
- `hello-agents>=1.0.0`
- OpenAI-compatible LLM
- SQLite（本地长期 Memory）
- 终端 CLI（流式 AI 财务教练与任务面板）
- Python 标准库（CSV、统计、日期处理）

## 📁 项目结构

```text
CoralGarden52-MoneyMirrorAgent/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                          # CLI：完整分析 / 分步对话 / LLM 月报
├── data/
│   ├── sample_01.csv                # 内置虚构账单
│   └── sample_02.csv 至 sample_05.csv
├── docs/
│   └── MONEY_MIRROR_EXEC_PLAN.md
├── outputs/                         # 本地报告、SQLite
├── src/
│   ├── agents/                      # 7 个 Agent 与强制 LLM runtime
│   ├── config/
│   │   └── personas.json            # 可配置人格原型、权重与证据门槛
│   ├── tools/                       # 8 个确定性工具
│   ├── memory/
│   │   └── sqlite_memory.py
│   └── models.py
└── tests/
```

## 🚀 安装与配置

```bash
cd Co-creation-projects/CoralGarden52-MoneyMirrorAgent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```


## ▶️ 运行方式

通过 `--csv` 指定需要分析的账单路径。`data/sample_01.csv` 至 `data/sample_05.csv` 提供可直接运行的虚构账单文件。

### 1. 完整账单分析

```bash
python main.py --csv data/sample_01.csv --reset
```

执行顺序为：导入 → 多 Agent 分析 → 规则发现信号 → LLM Quest 编排 → Python 强校验 → LLM 人格/Reflection/Markdown 月报。输出写入：

```text
outputs/sample_01_money_mirror_report.json  # 已验证事实快照
outputs/sample_01_money_mirror_report.md    # 由 LLM 生成的月度报告
outputs/moneymirror.db                       # SQLite Memory
```

输出报告会使用输入 CSV 的文件名作为前缀，便于区分不同账单数据。例如输入 `data/sample_01.csv` 时，报告文件为 `sample_01_money_mirror_report.json` 和 `sample_01_money_mirror_report.md`。

分析自己的账单时，替换为实际 CSV 路径；可用 `--month` 限定分析月份：

```bash
python main.py --csv /path/to/bill.csv --month 2026-08 --reset
```

### 2. 财务目标与分类修正

可重复传入 `--goal`。格式为：`标题|类型|目标金额|当前金额|截止日期`；类型为 `savings`、`travel` 或 `category_limit`。类别限额目标还需要追加 `|类别|月限额`。

```bash
python main.py --csv data/sample_01.csv --reset \
  --goal "三个月旅行基金|travel|10000|2800|2026-10-31"

python main.py --csv /path/to/bill.csv \
  --goal "本月娱乐限额|category_limit|800|0|2026-08-31|娱乐|800" \
  --correct "星巴克:餐饮"
```

### 3. CLI 分步对话（推荐体验）

```bash
python main.py --interactive --csv data/sample_02.csv
python main.py --interactive --csv /path/to/bill.csv
```

CLI 会先由 `ConversationAgent` 发出引导，再等待用户输入。每次输入都会流式转发到大模型；输入 `/done`、`/quit` 或 `退出` 后，才由 ReflectionAgent 生成最终 Markdown 报告。

示例：

```text
你> 我想先控制深夜外卖
MoneyMirrorAgent> 先观察到你本月的深夜消费……
          本周先把一次外卖加入购物车等 10 分钟。🎯
          你觉得最容易触发深夜点单的是加班、游戏还是追剧？
你> 追剧
你> /done
```

## 📄 CSV 格式

CSV 示例：

```csv
日期,商户,金额,收支,备注
2026-07-05 09:00,公司工资,7600,收入,七月工资到账
2026-07-06 22:42,美团外卖-火锅,76,支出,深夜外卖
```

同时支持 `date/日期/交易时间`、`merchant/商户/交易对方`、`amount/金额`、`direction/收支/类型`、独立 `income/expense` 等常见列。金额保存为正数，`kind` 明确为 `income` 或 `expense`。

## 🎮 Money Quest：真实信号 × LLM 编排 × Python 强校验

Money Quest 会根据账单中识别出的消费信号生成个性化任务，例如深夜消费、高频小额支出、弹性消费、连续扣费、周末消费、发薪后消费与储蓄目标进度等。

LLM 结合已验证的信号生成任务主题、引导文案和行动提示；Python 负责校验任务与账单事实的一致性，并管理目标值、进度、EXP、完成状态与奖励。任务及其完成记录会保存到 SQLite Memory，用户可在终端通过 `/quests` 查看任务面板，并使用 `/complete <quest_id> [备注]` 完成人工确认类任务。

## 🔄 Reflection 与 Markdown 报告

ReflectionAgent 的输入是：

```text
上月快照 + 本月实际消费 + 动态预算 + Quest 进度 + 目标投影 + 用户引导对话
```

它先给出下一周期策略；用户完成引导后，最终 LLM 报告会包含财务镜像、类别与趋势、行为模式、异常解释、消费人格、订阅提醒、目标、预算、Quest、等级与成就、Reflection 和可执行行动清单。金额、比例与任务进度由 JSON 事实快照提供。

## ⚠️ 限制与隐私

- 使用真实账单时，LLM 解释、引导和报告会将必要的账单分析上下文发送至你配置的模型服务；请先了解其隐私条款并自行脱敏。

## 👤 作者与许可证

- GitHub: [@CoralGarden52](https://github.com/CoralGarden52)
- 本项目随 Hello-Agents 共创目录遵循仓库的 CC BY-NC-SA 4.0 License。
