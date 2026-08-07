# Intelligent Stock Analysis Assistant

An A-share investment analysis tool built on the **HelloAgents multi-agent collaboration framework**, integrating market data, financial analysis, news sentiment, intelligent stock screening, simulated trading, and more to provide data-driven investment decision support.

> ⚠️ **Disclaimer**: All analysis results from this tool are for reference only and **do not constitute investment advice**. Investing involves risk; exercise caution when entering the market.

---

## Features

| Module | Feature | Status |
|--------|---------|:------:|
| 📊 **Market Quotes** | Real-time individual stock quotes, index quotes, sector quotes | ✅ |
| 📈 **Financial Analysis** | Financial indicators, company profile (description list layout), top 10 shareholders (multi-format table parsing) | ✅ |
| 📉 **Stock Analysis UX** | Prioritize loading quotes and charts; finance/profile/shareholders load asynchronously | ✅ |
| 🗣️ **AI Sentiment Analysis** | AI auto-searches news and analyzes market sentiment, streaming output | ✅ |
| 📉 **AI Data Analysis** | AI auto-queries market/financial data and generates analysis reports, streaming output | ✅ |
| 💬 **AI Chat Assistant** | Coordinator Agent parses user intent, auto-dispatches sub-agents, streaming dialogue output | ✅ |
| 📰 **News & Info** | Financial news search, hot headlines browsing | ✅ |
| 🔍 **Smart Stock Screener** | Multi-criteria combined screening (market + financial dual dimensions) | ✅ |
| 🏛️ **Buffett Evaluation** | Value investing framework, ReflectionAgent self-reflection optimized streaming report generation with Markdown download | ✅ |
| ⭐ **Watchlist** | MX watchlist add/delete/query; "Add to Watchlist" on stock analysis page & screener results; removal requires confirmation | ✅ |
| 🏠 **Dashboard** | Three-thread parallel warmup (indices/watchlist/hotspots), watchlist uses API-returned price data directly | ✅ |
| 💰 **Simulated Trading** | Simulated buy/sell/cancel orders, position management, profit curve; order/cancel confirmation dialogs to prevent misoperation | ✅ |
| 📝 **History Records** | AI Sentiment / AI Data / Buffett / AI Chat four analysis history types stored by day, with view/delete support | ✅ |
| 💾 **File Cache** | Each stock's data saved as an independent JSON file, no refresh within the day, supports grep keyword search | ✅ |
| 🧠 **Memory System** | Daily first-start date tracking, daily cutover re-fetches dashboard snapshot; persisted under `data/memory/` (JSON, not HelloAgents MemoryManager); watchlist count changes trigger refresh **when prior watchlist records exist** (frontend still requests watchlist API in real-time) | ✅ |
| ⚙️ **Preferences** | Personalized investment style, risk preference, and sector preference settings | ✅ |
| 🐳 **Docker Deployment** | One-click containerized deployment, frontend/backend separation | ✅ |
| 📦 **exe Packaging** | PyInstaller packaging as standalone exe, no Python/Node.js installation required | ✅ |

---

## Highlights

