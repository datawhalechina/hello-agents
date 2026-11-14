# StockAnalysisAgent（多智能体 A 股学术研报系统）

> 基于 hello-agents 框架的多智能体协作 A 股客观研究报告生成系统。

## 📝 项目简介

本项目是一个专为**学术研究场景**设计的多智能体股票分析系统。针对通用大模型在金融领域容易产生幻觉、违规给出投资建议的问题，系统基于 **hello-agents 框架** 的 `ToolRegistry` 机制，将两个专业子 Agent 封装为标准 Tool，由主控 `SimpleAgent` 通过原生 Function Calling 循环自主调度，最终输出一份结构固定、客观中立、无任何投资建议的学术研报。

**解决的问题**：
- 通用大模型直接问股票容易编造数据、给出"建议买入"等违规表述；
- 多数据源（行情 + 舆情）人工整合效率低、格式不统一；
- 传统单体脚本难以扩展新数据源。

**特色功能**：
- 一切皆为 Tool：行情采集、舆情分析均以标准 Tool 形式注册，主 Agent 自动学会调用，新增数据源零侵入；
- 双 Tool 并发：舆情 Tool 内部保留 `ThreadPoolExecutor` 并发调用大模型，并发度限制为 3 并带限流退避；
- 防幻觉约束：System Prompt 中硬性禁止预测涨跌、禁止给出买卖建议、强制附免责声明；
- 缓存与降级：新闻数据按日缓存，支持 `default_limit` 降级，演示时不卡死。

**适用场景**：毕业设计、课程项目、金融 NLP 学术研究演示。

## ✨ 核心功能

- [x] **hello-agents 工具化架构**：`MarketDataTool` 与 `NewsSentimentTool` 注册到 `ToolRegistry`，主控 `SimpleAgent` 自主调度，无需手写胶水代码。
- [x] **Tool 内并发调度**：舆情 Tool 内部使用 `ThreadPoolExecutor`（并发度 3）并发分析新闻，配合 `RateLimitError` 的 5s/10s 递增退避。
- [x] **数据聚合与兼容**：兼容 Pydantic 对象与普通 Dict，统一序列化为标准 JSON 作为 Tool 返回值。
- [x] **防幻觉 Prompt 约束**：System Prompt 中设定"硬性约束"优先级，禁止预测股价、编造数据、给出买卖建议。
- [x] **缺失数据兜底**：子 Tool 抛错或数据缺失时，报告对应模块必须如实标注"数据缺失"，严禁脑补。
- [x] **新闻日级缓存**：命中当日缓存直接从本地 JSON 读取，避免重复爬取与重复 LLM 调用。

## 🛠️ 技术栈

- **Python 3.10+**
- **HelloAgents 框架**：`SimpleAgent`（主控）、`ToolRegistry`（工具注册）、`HelloAgentsLLM`（LLM 客户端）、自定义 `Tool` 基类（工具封装）
- **智能体范式**：Plan-and-Solve 提示词工程 + 原生 Function Calling 循环
- **数据与工具**：AkShare（行情）、httpx（舆情爬取，`trust_env=False` 绕过系统代理）、OpenAI SDK 兼容的 LLM 接口
- **数据校验**：Pydantic（子 Agent 结构化返回）
- **并发**：`concurrent.futures.ThreadPoolExecutor`
- **配置**：python-dotenv

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 可访问 AkShare 数据源与大模型 API 的网络环境
- 推荐在 PyCharm 或 Jupyter Notebook 中运行

### 安装依赖

```bash
pip install -r requirements.txt
# 或直接安装核心依赖
pip install hello-agents[all] openai python-dotenv akshare pandas pydantic requests urllib3 httpx
```

### 配置 API 密钥

在项目根目录创建 `.env` 文件（或复制 `.env.example`）：

```bash
cp .env.example .env
```

填入 hello-agents 约定的配置项：

```env
LLM_MODEL_ID=your-model-name
LLM_API_KEY=your-api-key
LLM_BASE_URL=your-api-base-url
```

### 运行项目

**方式一：PyCharm 直接运行**

将 `main_hello_agent.py` 放在项目根目录（与 `src/` 同级），右键运行即可。

**方式二：Jupyter Notebook**

```bash
jupyter lab
# 打开 main.ipynb 并运行
```

## 📖 使用示例

