# ResumeAgent - 中日英三语智能简历生成器

> 基于 HelloAgents 框架的对话式多智能体简历助手：导师追问 → 证据确认 → 岗位版本 → 三语预览与导出

## 📝 项目简介

写一份简历已不易，写三种语言的简历更是灾难——中、日、英三种简历根本不是"互译"，而是三套规范体系：

- **中文**：单页模块化简历，按行业分流个人信息
- **日文**：履歴書 ＋ 職務経歴書 双文档，JIS 固定格式、和暦纪年、照片位
- **英文**：ATS 安全版式 Resume，动词开头、量化成果

ResumeAgent 用**面试式提问**收集求职者信息（用户也可自由补充），沉淀为唯一的结构化事实库，再由确定性渲染器 + LLM 润色器按各语言规范独立生成简历，支持模拟 HR/ATS 评审与 PDF 导出。

### 核心思路

```
Agent 访谈（提问→回答→解析入库）
        ↓
结构化事实库（唯一数据源，改一处三语同步）
        ↓
三语独立生成：中文单页 / 日文双文档 / 英文 ATS 版式（各自规范，而非直译）
        ↓
润色 → 评审 → Markdown / HTML / PDF 导出
```

## ✨ 核心功能

- [x] Agent 访谈式信息收集（缺口驱动提问 + 量化追问 + 回答解析入库）
- [x] 结构化事实库（本地落盘、草稿恢复、防编造约束）
- [x] 和暦换算工具（令和/平成/昭和/大正/明治，正确处理元号切换边界）
- [x] 三语独立生成：履歴書＋職務経歴書（日）/ 单页简历（中）/ ATS Resume（英）
- [x] 每语 3 套可选样式（共 9 种组合），样式画廊一键对比
- [x] 三语润色与摘要（数字一致性自动校验，防篡改）
- [x] JD 解析定制：关键词提取 → 缺口标注 → 定制建议报告
- [x] 导师式证据访谈核心（六维质量门槛、单点追问、确认后入库）
- [x] 多版本管理核心（创建、切换、克隆、重命名、删除、过期检测）
- [x] 模拟 HR / ATS 评审（四项评分 + 问题 + 建议）
- [x] Web 实时预览与 Markdown / HTML / DOCX / PDF 导出（A4 版式）

## 🛠️ 技术栈

- HelloAgents 框架（SimpleAgent + Tool + ToolRegistry）
- LLM：DeepSeek（OpenAI 兼容接口，可换 Qwen / Kimi / Ollama）
- PDF：本机 Chrome / Edge headless
- DOCX：python-docx
- Web：FastAPI、原生 ES Modules、HTTPX（Streamlit 作为可选旧界面）
- 其他：python-dotenv、Jupyter Notebook
- 导师核心：Pydantic 2、SQLite、pytest

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Google Chrome 或 Microsoft Edge（仅 PDF 导出需要；其他格式不受影响）

### 安装依赖

```bash
pip install -r requirements.txt
```

> 说明：`hello-agents` 自 1.0.0 起不再提供 `[all]` extra，直接安装基础包即可。

开发导师核心时使用可编辑安装：

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
```

只运行 Web、事实库和简历导出（不安装 LLM Agent）可以使用：

```bash
python3 -m pip install -e '.[web]'
```

运行完整导师产品使用：

```bash
python3 -m pip install -e '.[agents,web]'
```

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（默认 DeepSeek，也可换其他 OpenAI 兼容服务）
```

标准 API 入口会读取项目目录下的 `.env`，但不会覆盖终端中已经导出的环境变量。需要配置：

| 变量 | 说明 |
|---|---|
| `LLM_MODEL_ID` | 模型 ID，例如 `deepseek-chat` |
| `LLM_API_KEY` | API 密钥；兼容旧变量 `DEEPSEEK_API_KEY` |
| `LLM_BASE_URL` | OpenAI 兼容服务的 HTTP(S) 地址 |
| `LLM_TIMEOUT` | 请求超时秒数，默认 60 |
| `LLM_TEMPERATURE` | 事实抽取温度，默认 0.2 |
| `LLM_MAX_TOKENS` | 单次最大输出 token，默认 2048 |

占位密钥、缺失配置和非法地址不会被接受。API 启动时只构造 Agent，不会自动调用模型或消耗额度。

### 启动完整工作台

安装 Web 开发依赖：

```bash
python3 -m pip install -e '.[dev]'
```

启动 FastAPI 后，原版双栏工作台和 API 会由同一个进程提供：

```bash
uvicorn resume_agent.api.main:app --reload
# 浏览器打开 http://127.0.0.1:8000/
```

