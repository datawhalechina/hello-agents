# MoneyMirrorAgent —— 面向年轻人的游戏化个人财务行为智能体

> 将账单转化为可理解的消费镜像，并通过多智能体对话帮助用户制定下一步行动。

## 📝 项目简介

MoneyMirrorAgent 面向日常个人账单场景，接收用户提供的 CSV 交易记录，完成账单标准化、消费分类、行为分析、目标规划和游戏化行动编排。

项目将确定性计算与大模型能力分开：Python 工具负责金额、比例、趋势、异常、预算、目标投影和任务进度；Hello-Agents 负责调用智能体进行分类补全、行为解释、消费人格表达、分步引导、Money Quest 编排、月度 Reflection 和 Markdown 月报生成。

适用场景包括：

- 想了解自己消费结构和行为模式的个人用户；
- 希望围绕预算、储蓄或某一消费类别制定行动计划的用户；
- 需要使用自有 CSV 账单进行本地分析和长期记录的用户。

## ✨ 核心功能

- [x] **账单导入与标准化**：支持常见中英文列名、日期格式、收入/支出字段，以及 UTF-8 和 GB18030 编码。
- [x] **智能消费分类**：优先查询 SQLite Memory 和规则，低置信度交易交给 LLM 判断；用户纠正后会影响后续同商户分类。
- [x] **消费行为分析**：统计收入、支出、结余、储蓄率、类别占比、日/周/月趋势、深夜消费、周末消费、发薪后消费和高频小额消费。
- [x] **异常与订阅检测**：使用 IQR、Z-score、历史水平和周期性扣费规则发现行为信号，并由 LLM 生成解释。
- [x] **消费人格**：根据真实消费特征向量和配置化人格原型生成有证据支持的个性化表达。
- [x] **目标与预算规划**：根据现金流、历史消费和目标截止日期计算目标可行性、月度储蓄额度和动态预算。
- [x] **Money Quest**：LLM 根据真实行为信号编排个性化任务，Python 校验目标、金额、进度、EXP 和完成状态。
- [x] **等级与成就**：记录任务完成情况、连续完成天数、经验值和阶段性成就。
- [x] **长期 Memory**：使用 SQLite 保存分类修正、目标、预算、Quest、成就、历史快照、Reflection 和引导对话。
- [x] **月度 Reflection**：比较计划、实际消费、预算、目标进度和 Quest 完成情况，生成下一周期策略。
- [x] **分步 AI 引导与 Markdown 月报**：终端中流式输出观察、建议和追问，用户结束引导后生成 Markdown 月报。

## 🛠️ 技术栈

- **Hello-Agents**：`ToolRegistry`、`ReActAgent`、`PlanSolveAgent`、`ReflectionAgent`、`SimpleAgent`、`ContextBuilder`
- **大模型**：OpenAI 兼容 API，可配置 DeepSeek 等模型服务
- **数据处理**：Python 标准库、CSV、日期处理和统计计算
- **长期存储**：SQLite
- **交互方式**：Python CLI 和流式终端对话
- **测试工具**：pytest、compileall

### Agent 架构

```text
CSV 账单
   ↓
MoneyMirrorCoordinator
   ├── TransactionAgent   ReActAgent：分类、规则与 Memory
   ├── PatternAgent       PlanSolveAgent：统计、异常与订阅分析
   ├── PersonaAgent       特征提取、原型评分与 LLM 表达
   ├── GoalAgent          目标投影与预算规划
   ├── QuestAgent         真实信号与 LLM 任务编排
   ├── ReflectionAgent    计划、实际与下一周期策略
   └── ConversationAgent  分步引导与 Markdown 月报
```

项目中的确定性工具包括：

- `CSVImportTool`
- `TransactionCategoryTool`
- `StatisticsTool`
- `AnomalyDetectionTool`
- `BudgetCalculatorTool`
- `GoalProjectionTool`
- `SubscriptionDetectorTool`
- `QuestProgressTool`

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 可访问的 OpenAI 兼容模型服务
- Linux、macOS 或 Windows

### 安装依赖