- **Multi-Agent Collaboration**: Uses **Reflection** (Buffett evaluation), **ReAct** (sentiment/data/general advisor), and **coordinator routing**; stock analysis tabs run streaming agents independently; the AI chat assistant dispatches sub-agents on demand. Stock screening, watchlist, and simulated trading use backend services **directly against `skills/`**, not separate agents
- **AI Chat Assistant**: Single LLM routing decision (`data` / `sentiment` / `advisor` combinations), sub-agents run **non-streaming**, then coordinator consolidates; single-dimension pushes results directly, multi-dimension uses LLM **streaming** to generate a comprehensive reply (with length and word count limits, see `agents/coordinator_agent.py`, `agents/text_truncation.py`)
- **Streaming AI Analysis**: Sentiment analysis, data analysis, and Buffett evaluation all support NDJSON streaming output with real-time generation display
- **Buffett Value Investing Framework**: Full value investing analysis system integrated (8 reference documents), ReflectionAgent self-reflection optimizes evaluation reports
- **File Cache System**: All data per stock persisted to local files, prioritize cache reads over API calls, supports grep-style keyword search
- **Personalized Investment Analysis**: User preference storage (risk preference, investment style, sector preference), persisted via `preference_service` and exposed through `/api/v1/preferences`
- **Full-Stack Integration**: Vue3 frontend + FastAPI backend + HelloAgents agents + East Money MX data, end-to-end self-contained
- **Operational Safety**: Dangerous operations like simulated buy/sell and watchlist removal require confirmation dialogs

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Vue3 + Element Plus + ECharts | 3.x / 2.x / 5.x |
| Backend | FastAPI + Uvicorn | 0.110+ |
| Database | SQLite (SQLAlchemy + aiosqlite) | — |
| Agents | HelloAgents Optimized | 0.2.9 |
| LLM | DeepSeek / OpenAI-compatible API | — |
| Financial Data | East Money MX API | — |

---

## Quick Start

### Prerequisites

- Python ≥ 3.10
- Node.js ≥ 18
- Docker ≥ 24 (optional, for production deployment)

### Environment Variables

Copy `.env.example` to `.env` and fill in your keys. **For local dev, keep `BACKEND_PORT=8000`** (must match `frontend/vite.config.js` proxy). For exe builds, use `5174` if needed. Commonly used items are as follows (see `.env.example` comments for full details):

```env
# LLM (compatible with HelloAgents)
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
# Optional: single request timeout (seconds); backend merges with a longer floor value
# to prevent premature disconnection during ReAct/chat multi-turn
# LLM_TIMEOUT=180

# Buffett evaluation: optional reflection rounds (see BUFFETT_MAX_REFLECTIONS in .env.example)

# East Money MX financial data
MX_APIKEY=your-mx-apikey
# Optional: MX_API_URL, MX_CACHE_TTL_SECONDS, local replay MX_REPLAY_FIXTURES, etc.

# Service port: dev mode defaults to 8000 when not set; PyInstaller exe defaults to 5174 when not overridden
# (consistent with run_exe.py prompt)
# If modifying BACKEND_PORT, also update the /api proxy target in frontend/vite.config.js
```

> 💡 DeepSeek API: https://platform.deepseek.com  
> 💡 MX API: https://dl.dfcfs.com/m/itc4  

### Local Development

**Backend**:

```bash
# Install dependencies (equivalent: also run pip install -r requirements.txt from repo root)
pip install -r backend/requirements.txt

# Start service (from project root)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/docs

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Frontend UI: http://localhost:5173 (dev mode auto-proxies /api to backend port 8000)

### Docker Deployment

```bash
docker compose up -d
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/docs

For detailed deployment instructions, see [DEPLOY.md](./DEPLOY.md)

### Standalone exe Packaging

Package the frontend and backend into a single `.exe` file, no Python/Node.js installation required to run.

#### Requirements

| Component     | Purpose           | Packaging Only? |
| ------------- | ----------------- |:---------------:|
| Python 3.10+  | PyInstaller build | Yes             |
| Node.js 18+   | Frontend build    | Yes             |
| PyInstaller   | Python → exe      | Yes             |

#### One-Click Build

```bash
# 1. Install packaging dependencies
pip install pyinstaller

# 2. Run the build script (from project root)
python scripts/build_exe.py
```

### Screenshots

Due to the large amount of data loaded, it's best to wait for data warmup before entering the interface. Also, due to East Money restrictions, **do not use a VPN/proxy**, or it will fail.

> UI screenshots are not shipped with the repo. Capture them locally after startup, or place them under `outputs/screenshots/` for documentation.

---

## Project Structure

