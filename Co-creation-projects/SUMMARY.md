# Co-creation 项目摘要

---

### 1zrj-DataAnalysisAgent
描述：基于 HelloAgents 框架的智能数据分析助手，自动分析数据、生成可视化图表并撰写分析报告。
技术栈：HelloAgents (SimpleAgent), Python AST, OpenAI API, pandas, matplotlib
关键文件：main.ipynb, src/agents/, src/tools/

---

### 939147533-DatabaseAgent
描述：基于 HelloAgents 的智能数据库查询助手，支持将自然语言转换为 SQL 查询并从 Oracle 数据库获取数据。
技术栈：HelloAgents (ReAct), Oracle DB, ToolRegistry, HelloAgentsLLM
关键文件：main.py, test.py, setup_database.sql, .env.example

---

### afei-GuessWhoAmI
描述：基于 hello_agents 框架的交互式猜人物游戏，AI Agent 扮演历史人物/神话角色/网络红人，用户通过多轮对话提问来猜测身份。
技术栈：FastAPI, hello_agents (SimpleAgent, HelloAgentsLLM), Tavily Search, ModelScope API, HTML/CSS/JS 前端
关键文件：backend/main.py, backend/agents.py, frontend/app.js, restart.sh

---

### alexrunner-DataAnalysisAgent
描述：商品销售数据分析智能体，采用 Plan-and-Solve + ReAct 混合架构，自动多任务规划、深度分析并生成图文并茂的商业分析报告。
技术栈：HelloAgents (Plan-and-Solve, ReAct), pandas, OpenAI API
关键文件：main.py, agents/, tools/, out/analysis_report.md

---

### allen2000-FashionDailyDress
描述：多智能体协作的天气查询和穿衣建议系统，通过天气查询 + 穿衣建议 + 协调器三个智能体协作，基于实时天气提供专业穿衣建议。
技术栈：hello-agents, fastmcp, Gradio, OpenWeatherMap API, Python
关键文件：gradio_app.py, multi_agent_coordinator.py, fashion_agent.py, weather.py

---

### angelen-SoftwareDevHelper
描述：面向软件开发初学者的智能学习助手，支持水平记忆、智能出题、代码审查、自动化测试与打分，具有完整前后端。
技术栈：HelloAgents (SimpleAgent, ToolRegistry), FastAPI, Uvicorn, HTML/CSS/JS 前端
关键文件：src/main.py, src/agents/, src/tools/, frontend/

---

### Apricity-InnocoreAI
描述：基于多智能体协作的科研全流程自动化系统（研创·智核），支持论文搜索、深度分析、写作辅助、引用校验，四大智能体（Hunter/Miner/Coach/Validator）协同工作。
技术栈：HelloAgent, FastAPI, PostgreSQL/Qdrant/Redis, ArXiv API, PDF 解析, 向量检索, WebSocket
关键文件：agents/, api/, core/, frontend/, run.py, install.py

---

### AstrumPush-Smart-Recipe-Agent
描述：基于多 Agent 协作的菜谱搜索系统，自动搜索、筛选并生成完整菜谱，支持真实菜谱网站数据源。
技术栈：hello_agents, MCPTool, @mzxrai/mcp-webresearch, python-dotenv
关键文件：diet_recommendation_final.py, protocol_tools.py, basic_func_test.py, recipes/

---

### bichchibui5-hub-EmailSmartAssistant
描述：基于 AI 的智能邮件处理系统，自动分类邮件、生成回复草稿、提取关键信息并设置智能提醒，支持多邮箱服务。
技术栈：Python 3.8+, HelloAgents (ReAct), imaplib/smtplib, jieba/TextBlob, scikit-learn, pandas, matplotlib
关键文件：EmailSmartAssistant_HelloAgents.ipynb, demo.py, email_assistant.py, config/

---

### chen070808-ProgrammingTutor
描述：基于 HelloAgents 的多智能体编程学习助手系统，支持学习路径规划、智能出题、代码评审，采用 A2A (Agent-to-Agent) 协作模式。
技术栈：HelloAgents (SimpleAgent, ReAct), Python, Agent-to-Agent 工具调用, CodeRunner
关键文件：src/agents/tutor.py, src/agents/planner.py, src/agents/reviewer.py, main.ipynb

---

### czxgg0630-ProductAnalysisAgent
描述：智能竞品分析系统，提供 SimpleAgent 和 PlanAndSolveAgent 两种范式，自动收集竞品信息、进行多维度对比分析并生成专业报告。
技术栈：HelloAgents (SimpleAgent, PlanAndSolveAgent), Tavily Search, DuckDuckGo, Web Scraper, pandas
关键文件：ProductAnalysis_SimpleAgent.ipynb, ProductAnalysis_PlanSolveAgent.ipynb, src/tools/

---

