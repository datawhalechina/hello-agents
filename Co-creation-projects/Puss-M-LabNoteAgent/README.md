# Puss-M-LabNoteAgent · 实验记录整理 Agent

> 一句话：把你随口说的实验记录（参数、结果、标签）自动结构化归档，能检索、能对比、能统计的实验室小管家。

## 📝 项目简介

- **解决什么问题**：做 CV/计算成像实验时，参数和结果常常散落在便签、聊天记录和脑子里——"上次基线是多少来着？"、"这两次跑的有什么区别？"，事后翻找非常痛苦。
- **特色**：自然语言随手记 → 自动结构化入库 → 关键词/标签/日期检索 → 两次实验参数对比 → 库内统计。全程中文对话，笔记本离线可跑。
- **适用场景**：科研实验记录（ Stereo / 标定 / 检测 / 重建……任何带参数和指标的实验）、组内交接、组会前快速回顾。

## ✨ 核心功能

- [x] `save_note`：从随口描述中提炼 标题/参数/结果/标签 并落盘（JSON 笔记库，支持宽松兜底）
- [x] `search_notes`：关键词（标题/参数/结果/原文模糊匹配）、标签、日期前缀检索，最新优先
- [x] `compare_experiments`：两次实验的参数与结果逐项 diff（可传 ID 或关键词）
- [x] `note_stats`：库内统计（总数、最近实验日期、高频标签）
- [x] 多轮对话记忆：追问"上次基线是多少"无需重复上下文

## 🛠️ 技术栈

- [HelloAgents 框架](https://github.com/datawhalechina/hello-agents)：`SimpleAgent`（ReAct 式工具调用 + 对话记忆）+ 自定义 `Tool` 基类（新工具协议：`get_parameters` + `ToolResponse`）
- LLM：任意 OpenAI 兼容接口。本项目附赠 `mini_server.py`（可选）——用本地 Qwen2.5-VL-3B 起一个支持 function calling 的 OpenAI 兼容服务，**零 API 成本离线复现**
- 存储：单文件 JSON（`labnote_data.json`），无需数据库

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 方式 A（在线）：任意 OpenAI 兼容 API 的 KEY
- 方式 B（离线，推荐）：一张 ≥6GB 显存的显卡 + 本地 Qwen2.5-VL-3B（或任意 Qwen2.5 系权重）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置模型后端

**方式 A：云端 API**（创建 `.env` 或直接设环境变量）

```bash
LLM_MODEL_ID=your-model-name
LLM_API_KEY=your_key
LLM_BASE_URL=https://your-endpoint/v1
```

**方式 B：本地模型**（用随附的 mini_server，把任意本地 Qwen2.5 权重变成 OpenAI 兼容接口）

```bash
# 下载权重（示例为 Qwen2.5-VL-3B-Instruct，也可换 Qwen2.5-3B-Instruct 等纯文本模型）
huggingface-cli download Qwen/Qwen2.5-VL-3B-Instruct --local-dir ./qwen25vl-3b
# 起本地服务（VL 版 chat 模板不含 tools 段，mini_server 已手动注入并解析 <tool_call>）
python mini_server.py --model ./qwen25vl-3b --port 8080
# 新终端：指向本地服务
set LLM_MODEL_ID=local-mini
set LLM_API_KEY=dummy
set LLM_BASE_URL=http://127.0.0.1:8080/v1
```

### 运行项目

```bash
python main.py --demo    # 内置 5 轮真实场景演示（推荐先跑这个）
python main.py           # 交互式多轮对话
```

## 💬 效果示例

**端到端实测**（本地 Qwen2.5-7B 4bit，第一轮真实入库）：

```text
[用户] 记一下：今天跑了双目立体匹配，SGM 方法，基线 12cm，重投影误差 0.8px，图对 35 对
[LabNoteAgent] 已经记录了今天的实验，实验编号为 [20261115-001]，
包含双目立体匹配实验的相关参数和结果。

# labnote_data.json 实际落盘内容（工具层验证输出）：
# {"id": "20261115-001", "title": "双目立体匹配实验",
#  "params": {"method": "SGM", "baseline_cm": 12, "image_pairs": 35},
#  "results": {"reprojection_error_px": 0.8}, "tags": ["stereo"]}
```

工具层（存储/检索/对比/统计）在 `python -c` 单元验证中全部通过；`compare_experiments` 输出示例：

```text
对比 [20261115-001] 双目匹配基线实验  vs  [20261115-002] SGM+一致性检查
  参数 method: SGM -> SGM+LRcheck
  结果 err_px: 0.8 -> 0.5
```

**已知限制（诚实说明）**：本地 3B/7B 小模型的多轮工具调用稳定性有限（连续多轮后可能出现不调用工具而编造内容的情况）。多轮对话体验建议搭配更强的模型（任何 OpenAI 兼容的云端模型均可，改三个环境变量即可）。工具层与模型解耦，全部 4 个工具的逻辑已独立验证。

## 📂 目录结构

```text
Puss-M-LabNoteAgent/
├── main.py               # 入口：交互式 / --demo
├── mini_server.py        # 可选：把本地 Qwen 权重变成 OpenAI 兼容接口（支持 function calling）
├── labnote/
│   ├── storage.py        # JSON 笔记库（增/查/diff/统计，线程安全）
│   └── tools.py          # 4 个自定义工具（继承 hello_agents Tool 新协议）
├── requirements.txt
└── README.md
```

## 🧗 经验与坑点

- **VL 版模型的 chat 模板不含 tools 段**：`apply_chat_template(msgs, tools=...)` 对 Qwen2.5-VL 无效（与文本版不同），需要手动把工具定义按 Qwen 官方格式注入 system 消息，并自行解析 `<tool_call>`。`mini_server.py` 里是一个 ~100 行的最小实现，可直接复用。
- **工具入参要"双轨兼容"**：LLM 有时传字符串有时传结构化 dict，工具层统一做 JSON 宽松解析 + 正则兜底（`labnote/tools.py::_payload`），实测能显著降低"工具没被调用"的概率。
- **labels 不只是记参数**：把"标签"作为一等公民（英文小写、1-3 个），检索体验比纯关键词好很多。

## 📄 License

遵循本仓库 LICENSE（AGPL-3.0）。