```
intelligent-stock-analyzer/
├── README.md
├── README_EN.md
├── requirements.txt                # Root aggregated deps (points to backend/requirements.txt)
├── run_exe.py                      # exe runtime entry
├── scripts/
│   └── build_exe.py                # PyInstaller build script
├── data/                           # Data directory (created at runtime)
│   ├── stock_cache/                #   File cache (independent JSON per stock)
│   └── memory/                     #   Memory system state (dashboard_state.json)
├── outputs/                        # Optional: local reports/screenshots
├── backend/                        # 🖥️ Backend FastAPI
│   ├── app/
│   │   ├── main.py                 #   App entry + lifecycle
│   │   ├── config.py               #   Configuration management
│   │   ├── api/                    #   API route modules
│   │   │   ├── chat.py             #     AI chat assistant streaming endpoint
│   │   │   ├── sentiment.py        #     AI sentiment streaming (agreed path)
│   │   │   ├── data_analysis.py    #     AI data analysis streaming (agreed path)
│   │   │   ├── agent_api.py        #     Sentiment/data streaming impl + /agent compat path
│   │   │   ├── history.py          #     Analysis history CRUD
│   │   │   ├── system_browser.py   #     exe/desktop: backend opens system browser for external links
│   │   │   ├── cache_api.py        #     File cache management / grep search
│   │   │   └── ...                 #     market / financial / news / screener etc.
│   │   ├── services/               #   Business logic layer
│   │   │   ├── chat_service.py     #     Chat assistant dispatch (coordinator streaming)
│   │   │   ├── memory_service.py   #     Memory system (daily cutover + dashboard warmup etc.)
│   │   │   ├── stock_file_cache.py #     File cache (grep search support)
│   │   │   ├── history_service.py  #     History CRUD
│   │   │   ├── screener_service.py #     Stock screening (direct skills/mx-xuangu)
│   │   │   ├── watchlist_service.py#     Watchlist (direct skills/mx-zixuan)
│   │   │   ├── simulation_service.py#    Simulated trading (direct skills/mx-moni)
│   │   │   ├── preference_service.py#    User preferences CRUD / context
│   │   │   └── ...                 #     market / news / buffett etc.
│   │   ├── models/                 #   Data models
│   │   │   ├── report.py           #     AnalysisReport
│   │   │   ├── history_models.py   #     Analysis history ORM (SQLite)
│   │   │   ├── history.py          #     Compat re-export AnalysisHistory
│   │   │   ├── memory_models.py    #     MemorySnapshot and other memory data structures
│   │   │   └── preference.py       #     UserPreference
│   │   ├── middleware/             #   Middleware placeholder (skeleton, not registered in main)
│   │   └── utils/                  #   Utilities
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                       # 🎨 Frontend Vue3
│   ├── src/
│   │   ├── views/                  #   Page views
│   │   │   ├── Dashboard.vue       #     Dashboard (watchlist direct price display)
│   │   │   ├── StockAnalysis.vue   #     Stock analysis (6 tabs)
│   │   │   ├── StockScreener.vue   #     Smart stock screener
│   │   │   ├── NewsCenter.vue      #     News center
│   │   │   └── Simulation.vue      #     Simulated trading (confirmation dialogs)
│   │   ├── components/             #   Shared components
│   │   │   ├── StreamOutput.vue    #     Streaming output generic component
│   │   │   ├── AIAnalysisPanel.vue #     AI analysis panel
│   │   │   ├── ChatAssistant.vue   #     AI chat assistant
│   │   │   ├── HistoryDrawer.vue   #     History drawer
│   │   │   └── NewsDetailDrawer.vue#     News detail
│   │   ├── api/                    #   Axios wrapper
│   │   ├── router/                 #   Vue Router
│   │   └── store/                  #   Pinia state management
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── agents/                         # 🤖 Agent layer (AI analysis & chat only)
│   ├── agent_system.py             #   Unified agent management & streaming dispatch
│   ├── coordinator_agent.py        #   AI chat assistant (routing LLM + sequential sub-agent calls + integrated streaming)
│   ├── text_truncation.py          #   Coordinator output natural boundary truncation
│   ├── advisor_agent.py            #   Buffett evaluation agent (Reflection + streaming)
│   ├── general_advisor_agent.py    #   General investment advisor agent (ReAct)
│   ├── sentiment_agent.py          #   Sentiment analysis agent (ReAct + streaming)
│   ├── data_analysis_agent.py      #   Data analysis agent (ReAct + streaming)
│   ├── tests/                      #   Agent-layer unit tests
│   └── tools/                      #   ReAct tool wrappers (for agents above)
│       ├── mx_data_tool.py         #     Market data → skills/金融数据
│       └── mx_search_tool.py       #     News search → skills/资讯搜索
│
├── HelloAgents Optimized/          # 🧩 Multi-agent framework (StockSage slim build)
│   └── hello_agents/
│       ├── core/                   #   LLM, Config, Agent base, ConversationManager, etc.
│       └── agents/                 #   ReActAgent, ReflectionAgent (used by this app)
│
├── skills/                         # 🔧 East Money MX skills (business API layer)
│   ├── 金融数据/mx-data
│   ├── 资讯搜索/mx-search
│   ├── 智能选股/mx-xuangu
│   ├── 自选股管理/mx-zixuan
│   ├── 模拟组合管理/mx-moni
│   └── 巴菲特投资思维/             #   Value investing reference docs
│
├── docker-compose.yml
├── DEPLOY.md
└── .env.example
```

