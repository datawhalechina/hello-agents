# MeetingActionAgent

> 使用两个 HelloAgents 智能体，把会议文字记录整理成可追溯、可执行的会议纪要。

## 项目简介

这是一个生产力工具类的双 Agent 小项目。范围比较简单：输入一段中文会议记录，然后完成下面四步：

1. `MinutesAgent` 提取会议日期、摘要、决策、行动项和待确认问题。
2. `ReviewAgent` 对照原文检查遗漏、编造和日期冲突。
3. 审核未通过时，系统最多修正一次。
4. 最终生成结构化 JSON 和易读的 Markdown 会议纪要。

第一版有一条明确规则：原文没有的信息不猜。未知负责人或日期会显示为“未提供”。

## 核心功能

- 双 Agent 顺序协作：提取与审核职责分离
- Pydantic 数据校验：及时发现缺字段和错误类型
- 有限重试：最多四次模型调用，不会无限循环
- 证据追溯：每个行动项保留对应原文

## 工作流程

```text
会议文字记录
  → MinutesAgent 生成结构化草稿
  → ReviewAgent 对照原文审核
  → 必要时修正并复核一次
  → 保存 JSON 与 Markdown
```

## 项目结构

```text
Henry2513-MeetingActionAgent/
├── README.md
├── requirements.txt
├── main.ipynb
├── .env.example
├── .gitignore
├── data/
│   ├── sample_meeting.txt
│   └── edge_case_meeting.txt
└── outputs/
    ├── example_result.json
    └── example_minutes.md
```

## 快速开始

### 环境要求

- Python 3.11+
- 一个可用的 OpenAI-compatible LLM API

### 1. 创建环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. 配置模型

复制 `.env.example` 为 `.env`，填写一个 OpenAI-compatible 模型服务：

```dotenv
LLM_MODEL_ID=your-model-id
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-provider.example/v1
```

`.env` 已被 Git 忽略，禁止提交真实密钥。

### 3. 运行 Notebook

```powershell
jupyter lab
```

打开 `main.ipynb`，确认内核使用当前项目的 `.venv`，然后从上到下运行。

Notebook 会直接调用真实模型分析 `data/sample_meeting.txt`。
请从 `Henry2513-MeetingActionAgent` 项目目录启动 Jupyter；Notebook 不兼容其他工作目录。

## 输入与输出

默认输入是 UTF-8 `.txt` 文件，也可以在 Notebook 中直接替换为粘贴的文本。

输出包含：

- `MeetingResult` JSON：包含会议日期、摘要、决策、行动项和待确认问题
- Markdown 会议纪要：便于人阅读和分享
- 审核状态：`passed` 或 `needs_manual_review`

## 使用示例与测试

- `data/sample_meeting.txt`：正常会议，包含明确任务和负责人。
- `data/edge_case_meeting.txt`：包含模糊建议、日期冲突和缺失负责人。
- Notebook 自检覆盖 JSON 代码围栏、缺失可选字段、空行动项、空输入和非法优先级。
- `outputs/` 中的文件是正常会议的示例结果，可用于理解输出格式。

## 技术栈

- Python 3.11+
- HelloAgents 0.2.9
- Pydantic 2
- JupyterLab

## 项目亮点

- 提取与审核分开执行，ReviewAgent 必须回到会议原文逐项核对。
- 每个行动项保留原文证据，方便人工确认结果是否可靠。
- 整个流程最多调用模型四次，并且只允许一次审核后修正。

## 性能评估

本项目是入门规模的流程验证，没有进行大规模准确率基准测试。提交前使用 `data/sample_meeting.txt` 完成了一次真实运行：

- 共调用模型 2 次，最终审核状态为 `passed`。
- 提取 4 个行动项和 1 个已确认决策。
- 4 条行动项证据都能在会议原文中找到。
- Notebook 的 6 组离线自检全部通过。

实际响应时间会受到所选模型和 API 服务状态影响，因此不在这里给出固定数值。

## 当前限制

- 只处理文字记录，不处理录音或实时会议。
- 不搜索互联网，也不使用数据库、RAG、MCP 或长期记忆。
- LLM 输出存在不确定性；`needs_manual_review` 的结果必须人工确认。
- 示例数据均为虚构内容，不应输入敏感会议数据。

## 未来计划

- [ ] 增加日期标准化工具，同时保留原文日期用于核对。
- [ ] 支持连续处理多份会议记录并分别保存结果。

## 贡献指南

欢迎通过 Issue 或 Pull Request 提出问题和改进建议。

## 许可证

遵循 Hello-Agents 仓库的 CC BY-NC-SA 4.0 License。

## 作者

- GitHub: [@Henry2513](https://github.com/Henry2513)

## 致谢

感谢 Datawhale 社区和 Hello-Agents 项目提供的教程与框架。
