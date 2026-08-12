# NetworkHealthReportAgent

基于 Hello-Agents 的多智能体网络健康报告系统，支持地图展示站点、点击查看站点健康报告，并支持默认最近一周与自定义时间窗口查询。

## 📝 项目简介

本项目面向企业网络运维场景，演示如何用多智能体协作生成可读、可执行的网络健康报告。

- 前端（Vue + Leaflet）：展示各站点地理位置，点击站点拉取报告
- 后端（FastAPI）：提供站点、报告、全局问答、流式输出与报告下载 API
- 智能体层（HelloAgents）：

1. 日志分析 Agent
2. 网络设备状态 Agent
3. 网络用户状态分析 Agent
4. 网络健康报告 Agent（综合前 3 个结果）
5. 全局问答 Agent（支持站点问答与报告导出意图）

- MCP 层（FastMCP）：从 data 目录开放站点、设备、日志、终端合规数据读取接口

## ✨ 核心功能

- 地图可视化站点分布，点击站点查看报告
- 默认时间窗口为最近 7 天
- 支持自定义 `start_date` 和 `end_date`
- 假数据覆盖：站点、设备台账、设备状态时序、网络日志、终端合规
- 全局问答界面：可直接提问，例如“有几个site？”“上海有哪些site？”“某个site的设备情况如何？”“帮我生成成都site近一周的报告”
- 问答导出报告：生成 `outputs/*.md`，并返回可下载链接

## 🛠️ 技术栈

- HelloAgents (hello-agents)
- FastAPI
- FastMCP
- Vue 3 + Vite + Leaflet

## 📂 目录结构

```text
monkeyhlj-NetworkHealthReportAgent/
├── README.md                               # 项目说明文档
├── requirements.txt                        # Python 依赖
├── .env.example                            # LLM/模型环境变量模板
├── main.ipynb                              # Notebook 演示入口（7部分 walkthrough）
├── run_api.py                              # FastAPI 启动入口（uvicorn 指向此文件）
├── data/
│   ├── sites.json                          # 站点地理信息（经纬度、区域、等级）
│   ├── device_inventory.json               # 设备台账（交换机/WLC/AP 等）
│   ├── device_status_timeseries.json       # 设备状态时序（在线率、时延、丢包等）
│   ├── network_logs.json                   # 网络日志（告警事件）
│   ├── terminal_compliance.json            # 终端接入与合规数据
│   └── test_cases.json                     # 报告接口测试样例
├── outputs/
│   ├── review_report.md                    # 示例报告
│   └── site-*_YYYY-MM-DD_*.md             # 问答导出的站点周报文件（动态生成）
├── src/
│   ├── __init__.py
│   ├── api/
│   │   └── main.py                         # API 路由（/api/sites /api/reports /api/chat /api/chat/stream /api/outputs）
│   ├── agents/
│   │   ├── base.py                         # Agent 基类，负责 LLM 与 MCPTool 装载
│   │   ├── log_analysis_agent.py           # 日志分析 Agent
│   │   ├── device_status_agent.py          # 设备状态 Agent
│   │   ├── user_status_agent.py            # 用户状态 Agent
│   │   ├── network_health_report_agent.py  # 综合报告 Agent
│   │   ├── site_qa_agent.py                # 全局问答/报告导出 Agent
│   │   └── orchestrator.py                 # 多 Agent 编排与总流程
│   ├── tools/
│   │   ├── data_repository.py              # 数据访问层（读取 data/*.json）
│   │   └── data_mcp_server.py              # MCP 服务，向 Agent 暴露数据工具
│   └── utils/
│       └── date_utils.py                   # 日期窗口处理（默认最近 7 天）
└── frontend/
    ├── package.json                         # 前端依赖和脚本
    ├── vite.config.js                       # Vite 开发配置
    ├── index.html
    └── src/
        ├── main.js                          # 前端入口
        ├── App.vue                          # 页面主视图（左地图+下报告+右问答）
        ├── api.js                           # 后端 API 调用与地址探测
        ├── styles.css                       # 页面样式
        └── components/
            ├── SiteMap.vue                  # 地图组件
            └── ReportPanel.vue              # 报告展示组件
```

说明：目录树中省略了 `venv/`、`__pycache__/`、`.idea/`、`memory/` 等运行时或本地环境目录。

## 🤖 运行模式说明

系统支持两种模式：

1. 无 LLM 模式（可直接演示）

- 不配置 LLM_API_KEY / OPENAI_API_KEY 也能运行。
- 报告由本地规则逻辑生成，适合离线演示和开发联调。

2. LLM 模式（推荐）

- 需要配置 API Key。
- Agent 会实例化 HelloAgentsLLM，并尝试挂载 MCP 数据工具（不同 hello-agents 版本自动兼容）。

## 🔐 LLM 启动方式（重点）

### 1) 准备环境变量

先复制模板：

```bash
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
```

然后至少配置以下任意一组：

- 统一配置（推荐）

```env
LLM_MODEL_ID=gpt-4o-mini
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT=60
```