---

## API Route Overview

| Route Group | Prefix | Description |
|-------------|--------|-------------|
| System | `/api/v1/system` | `GET /health`, `GET /config` (registered in `main.py`); `POST /open-external-url` registered by `system_browser.py` under the same prefix, for exe scenarios to open http(s) links in the native browser |
| Market | `/api/v1/market` | Individual stock quotes, indices, sectors |
| Financial | `/api/v1/financial` | Financial indicators, company profile, shareholders |
| Analysis | `/api/v1/analysis` | In-depth stock report `POST /report/{code}`, `GET /report/{report_id}`, list `GET /reports` |
| News | `/api/v1/news` | News search, sentiment analysis, hot topics |
| Screener | `/api/v1/screener` | Conditional screening, filter criteria |
| Watchlist | `/api/v1/watchlist` | Watchlist add/delete/query |
| Simulation | `/api/v1/simulation` | Simulated trading (buy/sell/cancel/positions) |
| Buffett | `/api/v1/buffett` | Buffett evaluation (Reflection / advisor streaming, history type `buffett`) |
| Preferences | `/api/v1/preferences` | User investment preferences CRUD |
| **Chat** | `/api/v1/chat` | **AI chat assistant** NDJSON streaming `POST /stream` |
| **Sentiment** | `/api/v1/sentiment` | **AI sentiment** `POST /analyze/stream` (agreed path) |
| **Data analysis** | `/api/v1/data-analysis` | **AI data analysis** `POST /analyze/stream` (agreed path) |
| **Agent (compat)** | `/api/v1/agent` | Semantically same as above: `POST /sentiment/stream`, `POST /data-analysis/stream` |
| **History** | `/api/v1/history` | Analysis history list/detail/delete/clear; `type` includes `sentiment` / `data_analysis` / `buffett` / `chat` |
| **Cache** | `/api/v1/cache` | File cache grep / stats / clear |

> Full Swagger docs: dev default http://localhost:8000/docs (port per `BACKEND_PORT` in `.env`)

---

## Agent Collaboration Flow

### AI Chat Assistant Flow

```
User chat message
    │
    ▼
Coordinator (routing LLM, single-line keyword)
    │ none → general conversation (coordinator LLM streaming reply, or stock context guidance)
    │ data / sentiment / advisor or combinations
    ▼
Sub-Agents run sequentially (non-streaming, with word limit)
    ├── data → run_data_analysis
    ├── sentiment → run_sentiment
    └── advisor → inject existing data/sentiment summaries into advisor prompt → run_advisor
    │
    ▼
User-facing streaming output
    ├── single sub-agent only → directly push that result (truncated to limit)
    └── multiple agents → coordinator LLM stream_invoke to integrate into structured response
```

### Buffett Evaluation Flow

