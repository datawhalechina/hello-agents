# TraceableCodeAgent (Learning Project)
具有完整回溯能力的代码分析与改进智能体，可以返回路线。
这是一个用于学习智能体工作流的实践项目：
- 基于 HelloAgents 的 ReActAgent
- 增加了可追溯的 Research Map（步骤图）
- 支持工具调用记录、步骤回溯、基础产物关联
- 提供 Smoke Test 与 Markdown 报告导出

## 1. 项目目标

本项目用于个人学习与科研入门，重点不是“做一个最强 Agent”，而是理解并跑通一条完整工作流：

1. 接收用户任务
2. LLM 推理（Thought）
3. 工具调用（Read/Write 等）
4. 观察结果（observation）
5. 将过程结构化记录到 Research Map
6. 输出最终结果与可读报告

## 2. 核心能力

- ReAct 主流程对齐
  - 使用 `ReActAgent.run()` 的真实工具执行链路
- Research Map 追踪
  - 每个步骤包含：`step_id`、`parent_step_id`、`step_type`、`task`、`thought`、`action`、`observation`、`status`
- 工具调用标准化
  - 对接 `ToolResponse`（status/text/data/error）
- 回溯查询工具（运行时可调用）
  - `view_step`
  - `traceback_current`
  - `search_steps`
  - `trace_artifact`
  - `list_steps`
  - `get_current_step`
- Smoke Test 输出落盘
  - 自动保存到 `reports/smoke-test-output-*.md`

## 3. 目录结构（关键文件）

- `TraceableCodeAgent.py`：主 Agent 实现
- `ResearchStep.py`：步骤数据结构与序列化
- `ResearchMap.py`：步骤图存储与回溯
- `Smoke_test.py`：最小可运行验证
- `.gitignore`：上传前过滤运行产物与敏感配置

## 4. 快速开始

### 4.1 安装依赖

```powershell
pip install -r requirements.txt
pip install hello-agents
```

### 4.2 配置环境变量

创建 `.env`

```env
LLM_MODEL_ID=your-model
LLM_API_KEY=your-key
LLM_BASE_URL=your-base-url
LLM_TIMEOUT=60
```

### 4.3 运行 Smoke Test

```powershell
python .\Smoke_test.py
```

成功后会看到：
- 控制台输出 Agent 结果
- `reports/` 下生成 `smoke-test-output-时间戳.md`

## 5. 我学到的工作流

1. 先保证跑通代码，智能体能给输出，至于工具、函数方法注册调用什么的慢慢补
2. 要在初始化、run里面记得更新一些东西，比如记忆、thought
3. 再做可观测性（trace、步骤结构化）
4. 最后补体验与工程细节（报告导出、忽略规则、错误信息），这里摸着石头过河，不断让智能体去提建议去改

## 6. 已知限制

- 异步链路（`arun`/`arun_stream`）的追踪一致性还可以继续增强，目前没有做
- 当前只是学习演示

## 7. 后续计划

- 增强步骤标签与摘要能力，便于长会话检索

## 8. 声明

本仓库用于学习与科研训练场景，代码持续更新中。


## 🤝 贡献指南

欢迎提出Issue和Pull Request！

## 👤 作者

- GitHub: [@AlexenderSokolov](https://github.com/AlexenderSokolov)
- Email: 2060064513@qq.com

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！