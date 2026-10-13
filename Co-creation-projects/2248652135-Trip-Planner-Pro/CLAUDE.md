# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目简介

AI 驱动的智能旅行规划助手，后端 FastAPI，前端 Vue 3 + Vite，通过多智能体 LLM 编排和高德地图 MCP 协议集成实现行程规划。

## 常用命令

### 后端
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 填入 API 密钥
python run.py          # 启动 uvicorn，端口 8000
```

### 前端
```bash
cd frontend
npm install
cp .env.example .env
npm run dev    # Vite 开发服务器，端口 5173
npm run build  # 生产构建（vue-tsc + vite）
```

### HTTPS（可选）
```bash
# 1. 生成自签名证书
cd backend && openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "//CN=localhost"
# 2. 在 backend/.env 中设置 SSL_ENABLED=true
# 3. 重启后端 (python run.py)
# 4. 前端代理目标和环境变量已指向 https://localhost:8000
```

## 架构说明

### 后端（`backend/`）

**FastAPI 应用** 在 `app/api/main.py` 中创建，配置了 CORS，注册了 6 组路由（前缀 `/api`）：
- `auth` — JWT Cookie 认证（HS256 access/refresh token），RSA 加密密码传输
- `trip` — 多智能体系统生成旅行计划
- `chat` — AI 旅游对话，SSE 流式输出
- `history` — 历史行程 CRUD
- `map` — POI 搜索、天气、路线规划
- `poi` — POI 详情和图片

**关键设计模式：**
- **模块级单例**：每个服务暴露 `get_*()` 函数（如 `get_trip_planner_agent()`、`get_amap_service()`、`get_llm()`），惰性初始化并缓存全局实例。无依赖注入框架。
- **MCP 子进程**：`amap-mcp-server` 以子进程（`uvx`）方式运行。`agents/mcp_tool.py` 中的 `MCPTool` 通过 JSON-RPC 协议在 stdin/stdout 上通信，每次批量调用都启动新进程。每次调用序列在同一子进程内发送 `initialize` + `tools/call`（或 `tools/list`）。
- **多智能体流水线**（`agents/trip_planner_agent.py`）：4 个顺序步骤——景点搜索 → 天气 → 酒店 → 规划 Agent，每个都是 `SimpleAgent`，共享一个 `MCPTool`。最后一步通过 HTTP 方式直接调用高德 API 获取真实路线数据（绕过 MCP 以提高性能）。
- **认证**：双 JWT（access 30 分钟 + refresh 7 天），均通过 HttpOnly Cookie 传递。Refresh Token 存储在 Redis（jti → user_id 映射），刷新时轮换。不使用 `Authorization` 请求头。
- **密码加密**：前端使用 Web Crypto API 进行 RSA-OAEP 加密，后端使用 `cryptography` 库解密。
- **数据库**：原生 SQLite（`sqlite3` 模块），WAL 模式，无 ORM。表：users、auth_tokens、trip_history、chat_sessions、chat_messages。

### 前端（`frontend/`）

**Vue 3 + TypeScript + Vite + Ant Design Vue 4**，共 5 个视图：
- `Home.vue` — 旅行表单（城市、日期、偏好）
- `Result.vue` — 行程展示（地图、PDF/图片导出）
- `Login.vue` — 登录/注册（RSA 加密密码）
- `History.vue` — 历史行程列表
- `Chat.vue` — AI 旅游对话（SSE 流式聊天）

**API 层**：`services/api.ts` — Axios 客户端，`withCredentials: true`，401 自动刷新 Token（含重试锁）。使用原始 `fetch()` 的视图统一从环境变量 `VITE_API_BASE_URL` 读取后端地址。

### 数据流：旅行计划生成

```
请求 → POST /api/trip/plan
  → MultiAgentTripPlanner.plan_trip()
    → attraction_agent.run()        [MCP: maps_text_search]
    → weather_agent.run()           [MCP: maps_weather]
    → hotel_agent.run()             [MCP: maps_text_search]
    → planner_agent.run()           [仅 LLM，无工具]
    → _enrich_with_real_routes()    [HTTP 高德 API: 路线规划]
  → TripPlanResponse
```

### AI 聊天 SSE 流

```
POST /api/chat/sessions/{id}/messages
  → 保存用户消息到数据库
  → 加载用户画像上下文 → 注入系统提示词
  → chat_stream() → 产出 SSE 事件 (type: token/error/done)
  → 保存 AI 回复到数据库
  → 异步从消息中提取用户画像
```

前端使用 `ReadableStream.getReader()` 读取流，解析 SSE 的 `data:` 行。

## 配置说明

后端 `.env`：
- `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL` — LLM 提供商
- `AMAP_API_KEY` — 高德地图 API 密钥（必填）
- `REDIS_HOST`/`PORT`/`PASSWORD`/`DB` — Redis，用于 Refresh Token 持久化
- `SSL_ENABLED`/`SSL_CERTFILE`/`SSL_KEYFILE` — 可选 HTTPS
- `CORS_ORIGINS` — 逗号分隔的允许来源
- `JWT_SECRET` — 首次运行自动生成（如未设置）

前端 `.env`：
- `VITE_API_BASE_URL` — 后端地址（默认 `https://localhost:8000`）
- `VITE_AMAP_WEB_KEY`/`VITE_AMAP_WEB_JS_KEY` — 高德 JS API 密钥

## 重要依赖

- **hello-agents==1.0.2** — 自定义框架，从 `D:\learn-agent\hello-agents-1.0.2` 安装（`run.py` 中通过 `sys.path.append` 引入）。提供 `SimpleAgent`、`HelloAgentsLLM` 和 `Tool` 基类。
- **amap-mcp-server** — 高德地图 MCP 服务器，通过 `uvx` 子进程运行。提供：`maps_text_search`、`maps_weather`、`maps_direction_*`、`maps_geo`、`maps_search_detail`。
- **ant-design-vue 4** — UI 组件库。
- **html2canvas + jspdf** — 导出行程为 PDF/图片。
