# 猜猜我是谁 (GuessWhoAmI)

一个基于 `hello_agents` 框架开发的交互式猜人物游戏。AI Agent 随机扮演一位历史人物、神话人物或网络红人，用户通过多轮对话提问来猜测其身份。

## 项目特色

- 🤖 **LLM 动态生成人物** —— 每局由大模型随机生成人物，涵盖中西历史、神话、虚构角色、网络红人等多个领域，不重复
- 🎭 **沉浸式角色扮演** —— Agent 以第一人称扮演人物，语气符合其性格与时代背景，回答具有迷惑性和引导性
- 🔍 **Tavily 搜索增强** —— 自动搜索人物资料，生成由模糊到具体的 3 条提示
- 🖼️ **猜对后展示人物图片** —— 猜对后通过 Wikipedia 搜索并展示人物图片
- 🧠 **语义猜测匹配** —— 使用 LLM 语义判断猜测是否正确，支持别名、外号等多种表达
- ⚡ **FastAPI 高性能后端** + 现代化 Web 前端

## 项目结构

```
afei-GuessWhoAmI/
├── restart.sh               # 一键启动脚本（前后端）
├── backend/
│   ├── main.py              # FastAPI 入口，API 路由
│   ├── agents.py            # Agent 核心逻辑（人物生成、角色扮演、猜测判断）
│   ├── game_logic.py        # 游戏状态管理（GameSession）
│   ├── config.py            # 配置管理（Settings 单例）
│   ├── models.py            # Pydantic 请求/响应模型
│   ├── requirements.txt     # Python 依赖
│   ├── .env.example         # 环境变量模板
│   └── tools/
│       ├── tavily_search_tool.py   # Tavily 搜索工具（生成提示）
│       └── search_image_tool.py    # Wikipedia 图片搜索工具
├── frontend/
│   ├── index.html           # 主页面
│   ├── style.css            # 样式文件
│   └── app.js               # 交互逻辑
└── logs/
    ├── backend.log          # 后端运行日志
    └── frontend.log         # 前端服务日志
```

## 环境要求

- Python 3.8+
- ModelScope API Key（必须）
- Tavily API Key（必须，用于搜索增强提示，获取：https://app.tavily.com/）

## 快速开始

### 1. 安装依赖

```bash
cd /home/afei/hello-agents/Co-creation-projects/afei-GuessWhoAmI/backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制模板并填写配置：

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```env
# LLM 配置（ModelScope API，必填）
LLM_MODEL_ID=qwen-flash
LLM_API_KEY=your_modelscope_api_key
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
LLM_TIMEOUT=180

# Tavily 搜索 API（必填，用于搜索增强提示）
# 获取 Key: https://app.tavily.com/
TAVILY_API_KEY=your_tavily_api_key
```

### 3. 一键启动（推荐）

使用 `restart.sh` 脚本同时启动前后端服务：

```bash
cd /home/afei/hello-agents/Co-creation-projects/afei-GuessWhoAmI
bash restart.sh
```

脚本会自动：
- 停止已有的前后端进程
- 启动后端（FastAPI，端口 **8000**）
- 启动前端（Python http.server，端口 **3000**）
- 等待服务就绪并打印访问地址

启动成功后输出示例：
```
✅ All services started successfully!

  🔧 Backend  → http://localhost:8000
  🔧 API Docs → http://localhost:8000/docs
  🌐 Frontend → http://localhost:3000
```

### 4. 访问地址

| 服务 | 地址 |
|------|------|
| 🌐 游戏前端 | http://localhost:3000 |
| 🔧 后端 API | http://localhost:8000 |
| 📖 API 文档 | http://localhost:8000/docs |

### 5. 手动启动（可选）

如需单独启动各服务：

```bash
# 启动后端
cd backend
python main.py

# 启动前端（另开终端）
cd frontend
python -m http.server 3000
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/game/start` | 开始新游戏（LLM 生成人物 + 预生成提示） |
| `POST` | `/api/game/chat` | 向 Agent 提问（角色扮演对话） |
| `POST` | `/api/game/guess` | 提交猜测（语义匹配判断，猜对返回人物图片） |
| `GET`  | `/api/game/hint` | 获取下一条提示 |
| `POST` | `/api/game/end` | 结束当前游戏 |
| `GET`  | `/api/game/status` | 获取当前游戏状态 |

## 游戏规则

1. 点击「开始游戏」，系统由 LLM 随机生成一位人物（历史、神话、虚构、网络红人均有可能）
2. 通过对话向 Agent 提问，Agent 以该人物第一人称回答，**不会直接说出名字**
3. 最多可提问 **10 次**，可使用提示 **3 次**（提示由模糊到具体）
4. 随时可以提交猜测，支持别名、外号等多种表达方式
5. 猜对后展示人物图片；提问次数用完或主动结束则游戏结束并揭晓答案

## 技术栈

### 后端
- **FastAPI** —— Web 框架
- **hello_agents** —— AI Agent 框架（SimpleAgent、HelloAgentsLLM）
- **Pydantic v2** —— 数据验证
- **Uvicorn** —— ASGI 服务器
- **Tavily Python SDK** —— 搜索增强
- **Wikipedia API** —— 人物图片搜索

### 前端
- **HTML5 / CSS3 / JavaScript** —— 原生实现，无框架依赖
- **Fetch API** —— 与后端通信

### AI / LLM
- **ModelScope API** —— OpenAI 兼容接口（默认模型：`qwen-flash`）
- **LLM 人物生成** —— 动态随机生成，避免重复
- **LLM 语义匹配** —— 判断猜测是否与答案指代同一人物

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_MODEL_ID` | `qwen-flash` | 使用的 LLM 模型（推荐 flash 系列以降低延迟） |
| `LLM_BASE_URL` | ModelScope API | LLM 接口地址 |
| `LLM_TIMEOUT` | `180` | LLM 请求超时（秒） |
| `TAVILY_API_KEY` | 无 | Tavily 搜索 Key（必填），用于搜索人物资料生成提示，获取：https://app.tavily.com/ |
| `MAX_QUESTIONS` | `10` | 每局最大提问次数 |
| `MAX_HINTS` | `3` | 每局最大提示次数 |

## 日志

运行日志保存在 `logs/` 目录：

```bash
# 实时查看后端日志
tail -f logs/backend.log

# 实时查看前端日志
tail -f logs/frontend.log
```

## 故障排除

**LLM 调用失败**
- 检查 `backend/.env` 中的 `LLM_API_KEY` 和 `LLM_BASE_URL`
- 确认 ModelScope 账号有对应模型的访问权限

**每次生成同一个人物**
- 已通过随机种子 + 时间戳注入解决，若仍出现请检查 LLM 模型是否支持随机性参数

**Tavily 搜索不可用**
- 检查 `backend/.env` 中的 `TAVILY_API_KEY` 是否正确填写
- 未配置时系统会自动降级使用 fallback 提示，但提示质量会下降
- 获取 Key：https://app.tavily.com/

**端口被占用**
- `restart.sh` 会自动清理占用端口的进程，重新运行脚本即可

**CORS 错误**
- 后端已配置 CORS 允许所有来源，确保前端访问正确的后端端口（默认 8000）
