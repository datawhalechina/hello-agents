# Trip Planner Pro — HelloAgents智能旅行助手

## 项目信息

- **项目名称**: Trip Planner Pro — HelloAgents智能旅行助手
- **作者**: @shengyuantong
- **项目类型**: 生活服务

## 项目简介

AI 驱动的智能旅行规划助手，后端 FastAPI + 前端 Vue 3，通过多智能体 LLM 编排和高德地图 MCP 协议集成，实现个性化的旅行计划生成。系统支持多智能体协作自动搜索景点、查询天气、推荐酒店并生成完整行程，同时提供 AI 旅游对话和行程管理功能。

## 核心功能

- [x] **AI 智能生成旅行计划** — 用户输入城市、日期、偏好等基本信息，系统自动调用多智能体流水线（景点搜索 → 天气查询 → 酒店推荐 → 行程规划 Agent）生成详尽的 PDF/图片可导出行程
- [x] **流式 AI 旅游对话** — 基于 SSE 的流式聊天，具备用户画像自动提取、跨会话上下文记忆，提供智能旅行问答
- [x] **用户认证系统** — 双 JWT（HttpOnly Cookie）+ Redis Refresh Token 持久化 + RSA 加密密码传输，支持无 Cookie 设备兼容
- [x] **高德地图深度集成** — 通过 MCP 协议接入高德地图服务，支持 POI 搜索、天气查询、多种交通方式路线规划（公共交通 / 自驾 / 步行 / 混合）
- [x] **出行人群定制** — 支持 7 种出行人群（独自旅行、情侣夫妻、朋友结伴、家庭亲子、公司团建、老年旅行、研学旅行）个性化行程定制
- [x] **历史行程管理** — 历史行程 CRUD、PDF / 图片导出

## 技术亮点

- **多智能体流水线架构** — 4 个顺序/并行步骤（景点搜索 → 天气 → 酒店 → 规划），采用 `ThreadPoolExecutor` 并行执行无依赖任务，显著提升生成效率
- **MCP 协议集成** — 通过 JSON-RPC 子进程方式接入高德地图 MCP 服务，每次批量调用独立启动子进程，实现 Agent 自动工具调用
- **用户画像系统** — 异步提取用户意图和偏好，跨会话持久化缓存，首次对话时按需加载，作为上下文注入提示词
- **双 JWT 认证** — Access Token（30 分钟）+ Refresh Token（7 天），均通过 HttpOnly Cookie 传递，Refresh Token 存储在 Redis 中支持轮换和撤销
- **RSA 加密密码传输** — 前端使用 Web Crypto API 进行 RSA-OAEP 加密，后端使用 `cryptography` 库解密，保障密码安全
- **SSE 流式输出** — AI 对话采用 Server-Sent Events 实时推送 Token，前端使用 `ReadableStream.getReader()` 解析流数据
- **HTTPS 支持** — 内建自签名证书生成脚本，支持全站 HTTPS 访问
- **无 ORM 数据库** — 使用原生 SQLite + WAL 模式，无 ORM 依赖，轻量高效

## 演示效果

（待补充截图或 GIF）

## 自检清单

- [x] 代码能够正常运行
- [x] README 文档完整
- [x] requirements.txt 完整
- [x] 有清晰的使用示例
- [x] 代码有适当的注释

## 其他说明

- **项目结构**：前后端分离，`backend/` 为 FastAPI 后端，`frontend/` 为 Vue 3 + Vite 前端
- **框架依赖**：基于自定义 `hello-agents==1.0.2` 框架（提供 `SimpleAgent`、`HelloAgentsLLM` 和 `Tool` 基类）
- **6 组 API 路由**：`auth`（认证）、`trip`（旅行规划）、`chat`（AI 对话）、`history`（历史行程）、`map`（地图服务）、`poi`（POI 详情）
- **模块级单例模式**：每个服务暴露 `get_*()` 函数惰性初始化并缓存全局实例，无依赖注入框架