- OpenAI 兼容配置（备选）

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

说明：当前代码在 agents/base.py 中通过以下逻辑判断是否启用 LLM：

- 读取 LLM_API_KEY 或 OPENAI_API_KEY
- 有 Key：创建 HelloAgentsLLM
- 无 Key：降级到无 LLM 模式

### 2) 启动后端

```bash
uvicorn run_api:app --reload --port 8000
```

### 3) 验证 LLM 是否生效

- 可先访问健康检查：

```bash
curl "http://localhost:8000/api/health"
```

- 再请求任意站点报告，确认接口返回正常：

```bash
curl "http://localhost:8000/api/reports/site-sh-fin"
```

## 🚀 快速开始

### 1) Python 环境和依赖

```bash
pip install -r requirements.txt
```

### 2) 配置环境变量

```bash
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
```

如果要启用 LLM 模式，请在 .env 配置 LLM_API_KEY（或 OPENAI_API_KEY）。

### 3) 启动后端 API

```bash
uvicorn run_api:app --reload --port 8000
```

API 入口：`http://localhost:8000`

- 站点列表：`GET /api/sites`
- 单站报告：`GET /api/reports/{site_id}`
- 参数：`start_date`、`end_date`（格式 `YYYY-MM-DD`）
- 全站报告：`GET /api/reports`
- 问答接口：`POST /api/chat`
- 流式问答接口：`POST /api/chat/stream`
- 报告文件下载：`GET /api/outputs/{filename}`
- 运行时状态：`GET /api/runtime`

### 4) 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

## 📖 使用示例

查询上海站点最近一周报告：

```bash
curl "http://localhost:8000/api/reports/site-sh-fin"
```

查询深圳站点自定义时间窗口：

```bash
curl "http://localhost:8000/api/reports/site-sz-ops?start_date=2026-05-23&end_date=2026-05-29"
```

查询全部站点报告：

```bash
curl "http://localhost:8000/api/reports"
```

让问答 Agent 生成某个站点近一周报告，并返回可下载文件：

```bash
curl -X POST "http://localhost:8000/api/chat" \
	-H "Content-Type: application/json" \
	-d '{
		"question": "帮我生成 site-sh-fin 近一周的报告",
		"site_id": "site-sh-fin",
		"start_date": "2026-05-23",
		"end_date": "2026-05-29"
	}'
```

返回结果里会包含 `artifact.download_url`，前端会把它展示成下载链接，生成文件默认保存在 `outputs/` 目录下。

全局问答示例：

```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
	-H "Content-Type: application/json" \
	-d '{
		"question": "上海有哪些 site？",
		"start_date": "2026-05-23",
		"end_date": "2026-05-29"
	}'
```

如果当前选中了某个站点，问题里写“帮我生成当前站点近一周报告”也可以直接触发文件生成。

## 🧪 Notebook 使用

```bash
jupyter lab
```

打开 main.ipynb：

- 第 1 部分：项目介绍
- 第 2 部分：环境配置
- 第 3 部分：工具定义（`SiteQuickLookupTool`）
- 第 4 部分：智能体构建（`NetworkHealthOrchestrator` + 可选 `demo_agent`）
- 第 5 部分：功能演示（问答、报告、导出下载链接）
- 第 6 部分：性能评估（可选）
- 第 7 部分：总结与展望

## 🎯 项目亮点

- 从数据层到 Agent 层可追溯：每个结论都有原始指标依据
- MCP 抽象数据访问接口，便于后续替换真实数据源
- 前后端解耦，便于扩展告警中心、工单系统和趋势大屏

## 🔮 下一步建议

- 接入真实设备数据源（SNMP/Telemetry/NetFlow）
- 引入时序库存储并做趋势预测
- 加入报告导出（PDF/Markdown）和自动推送（邮件/飞书）

## 🧰 常见问题

1. 报错 cannot import name MCPTool

- 原因：hello-agents 不同版本导出路径不一致。
- 现状：base.py 已做兼容探测，找不到会自动降级，系统仍可运行。

2. 接口能访问但不是 LLM 风格输出

- 原因：未配置 LLM_API_KEY/OPENAI_API_KEY，系统在无 LLM 模式下运行。
- 处理：补齐 .env 后重启 uvicorn。

3. 问答能回答，但“导出站点周报”失败

- 原因：导出周报场景要求 LLM 可用；若 LLM 未启用或调用失败，会返回提示且不生成文件。
- 处理：确认 `.env` 中 `LLM_API_KEY`（或 `OPENAI_API_KEY`）有效，并检查模型可访问性。

4. 前端请求失败（CORS 或连接失败）

- 检查后端是否已启动在 8000 端口。
- 检查前端是否在 5173 端口运行。

5. MCP Server 需要单独启动吗

- 一般不需要。当前项目通过 `MCPTool(server_command=[...])` 由 Agent 在调用时自动拉起。
- 仅在你要单独调试 MCP 服务时，才手动运行：

```bash
python -m src.tools.data_mcp_server
```

## 📄 许可证

MIT License

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！
