# Trip Planner Pro — HelloAgents 智能旅行助手 🌍✈️

## 项目信息

- **项目名称**: Trip Planner Pro — HelloAgents 智能旅行助手
- **项目类型**: 生活服务

## 项目简介

AI 驱动的智能旅行规划助手，基于 HelloAgents 框架构建，后端 FastAPI + 前端 Vue 3 + TypeScript。通过多智能体 LLM 编排和高德地图 MCP 协议集成，实现个性化的旅行计划生成。系统支持多智能体协作自动搜索景点、查询天气、推荐酒店并生成完整行程，同时提供 AI 旅游对话和行程管理功能。

## 核心功能

- [x] **AI 智能生成旅行计划** — 基于多智能体流水线自动生成详细的多日旅程，涵盖景点、住宿、交通、餐饮推荐
- [x] **流式 AI 旅游对话** — 基于 SSE 的流式聊天，具备用户画像自动提取、跨会话上下文记忆
- [x] **高德地图深度集成** — 通过 MCP 协议接入高德地图服务，支持 POI 搜索、天气预报、路线规划（公共交通 / 自驾 / 步行 / 混合）
- [x] **出行人群定制** — 支持 7 种出行人群（独自旅行、情侣夫妻、朋友结伴、家庭亲子、公司团建、老年旅行、研学旅行）个性化行程定制
- [x] **用户认证系统** — 双 JWT + HttpOnly Cookie + Redis 持久化 + RSA 加密密码传输
- [x] **历史行程管理** — 历史行程 CRUD，支持 PDF/图片导出

## 🏗️ 技术栈

### 后端
- **框架**: HelloAgents (SimpleAgent) + FastAPI
- **数据库**: 原生 SQLite（WAL 模式，无 ORM）
- **缓存**: Redis（Refresh Token 持久化）
- **MCP 工具**: amap-mcp-server（高德地图服务）
- **LLM**: 支持多种 LLM 提供商（OpenAI、DeepSeek 等）
- **认证**: 双 JWT（HS256）、HttpOnly Cookie、RSA-OAEP 密码加密

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Ant Design Vue 4
- **地图服务**: 高德地图 JavaScript API
- **HTTP 客户端**: Axios（withCredentials 自动携带 Cookie）

## 技术亮点

- **多智能体流水线架构** — 4 个顺序/并行步骤（景点搜索 → 天气 → 酒店 → 规划），采用 `ThreadPoolExecutor` 并行执行无依赖任务，显著提升生成效率
- **MCP 协议集成** — 通过 JSON-RPC 子进程方式接入高德地图 MCP 服务，Agent 自动调用地图工具获取实时数据
- **用户画像系统** — 异步提取用户意图和偏好，跨会话持久化缓存，按需加载注入上下文
- **双 JWT 认证** — Access Token（30 分钟）+ Refresh Token（7 天），HttpOnly Cookie 传递 + Redis 持久化，支持轮换和撤销
- **SSE 流式输出** — AI 对话采用 Server-Sent Events 实时推送 Token，前端使用 `ReadableStream.getReader()` 解析流数据
- **模块级单例模式** — 每个服务暴露 `get_*()` 函数惰性初始化并缓存全局实例，无依赖注入框架

## 📁 项目结构

```
helloagents-trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent 实现
│   │   │   ├── trip_planner_agent.py  # 多智能体旅行规划系统
│   │   │   ├── mcp_tool.py           # MCP 工具封装
│   │   │   └── profile_extraction_agent.py  # 用户画像提取
│   │   ├── api/               # FastAPI 路由
│   │   │   ├── main.py        # 应用入口，CORS、中间件、路由注册
│   │   │   └── routes/
│   │   │       ├── auth.py    # 用户认证
│   │   │       ├── trip.py    # 旅行计划生成
│   │   │       ├── chat.py    # AI 旅游对话（SSE）
│   │   │       ├── history.py # 历史行程
│   │   │       ├── map.py     # 地图服务
│   │   │       └── poi.py     # POI 详情
│   │   ├── services/          # 服务层
│   │   │   ├── amap_service.py       # 高德地图 HTTP 封装
│   │   │   ├── llm_service.py        # LLM 客户端
│   │   │   ├── travel_chat_service.py # AI 聊天服务
│   │   │   ├── user_profile_service.py # 用户画像管理
│   │   │   └── unsplash_service.py   # 图片服务
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic 数据模型
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # SQLite 数据库
│   │   ├── jwt_utils.py       # JWT 工具
│   │   ├── redis_service.py   # Redis 客户端
│   │   ├── rsa_service.py     # RSA 加解密
│   │   └── user_context.py    # 用户上下文中间件
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/             # 页面视图
│   │   │   ├── Home.vue       # 旅行表单首页
│   │   │   ├── Result.vue     # 行程展示（地图、导出）
│   │   │   ├── Login.vue      # 登录/注册
│   │   │   ├── History.vue    # 历史行程列表
│   │   │   └── Chat.vue       # AI 旅游对话
│   │   ├── components/        # 公共组件
│   │   ├── services/          # API 服务（Axios）
│   │   ├── types/             # TypeScript 类型
│   │   └── App.vue
│   ├── package.json
│   ├── .env.example
│   └── vite.config.ts
└── README.md
```

