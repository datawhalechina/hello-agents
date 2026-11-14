# MarketDataCollectorAgent

> StockAnalysisAgent 多智能体系统中的**数据采集子智能体**，负责单只 A 股的行情、估值、技术面、基本面数据采集与清洗。

---

## 简介

`MarketDataCollectorAgent` 是 `StockAnalysisAgent` 的两个子智能体之一（另一个是 `NewsSentimentAgent`），把分散在 `akshare` 等财经数据源里的原始数据，统一清洗成标准化的 Pydantic Schema，供外层主 Agent 消费。

**核心职责：**

- 获取 K 线、成交量、成交额等行情数据
- 获取估值指标（PE、PB、PS、PEG、EV/EBITDA）
- 计算技术指标（MA、MACD、RSI、KDJ、BOLL、OBV）
- 抓取基本面财务数据（ROE、毛利率、资产负债率、现金流等）

---

## 目录结构

```
MarketDataCollectorAgent/
├── schemas.py                  # Pydantic 数据模型
├── agents/
│   ├── __init__.py
│   ├── stock_data_agent.py     # StockDataAgent 核心类
│   ├── stock_data_tool.py      # 封装为 LangChain Tool
│   └── main_agent.py           # 主 Agent 构建
└── stock_tools/
    ├── __init__.py             # StockDataTool + fetch 函数导出
    ├── _common.py              # 重试 Session / 超时 / 交易状态
    ├── quote.py                # 行情
    ├── valuation.py            # 估值
    ├── technical.py            # 技术面（含 K 线本地缓存）
    └── fundamental.py          # 基本面
```


## 主要特性

- **多源回退**：K 线东财 → 腾讯 → 新浪；快照新浪 → 东财
- **重试机制**：维度级重试 2 次，随机节流 0.5~1.5s；HTTP 指数退避
- **超时控制**：Linux/Mac 用 `signal`，Windows 优雅降级
- **本地缓存**：K 线缓存至 `./stock_data_cache/{code}_kline.csv`，当日复用
- **字段容错**：`SafeFloat` 自动清洗 `'xx%'`、NaN 等脏数据

---

## 安装

Python ≥ 3.10

```bash
pip install -r requirements.txt
```

## 快速开始

配置项目根目录 `.env`：

```env
API_KEY=your_api_key
BASE_URL=https://api.openai.com/v1  
MODEL=gpt-4o-mini
```


---

## 注意事项

- `quote` 依赖本地 K 线缓存，若无缓存且未拉取过 `technical`，首次会触发网络
- `technical` 指标需 ≥ 30 条 K 线，MA60 需 ≥ 60 条
- `fundamental` 最慢最易失败，部分字段缺失属正常
- Windows 下 `timeout()` 不生效，依赖 akshare 自身超时
- `StockDataTool.run()` 无重试/节流/超时，业务建议统一走 `StockDataAgent.run()`
- 数据源与反爬策略：
优先访问东方财富接口，若遭风控，可打补丁 pip install akshare-proxy-patch 并结合海外纯净代理 IP（如 cheapproxy.net，需自行充值获取 token）来降低反爬概率。
若东财仍不可用，自动回退至腾讯接口获取数据，并存储到本地。同一天内再次访问将直接读取本地缓存，牺牲部分高精度数据换取稳定性。
quote 维度完全依赖本地 K 线缓存，若无缓存且未拉取过 technical，首次会触发网络请求。
- 路径报错提醒：启动时请确保在项目根目录执行，因为代码中使用了相对导入（如 ..schemas）且会在当前目录生成 ./stock_data_cache 缓存文件夹，路径层级不对会导致模块导入失败或找不到缓存。

---

## 与 NewsSentimentAgent 的协作

```
StockAnalysisAgent（主 Agent）
├── MarketDataCollectorAgent   ← 本包
└── NewsSentimentAgent         ← 舆情分析
```

本包只暴露 `STOCK_DATA_TOOL`，不感知舆情逻辑，职责单一。

---
未来改进方向：计划引入 MCP (Model Context Protocol) 服务，将数据采集功能进一步标准化解耦，提升 Agent 间调用的灵活性与扩展性。

## 数据来源

- [AKShare](https://akshare.akfamily.xyz/) — 开源财经数据接口
- 东方财富 / 腾讯 / 新浪 — 行情与财务原始来源
- LangChain / LangGraph — Agent 编排框架

> 毕业设计作品，数据仅供学习研究，**不构成投资建议**。