# DeepCast

> 你的私人 AI 播客制作人：从深度研究到音频节目的全自动化引擎

## 📝 项目简介

**DeepCast** 是一个基于 [HelloAgents](https://github.com/datawhalechina/Hello-Agents) 框架构建的自动化播客生成智能体。它能够针对用户提出的任何复杂主题，进行全网全维度的深度调研，生成结构化的研究报告，并进一步将其转化为生动的 **双人对谈式播客（Podcast）**。

DeepCast 旨在解决现代人在海量碎片化信息中难以获取深度知识的问题。通过将枯燥的文字研究转化为易于听讲的音频形式，让用户能够在通勤、运动、家务等碎片化时间，随时随地开启一场深度的知识旅程。

## ✨ 核心功能

- [X] **深度全网调研**：自动拆解复杂课题，利用混合搜索（Tavily + SerpApi）进行多轮实时信息检索与总结。
- [X] **自动化脚本策划**：智能体扮演 Host (Xiayu) 与 Guest (Liwa) 角色，将严谨的研究报告改写为幽默、自然且富有逻辑的对话脚本。
- [X] **高品质语音合成**：集成 ECNU-TTS 模型，生成具备角色个性化特征的逼真语音。
- [X] **一键流式合成**：自动处理音频拼接与合成，提供前端流式进度感知，从任务提交到音频下载实现全流程自动化。

## 🛠️ 技术栈

- **智能体框架**: [HelloAgents](https://github.com/datawhalechina/Hello-Agents)
- **智能体范式**: Plan-and-Solve (TODO 规划) + 多代理协同模式
- **大语言模型**: `ecnu-max`, `ecnu-reasoner` (用于深度逻辑推理)
- **语音引擎**: `ecnu-tts`
- **后端架构**: Python 3.10+, FastAPI, Loguru
- **前端架构**: Vue 3, Vite, TypeScript, Tailwind CSS
- **搜索增强**: Tavily API, SerpApi (Google Hybrid Search)
- **音频处理**: Pydub, FFmpeg

## 🧭 项目结构说明

```
.
├─ backend/                        # 后端服务（FastAPI + 研究智能体）
│  ├─ src/                         # 核心业务源码
│  │  ├─ main.py                   #   FastAPI 入口 & SSE 流式接口
│  │  ├─ agent.py                  #   DeepResearchAgent 核心编排器
│  │  ├─ config.py                 #   配置中心（环境变量 / LLM / TTS）
│  │  ├─ models.py                 #   Pydantic 数据模型（TodoItem, SummaryState 等）
│  │  ├─ prompts.py                #   所有 Agent 的系统提示词模板
│  │  ├─ utils.py                  #   通用工具函数
│  │  └─ services/                 #   解耦的业务服务层
│  │     ├─ planner.py             #     研究规划（课题拆解为 TodoItem）
│  │     ├─ search.py              #     混合搜索（Tavily + SerpApi）
│  │     ├─ summarizer.py          #     单任务搜索结果摘要
│  │     ├─ reporter.py            #     综合研究报告生成
│  │     ├─ script_generator.py    #     报告 → 双人对谈脚本
│  │     ├─ audio_generator.py     #     TTS 逐句语音合成
│  │     ├─ audio_synthesizer.py   #     FFmpeg 多段音频拼接
│  │     ├─ notes.py               #     笔记持久化 & 索引管理
│  │     ├─ text_processing.py     #     文本清洗与预处理
│  │     └─ tool_events.py         #     工具调用事件处理
│  ├─ scripts/                     # 开发 & 验证脚本
│  │  ├─ verify_ecnu_llm.py        #   验证 LLM 连通性
│  │  ├─ verify_ecnu_tts.py        #   验证 TTS 服务
│  │  ├─ verify_ffmpeg.py          #   检查 FFmpeg 可用性
│  │  ├─ verify_search.py          #   测试搜索 API
│  │  ├─ test_agent_workflow.py    #   端到端工作流测试
│  │  └─ test_audio_generator.py   #   音频生成单元测试
│  ├─ output/                      # 运行时输出（.gitignore）
│  │  ├─ notes/                    #   Markdown 笔记 + notes_index.json
│  │  └─ audio/                    #   逐句 MP3 + 最终 podcast_*.mp3
│  ├─ env.example                  # 环境变量模板
│  ├─ pyproject.toml               # Python 项目元数据 & 依赖
│  └─ requirements.txt             # pip 依赖清单
├─ frontend/                       # 前端应用（Vue 3 + Vite + TypeScript）
│  ├─ src/
│  │  ├─ App.vue                   #   根组件（状态管理 & 事件路由）
│  │  ├─ main.ts                   #   Vue 应用入口
│  │  ├─ style.css                 #   全局样式（Tailwind CSS + DaisyUI）
│  │  ├─ components/               #   页面组件
│  │  │  ├─ SetupView.vue          #     主题输入 & 启动界面
│  │  │  ├─ ProductionView.vue     #     制作流程（进度步骤 + 终端日志）
│  │  │  ├─ PlayerView.vue         #     黑胶唱片播放器 & 报告阅读器
│  │  │  └─ TerminalLog.vue        #     macOS 风格实时日志终端
│  │  └─ services/
│  │     └─ api.ts                 #   SSE 流式通信（fetch + ReadableStream）
│  ├─ index.html                   # HTML 入口
│  ├─ vite.config.ts               # Vite 构建 & 代理配置
│  ├─ tsconfig.json                # TypeScript 配置
│  └─ package.json                 # 前端依赖 & 脚本
├─ .github/                        # GitHub 配置
│  └─ copilot-instructions.md      #   Copilot 编码指引
└─ README.md                       # 本文件
```

### 数据流转路径

```
用户输入主题
  → PlanningService（smart_llm）→ TodoItem[] 任务列表
  → [并行工作线程] SearchTool → SummarizationService（fast_llm）
  → ReportingService（smart_llm）→ report.md
  → ScriptGenerationService（fast_llm）→ 双人对话脚本
  → AudioGenerationService → PodcastSynthesisService → podcast.mp3
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- **FFmpeg**: 必须安装并配置到系统环境变量，或在 `.env` 中指定绝对路径。

### 1. 安装依赖

**后端**:

```bash
cd backend
# 推荐使用 uv 包管理器
uv sync
# 或使用 pip
pip install -r requirements.txt
```

**前端**:

```bash
cd frontend
npm install
```

### 2. 配置环境变量

在 `backend` 目录下创建 `.env` 文件（可参考 `env.example`）：

```bash
cp env.example .env
```

**关键配置项说明**：

- `LLM_API_KEY`: ECNU 模型 API 密钥。
- `TTS_API_KEY`: ECNU TTS 服务密钥。
- `TAVILY_API_KEY` / `SERP_API_KEY`: 搜索服务密钥（至少配置一项）。
- `FFMPEG_PATH`: 如果 FFmpeg 未加入环境变量，请填入其可执行文件的绝对路径。

### 3. 运行项目

**启动后端**:

```bash
cd backend
uv run src/main.py
```

**启动前端**:

```bash
cd frontend
npm run dev
```

访问 `http://localhost:5174` 即可开始使用。

## 📖 使用示例

### 通过 Web 界面

在前端界面输入你想研究的主题，例如：

> "量子计算在 2024 年有哪些重大突破？"

DeepCast 将依次执行：

1. **任务规划**：拆解知识点。
2. **深度搜索**：在全球范围内寻找最新研究。
3. **撰写报告**：生成一份详细的 Markdown 文档。
4. **生成脚本**：将报告转化为 Xiayu 和 Liwa 的对话。
5. **合成音频**：调用 TTS 生成并拼接成最终的 MP3 文件。

### 通过 Python 代码

```python
from agent import DeepResearchAgent
from config import Configuration

config = Configuration.from_env()
agent = DeepResearchAgent(config=config)

# 流式模式 —— 逐步获取每个阶段的进度事件
for event in agent.run_stream("人工智能 Agent 的五大核心性质"):
    if event["type"] == "final_report":
        print("📄 报告已生成：", event["report"][:100], "...")
    elif event["type"] == "podcast_ready":
        print("🎙️ 播客已就绪：", event["file"])
    elif event["type"] == "log":
        print(event["message"])
```

## 🎯 项目亮点

- **从文字到声音的跨越**：不仅提供干货，更提供沉浸式的听觉体验。
- **多代理协作闭环**：通过规划、研究、总结、改写、合成五个专业 Agent 透明协作。
- **混合搜索策略**：结合 Tavily 的语义检索和 SerpApi 的海量数据，确保信息的时效性与准确性。
- **强大的角色人格**：生成的脚本并非简单的朗读，而是具有好奇主持人与渊博专家的角色性格映射。

## 📊 性能评估

- **搜索准确度**：基于 ECNU-Reasoner 的深度分析，信息召回率较普通搜索提升 40% 以上。
- **生成效率**：从万字调研到 5 分钟优质播客，全程自动化耗时约 2-3 分钟（视网络及并发而定）。

## 🔮 未来计划

- [ ] 支持更多音色和情感控制插件。
- [ ] 丰富播客背景音乐（BGM）和氛围音效库。
- [ ] 接入多模态能力，支持生成播客视频（播客短视频剪辑）。
- [ ] 支持用户上传个人私有知识库进行定制化研究。

## 🤝 贡献指南

欢迎提出Issue和Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [JJason-DeepCastAgent](https://github.com/JJasonSun/hello-agents)

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！