### haoye2-UnivesalAgent
描述：基于 Hello-Agents 框架的通用智能体系统，采用单智能体+多工具设计，支持多引擎智能搜索和安全终端执行。
技术栈：HelloAgents (SimpleAgent, ToolRegistry), Python AST, ModelScope API, Beautiful Soup, DuckDuckGo/Brave/Ecosia/Searx
关键文件：main.ipynb, main.py, src/agents/agent_universal.py, src/tools/browser_tool.py

---

### healer-666-Academic-Data-Agent
描述：面向科研场景的智能数据分析 Agent，支持 csv/xls/xlsx 表格分析与 PDF 文献主表提取分析，含轻量审稿治理功能。
技术栈：Hello-Agents, Scientific ReAct, pandas/numpy/scipy, matplotlib/seaborn, pdfplumber/pypdf, TavilySearchTool
关键文件：main.ipynb, src/agents/, src/services/

---

### huailishang-AgentPlatformBase
描述：双智能体任务平台（搜索员 deep_research + 资讯员 rss_digest），基于 FastAPI 统一后端，支持后台长任务执行、前端轮询。
技术栈：FastAPI/Uvicorn, hello-agents, Tavily/DDGS, RSS 解析, HTML/CSS/JS 前端, Pydantic
关键文件：backend/main.py, agents/deep_research/, agents/rss_digest/, frontend/, smoke_test.py

---

### jack6249-GiftGeniusAgent
描述：智能送礼助手，多智能体流水线（军师→猎人→编辑）协作，支持 MBTI/星座心理分析、自动比价与平替查找。
技术栈：HelloAgents (SimpleAgent), Tavily Search API, 百度优选 MCP, python-dotenv, numpy
关键文件：main.ipynb, user_profile.json, outputs/gift_plan_output.md, protocol_tools/

---

### JJason-DeepCastAgent
描述：自动化播客生成智能体，从深度研究到音频节目的全自动化引擎，支持全网调研、脚本策划、高品质语音合成。
技术栈：HelloAgents (Plan-and-Solve), FastAPI, Vue 3/Vite/TypeScript, Tavily/SerpApi, ECNU-TTS, FFmpeg/Pydub
关键文件：backend/src/main.py, backend/src/agent.py, frontend/src/, backend/services/

---

### jjyaoao-CodeReviewAgent
描述：基于 HelloAgents 框架的智能代码审查助手，自动分析 Python 代码质量、发现潜在问题并提供优化建议和审查报告。
技术栈：HelloAgents (SimpleAgent), Python AST, OpenAI API
关键文件：main.ipynb, data/sample_code.py, outputs/review_report.md

---

### kkkano-FinReportAgent
描述：基于 HelloAgents 的金融研报生成智能体，自动收集多源数据（Yahoo Finance + DuckDuckGo 搜索）并生成投资分析报告。
技术栈：HelloAgents (ReAct), DuckDuckGo Search, Yahoo Finance (yfinance), DeepSeek/OpenAI API
关键文件：main.ipynb, requirements.txt, .env.example

---

### laoyouf-aistory
描述：智能故事生成器，根据用户输入的文体、主题、风格生成对应文体的故事（小说/剧本/诗歌），适用于娱乐场景。
技术栈：HelloAgents 框架
关键文件：main.ipynb, requirements.txt, .env.example

---

### lgs-only-NovelGenerator
描述：基于 HelloAgents 的智能小说辅助创作系统，支持智能大纲生成、上下文感知章节生成、多章连续创作和内容管理系统。
技术栈：HelloAgents (SimpleAgent), FastAPI, Pydantic, Markdown/JSON 文件存储, OpenAI 兼容 API
关键文件：src/app.py, agents/outline_agent.py, agents/chapter_generate_agent.py, frontend/index.html, main.py

---

### lh2021739-pixel-Personal_Information_Signaling_System
描述：个人信息维度化系统，通过写日报/周报/月报 → LLM 提取维度 → 分析维度 → 自动修正 YouTube 搜索主题（themes）的完整闭环。
技术栈：Python, LLM (ModelScope API), YAML 配置, tkinter 桌面提醒, 定时任务 (Windows Task Scheduler)
关键文件：write_report.py, extract_dimensions.py, analyze_dimensions.py, daily_reminder.py, manage_themes.py, themes.yaml

---

### lll0807-CodeTutorAgent
描述：基于多智能体协作的智能编程导师系统（TutorAgent），支持学习路径规划、RAG 出题、代码评审与学习记忆回顾。
技术栈：HelloAgents (A2A), LLM (OpenAI/本地), RAG, 长短期 Memory, NoteTool, Python 3.10+
关键文件：main.py, agents/, programmer/README.md

---

### megg-ops-roleplay_agent
描述：沉浸式角色扮演智能体（Python 版），允许用户与自定义角色对话，支持多种兼容 OpenAI API 格式的模型和多个角色切换。
技术栈：Python 3.8+, OpenAI Python SDK, python-dotenv
关键文件：roleplay_agent.py, requirements.txt, .env.example

