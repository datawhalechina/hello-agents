# 智能股票分析助手 — 部署文档 (DEPLOY.md)

> **版本**: v0.1.0  
> **日期**: 2026-05-09  
> **适用**: 生产环境 / 开发环境部署

---

## 目录

1. [环境要求](#1-环境要求)
2. [本地开发部署](#2-本地开发部署)
3. [Docker 容器化部署](#3-docker-容器化部署)
4. [exe 独立打包部署](#4-exe-独立打包部署)
5. [配置说明](#5-配置说明)
6. [健康检查](#6-健康检查)
7. [常见问题](#7-常见问题)

---

## 1. 环境要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.10+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| Docker | 24+ | 容器化部署（可选） |
| Docker Compose | 2.0+ | 服务编排（可选） |
| Git | 2.0+ | 版本控制 |

### 外部服务依赖

| 服务 | 用途 | 必需？ |
|------|------|--------|
| DeepSeek API | LLM 大模型推理 | 是（智能体功能） |
| 东方财富妙想 API | 金融数据获取 | 是（行情/财务/资讯） |

---

## 2. 本地开发部署

### 2.1 克隆项目

```bash
git clone <your-repo-url>
cd 智能股票分析器
```

### 2.2 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY、MX_APIKEY
# 本地开发请使用 BACKEND_PORT=8000（与 vite proxy 一致）
```

### 2.3 后端启动

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r backend/requirements.txt

# 启动后端服务（开发模式，热重载）
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或从项目根目录启动
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档地址：http://localhost:8000/docs

### 2.4 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端访问地址：http://localhost:5173

> 开发模式下 Vite 自动将 `/api` 代理到 `http://localhost:8000`，无需额外配置。

### 2.5 验证

```bash
# 健康检查（端口与 BACKEND_PORT 一致，默认开发为 8000）
curl http://localhost:8000/api/v1/system/health

# 前端构建验证
cd frontend && npm run build
```

> **端口提示**：`backend/app/config.py` 中开发模式默认后端端口为 **8000**，与 `frontend/vite.config.js` 里 `/api` → `http://localhost:8000` 一致。若在 `.env` 中修改 `BACKEND_PORT`，请同步修改 Vite `proxy.target`，否则前端无法代理到后端。

---

## 3. Docker 容器化部署

### 3.1 项目结构

```
智能股票分析器/
├── backend/           # 后端 FastAPI
│   └── Dockerfile
├── frontend/          # 前端 Vue3
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml # 服务编排
├── .dockerignore      # 构建忽略
└── .env               # 环境变量
```

### 3.2 一键启动

```bash
# 确保 .env 已配置正确
docker compose up -d
```

### 3.3 分步构建

```bash
# 构建后端镜像
docker build -t stock-analyzer-backend -f backend/Dockerfile .

# 构建前端镜像
docker build -t stock-analyzer-frontend -f frontend/Dockerfile .

# 运行后端
docker run -d -p 8000:8000 \
  -v stock_data:/app/data \
  --name stock-backend \
  stock-analyzer-backend

# 运行前端
docker run -d -p 8080:80 \
  --name stock-frontend \
  stock-analyzer-frontend
```

### 3.4 服务端口

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| 后端 API | 8000 | http://localhost:8000/docs |
| 前端界面 | 8080 | http://localhost:8080 |

### 3.5 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 重启服务
docker compose restart

# 停止并清理
docker compose down

# 重新构建并启动
docker compose up -d --build
```

### 3.6 数据持久化

SQLite 数据库通过 Docker Volume 持久化：

- **Volume 名称**: `stock_analyzer_data`
- **挂载路径**: `/app/data`
- **数据库文件**: `/app/data/stock_analyzer.db`

```bash
# 查看 Volume
docker volume ls | grep stock

# 备份数据库
docker compose exec backend python -c "
import shutil
shutil.copy('/app/data/stock_analyzer.db', '/tmp/backup.db')
"
docker compose cp backend:/tmp/backup.db ./backup.db
```

---

## 4. exe 独立打包部署

将前后端打包为一个独立 `.exe` 文件，无需安装 Python/Node.js 即可运行。

### 4.1 环境要求

| 组件 | 用途 | 仅打包时需要？ |
|------|------|:---:|
| Python 3.10+ | PyInstaller 打包 | 是 |
| Node.js 18+ | 前端构建 | 是 |
| PyInstaller | Python → exe | 是 |

> 运行时仅需 Windows 系统，无需任何依赖。

### 4.2 一键打包

```bash
# 1. 安装打包依赖
pip install pyinstaller

# 2. 执行打包脚本（从项目根目录）
python scripts/build_exe.py

# 3. 或设置环境变量强制重建前端
# 编辑 .env，设置 BUILD_EXE=1，然后执行上述命令
```

### 4.3 打包产物

```
dist_exe/
├── stock_analyzer.exe      # 主程序（前后端合一）
├── .env.example             # 配置模板
└── data/                    # 数据目录（运行时自动使用）
```

### 4.4 使用方式

```bash
# 1. 将 dist_exe/ 目录拷贝到目标 Windows 机器
# 2. 将 .env.example 重命名为 .env
# 3. 编辑 .env，填入 API Key（LLM_API_KEY、MX_APIKEY）
# 4. 双击 stock_analyzer.exe 启动
# 5. 浏览器访问 http://127.0.0.1:<BACKEND_PORT>/dashboard（默认与 `app.config` 一致：exe 常为 5174，以 exe 旁 `.env` 为准）
```

- 启动后自动打开浏览器（设置环境变量 `NO_BROWSER=1` 可禁用自动打开）
- exe 窗口显示运行日志
- 退出时关闭窗口即可

### 4.5 环境变量触发

可通过环境变量 `BUILD_EXE` 控制打包行为：

```bash
# Windows PowerShell
$env:BUILD_EXE="1"
python scripts/build_exe.py

# 或在 .env 中设置
# BUILD_EXE=1
```

### 4.6 自定义端口

编辑 `.env`：
```
BACKEND_HOST=0.0.0.0
BACKEND_PORT=9000
```
重启 exe 即可。

---

## 5. 配置说明

### 5.1 环境变量完整列表

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_MODEL_ID` | `deepseek-chat` | LLM 模型名称 |
| `LLM_API_KEY` | — | **必需** LLM API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | LLM 服务地址 |
| `LLM_TIMEOUT` | `60` | LLM HTTP 超时(秒)；后端会与更长下限合并，避免多轮 Agent 过早断开 |
| `BUFFETT_MAX_REFLECTIONS` | `0` | 巴菲特评估初稿后的反思轮数（可选，见 `.env.example`） |
| `MX_APIKEY` | — | **必需** 东方财富妙想 API 密钥 |
| `MX_API_URL` | `https://mkapi2.dfcfs.com/finskillshub` | 妙想 API 地址 |
| `MX_CACHE_TTL_SECONDS` | `600` | 妙想查询进程内缓存 TTL（秒） |
| `MX_REPLAY_FIXTURES` | 关闭 | 为 true 时优先回放 `MX_FIXTURE_DIR` 下 fixture，不调妙想 HTTP |
| `MX_FIXTURE_DIR` | `backend/fixtures/mx_raw` | 回放目录 |
| `BACKEND_HOST` | `0.0.0.0` | 后端监听地址 |
| `BACKEND_PORT` | **开发 `8000`** / **exe 默认 `5174`** | 未设置环境变量时由 `config.py` 按是否冻结自动选择 |
| `FRONTEND_PORT` | `5173` | 前端开发端口 |
| `FRONTEND_DIR` | — | 可选：显式指定已构建的前端 `dist` 目录 |
| `DATA_DIR` | — | 可选：数据目录；默认 exe 旁或项目根下 `data` |
| `DATABASE_URL` | `sqlite:///./data/stock_analyzer.db` | 数据库连接 |
| `BUILD_EXE` | — | 打包脚本使用：`1`/`true`/`rebuild` 时强制重建前端 |
| `REDIS_*` | 见 `.env.example` | **预留**，当前版本未使用（`requirements.txt` 中 redis 已注释） |
| `JWT_SECRET_KEY` | `dev-secret-key` | **预留**，当前版本无登录鉴权，可不配置 |
| `JWT_EXPIRE_MINUTES` | `1440` | **预留**，接入用户认证后生效 |

接口路径补充（与 Swagger 一致）：

- AI 舆情流式：`POST /api/v1/sentiment/analyze/stream`（兼容：`POST /api/v1/agent/sentiment/stream`）
- AI 数据流式：`POST /api/v1/data-analysis/analyze/stream`（兼容：`POST /api/v1/agent/data-analysis/stream`）
- exe / 桌面：`POST /api/v1/system/open-external-url` 在本机默认浏览器打开允许的 http(s) 链接

### 5.2 安全配置（生产环境）

当前版本 **不要求** JWT；对外暴露 API 时建议：

- 使用 Nginx/网关限制来源 IP 或加独立鉴权层
- 勿将 `.env` 中的 `LLM_API_KEY`、`MX_APIKEY` 提交到版本库
- 用户认证（JWT）实现后，可用以下命令预生成密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 写入 .env: JWT_SECRET_KEY=<生成的密钥>
```

### 5.3 Nginx 反向代理配置（生产示例）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        proxy_pass http://frontend:80;
    }

    # 后端 API
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

---

## 6. 健康检查

### 6.1 后端健康检查

```bash
curl http://localhost:8000/api/v1/system/health
```

正常响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "agent_ready": true,
    "skills_ready": true
  }
}
```

- `agent_ready: false` → LLM_API_KEY 未配置
- `skills_ready: false` → MX_APIKEY 未配置

### 6.2 Docker 健康检查

Docker Compose 自动监控后端 `/api/v1/system/health` 端点，30秒间隔检查。

```bash
# 查看健康状态
docker compose ps
# 输出中 (healthy) 表示通过
```

---

## 7. 常见问题

### Q: 如何获取 API 密钥？

- **DeepSeek API**: https://platform.deepseek.com
- **东方财富妙想 API**: https://dl.dfcfs.com/m/itc4

### Q: 启动后前端能访问但数据为空？

检查 `.env` 中的 `MX_APIKEY` 是否有效，运行健康检查确认 `skills_ready: true`。

### Q: Docker 构建速度慢？

项目已配置 `.dockerignore` 排除不必要的文件。首次构建需下载基础镜像，后续使用缓存。

### Q: SQLite 数据库如何迁移至 PostgreSQL？

修改 `DATABASE_URL`：
```
DATABASE_URL=postgresql://user:password@host:5432/stock_analyzer
```
并在 `requirements.txt` 中替换 `aiosqlite` 为 `asyncpg`。

### Q: 如何扩容至多副本？

后端无状态设计支持多副本（SQLite 需切换为 PostgreSQL/MySQL）：

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
  frontend:
    deploy:
      replicas: 2
```

> 注意：多副本时需将数据存储切换为数据库服务器（PostgreSQL）并添加 Redis 缓存。

---

## 附录

### A. 网络架构

```
浏览器(8080)
    │
    ▼
Nginx(前端容器:80)
    │ /           → dist/ (SPA静态文件)
    │ /api/*      → proxy_pass
    │
    ▼
FastAPI(后端容器:8000)
    │
    ├── SQLite (/app/data)
    ├── HelloAgents (智能体推理)
    └── 东方财富妙想API (外部金融数据)
```

### B. 开发 vs 生产对比

| 项目 | 开发 | 生产 |
|------|------|------|
| 后端启动 | `uvicorn --reload` | `uvicorn` (无热重载) |
| 前端启动 | `vite dev` (5173) | Nginx (80) |
| API 代理 | Vite proxy | Nginx reverse proxy |
| 数据库 | 本地文件 | Docker Volume |
| CORS | 允许所有来源 | 仅允许前端域名 |