```python
import os
from dotenv import load_dotenv
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from tools.market_data_tool import MarketDataTool
from tools.news_sentiment_tool import NewsSentimentTool

load_dotenv()

# 1. 初始化 LLM 与工具注册表
llm = HelloAgentsLLM()
registry = ToolRegistry()
registry.register_tool(MarketDataTool())
registry.register_tool(NewsSentimentTool(default_limit=2))  # 演示时只分析 2 条，防卡死

# 2. 创建主控 Agent
master_agent = SimpleAgent(
    name="StockAnalysisMaster",
    llm=llm,
    tool_registry=registry,
    system_prompt="""你是一个严谨的 A 股学术研究助手。
    你的任务是：根据用户提供的股票代码，调用工具获取行情数据和舆情分析结果，
    然后生成一份结构化的学术研报。
    要求：
    1. 必须同时调用 market_data_collector 和 news_sentiment_analyzer 两个工具。
    2. 报告必须包含：行情概览、舆情摘要、综合观察。
    3. 严禁预测后市涨跌，严禁给出投资建议。
    4. 报告末尾必须附上免责声明。"""
)

# 3. 执行任务
report = master_agent.run("请分析股票 600519，并生成学术研报。")
print(report)
```

**输出报告结构**（严格 6 大模块）：

1. 标的基础概况
2. 行情概览
3. 基本面与估值
4. 技术指标解读
5. 舆情分析总结（直接引用 Top 利好/利空）
6. 综合总结与风险提示 + 免责声明

*（注：子 Tool 数据采集失败时，对应模块显示"数据缺失/采集失败"。）*

## 🎯 项目亮点
- **Plan-and-Solve 落地**：System Prompt 强制要求模型先规划"数据是否齐备"，再执行"研报撰写"，有效降低复杂多源数据下的幻觉率。
- **绝对合规与防诱导**：通过硬性 Prompt 约束屏蔽"大概率上涨""建议关注"等煽动性词汇，完全符合毕业设计与学术研究要求。
- **工程化容错**：
  - 兼容 Pydantic 与 Dict 两种返回形态（`hasattr(obj, 'model_dump_json')`）；
  - 舆情 Tool 内部保留并发度 3 + 限流递增退避；
  - 新闻日级缓存 + `default_limit` 降级，演示零卡死。
- **并发能力未丢失**：迁移到 hello-agents 后，并发逻辑下沉到 Tool 内部，工具间调用顺序由主 Agent 决策，工具内并发不受框架影响。

## 📊 性能评估

基于真实运行日志（600519 贵州茅台）：

| 阶段 | 耗时 |
| :--- | :--- |
| 舆情 Tool 内部并发分析（2 条新闻，并发度 3） | 3.49 秒 |
| 主 Agent 双 Tool 调度总耗时（含缓存命中） | 5.70 秒 |
| 主 LLM 撰写最终研报 | 24.60 秒 |
| **端到端总耗时** | **约 25 秒** |

- **准确率**：报告结构 6 大模块齐全率 100%（数据缺失时按规范降级）；
- **防幻觉指标**：报告中未出现任何预测涨跌、目标价或买卖建议表述；
- **响应时间**：单只股票全维度诊断通常 30 秒内完成，受 LLM 首字延迟影响较大（Qwen2.5-7B 在长 prompt 下约为 15~30 秒）。
- **提醒**：1.本测试因为模型限制，如果条件允许，建议采用更大的模型，目前的模型容易出现幻觉，存在“做主观定性和后市预测”和“变相预测”等问题，小模型“指令遵从能力”很弱，如果还是要用小模型，建议优化Prompt文件，加强约束。
            2.本模型中MarketDataCollectorAgent底层采用Akshare去爬取数据，目前封装了三个接口，首先访问东方财富的接口，第一次可能成功，后面可能风控，可以打一个补丁 pip install akshare-proxy-patch 然后去该补丁的网站充值获得 token，可能可以减少反爬虫的概率，如果不行，则会更换到腾讯的接口拿数据，最后是新浪接口，然后会存储在本地，同一天访问可以直接访问本地数据，如果对数据精度要求过高，可能会没有办法拿到精确数据，但是这样可以减少反爬虫概率。

## 🔮 未来计划

- [ ] **接入 MCP 服务**：将 `MarketDataTool` 与 `NewsSentimentTool` 改造为标准 MCP Server，实现跨语言、跨进程的灵活插拔（hello-agents 的 Tool 体系已为此铺路）。
- [ ] **RAG 检索增强**：针对财报长文本建立向量索引，辅助基本面深度问答。
- [ ] **异步化改造**：将 Tool 内部的 `ThreadPoolExecutor` 升级为 `asyncio`，进一步提升高并发下的资源利用率。
- [ ] **字段语义对齐**：在 Tool 返回值中补齐 `trade_date`、`volume_change_pct`、`top_positive`、`top_negative` 等字段，减少主 Agent 二次推断，提升小模型输出稳定性。

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@IUING2059](https://github.com/IUING2059)
- Email: 你的邮箱（可选）

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目提供的多智能体范式与框架支持。
