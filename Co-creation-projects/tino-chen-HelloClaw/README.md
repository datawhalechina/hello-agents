# HelloClaw - 个性化 AI Agent 助手

> 基于 HelloAgents 框架的个性化 AI Agent 应用，支持身份定制、记忆系统和流式工具调用

<div align="center">
  <img src="outputs/helloclaw.png" alt="HelloClaw Screenshot" width="80%"/>
</div>

## 项目简介

HelloClaw 是一个基于 Hello-Agents 框架构建的个性化 AI Agent 应用，实现了类似 OpenClaw 的核心功能。它不仅是一个智能对话助手，更是一个可以"认识你"、记住你、并根据你的需求不断成长的个性化 AI 伙伴。

**核心特性：**
- 支持自定义 Agent 身份和个性
- 长期记忆和每日记忆的自动管理
- 流式工具调用，实时反馈执行状态
- 多会话支持，会话历史持久化
- 现代化 Web 界面（Vue3 + FastAPI）

## 核心功能

- [x] **智能对话** - 基于 ReActAgent 的智能对话能力
- [x] **记忆系统** - 支持长期记忆(MEMORY.md)和每日记忆的自动管理
- [x] **工具调用** - 内置多种工具（文件操作、代码执行、网页搜索、网页抓取等）
- [x] **会话管理** - 多会话支持，会话历史持久化
- [x] **身份定制** - 可通过配置文件自定义 Agent 身份和个性
- [x] **流式输出** - 支持 SSE 流式响应，实时显示回复
- [x] **Web 界面** - 现代化的 Vue3 前端界面

## 技术栈

| 层级 | 技术 |
|------|------|
| Agent 框架 | Hello-Agents (ReActAgent / SimpleAgent) |
| 后端框架 | Python + FastAPI |
| 前端框架 | Vue 3 + TypeScript + Ant Design Vue |
| 流式通信 | SSE (Server-Sent Events) |
| 包管理 | uv (Python) / pnpm (前端) |

## 技术亮点

### 1. 增强版流式工具调用

实现了 `EnhancedSimpleAgent` 和 `EnhancedHelloAgentsLLM`，支持真正的流式工具调用：
- 实时推送工具调用状态（开始/完成）
- 支持多轮工具调用迭代
- 优雅的错误处理和回退机制

### 2. 智能记忆系统

- **长期记忆 (MEMORY.md)**: 存储重要信息，跨会话保持
- **每日记忆**: 自动按日期分类存储对话记忆
- **Memory Flush**: 当上下文接近阈值时，自动提醒 Agent 保存重要信息

### 3. 工作空间管理

- 基于 Markdown 配置文件的身份定制系统
- 支持 IDENTITY.md、USER.md、SOUL.md 等多种配置
- 热加载配置，无需重启服务

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（可选，仅前端需要）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
# 创建.env文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# 支持 OpenAI 兼容的 API（如智谱 AI、ModelScope 等）
```

### 运行项目

**方式一：使用 Jupyter Notebook（推荐）**

```bash
jupyter lab
# 打开 main.ipynb 并运行
```

**方式二：运行完整 Web 服务**

```bash
# 启动后端
cd tino-chen-HelloClaw
pip install uvicorn
uvicorn src.main:app --reload --port 8000

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用 Web 界面。

## 使用示例

### 基础对话

```python
from src.agent.helloclaw_agent import HelloClawAgent

# 创建 Agent
agent = HelloClawAgent()

# 同步对话
response = agent.chat("你好，请介绍一下你自己")
print(response)
```

### 流式对话

```python
import asyncio

async def chat_stream():
    agent = HelloClawAgent()

    async for event in agent.achat("帮我搜索一下今天的新闻"):
        if event.type.value == "llm_chunk":
            print(event.data.get("chunk", ""), end="", flush=True)
        elif event.type.value == "tool_call_start":
            print(f"\n[调用工具: {event.data.get('tool_name')}]")
        elif event.type.value == "tool_call_finish":
            print(f"[工具执行完成]")

asyncio.run(chat_stream())
```

## 项目结构

```
tino-chen-HelloClaw/
├── README.md              # 项目说明文档
├── requirements.txt       # Python 依赖列表
├── main.ipynb            # 主要的 Jupyter Notebook（快速演示）
├── .env.example          # 环境变量模板
├── data/                 # 数据文件
├── outputs/              # 输出结果（截图等）
│   └── helloclaw.png     # 项目截图
├── src/                  # 后端源代码
│   ├── agent/            # Agent 封装
│   │   ├── helloclaw_agent.py      # 主 Agent 类
│   │   ├── enhanced_simple_agent.py # 增强版 SimpleAgent
│   │   └── enhanced_llm.py         # 增强版 LLM（流式工具调用）
│   ├── tools/            # 自定义工具
│   │   └── builtin/
│   │       ├── memory.py              # 记忆工具
│   │       ├── execute_command.py     # 命令执行工具
│   │       ├── web_search.py          # 网页搜索工具
│   │       └── web_fetch.py           # 网页抓取工具
│   ├── memory/           # 记忆管理
│   │   ├── capture.py             # 记忆捕获
│   │   ├── memory_flush.py        # 记忆刷新
│   │   └── session_summarizer.py  # 会话摘要
│   ├── workspace/        # 工作空间管理
│   │   ├── manager.py             # 工作空间管理器
│   │   └── templates/             # 配置模板
│   └── api/              # FastAPI 路由
│       ├── chat.py                # 聊天接口
│       ├── session.py             # 会话管理
│       ├── config.py              # 配置管理
│       └── memory.py              # 记忆接口
└── frontend/             # 前端源代码（Vue3）
    ├── src/
    │   ├── views/                 # 页面组件
    │   ├── components/            # 通用组件
    │   ├── api/                   # API 请求
    │   └── assets/                # 静态资源
    ├── public/                    # 公共资源
    ├── package.json               # 前端依赖配置
    └── vite.config.ts             # Vite 配置
```

## 工作空间配置

工作空间位于 `~/.helloclaw/`，包含：

```
~/.helloclaw/
├── config.json       # 全局 LLM 配置
└── workspace/        # Agent 工作空间
    ├── IDENTITY.md   # 身份配置
    ├── MEMORY.md     # 长期记忆
    ├── SOUL.md       # 灵魂/个性
    ├── USER.md       # 用户信息
    ├── AGENTS.md     # 系统提示词
    ├── memory/       # 每日记忆
    └── sessions/     # 会话历史
```

## 项目亮点

1. **真正的流式工具调用** - 不是简单的流式文本输出，而是完整的流式工具调用流程
2. **智能记忆管理** - 自动捕获对话中的重要信息，支持长期记忆和每日记忆
3. **高度可定制** - 通过 Markdown 配置文件自定义 Agent 的身份、个性、用户信息
4. **生产级代码** - 完整的错误处理、日志记录、配置管理

## 未来计划

- [ ] 支持多模态输入（图片、文件）
- [ ] 添加更多内置工具（代码解释器、数据库查询等）
- [ ] 支持 Agent 间协作
- [ ] 添加语音交互能力

## 许可证

MIT License

## 作者

- GitHub: [@tino-chen](https://github.com/tino-chen)
- 项目链接: [HelloClaw](https://github.com/tino-chen/helloclaw)

## 致谢

- [Hello-Agents](https://github.com/datawhalechina/hello-agents) - Agent 框架
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架
- [Vue.js](https://vuejs.org/) - 前端框架
- [Ant Design Vue](https://antdv.com/) - UI 组件库

感谢 Datawhale 社区和 Hello-Agents 项目！