```
User clicks "Generate Buffett Evaluation Report"
    │
    ▼
advisor_agent (ReflectionAgent)
    │ collects market/financial/sentiment data
    ├── initial analysis → moat / management / margin of safety
    ├── self-reflection → data accuracy / logical consistency
    └── iterative optimization → refine report
    │
    ▼
Streaming final evaluation report + auto-save history
```

### Business API vs. Agents

| Capability | Implementation |
|------------|----------------|
| AI sentiment / data analysis / chat / Buffett evaluation | `agents/*` + HelloAgents (ReAct / Reflection / coordinator) |
| Stock screening / watchlist / simulated trading / market & news queries | `backend/app/services/*` → `skills/*` (MX API) |
| User preferences | `preference_service` + `/api/v1/preferences` |

---

## Stock Analysis Page Structure

When entering individual stock analysis (`/analysis` or `/analysis/:code`, `:code` optional), there are **6 tabs**:

| Tab | Content | Notes |
|-----|---------|-------|
| 📊 Market Charts | ECharts candlestick + market details | Priority loading |
| 📈 Financial Data | Financial indicator cards + company profile + top 10 shareholders | Async loading |
| 🗣️ AI Sentiment | AI auto-searches news for market sentiment analysis | Streaming output |
| 📉 AI Data Analysis | AI queries market/financial data to generate reports | Streaming output |
| 🧠 Buffett Evaluation | ReflectionAgent self-reflection optimized evaluation | Streaming output |
| 💬 AI Chat Assistant | Free-form conversation, auto-dispatches sub-agents | Streaming output |

Each analysis tab supports viewing history records and downloading reports.

---

## File Cache System

All stock data is automatically persisted to the `data/stock_cache/{stock_code}/` directory:

```
data/stock_cache/
  _index.json           # Master index
  600519/
    quote.json          # Market data
    financial.json      # Financial indicators
    profile.json        # Company profile
    holders.json        # Top 10 shareholders
    sentiment.json      # Sentiment analysis
    news.json           # Related news (when cached)
```

- Same-day cache returns directly with no hourly limit; cross-day data expires after 24h
- API is called only on cache miss, and results are automatically written back
- Supports `GET /api/v1/cache/search?keyword=Kweichow Moutai` grep-style keyword search
- Cache persists across service restarts

---

## Reserved Config (Not Wired Yet)

**Redis** and **JWT** variables in `.env.example` are read by `config.py` but **not used** in the current release (caching uses in-process MX TTL + file cache; APIs have no login). See Roadmap below.

## Roadmap

- [ ] Add technical indicator analysis (MACD, KDJ, RSI, etc.)
- [ ] Implement user authentication system (JWT Token; env vars reserved)
- [ ] Add portfolio optimization algorithms (Markowitz model)
- [ ] Add A-share trading calendar and holiday detection
- [ ] Add strategy backtesting engine
- [ ] Add full-text search for history records

---

## Contributing

Issues and Pull Requests are welcome!

### Development Workflow

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "feat: feature description"`
4. Push to branch: `git push origin feature/your-feature`
5. Create a Pull Request

### Commit Conventions

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation update |
| `style` | Code formatting (no logic change) |
| `refactor` | Code refactoring |
| `test` | Test-related |
| `chore` | Miscellaneous (e.g., dependency updates) |

### PR Checklist

- [x] Code runs normally without errors
- [x] Related documentation updated
- [x] Clear usage examples (if applicable)
- [x] Code has appropriate comments
- [x] Common exceptions are handled

---

## License

MIT License

---

## Author

```
- GitHub: [@lcyting](https://github.com/lcyting)
- Email: lcy154745@163.com
```

---

## Acknowledgments

- Thanks to [Hello-Agents](https://github.com/datawhalechina/hello-agents) for the multi-agent framework
- Thanks to [Datawhale](https://www.datawhale.cn) open-source learning community
- Thanks to [agi-queen](https://github.com/agi-now/buffett-skills/commits?author=agi-queen) for the open-source bft-skills
- Thanks to East Money MX API for financial data services
- Thanks to all GitHub open-source contributors