---

### meiguanxiHXX-historyReviewAgent
描述：多角色历史辩论智能体，采用五角色人设 + 终局综合模板，对历史议题进行多视角思辨与分析，可选维基检索作为考据附录。
技术栈：FastAPI, OpenRouter/OpenAI, Python, HTML/CSS/JS 前端
关键文件：historical_review/run_agent.py, run_web.py, historical_review/web/

---

### melxy1997-ColumnWriter
描述：基于 HelloAgents 的智能专栏写作系统，采用多智能体/多设计模式（Plan-and-Solve, ReAct, Reflection），自动完成专栏的规划、撰写、评审和优化。
技术栈：HelloAgents (Plan-and-Solve, ReAct, Reflection), MCP (Model Context Protocol), Tavily/SerpApi, GitHub API, Python 3.10+
关键文件：main.py, orchestrator.py, agents.py, models.py, config.py, prompts.py

---

### pamdla-MindEchoAgent
描述：情绪驱动的音乐推荐智能体（MindEchoAgent），基于深度情绪识别而非简单标签匹配，用 AI 感知心情、用音乐温暖心灵。
技术栈：hello-agents >= 0.2.7, gradio >= 4.0, Python 3.10+, json/datetime
关键文件：main.py, src/agents/mind_echo_agent.py, src/tools/mood_music_tool.py, src/tools/text_comfort_tool.py

---

### Shawnxyxy-HealthRecordAgent
描述：基于 HelloAgents 与 FastAPI 的多智能体健康档案助手，支持体检报告解读、饮食推荐与执行反馈闭环，可选 Milvus 语义检索 + SQLite 长期记忆。
技术栈：HelloAgents (HelloAgentsLLM), FastAPI, Milvus, SQLite, Pydantic, HTML/CSS/JS 前端
关键文件：backend/api/main.py, backend/agents/, backend/service/, backend/memory/, frontend/

---

### tino-chen-HelloClaw
描述：基于 Hello-Agents 的个性化 AI Agent 应用（类似 OpenClaw），支持身份定制、长期/每日记忆系统、流式工具调用和多会话管理。
技术栈：Hello-Agents (ReActAgent/SimpleAgent), FastAPI, Vue 3/TypeScript/Ant Design Vue, SSE 流式通信
关键文件：src/agent/helloclaw_agent.py, src/memory/, src/api/, frontend/, main.ipynb

---

### usernamedadad-AutoFlow
描述：智能流程图生成工具，从自然语言到 Mermaid 流程图一键生成并实时预览，支持灵感模式、标准模式、计划模式和代码模式。
技术栈：HelloAgents, FastAPI + SSE, React + Vite + Mermaid
关键文件：backend/app/main.py, backend/app/agents/mermaid/, frontend/src/App.jsx, frontend/src/services/

---

### xujikai-SentenceExpandAgent
描述：基于多智能体协作的英语写作教练，通过记者提问法将简单英文句子逐步扩写为高级长句，支持手动模式和自动模式。
技术栈：Vue 3/TypeScript/Vite, FastAPI, HelloAgents (多智能体), SSE 流式传输, Pydantic
关键文件：backend/src/main.py, backend/src/agents/, frontend/src/views/, frontend/src/components/

---

### Yixiang-Wu-LearningAgent
描述：基于 HelloAgents 框架的个性化学习助手，支持学习计划生成、知识管理、互动学习和进度追踪，采用三层 Agent 架构。
技术栈：HelloAgents (SimpleAgent, ReActAgent, ReflectionAgent), Python, pytest/black/mypy/flake8, 流式输出
关键文件：main.py, core/, agents/, specialist/, cli/, tests/

---

### YYHDBL-HelloCodeAgentCli
描述：面向本地代码仓库的智能 Code Agent 命令行工具，提供类似 Claude Code/Codex 的交互体验，专注安全智能的代码操作。
技术栈：HelloAgents (ReAct, Plan-Solve, Reflection), LLM (OpenAI/DeepSeek/Qwen), GSSC 上下文流水线, 多层记忆系统
关键文件：code_agent/hello_code_cli.py, code_agent/agentic/code_agent.py, agents/, tools/, memory/

---

### zjzhou-SREOnCallAgent
描述：AI 驱动的 SRE 值班助手，通过三阶段智能体流水线（Plan-and-Solve → ReAct → Reflection）自动完成告警分诊、根因调查和故障复盘报告生成。
技术栈：HelloAgents (Plan-and-Solve, ReAct, Reflection), FastAPI/Uvicorn, JSON/YAML 模拟数据
关键文件：main.ipynb, src/api/main.py, src/agents/pipeline.py, src/agents/investigation_agent.py, src/tools/

---

### EXAMPLE-ProjectTemplate
描述：项目模板示例，供社区成员参考项目结构和 README 规范。
技术栈：N/A（模板）
关键文件：README.md