- 工作台：`http://127.0.0.1:8000/`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`
- 默认数据库：`data/resume_agent.db`
- 可通过 `RESUME_AGENT_DB=/path/to/file.db` 指定其他数据库

默认入口会按上述环境变量自动构造 HelloAgents 事实审计 Agent 和导师追问 Agent。每次结构化调用都会创建新的 `SimpleAgent`，不共享框架对话历史，避免候选人会话互相污染。由于简历提示可能包含个人敏感信息，HelloAgents 的 trace、session、skills、todo、devlog 和 subagent 持久化在这两个专用 Agent 上默认关闭；业务会话只由 ResumeAgent 自己的 SQLite 仓库管理。没有配置时，事实库、版本管理、预览和导出仍可离线使用；页头会显示“仅离线功能”，回答会先保存，导师恢复后可以继续提炼。

运行状态可以通过 `GET /capabilities` 查看。该接口只返回框架、模型名和功能开关，不返回 API Key 或完整供应商地址。

### 评测导师 Agent

项目内置一套版本化、完全由合成数据组成的导师质量基准。它重点检查的不是回答长度，而是这个 Agent 是否真的像一位可靠导师：一次只问一个问题、追问当前证据缺口、不把团队成绩冒认为个人贡献、不捏造数字、保留估算与敏感标记，并让抽取事实可追溯到用户原话。

配置好上述模型环境变量后运行：

```bash
python -m resume_agent.evaluation.cli \
  --repeats 3 \
  --fail-under 0.90 \
  --output-dir evaluation/reports

# 可编辑安装后也可以使用
resume-agent-eval --repeats 3 --fail-under 0.90
```

也可以通过 `--dataset path/to/cases.jsonl` 比较新的提示词或模型。核心指标包括单问题契约通过率、事实维度准确率、证据保留率、无幻觉率、置信度/敏感信息标签准确率、运行成功率和严格案例通过率。`strict_pass_rate` 低于 `--fail-under` 时命令退出码为 1；配置或数据输入错误时为 2，适合接入 CI。

每次运行会生成同名的 JSON 和 Markdown 报告。报告只记录模型名、框架、案例 ID、检查项和安全的异常类别，不保存测试回答、完整提示词、模型原始输出、API Key 或供应商地址。模型运行有随机性时使用 `--repeats`；同一个案例必须在每次重复中都满足确定性安全检查，才适合作为发布依据。

### 可选：旧版 Streamlit 界面

如需对照旧实现，可在 FastAPI 已运行时另开终端：

```bash
streamlit run streamlit_app.py
```

Web 界面默认连接 `http://127.0.0.1:8000`，可以覆盖：

```bash
RESUME_AGENT_API_URL=http://127.0.0.1:9000 streamlit run streamlit_app.py
```

默认双栏工作台包含四个工作区：

- **导师对话**：默认入口，一次只追问一个证据缺口，候选事实必须确认后入库
- **证据档案**：维护姓名和联系方式，查看六维证据状态和已确认事实，敏感内容默认折叠
- **JD 定制**：针对岗位创建和切换中文、日文、英文投递版本
- **工具**：和暦换算、运行状态和当前版本导出入口

当前档案、经历、版本、语言和工作区只保存必要的选择 ID；回答、事实和手工简历草稿都落在服务端 SQLite，不写入浏览器存储。页面刷新后可恢复访谈与编辑稿。当前问题是幂等读取，HTTP 写操作不会自动重试。

渲染器只使用版本选中的经历，并排除所有未确认事实。估算事实会保留并显示核对警告；事实库更新后，旧版本仍可预览，但会标记为陈旧。中文、英文、日文模板只本地化标题和版式，不会擅自翻译用户事实。日文 Web 版当前生成 `職務経歴書`；需要生日、教育、照片和资格信息的 JIS `履歴書` 将在资料模型扩展后接入。

PDF 由 API 进程调用本机 Chrome 或 Edge 生成。如果没有可用浏览器，PDF 接口返回 HTTP 503，HTML、Markdown 与 DOCX 仍然可以正常导出。

## 📖 使用示例

1. **快速演示**：直接运行全部单元格，会自动完成「访谈 → 解析 → 三语生成 → 样式画廊 → 润色 → 评审 → PDF 导出」全流程，产物在 `outputs/` 目录
2. **选择样式**：运行「样式画廊」单元格后到 `outputs/style_preview/` 对比 9 种组合；在「演示 6」单元格修改 `STYLE_CHOICE` 后重新运行即可换样式导出
3. **真实使用**：把「交互模式」单元格中的 `RUN_INTERACTIVE` 改为 `True`，即可与 Agent 实时对话完善简历
4. **自定义数据**：修改 `data/sample_answers.json` 中的示例求职者信息

## 🧭 导师核心架构

