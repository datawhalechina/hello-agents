---

# NewsSentimentAgent

> StockAnalysisAgent 多智能体系统中的**舆情分析子智能体**，负责个股新闻的采集、大模型情感极性分析、风险提取与聚合统计。

---

## 简介

`NewsSentimentAgent` 是 `StockAnalysisAgent` 的两个核心子智能体之一（另一个是 `MarketDataCollectorAgent`）。它负责获取个股相关的最新资讯，利用大模型（LLM）对新闻逐条进行情感分析（利好/利空/中性），最终汇总为结构化的舆情信号，供外层主 Agent 写研报使用。

**核心职责：**
- **新闻采集**：从东财、新浪等多源抓取个股新闻，支持本地按日缓存。
- **大模型分析**：解析新闻，判断情绪极性（positive/negative/neutral）及对股价的实际传导预期。
- **并发与容错**：多线程并发调用 LLM，内置限流退避、超时重试与代理隔离。
- **聚合统计**：计算利好/利空比例、加权情绪得分，并提取最重要的 Top 3 利好与利空。

---

## 目录结构

```text
NewsSentimentAgent/
├── schemas.py                  # Pydantic 数据模型（原始新闻、单条分析、聚合结果）
├── agents/
│   ├── __init__.py
│   └── news_agent.py           # NewsSentimentAgent 核心类（对外暴露 run 接口）
└── news_tools/
    ├── __init__.py
    ├── collector.py            # 新闻采集（多源回退 + 按日缓存）
    ├── llm_analyzer.py         # LLM 单条分析（JSON 清洗 + 重试 + 代理隔离）
    └── aggregator.py           # 并发调度（ThreadPool）+ 聚合计算
```

---

## 主要特性

- **多源回退**：新闻优先取东方财富，失败自动降级到新浪财经。
- **按日缓存**：当天抓取的新闻缓存为本地 JSON，同一天内重复请求不再走网络（支持 `force_refresh` 强制刷新）。
- **并发分析防限流**：采用 `ThreadPoolExecutor`，最大并发度限制为 3，防止瞬间触发 LLM API 限流。
- **鲁棒的 JSON 解析**：`_clean_json_response` 自动剥离大模型返回的 Markdown 代码块，截取纯净 JSON 避免解析崩溃。
- **网络代理隔离**：显式清空系统 `HTTP_PROXY` 等环境变量，并配置 `httpx.Client(trust_env=False)`，彻底解决部分环境因代理导致 LLM 请求挂起的问题。
- **智能重试**：遇到限流（RateLimitError）按 5s、10s、15s 退避；网络超时按 2s、4s 退避。

---

## 安装

Python ≥ 3.10，建议在虚拟环境中安装：

```bash
pip install -r requirements.txt
```

**`requirements.txt`：**

```

---

## 快速开始

在项目根目录配置 `.env`：

```env
API_KEY=your_api_key
BASE_URL=https://api.openai.com/v1  
MODEL=gpt-4o-mini
```

**直接调用子 Agent：**

```python
from src.agent.NewsSentimentAgent.agents import NewsSentimentAgent

agent = NewsSentimentAgent(default_limit=15)
result = agent.run("600519", force_refresh=False)

print(f"整体舆情: {result.overall_sentiment}")
print(f"利好占比: {result.positive_ratio}")
for news in result.top_positive_news:
    print(f"- {news.title}: {news.one_line_summary}")
```

---

## 接口说明

```python
class NewsSentimentAgent:
    def run(self, symbol: str, limit: int = None, force_refresh: bool = False) -> NewsSentimentResultSchema
```

**返回结构 (`NewsSentimentResultSchema`)：**

```json
{
  "analyzed_count": 15,
  "failed_count": 0,
  "overall_sentiment": "偏多",
  "weighted_sentiment_score": 0.45,
  "positive_ratio": 0.6,
  "negative_ratio": 0.2,
  "neutral_ratio": 0.2,
  "top_positive_news": [...],
  "top_negative_news": [...],
  "articles": [...]
}
```

---

## 注意事项

- **大模型输出约束**：Prompt 严格限制了 JSON 输出格式，若更换模型（尤其是带思维链的模型）输出格式跑飞，可通过调整 `max_tokens` 或修改 System Prompt 强化约束。
- **缓存目录**：默认在当前运行目录下生成 `./news_data_cache`，若出现找不到文件错误，请检查启动路径权限。
- **依赖耦合**：`collector.py` 中尝试引用了 Agent1（MarketDataCollectorAgent）的 `_common._create_retry_session` 来复用重试请求，若模块位置变动，需调整 `import` 路径或忽略该 Warning。
- **LLM 并发限制**：`ThreadPoolExecutor(max_workers=3)` 是安全值，若你的 API 额度极高且不介意被封，可适当调大，但不建议超过 10。
- **未来改进**：计划引入 **MCP (Model Context Protocol)** 服务，将新闻爬取与分析能力通过 MCP Server 暴露，进一步增强与主 Agent 的标准解耦和复用性。