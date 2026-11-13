# CodeAssistantAgent · 本地代码助手

基于 HelloAgents 的桌面代码助手，支持为项目添加中文代码注释，并生成项目说明、架构图、流程图和时序图。

![客户端首页](docs/screenshots/home.png)

## 核心功能

- **代码注释**：为项目源码添加中文文件头和逐函数说明，校验后自动应用。
- **项目解析**：依据真实代码生成 `项目说明.md` 和 `docs/diagrams/` 中的图说明及三张 PNG。
- **修改管理**：保留 Diff、图片预览和撤销记录，写入前检查文件版本冲突。
- **任务管理**：查看进度和历史、停止任务；代码注释任务中断后可继续执行。
- **桌面入口**：点击菲比悬浮挂件打开客户端，支持拖入项目和配置多个模型连接。

注释和解析仅静态处理，不运行目标项目或测试。PNG 由 Pillow 在本地绘制，无需模型具备生图能力。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 桌面客户端 | Electron、React、TypeScript、Vite |
| 本地服务 | Python、FastAPI、HTTP + SSE |
| 模型与工具 | HelloAgentsLLM、ToolRegistry，自定义任务循环 |
| 数据与绘图 | SQLite、系统凭据库、Pillow |

[架构图](docs/diagrams/architecture.png) · [流程图](docs/diagrams/workflow.png) · [时序图](docs/diagrams/sequence.png) · [设计说明](docs/diagrams/README.md)

## 快速开始

需要 **Python 3.11+、Node.js 22.12+**，当前主要在 Windows 验证。在仓库根目录打开 PowerShell：

```powershell
cd .\Co-creation-projects\minibeartwo-CodeAssistantAgent
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Dev
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

首次运行需要安装依赖，之后只需执行启动命令。`-Dev` 安装测试依赖；开发热更新使用 `.\start.ps1 -Dev`。

启动后点击菲比打开或收起客户端，右键可配置模型或退出。关闭客户端窗口会回到挂件，退出程序请使用挂件右键菜单。

若 Electron 下载失败，可设置镜像后重新安装：

```powershell
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
.\setup.ps1 -Dev
```

## 使用方法

1. 打开“模型设置”，填写 API 地址、模型名称和 API Key，保存连接。模型服务需支持 OpenAI 兼容的原生工具调用（`tools/tool_choice`）。
2. 拖入项目文件夹，选择“代码注释”或“项目解析”，补充需求后开始处理。可先使用 [计算器示例](examples/buggy-calculator/README.md) 体验。
3. 校验通过后自动应用结果，在任务面板查看修改或撤销。处理过程中可停止，注释任务可通过“继续执行”恢复。

新配置默认最多执行 **1000 步**，可自行调整；任务无总时间上限。API Key 优先保存在系统凭据库，不支持时仅在当前会话保留。

项目解析固定生成：

```text
项目说明.md
docs/diagrams/
├── README.md
├── architecture.png
├── workflow.png
└── sequence.png
```

项目解析不修改源码和原有 README；遇到文件版本冲突会停止写入。Python 注释有静态校验，生成内容仍需结合实际代码核对。

## 项目结构与验证

`backend/` 为本地服务，`desktop/` 为客户端，`skills/` 保存注释技能，`tests/` 为测试，`docs/` 为截图与设计图。

在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -E -X utf8 -m pytest -q
cd desktop
npm run build
npm run test:desktop
npm run test:bubble
```

桌面流程测试使用本地模拟模型，不消耗云端额度。[main.ipynb](main.ipynb) 提供无需模型密钥的补丁应用与撤销演示；运行前执行 `.\setup.ps1 -Notebook`，再用 `.\.venv\Scripts\python.exe -E -m jupyterlab main.ipynb` 打开。

## 作者

[@minibeartwo](https://github.com/minibeartwo) · 遵循 [Hello-Agents 共创规范](../README.md) · [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
