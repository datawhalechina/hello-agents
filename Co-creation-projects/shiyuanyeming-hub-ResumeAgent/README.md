# ResumeAgent - 中日英三语智能简历生成器

> 基于 HelloAgents 框架的对话式多智能体简历助手：Agent 提问收集 → 结构化事实库 → 三语独立生成 → 导出 PDF

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
- [x] Markdown / HTML / PDF 导出（A4 版式，系统 CJK 字体）

## 🛠️ 技术栈

- HelloAgents 框架（SimpleAgent + Tool + ToolRegistry）
- LLM：DeepSeek（OpenAI 兼容接口，可换 Qwen / Kimi / Ollama）
- PDF：Playwright Chromium（备选：本机 Chrome headless / 浏览器打印）
- 其他：python-dotenv、Jupyter Notebook
- 导师核心：Pydantic 2、SQLite、pytest

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 可选：Playwright Chromium（PDF 导出，`playwright install chromium`）

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

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（默认 DeepSeek，也可换其他 OpenAI 兼容服务）
```

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb，按顺序运行全部单元格
```

### 启动 FastAPI 服务

安装开发依赖后运行：

```bash
uvicorn resume_agent.api.main:app --reload
```

- API 默认地址：`http://127.0.0.1:8000`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`
- 默认数据库：`data/resume_agent.db`
- 可通过 `RESUME_AGENT_DB=/path/to/file.db` 指定其他数据库

默认入口不会在导入时读取 LLM API Key，因此事实库、版本管理和确定性追问可以离线使用；提交自然语言回答进行事实抽取前，需要通过 `create_app(..., fact_audit_agent=...)` 注入配置好的事实审计 Agent。没有配置时接口会明确返回 HTTP 503，同时保留用户刚提交的消息。

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
- [ ] 提供 Streamlit Web 界面
- [ ] 将现有三语渲染器迁移为独立 Python 包，并让 Notebook 调用公开 API
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
