# Stock Analysis Agent

基于 **LangGraph + Qwen** 的 A股 / 港股 / 美股多维度智能分析 Agent，支持代码 / 中文名 / 拼音 / 首字母多路搜索，主页直接展示三市当日涨幅 Top 8。

## ✨ 核心特性

- **三市统一搜索**：A 股 / 港股 / 美股一个搜索框搞定，支持 `茅台 / 600519 / 00700 / AAPL / 苹果 / mt` 等多种输入
- **多维度评分**：情感面（新闻 LLM 分析）+ 技术面（MA / RSI / MACD / 量能）+ 基本面（PE / PB / 成长 / 市值），加权综合给出风险等级
- **并行 Agent Graph**：LangGraph 把 sentiment / technical / fundamental 三路并行，aggregator 收敛后再生成报告
- **主页热门榜**：A / 港 / 美 各 30 只大盘股候选池，按当日涨幅排序展示 Top 8，三色区分（蓝 / 红 / 绿），点击直接分析
- **国内网络友好**：美股 / 港股优先走 Sina 通道（akshare 内置），eastmoney / Yahoo Finance 不可达时自动降级，全部带 5 分钟 TTL 缓存
- **进度可视化**：分析期间用 antd Steps 实时展示"采集数据 → 三维分析 → 生成报告"四个阶段

## 🏗 技术栈

### 后端
| 模块 | 选型 | 说明 |
|---|---|---|
| Web 框架 | **FastAPI 0.115** | 异步 + Pydantic v2 |
| Agent 框架 | **LangGraph 1.2** | StateGraph + 并行 fan-out |
| LLM | **ModelScope Qwen3** | 报告 35B-A3B，情感 235B-A22B（MoE） |
| 数据源 | **AKShare（Sina/eastmoney）+ yfinance** | 美股双源兜底，港股 Sina + eastmoney |
| 中文转拼音 | **pypinyin** | 搜索倒排索引 |
| Python | **3.11+** | |

### 前端
| 模块 | 选型 |
|---|---|
| 框架 | **React 19 + Vite 8** |
| UI 组件 | **Ant Design 6** |
| 图表 | **Recharts 3** |
| HTTP | **Axios** |

### Agent Graph 结构

```
                 ┌─→ sentiment ─┐
                 │              │
data_collector ──┼─→ technical ─┼─→ aggregator → report_generator → END
                 │              │
                 └─→ fundamental┘
                              ↘ risk_warning（极端悲观时）→ END
```

## 📂 目录结构

```
stock-agent/
├── backend/
│   ├── agent/
│   │   ├── graph.py              # LangGraph 装配
│   │   ├── state.py              # TypedDict 状态
│   │   └── nodes/
│   │       ├── data_collector.py # 行情/K线/新闻/基本面采集
│   │       ├── sentiment.py      # 情感分析（Qwen）
│   │       ├── technical.py      # 技术指标本地计算
│   │       ├── fundamental.py    # 基本面评分
│   │       └── report_generator.py
│   ├── api/
│   │   ├── routes/analysis.py    # /search /hot/all /analyze
│   │   └── schemas.py            # Pydantic 模型
│   ├── app/
│   │   ├── main.py               # FastAPI 入口
│   │   └── config.py             # 配置（pydantic-settings）
│   ├── data/sources/
│   │   ├── akshare_adapter.py    # A/HK 主源 + 三市 Sina 兜底
│   │   ├── yfinance_adapter.py   # 美股可选源
│   │   ├── news_adapter.py       # 个股新闻
│   │   ├── hot_stocks.py         # 热门涨幅榜
│   │   └── stock_list.py         # 三市股票列表 + 搜索倒排索引
│   ├── tests/                    # pytest 单测
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/client.js
│   │   ├── components/
│   │   │   ├── SearchBar.jsx
│   │   │   ├── HotStocks.jsx        # 三栏涨幅榜
│   │   │   ├── AnalysisProgress.jsx # 分析进度条
│   │   │   ├── MetricCards.jsx
│   │   │   ├── KlineChart.jsx
│   │   │   ├── ScorePanel.jsx
│   │   │   └── ReportPanel.jsx
│   │   ├── hooks/useAnalysis.js
│   │   ├── pages/Dashboard.jsx
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── A-stock.csv  / G-stock.csv / U-stock.csv   # 三市股票名录
├── scripts/                                    # 调试脚本
└── README.md
```

## 🚀 部署运行

### 1. 准备环境

```bash
# Python 3.11+
python --version

# Node 18+
node --version
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 ModelScope API Key（[申请地址](https://modelscope.cn)）：

```bash
cd stock-agent
cp .env.example .env
# 编辑 .env，至少填 MODELSCOPE_API_KEY
```

可选环境变量说明：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MODELSCOPE_API_KEY` | 必填 | 通过该 Key 调用 Qwen 系列模型 |
| `QWEN_MODEL` | `Qwen/Qwen3.5-35B-A3B` | 报告生成模型 |
| `QWEN_SENTIMENT_MODEL` | `Qwen/Qwen3-235B-A22B` | 情感分析模型（MoE，更快） |
| `USE_MOCK_DATA` | `false` | 设 `true` 时跳过所有外部 API，使用 mock，便于纯前端调试 |
| `TUSHARE_TOKEN` | 空 | 提供则 A 股优先用 Tushare 而非 AKShare |

### 3. 启动后端

```bash
cd stock-agent/backend
pip install -e .
# 或：pip install -r ../../requirements.txt

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动日志会显示三市股票名录的加载情况：

```
[OK] A股 加载 5151 只
[OK] 港股 加载 4951 只
[OK] 美股 加载 11174 只
```

热门股票候选池会在后台异步预热（首次约 30-60s），预热完毕后访问首页秒回。

### 4. 启动前端

```bash
cd stock-agent/frontend
npm install
npm run dev
```

打开 http://localhost:5173/ 即可使用。

### 5. Docker（仅后端）

```bash
cd stock-agent/backend
docker build -t stock-agent-backend .
docker run -p 8000:8000 --env-file ../.env stock-agent-backend
```

## 🔌 API 简介

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/search?q=苹果` | 多路模糊搜索，返回 Top 10 |
| GET | `/api/v1/hot/all` | 三市当日涨幅 Top 8（缓存 5 分钟） |
| POST | `/api/v1/analyze` | 主分析接口，body 形如 `{"symbol":"AAPL","market":"美股"}` |

FastAPI 自动文档：http://127.0.0.1:8000/docs

## 🧪 测试

```bash
cd stock-agent/backend
pytest
```

## 📌 已知限制

- **美股基本面**走 yfinance，受 Yahoo Finance 限流影响时会降级为零值占位（不影响 quote / K 线 / 报告生成）
- **港股 / A 股**接 eastmoney 在部分网络下偶发 `RemoteDisconnected`，已自动降级到 Sina 通道
- **ModelScope** 免费额度下不同模型可用性可能不同，Qwen3 dense 系列（8B/14B/32B）可能需要在 modelscope 控制台单独开通
- 单次 `/analyze` 端到端约 **30-80s**，瓶颈在 LLM 调用，可通过 `USE_MOCK_DATA=true` 跳过

## 📝 License

MIT

## 🙏 致谢

- [Datawhale HelloAgents](https://github.com/datawhalechina/hello-agents)
- [AKShare](https://github.com/akfamily/akshare)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [ModelScope](https://modelscope.cn)
