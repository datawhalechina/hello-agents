# CryptoAnalysisAgent - 加密货币多维分析智能体

> 基于 HelloAgents 框架构建的多 Agent 协作加密货币分析系统，融合技术分析、链上数据、市场情绪三维视角，为交易决策提供结构化参考。

## 📝 项目介绍

CryptoAnalysisAgent 是一个面向加密货币交易场景的多智能体分析系统。它不是一个"预测涨跌"的黑盒，而是一个帮助交易者**系统化整理市场信息、降低认知负荷、提高决策质量**的工具。

本项目的设计理念来源于 [NOFXi](https://github.com/nofx-trading/nofx) 交易智能助手的实战经验：

- **Skill-first 架构**：高频分析任务由预定义 Skill 处理，避免模型自由发挥
- **多 Agent 协作**：技术分析、链上分析、情绪分析各司其职，最终由综合分析 Agent 汇总
- **条件化建议**：不给绝对判断，只给条件化的可执行建议
- **风险优先**：所有分析结论都附带风险提示和置信度标注

### 核心特点

- ✅ **多维度分析**：技术指标 + 链上数据 + 市场情绪三维交叉验证
- ✅ **ReAct 范式**：Agent 通过观察-思考-行动循环完成分析任务
- ✅ **多 Agent 协作**：专业分工 + 综合汇总的协作模式
- ✅ **结构化输出**：生成标准化 Markdown 分析报告
- ✅ **风险意识**：所有建议均为条件化表述，明确标注不确定性

## 🏗️ 系统架构

```
用户请求 (如: "分析 BTC 当前走势")
        │
        ▼
┌─────────────────────────┐
│   Coordinator Agent     │  ← 任务分发与结果汇总
│   (Plan-and-Solve)      │  ← run_full_analysis 并行调用三位分析师
└─────────┬───────────────┘
          │ (并行执行)
    ┌─────┼─────────────┐
    ▼     ▼             ▼
┌───────┐ ┌──────────┐ ┌──────────┐
│技术分析│ │链上数据  │ │情绪分析  │
│ Agent │ │ Agent    │ │ Agent    │
│(ReAct)│ │(ReAct)   │ │(ReAct)   │
└───┬───┘ └────┬─────┘ └────┬─────┘
    │          │             │
    ▼          ▼             ▼
┌───────┐ ┌──────────┐ ┌──────────┐
│K线数据│ │链上指标  │ │恐惧贪婪  │
│技术指标│ │巨鲸动向  │ │社交热度  │
│形态识别│ │资金流向  │ │新闻情绪  │
└───┬───┘ └────┬─────┘ └────┬─────┘
    └──────────┼─────────────┘
               ▼
┌─────────────────────────────────┐
│  market_data 共享数据访问层      │
│  Session 连接复用 + TTL 缓存     │
│  + 自动重试 (Binance/Alt.me)     │
└─────────────────────────────────┘
```

**性能设计**:
- **并行子 Agent**: Coordinator 的 `run_full_analysis` 工具用线程池同时运行三位分析师，综合分析耗时从三者之和降为最慢的一个
- **共享数据层**: 所有工具的 HTTP 请求经过 `market_data` 模块——连接复用、60s TTL 缓存（一轮分析中同一份 K 线/ticker 只请求一次）、网络抖动自动重试
- **向量化计算**: EMA/MACD/支撑阻力位识别均为 numpy/pandas 向量化实现，MACD 一次计算完整序列
- **模型分级路由**: 子 Agent 的数据整理用小模型、Coordinator 的综合判断用强模型，在 `.env` 设置 `LLM_SUB_MODEL_ID`（如 Qwen2.5-7B）即可启用，显著降低单次分析的 Token 成本

## ✨ 核心功能

### 1. 技术分析 Agent
- K 线数据获取与多周期分析
- 技术指标计算（EMA、RSI、MACD、布林带、ATR）
- 支撑阻力位识别
- 趋势判断与形态识别

### 2. 链上数据 Agent
- 交易所净流入/流出监控
- 巨鲸地址活动追踪
- 持仓分布分析
- 活跃地址数趋势

### 3. 情绪分析 Agent
- 恐惧贪婪指数解读
- 社交媒体热度分析
- 资金费率与多空比
- 重大新闻事件影响评估

### 4. 综合分析 Coordinator
- 多维度信号交叉验证
- 矛盾信号识别与标注
- 条件化交易建议生成
- 风险等级评估

## 🛠️ 技术栈

- **Agent 框架**: HelloAgents (SimpleAgent + ToolRegistry + Multi-Agent)
- **Agent 范式**: ReAct (技术/链上/情绪 Agent) + Plan-and-Solve (Coordinator)
- **数据源**: Binance API (K线)、CoinGlass (链上)、Alternative.me (情绪)
- **技术指标**: 自研计算模块（基于 pandas/numpy）
- **LLM**: 兼容 OpenAI API 格式（推荐 Qwen2.5-72B / DeepSeek）

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 网络环境可访问 Binance API

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 LLM API Key
```

### 运行项目

**方式一: 命令行 (推荐，适合生产/定时运行)**

```bash
python analyze.py BTC              # 完整分析: 报告 + 质量门禁 + 归档信号
python analyze.py BTC ETH SOL      # 批量分析
python analyze.py --settle         # 核算到期信号，打印历史胜率
python analyze.py BTC --judge      # 额外执行 LLM Judge 语义评审
```

报告（含考核结果与性能指标）保存到 `outputs/reports/`；通过质量门禁的分析自动归档为信号。配合 crontab 可实现每日定时报告:

```cron
0 9 * * *  cd /path/to/project && python analyze.py BTC ETH
0 10 * * * cd /path/to/project && python analyze.py --settle
```

**方式二: Jupyter (适合学习/交互探索)**

```bash
jupyter lab
# 打开 main.ipynb 运行所有 cell
```

## 📖 使用示例

```python
# 快速分析 BTC 当前走势
result = coordinator.run("分析 BTC 当前的市场状况，给出交易建议")

# 指定分析维度
result = coordinator.run("从技术面分析 ETH 是否适合入场做多")

# 多币种对比
result = coordinator.run("对比 BTC 和 SOL 近期的链上资金流向")
```

### 输出示例

```markdown
## BTC 综合分析报告

### 技术面
- 趋势: 4H 级别震荡偏多，日线处于上升通道中轨
- 关键位: 支撑 $67,200 | 阻力 $71,500
- 指标: RSI(14)=58 中性偏多，MACD 金叉后动能减弱

### 链上面
- 交易所净流出 $1.2B (7日)，供给收缩信号
- 巨鲸地址近 24h 增持 2,300 BTC
- 长期持有者占比持续上升

### 情绪面
- 恐惧贪婪指数: 72 (贪婪)
- 资金费率: 0.01% (中性)
- 社交热度: 较上周 +15%

### 综合判断
- 信号一致性: 中等 (技术面+链上面看多，情绪面偏热需警惕)
- 风险提示: 贪婪指数偏高，短期回调风险存在
- 条件化建议:
  - 若持有多头仓位: 可继续持有，止损设在 $67,200 下方
  - 若计划入场: 建议等待回踩 $68,500 附近再考虑
  - 若偏保守: 当前不是最佳入场点，观望为主

⚠️ 免责声明: 以上分析仅供参考，不构成投资建议。加密货币市场波动剧烈，请根据自身风险承受能力做出决策。
```

## 📏 Agent 考核体系

项目内置 `src/evaluation/` 评估模块，对 Agent 输出做自动化考核（设计对应 Hello-Agents 第十二章的评估框架）:

| 指标 | 方法 | 实现 |
|---|---|---|
| 结构合规率 | 规则 | 报告是否包含模板要求的 8 个章节与免责声明 |
| 条件化建议 | 规则 | 检测"必涨/稳赚"等绝对化表述，统计条件化表述数量 |
| 数据真实性 | 规则 | 报告中的价格/百分比能否在工具原始返回中溯源（反幻觉抽查） |
| 端到端延迟 | 埋点 | `timed_run()` 统计耗时 |
| 工具调用效率 | 埋点 | HTTP 请求数、缓存命中率、各工具调用次数 |
| 语义质量 | LLM Judge | 评审 Agent 按矛盾信号处理/条件化/风险意识/事实判断分离/可执行性五维打分 |

```python
from src.evaluation import evaluate_report, format_evaluation, ToolCallCounter, timed_run

counter = ToolCallCounter()
coordinator = create_coordinator(llm=llm, tool_counter=counter)
report, metrics = timed_run(coordinator, "分析 BTC")

print(format_evaluation(evaluate_report(report, tool_outputs=counter.outputs)))
```

详见 `main.ipynb` Part 4.5。

### 信号留痕与历史胜率 (Track Record)

每次综合分析可自动归档为一条信号（币种、方向判断、信号时刻价格），到期后用 Binance 真实历史 K 线核算对错，积累可对外展示的胜率统计——商业化所需"可验证效果记录"的数据基础:

```python
from src.evaluation import record_signal, update_outcomes, summarize_signals, format_signal_summary

record_signal("BTC", comprehensive_report)   # 分析后归档 (方向自动提取)
update_outcomes()                            # 每天运行一次，核算到期信号
print(format_signal_summary(summarize_signals()))  # 24h/7d 胜率、分币种统计
```

信号存储于 `outputs/signals.jsonl`（追加写、可审计）。详见 `main.ipynb` Part 4.6。

## 🎯 项目亮点

- **实战驱动**: 设计理念来源于 NOFXi 真实交易系统的架构经验
- **Skill-first**: 借鉴 NOFXi 的 "80% Skill + 20% 动态规划" 思路
- **多 Agent 协作**: 展示了专业分工型多智能体系统的设计模式
- **条件化输出**: 不做绝对预测，给出条件化的可执行建议
- **可扩展**: 易于添加新的分析维度和数据源

## 📊 设计决策说明

### 为什么选择多 Agent 而非单 Agent？

加密货币分析涉及多个专业领域（技术分析、链上分析、情绪分析），每个领域有独立的数据源和分析逻辑。单 Agent 模式下：
- Prompt 过长，模型注意力分散
- 工具过多，模型选择困难
- 单点失败影响全局

多 Agent 模式的优势：
- 每个 Agent 专注一个领域，Prompt 精简
- 工具集小而精，减少模型决策负担
- 单个 Agent 失败不影响其他维度分析

### 为什么使用条件化建议？

参考 NOFXi 的设计原则：
> "不应伪装成对市场有绝对把握"
> "应优先给出条件化建议，而不是绝对判断"

市场是复杂系统，任何分析都有局限性。条件化建议让用户根据自身情况做出选择，而不是盲目跟随。

## 🔮 未来计划

- [ ] 接入更多链上数据源（Glassnode、Dune Analytics）
- [x] 信号留痕与胜率核算（`src/evaluation/signal_ledger.py`，回测模块的数据基础）
- [x] 支持定时分析（`analyze.py` CLI + crontab，含质量门禁与信号归档）
- [ ] 集成 MCP 协议，支持与其他 Agent 系统互操作
- [x] 添加质量评估机制（规则化考核 + LLM Judge，见 `src/evaluation/`）
- [ ] 用 HelloAgents 内置的 BFCL 评估器测三个子 Agent 的工具调用准确率

## 👤 作者

- GitHub: [@gpteth](https://github.com/gpteth)
- 项目: [NOFXi Trading](https://nofx.pro)

## 🙏 致谢

- 感谢 Datawhale 社区和 Hello-Agents 项目
- 感谢 NOFXi 交易系统提供的实战架构经验
- 感谢所有开源数据 API 提供者

## 📄 许可证

MIT License

## ⚠️ 免责声明

本项目仅用于学习和研究目的。加密货币交易具有高风险，本项目的分析结果不构成任何投资建议。请在充分了解风险的前提下，根据自身情况做出投资决策。