新版核心把“问问题”和“判断该问什么”分开：LLM Agent 负责理解用户、抽取候选事实和组织自然语言；确定性程序负责访谈状态、质量评分、跳过规则、事实确认、版本隔离和持久化。默认测试完全离线，不需要 API Key。

每段经历从六个维度评估：情境、个人责任、行动、方法、结果和证据。只有用户确认的事实才进入统一事实库；估算值会保留估算标记，敏感标记与事实可信度分别保存。不同岗位版本只引用统一事实库中的经历，不复制或改写原始事实。

### 接入现有 HelloAgents

导师核心不会在导入时创建模型或读取 API Key。Notebook 可以继续使用已有的 `SimpleAgent`，只需要用核心提供的提示词分别创建事实审计 Agent 和问题生成 Agent，再通过适配器接入：

```python
from hello_agents import SimpleAgent
from resume_agent import (
    FACT_AUDIT_PROMPT,
    QUESTION_WRITER_PROMPT,
    build_mentor_agents,
)

audit_agent = SimpleAgent(
    name="事实审计",
    llm=llm,
    system_prompt=FACT_AUDIT_PROMPT,
)
question_agent = SimpleAgent(
    name="导师追问",
    llm=llm,
    system_prompt=QUESTION_WRITER_PROMPT,
)
mentor_agents = build_mentor_agents(audit_agent, question_agent)
```

`mentor_agents.fact_auditor` 和 `mentor_agents.question_writer` 可直接传给 `InterviewService`。模型返回的经历 ID 和事实库版本号不会被信任，这两个值始终由程序状态注入；结构化输出连续两次不合法时会返回可恢复错误。

### 可选样式（每语 3 套）

| 语言 | 样式 | 说明 |
|------|------|------|
| 中文 | 藏青现代（默认）/ 经典墨色 / 清新青碧 | 墨色为衬线宋体版，青碧为现代青绿色调 |
| 日文 | 藏青JIS（默认）/ 墨黑JIS / 蓝灰JIS | 履歴書与職務経歴書同色系联动，JIS 结构不变 |
| 英文 | 青灰Teal（默认）/ 经典黑白 / 现代蓝 | 均为 ATS 安全单栏，仅配色不同 |

演示产物（`outputs/`）：

| 语言 | 文件 |
|------|------|
| 中文 | `resume_zh.md / .html / .pdf` |
| 日文 | `rirekisho_ja.*`（履歴書）、`shokumu_keirekisho_ja.*`（職務経歴書） |
| 英文 | `resume_en.md / .html / .pdf` |
| JD 定制 | `jd_match_report.md`（关键词/匹配/建议） |

## 🎯 项目亮点

- **三语独立生成而非互译**：日文走和暦+双文档+照片位，英文走 ATS 安全版式，从渲染层杜绝"翻译腔"
- **每语独立视觉版式**：中文藏青蓝现代单页（色块标题＋技能标签）、日文 JIS 藏青表单（标题带＋照片位）、英文 ATS 安全单栏青灰强调色——三语排版与配色各自设计，而非同一模板换文案
- **样式自选**：每语 3 套样式、共 9 种组合，CSS 变量驱动（换样式＝换配色），样式画廊一键渲染全部组合供对比挑选
- **JD 定制闭环**：JD 分析师提取关键词/硬性要求/加分项 → 缺口匹配顾问对照事实库标注缺失 → 生成可执行的定制建议报告
- **确定性工具层**：和暦换算、事实库、渲染器全部可离线复现，LLM 只负责语言任务
- **防幻觉约束**：解析与润色均要求"只基于事实、禁止编造"，并有数字一致性自动校验
- **元号边界正确**：1989/2019 等跨年月份按规范切换（昭和64年→平成元年、平成31年→令和元年）

## 📊 性能评估

- 和暦换算：9 组边界用例全部通过（含 1912/1926/1989/2019 切换点）
- 润色数字一致性：中/日/英三语输出与原文数字集合比对，无篡改遗漏
- 本地渲染四份文档：< 0.5s（不含 LLM 调用）

## 🔮 未来计划

- [x] 粘贴目标 JD，自动标注简历缺失关键词
- [x] 多版本管理核心（同一事实库派生多个投递版本）
- [x] 接入结构化 HelloAgents 多智能体提示词
- [x] 提供 FastAPI 服务接口与 OpenAPI 文档
- [x] 提供 Streamlit Web 界面（导师对话、证据档案、投递版本、实时预览）
- [x] 将三语证据渲染器迁移为独立 Python 包并提供预览/导出 API
- [ ] 让 Notebook 改为调用新的公开渲染 API
- [ ] 多模板切换与日文 B5 纸张支持
- [ ] 上传已有简历（PDF/DOCX）解析导入

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@shiyuanyeming-hub](https://github.com/shiyuanyeming-hub)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