```bash
cd Co-creation-projects/CoralGarden52-MoneyMirrorAgent
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 配置 API 密钥

复制配置文件并填写模型服务信息：

```bash
cp .env.example .env
```

`.env` 中的主要配置项如下：

```dotenv
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-v4-flash
LLM_API_KEY=your_api_key_here
LLM_MAX_TOKENS=16384
LLM_CONTEXT_MAX_TOKENS=100000
LLM_TEMPERATURE=0.2
```

请将 API Key 仅保存在本地 `.env` 文件中，不要提交到 Git 仓库。

### 运行项目

使用 `--csv` 指定账单路径，项目不会依赖固定文件名，用户可以替换为自己的 CSV 文件：

```bash
# 完整分析：导入、分类、统计、目标、预算、Quest、Reflection 和 Markdown 月报
python main.py --csv data/sample_01.csv --reset

# 使用自己的账单
python main.py --csv /path/to/your_transactions.csv --reset

# 进入 CLI 分步对话
python main.py --interactive --csv data/sample_01.csv
```

运行结果写入 `outputs/`：

```text
outputs/<输入文件名>_money_mirror_report.json
outputs/<输入文件名>_money_mirror_report.md
outputs/moneymirror.db
```

JSON 文件保存已验证的事实快照，Markdown 文件由大模型根据账单事实、Memory 和用户对话生成。

## 📖 使用示例

### CSV 输入

```csv
日期,商户,金额,收支,备注
2026-07-05 09:00,公司工资,7600,收入,七月工资到账
2026-07-06 22:42,美团外卖-火锅,76,支出,深夜外卖
2026-07-07 08:20,地铁,6,支出,通勤
```

程序也支持以下常见字段名：`date`、`日期`、`交易时间`、`merchant`、`商户`、`amount`、`金额`、`direction`、`收支`、`type`，以及独立的收入和支出列。

### 创建目标和修正分类

```bash
python main.py --csv data/sample_01.csv --reset \
  --goal "三个月旅行基金|travel|10000|2800|2026-10-31"

python main.py --csv /path/to/your_transactions.csv \
  --correct "星巴克:餐饮"
```

### CLI 分步引导

```text
MoneyMirrorAgent> 这份账单中观察到深夜餐饮支出较集中。
MoneyMirrorAgent> 你想先从减少深夜外卖、控制周末消费，还是检查连续扣费开始？
你> 我想先控制深夜外卖
MoneyMirrorAgent> 我们先设定一个本周可完成的小目标。最容易触发深夜点单的时间通常是什么时候？
你> 晚上加班以后
你> /done
```

输入 `/done`、`/quit` 或 `退出` 后，系统会综合本轮对话和已验证账单数据生成 Markdown 月报。输入 `/quests` 可以查看当前任务，输入 `/complete <quest_id>` 可以记录人工确认的任务完成情况。

## 🎯 项目亮点

- **数据与推理分工明确**：金额和统计由 Python 完成，大模型负责理解、解释、规划和表达。
- **真实信号驱动行动**：消费人格和 Money Quest 来自账单中的实际行为特征。
- **Memory 影响后续流程**：分类纠正、目标、预算、Quest 和对话会被保存，并参与后续分析。
- **对话逐步推进**：MoneyMirrorAgent 通过观察、建议和追问引导用户，完成交流后再生成月报。
- **文件名可追溯**：报告使用输入 CSV 的文件名作为前缀，方便区分不同账单。

## 📊 性能评估

当前版本已完成以下本地验证：

- 自动化测试：`28 passed`
- 编译检查：`python -m compileall -q src main.py tests` 通过
- CSV 导入、分类、Memory、统计、异常检测、预算、目标、Quest、Reflection 和对话流程均有测试覆盖
- 已使用配置的 OpenAI 兼容模型完成完整 CLI 分析，并生成 JSON 事实快照和 Markdown 月报

## 🔮 未来计划

- [ ] 扩展更多银行、支付平台和记账软件的 CSV 字段映射
- [ ] 支持跨月账单合并和更长周期的趋势比较
- [ ] 增加更多可配置的成就和 Quest 进度事件
- [ ] 增加脱敏导出和本地报告归档管理
- [ ] 补充不同账单格式下的端到端回归样例

## 🤝 贡献指南

欢迎通过 Issue 或 Pull Request 提出改进建议。提交代码时请：

1. 保持确定性计算与大模型推理职责分离；
2. 为新增工具、Agent 或数据格式补充测试；
3. 不提交 `.env`、API Key、SQLite 数据库和运行生成文件；
4. 同步更新 README 和 ExecPlan。

## 📄 许可证

本项目随 Hello-Agents 共创目录遵循 CC BY-NC-SA 4.0 License。

## 👤 作者

- GitHub: [@CoralGarden52](https://github.com/CoralGarden52)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目提供的教程、框架与共创平台。
