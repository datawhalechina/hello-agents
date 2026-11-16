# 溯流 · Workflow Atlas

面向聊天导出记录的工作流重建工作台，支持消息导入、项目图谱、原文证据、人工审核与模型分析。适用于学习多阶段智能体编排、企业消息分析和可追溯的信息提取。

## 核心功能

- 导入飞书、微信、QQ 等平台的 JSON、JSONL、CSV、TSV、TXT 和静态 HTML 导出，提供预检、冲突诊断与去重。
- 本地六阶段流程依次完成信息过滤、事实提取、项目解析、关系解析、工作流重建和原文证据核验。
- 查看项目、节点、时间线、消息引文和版本，人工接受或驳回事实，导出 JSON、JSONL 与人工审核后的训练样本。
- 可选接入 OpenAI 兼容模型，生成自然 Markdown 回答、表格和 Mermaid 图示，并支持缓存、取消和显式触发的交互事实图谱。
- 通过 FastAPI、SQLite 与 React 提供本地持久化工作台，支持来源范围筛选和整批来源删除。

## 技术栈与 HelloAgents 使用

后端使用 Python、FastAPI、Pydantic 和 SQLite，前端使用 React、TypeScript、Vite、Mermaid 和 DOMPurify。

`backend/app/agents/orchestrator.py` 使用真实 HelloAgents `Tool`、`ToolRegistry`、`ToolResponse` 编排六个有界阶段。默认 `local-demo` 使用确定性规则，可用模拟数据完整运行。兼容远程提取路径使用 `SimpleAgent.run_as_subagent`，工作台的完整来源分析另有直接模型回答路径。框架依赖固定到 `c597a7ca46ea9969e5b21d9e130549ab69626ff9`。

## 快速开始

### 环境

使用 Python 3.13、Git、Node.js 24 和 npm。项目 Python 声明范围为 `>=3.12,<3.14`。所有命令均在本项目子目录 `Co-creation-projects/Nicola-WK-WorkflowAtlas` 内执行。

### Notebook 演示

```bash
python -m venv .venv
# Windows PowerShell
.venv/Scripts/Activate.ps1
# macOS / Linux
# source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip install jupyterlab
jupyter lab main.ipynb
```

选择该虚拟环境的 Python 内核，依次运行全部单元格。Notebook 加载项目自带的 29 条模拟消息，执行六阶段流程，展示项目和精确引文，并以临时数据库验证 API 导入、分析和训练导出。默认演示使用本地规则与模拟数据。

### Windows 完整工作台

```powershell
.\scripts\setup.ps1
$env:WORKFLOW_ROOT = (Get-Location).Path
.\scripts\start.ps1
```

打开 http://127.0.0.1:8000，点击「导入模拟数据」。API 文档位于 http://127.0.0.1:8000/docs。`WORKFLOW_ROOT` 应指向当前项目子目录，用于定位模拟数据和前端构建产物。

### macOS / Linux 完整工作台

在已安装 Python 依赖的环境中执行以下命令。

```bash
npm ci --prefix frontend
npm run build --prefix frontend
export WORKFLOW_ROOT="$PWD"
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

### 模型配置

本地演示可直接运行。需要模型分析时，在「大模型设置」填写 OpenAI 兼容 Base URL、模型 ID 和自己的 API Key，测试连接成功后显式授权数据发送，再保存并启用模型。随后选择单个来源并点击「更新工作流」。密钥在本地加密保存，原始消息与人工审核状态存储在本地 SQLite 中。

飞书同步需要单独配置合法的只读访问令牌并启用同步。平台导出文件可直接通过导入界面处理。格式与接口见 [多平台导入说明](docs/platform_import.md) 和 [接口契约](docs/interfaces.md)。

## 使用示例

```python
from pathlib import Path
from app.connectors.local import parse_messages
from app.agents.orchestrator import WorkflowOrchestrator

messages = parse_messages(
    Path("data/fixtures/demo_messages.json").read_text(encoding="utf-8"),
    "demo-feishu",
)
result = WorkflowOrchestrator(provider="local-demo").analyze(messages)
print([project.name for project in result.proposal.projects])
print(len(result.agent_results))
```

模拟数据的项目名称为「北辰门户」和「星河数据平台」，阶段数为 6。提取出的事实初始状态为 `pending`，原文引用通过核验且由人工接受的事实才可进入训练导出。更多可运行步骤见 `main.ipynb`。

## 验证

```bash
python -m pytest
python -m unittest discover -s backend/app/connectors/tests -v
python -m evaluation.run --strict
npm run build --prefix frontend
```

执行前按上文设置 `WORKFLOW_ROOT`。`evaluation` 使用受控模拟样本评估过滤、事实字段、显式关系和引文完整性，泛化效果需要另外评估。Notebook 演示与自动化测试使用模拟数据或测试替身，真实飞书授权、真实模型效果和容器运行仍需在对应环境验收。

本次共创提交在 Windows 本地环境完成以下验证。

- `python -m pytest -q` 通过 553 项。
- 连接器 `unittest` 通过 37 项。
- `evaluation.run --strict` 通过，受控样本的 49 条引文核验通过。
- `npm ci` 与前端 TypeScript / Vite 生产构建通过。
- `main.ipynb` 的 4 个代码单元顺序执行通过，演示输出保存在 Notebook 中。

测试出现 1 条 Starlette/httpx 弃用提示，构建出现大于 500 kB 的分块提示。测试和构建均正常完成。

## 项目结构

```text
main.ipynb          可运行的本地演示
backend/app/       API、连接器、HelloAgents 编排、提取、图谱与存储
backend/tests/     API、数据边界、模型替身和回归测试
frontend/          React 工作台
data/fixtures/     模拟消息和受控评估标注
evaluation/        受控样本评估
docs/              架构、接口与多平台导入说明
scripts/           Windows 安装、启动和检查脚本
requirements.txt   Python 依赖入口
requirements.lock  固定的依赖版本
```

## 作者与许可

作者为王康，GitHub 账号为 [@Nicola-WK](https://github.com/Nicola-WK)。感谢 Datawhale Hello-Agents 教程和 HelloAgents 框架。

本共创目录按 Hello-Agents 共创项目要求使用 CC BY-NC-SA 4.0，完整文本见 [LICENSE.txt](LICENSE.txt)。依赖分别遵循各自许可，HelloAgents 许可与其他第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
