# 智能求职助手

基于多 Agent 协作的智能求职规划应用。输入你的求职需求，四个 AI Agent 分工协作，自动生成包含职位推荐、公司分析、薪资行情、每日任务和面试准备的完整求职策略报告。

## 功能

- **职位搜索** — 根据目标职位、城市和偏好搜索匹配岗位
- **公司研究** — 分析目标公司的背景、文化、融资和发展前景
- **薪资查询** — 查询行业薪资水平，为薪资谈判提供参考
- **求职规划** — 整合全部信息，输出每日任务、简历建议和面试准备清单

## 界面预览

打开浏览器后在左侧填写求职需求，点击生成按钮，右侧展示完整报告：推荐职位卡片、公司分析、薪资行情、每日任务（按天分 Tab）、简历优化建议和面试准备清单。

## 架构

```
用户界面 (Streamlit)
    ↓ 调用 Agent
智能体层 (HelloAgents + 4 个 Agent)
    ├── JobSearchAgent      职位搜索（Brave Search MCP）
    ├── CompanyResearchAgent  公司研究（Brave Search MCP）
    ├── SalaryAgent          薪资查询（Brave Search MCP）
    └── CareerPlanAgent      整合规划（纯 LLM 推理）
    ↓ MCP / SDK
外部服务 (Brave Search API / LLM API)
```

每个 Agent 专注单一职责，共享一个搜索工具实例，避免重复启动和 API 限流。

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js（Brave Search MCP 需要 npx）

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
# DeepSeek（或其他兼容 OpenAI SDK 的 LLM）
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=你的DeepSeek_API_Key
LLM_BASE_URL=https://api.deepseek.com/v1/
LLM_TIMEOUT=60

# Brave Search（可选，不填则 Agent 使用 LLM 内置知识）
# 免费额度 2000次/月，申请地址：https://brave.com/search/api/
BRAVE_SEARCH_API_KEY=
```

### 4. 启动应用

```bash
cd backend
streamlit run streamlit_app.py
```

浏览器打开 http://localhost:8501 即可使用。

### 5. 其他启动方式

如果只需要 API 服务（不需要界面），运行：

```bash
python run.py
```

FastAPI 文档在 http://localhost:8000/docs，提供 `POST /api/career/plan` 接口。

## 项目结构

```
career-agent/
├── README.md
├── .gitignore
└── backend/
    ├── .env.example                # 环境变量模板
    ├── requirements.txt            # Python 依赖
    ├── run.py                      # FastAPI 启动入口
    ├── streamlit_app.py            # Streamlit 界面入口
    └── app/
        ├── config.py               # 配置管理
        ├── agents/
        │   └── career_planner_agent.py   # 4 个 Agent + 协作逻辑
        ├── models/
        │   └── schemas.py          # Pydantic 数据模型
        ├── api/
        │   ├── main.py             # FastAPI 主应用
        │   └── routes/
        │       └── career.py       # /api/career/plan 路由
        └── services/
            └── llm_service.py      # LLM 服务封装
```

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Streamlit |
| 后端 API | FastAPI + Pydantic |
| Agent 框架 | HelloAgents |
| 工具协议 | MCP (Model Context Protocol) |
| 搜索引擎 | Brave Search API |
| LLM | DeepSeek / OpenAI 兼容接口 |

## 工作原理

1. 用户在界面填写求职需求（职位、城市、经验、偏好等）
2. **JobSearchAgent** 调用搜索引擎查找匹配的招聘信息
3. **CompanyResearchAgent** 从职位结果中提取公司名，逐一研究公司背景
4. **SalaryAgent** 查询目标职位在当前城市的薪资行情
5. **CareerPlanAgent** 整合前三者的输出，生成结构化的求职策略报告
6. 结果以卡片、表格、标签页等形式美观展示

如果未配置 Brave Search API Key，各 Agent 会自动降级使用 LLM 训练数据中的知识。

## License

MIT