## 🚀 快速开始

### 前提条件

- Python 3.10+
- Node.js 16+
- 高德地图 API 密钥（Web 服务 API 和 Web 端 JS API）
- LLM API 密钥（OpenAI / DeepSeek 等）
- Redis 服务（可选，用于 Refresh Token 持久化）

### 后端安装

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填入 API 密钥
python run.py          # 启动 uvicorn，端口 8000
```

### 前端安装

```bash
cd frontend
npm install
cp .env.example .env  # 填入高德地图密钥
npm run dev           # Vite 开发服务器，端口 5173
npm run build         # 生产构建
```

### HTTPS（可选）

```bash
cd backend && openssl req -x509 -newkey rsa:2048 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "//CN=localhost"
# 在 backend/.env 中设置 SSL_ENABLED=true，重启后端
# 前端代理目标已指向 https://localhost:8000
```

## 📝 使用指南

1. **注册/登录** — 在登录页面注册账号（密码经过 RSA 加密传输）
2. **填写旅行信息** — 目的地城市、旅行日期、交通方式、住宿偏好、出行人群、旅行风格标签
3. **生成旅行计划** — 点击"生成旅行计划"，系统将：
   - 并行搜索景点、查询天气、推荐酒店
   - 整合信息生成完整行程
   - 调用高德地图 API 获取真实交通路线数据
4. **查看结果** — 每日详细行程、景点信息与地图标记、交通路线规划、天气预报、餐饮推荐、预算汇总
5. **AI 旅游对话** — 针对行程进行智能问答，系统自动提取用户偏好

## 🔧 核心实现

### 多智能体流水线

```python
# 4 个 Agent 协同工作
attraction_agent.run()   # [MCP] 搜索景点 POI
weather_agent.run()      # [MCP] 查询天气
hotel_agent.run()        # [MCP] 搜索酒店
planner_agent.run()      # [LLM 仅] 整合生成行程
_enrich_with_real_routes()  # [HTTP] 获取真实交通路线
```

其中景点搜索、天气查询、酒店推荐通过 `ThreadPoolExecutor` **并行执行**，行程规划 Agent 在并行结果上顺序执行。

### MCP 工具调用

Agent 自动调用高德地图 MCP 工具获取实时数据：

- `maps_text_search` — 景点 / 酒店 POI 搜索
- `maps_weather` — 天气查询
- `maps_direction_*` — 步行 / 驾车 / 公共交通路线规划

### AI 聊天 SSE 流

```
POST /api/chat/sessions/{id}/messages
  → 保存用户消息 → 加载用户画像 → 注入系统提示词
  → SSE 流式返回 Token (type: token/error/done)
  → 保存 AI 回复 → 异步提取用户画像
```

## 📄 API 文档

启动后端后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

6 组路由（前缀 `/api`）：

| 路由 | 功能 |
|------|------|
| `POST /api/auth/*` | 登录/注册/刷新 Token |
| `POST /api/trip/plan` | 生成旅行计划 |
| `POST /api/chat/sessions/{id}/messages` | AI 对话（SSE 流式） |
| `GET /api/history/*` | 历史行程 CRUD |
| `GET /api/map/*` | POI 搜索、天气、路线规划 |
| `GET /api/poi/*` | POI 详情和图片 |

## 数据流：旅行计划生成

```
请求 → POST /api/trip/plan
  → MultiAgentTripPlanner.plan_trip()
    ┌─ attraction_agent.run()    [MCP: maps_text_search]  ─┐
    ├─ weather_agent.run()       [MCP: maps_weather]      ├─ 并行执行
    └─ hotel_agent.run()         [MCP: maps_text_search]  ┘
    → planner_agent.run()        [仅 LLM，无工具]
    → _enrich_with_real_routes() [HTTP 高德 API]
  → TripPlanResponse
```

## 配置说明

后端 `.env` 主要配置项：

- `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL` — LLM 提供商
- `AMAP_API_KEY` — 高德地图 API 密钥（必填）
- `REDIS_HOST`/`PORT`/`PASSWORD`/`DB` — Redis 配置
- `JWT_SECRET` — 首次运行自动生成
- `SSL_ENABLED`/`SSL_CERTFILE`/`SSL_KEYFILE` — 可选 HTTPS

前端 `.env` 主要配置项：

- `VITE_API_BASE_URL` — 后端地址（默认 `https://localhost:8000`）
- `VITE_AMAP_WEB_KEY`/`VITE_AMAP_WEB_JS_KEY` — 高德 JS API 密钥

## 自检清单

- [x] 代码能够正常运行
- [x] README 文档完整
- [x] requirements.txt 完整
- [x] 有清晰的使用示例
- [x] 代码有适当的注释

## 🤝 贡献指南

欢迎提交 Pull Request 或 Issue！

## 📜 开源协议

CC BY-NC-SA 4.0

## 🙏 致谢

- [HelloAgents](https://github.com/datawhalechina/Hello-Agents) — 智能体教程
- [HelloAgents 框架](https://github.com/jjyaoao/HelloAgents) — 智能体框架
- [高德地图开放平台](https://lbs.amap.com/) — 地图服务
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) — 高德地图 MCP 服务器

---

**Trip Planner Pro** — 让旅行计划变得简单而智能 🌈
