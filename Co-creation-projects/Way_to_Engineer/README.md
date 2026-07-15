# Way to Engineer

> AI 辅助编程学习平台 — 多 Agent 协作，交互式代码练习

---

## 简介

Way to Engineer 是一个 AI 驱动的编程学习平台。用户通过与多个 AI Agent 对话来学习编程，每个 Agent 扮演不同角色（导师、调试员、审查员、架构师、学习教练），覆盖了从概念讲解到代码审查的完整学习闭环。

### 核心功能

- **多 Agent 对话** — 自动路由到最合适的 AI 角色（编程导师 / 调试助手 / 代码审查 / 架构设计 / 学习教练）
- **交互式代码运行** — 聊天中的代码块可一键执行，右侧 Monaco 编辑器提供完整的编码环境
- **练习反馈** — 写完练习代码后可提交给 AI 审查，获得教学性反馈
- **学习路径** — 前端 / 后端 / 全栈的学习路线规划与进度追踪
- **水平评估** — AI 生成测验题目，评估用户当前水平并推荐学习起点
- **游戏化** — XP 经验值、连续学习天数、徽章系统
- **LLM 配置切换** — 运行时切换 API Base URL、Model ID、API Key，无需重启服务
- **暗色主题 / 中英文切换**

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | FastAPI + Python 3.10+ |
| AI 框架 | hello-agents（轻量 LLM Agent 封装） |
| 代码编辑器 | Monaco Editor |
| 持久化 | JSON 文件存储 |
| 代码执行 | 子进程沙箱（subprocess + 安全过滤） |

---

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- 一个 LLM API Key（默认支持 DeepSeek，也可配置其他 OpenAI 兼容接口）

### 1. 克隆并进入项目

```bash
git clone <repo-url>
cd Way_to_Engineer
```

### 2. 配置后端

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

复制环境变量文件并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env`，至少设置 `DEEPSEEK_API_KEY`。

### 3. 启动后端

```bash
python run.py
```

后端默认运行在 `http://localhost:8000`。

### 4. 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，Vite 会自动代理 `/api` 请求到后端。

### 5. 开始使用

打开浏览器访问 `http://localhost:5173`，输入用户名即可开始。

---

## 项目结构

```
Way_to_Engineer/
├── backend/
│   ├── app/
│   │   ├── agents/               # AI Agent 定义（共 5 个角色 + 路由编排器）
│   │   │   ├── orchestrator.py   # 智能路由：分析用户输入，分配 Agent
│   │   │   ├── tutor_agent.py    # 编程导师：概念讲解、示例、练习
│   │   │   ├── debug_agent.py    # 调试助手：错误分析、修复建议
│   │   │   ├── review_agent.py   # 代码审查员：代码质量审查 + 练习反馈
│   │   │   ├── arch_agent.py     # 架构师：系统设计、技术选型
│   │   │   └── coach_agent.py    # 学习教练：路径规划、进度跟踪
│   │   ├── api/
│   │   │   ├── routes/           # API 路由（chat / code / settings / auth 等）
│   │   │   └── main.py           # FastAPI 应用入口
│   │   ├── models/               # Pydantic 数据模型
│   │   ├── services/             # 业务服务（LLM / 代码执行 / 持久化 / 测验等）
│   │   └── config.py             # 配置管理（pydantic-settings）
│   ├── data/                     # 用户数据持久化（不纳入版本控制）
│   ├── .env.example              # 环境变量模板
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/           # 可复用组件（CodeEditor / CodeRunner / MarkdownRenderer / QuizWidget 等）
│   │   ├── views/                # 页面（Chat / Learning / Dashboard / Orchestration / Login）
│   │   ├── stores/               # Pinia 状态管理（auth / theme / lang / agent）
│   │   ├── locales/              # 中英文国际化
│   │   ├── types/                # TypeScript 类型定义
│   │   └── router/               # Vue Router 路由定义
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                         # 开发阶段文档
├── .gitignore
└── README.md
```

---

## 配置说明

### 环境变量（`.env`）

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | — |
| `DEEPSEEK_MODEL_ID` | 模型名称 | `deepseek-chat` |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com/v1` |
| `LLM_TIMEOUT` | LLM 请求超时（秒） | `60` |
| `HOST` | 后端监听地址 | `0.0.0.0` |
| `PORT` | 后端端口 | `8000` |

### 运行时 LLM 配置

登录后在导航栏点击齿轮图标 ⚙️，可在页面中直接修改 LLM 配置（Base URL / Model ID / API Key），修改后即时生效，无需重启服务。页面配置优先于 `.env` 文件。

---

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat/` | 发送聊天消息，自动路由到对应 Agent |
| POST | `/api/code/execute` | 执行 Python 代码 |
| POST | `/api/code/submit` | 提交练习代码获取 AI 反馈 |
| GET | `/api/settings/llm` | 获取当前 LLM 配置 |
| POST | `/api/settings/llm` | 更新 LLM 配置 |
| POST | `/api/settings/llm/reset` | 恢复 LLM 配置为默认值 |
| POST | `/api/auth/login` | 用户名登录 / 注册 |
| GET | `/api/learning/paths` | 获取学习路径列表 |
| GET | `/api/gamification/profile` | 获取游戏化档案 |

完整 API 文档在服务启动后访问 `http://localhost:8000/docs`（Swagger UI）。

---

## License

MIT
