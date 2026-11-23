# AI Product Manager · 从 Idea 到 PRD

> 输入一个真实产品想法，通过逐步问答确认需求，查询竞品并生成可继续修改的产品需求文档。

作者：[dandan1232](https://github.com/dandan1232) · Hello-Agents 共创项目 · 生产力工具

## 项目简介

这是一个本地运行的 AI 产品经理 Demo，面向想把模糊想法整理成明确需求的个人开发者与学习者。左侧逐步访谈，右侧同步整理需求草稿；用户确认后，再进行竞品研究、实现条件评估和 PRD 编写。

不需要准备知识库或训练数据。用户的真实回答和联网搜索结果是输入；未配置服务时明确提示，不用假结果填充界面。

## 核心功能

- 逐步澄清：每轮一个关键问题、最多三个参考选项，最多六轮，可提前确认。
- 需求确认：直接编辑八项需求字段，确认后保存独立快照。
- 竞品研究：Tavily 实际联网搜索，最多整理三个竞品，保留摘录、来源和查询时间。
- 可行性建议：说明实现路径、依赖与风险，把商业需求列为待验证内容。
- PRD 草稿：包含用户故事、功能行为、验收条件、实施建议与待确认事项。
- 一致性复核：检查生成建议与确认需求是否矛盾，发现问题时明确标出。
- 项目恢复与导出：SQLite 保存本地历史，后台进度可查看，Markdown 可下载。
- 失败重试：保留输入，重试不重复追加回答；修改需求时旧分析自动失效。

## 技术栈

| 部分 | 实现 |
| --- | --- |
| 智能体 | HelloAgents 0.2.9：SimpleAgent、HelloAgentsLLM |
| 工作流 | 需求澄清 → 用户确认 → 竞品研究 → 可行性评估 → PRD → 一致性复核 |
| 外部工具 | Tavily Search HTTP API，支持 OpenAI 兼容接口的模型服务 |
| 后端 | Python 标准库 HTTP 服务、后台线程、SQLite |
| 前端 | HTML / CSS / JavaScript，无前端构建依赖 |
| 验证 | unittest：领域流程、真实框架适配、HTTP 接口 |

使用固定阶段的多智能体协作，各阶段接收显式上下文；不是多个角色在页面上互相聊天。每次调用独立创建角色，避免把一个项目的历史带入另一个项目。

## 项目结构

```text
dandan1232-AIProductManager/
├── README.md
├── requirements.txt
├── requirements-notebook.txt
├── main.ipynb                 # 调用真实工作流的交互演示
├── main.py                    # 本地网页入口
├── .env.example               # 空密钥配置示例
├── .gitignore
├── .impeccable.md             # 界面设计约定
├── docs/
│   ├── requirements.md        # 需求与验收项
│   ├── architecture.md        # 架构、状态、接口
│   ├── plan.md                # 分阶段实施计划
│   └── verification.md        # 实际验证结果与限制
├── src/
│   ├── config.py
│   ├── prompts.py
│   ├── services.py
│   ├── workflow.py
│   └── server.py
├── web/                      # 工作台及本地字体
└── tests/                    # 测试替身只用于测试
```

`runtime/`（本地数据库）、`outputs/`（导出结果）、虚拟环境和截图在运行时产生，均不提交。项目没有必须下载的数据集。

## 快速开始

### 环境要求

- 推荐 64 位 Python 3.12；代码支持 Python 3.10+。
- 一个支持 OpenAI 兼容接口的模型服务，模型需能遵循 JSON 输出要求。
- 可选 Tavily API Key，用于联网竞品研究。
- 不需要安装 Node.js、Godot 或向量数据库。

### 安装

在项目目录执行：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

macOS / Linux：

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

浏览器打开 **http://127.0.0.1:8765**。只监听本机回环地址。端口被占用时可执行 `python main.py --port 8766`。

HelloAgents 0.2.9 会在导入时引用评估模块，因此依赖清单额外声明了 `huggingface-hub`；本项目不需要下载 Hugging Face 数据集或模型。

### 配置连接

方式一：打开网页右上角“连接设置”，填写模型名称、接口基础地址、模型密钥和可选的 Tavily 密钥。

- 网页提交的密钥只保存在当前服务端进程，重启后需要重新填写。
- API 响应不回传密钥，密钥不写入项目 SQLite 或浏览器 localStorage。
- 留空密钥表示保留当前设置。模型名称必须填写服务商实际支持的标识。

方式二：将 `.env.example` 复制为项目目录的 `.env`，填写自己的服务信息后启动。已有进程环境变量优先。

```dotenv
LLM_MODEL_ID=填写实际模型名称
LLM_BASE_URL=填写服务商的兼容接口基础地址
LLM_API_KEY=填写自己的模型密钥
TAVILY_API_KEY=需要联网时填写
LLM_TIMEOUT=90
```

真实 `.env` 已被忽略，不能提交密钥。配置发生变化后重启服务。模型请求和搜索可能产生相应服务费用；具体以所用服务商为准。

### Notebook 演示

```bash
python -m pip install -r requirements-notebook.txt
python -m jupyter lab main.ipynb
```

请用安装了依赖的同一个 Python 运行。Notebook 逐格执行，使用隐藏输入读取密钥；需要本人输入真实 Idea、回答问题并确认需求。它复用网页的工作流，没有预置竞品或伪造报告。

## 使用示例

1. 输入你自己的想法，例如“我想做一个个人任务管理工具，第一版只在本地使用”。这句话是输入示例，不是预先生成的分析结果。
2. 回答模型的问题；如暂时不确定，可以如实说明。
3. 检查右侧草稿，明确“本次不做”和资源限制，点击“确认这份需求”。
4. 有搜索密钥时启用“联网研究相关竞品”；没有时主动取消，文档会说明未开展竞品研究。
5. 点击“生成分析与 PRD”，查看真实阶段状态、竞品来源与 PRD 草稿。
6. 下载 Markdown。修改需求时，已有分析失效，需要重新生成。

右侧的资料来源支持查看搜索摘录。已确认需求由程序直接写入报告；其他功能细节和实现方案均标记为 AI 建议。

## 项目亮点

- **确认内容不被覆盖**：用户确认快照与模型建议分开保存。
- **追问影响后续分析**：访谈回答进入当前项目上下文和最后确认的需求。
- **结果可追溯**：竞品条目需要引用实际搜索得到的编号，搜索失败不补造产品。
- **真实可恢复的流程**：后台任务、失败重试、重启恢复和旧结果失效处理。
- **一套核心，两种入口**：网页与 Notebook 复用工作流。

## 测试与性能评估

```bash
python -m unittest discover -s tests -t . -v
```

测试不发送付费模型请求。领域与 HTTP 测试注入明确标记的替身；框架适配测试使用实际安装的 HelloAgents 包，只替换外部模型响应。没有安装依赖时，框架适配测试会跳过，其余标准库测试仍可运行。

实际验收结果、浏览器检查和未验证部分见 [验证记录](docs/verification.md)。本项目未宣称模型准确率、商业判断成功率或未实测的性能数字。

## 已知限制

- 本地单用户 Demo，没有公网身份认证和访问隔离，不应直接暴露到公网。
- 模型可能重复提问、误解需求或生成不准确的建议；六轮上限与显式确认用于控制流程，不能保证语义质量。
- 搜索结果可能不完整，引用存在不等于完成事实核验；对比信息以来源原文为准。
- 可行性评估是初步建议，不代替真实用户验证；一致性复核也可能漏报或误报。
- 文档始终为待评审草稿；通过复核不代表自动批准立项。
- 所有密钥需使用者自行配置，仓库不提供共享服务凭据。

## 设计、文档与后续计划

界面按用户指定的 taste-skill 设计：白底、蓝色操作强调、文档优先的工作台；没有虚构客户、指标、竞品或演示报告。

- [需求分析](docs/requirements.md)
- [架构设计](docs/architecture.md)
- [实施计划](docs/plan.md)
- 后续可评估：带版本差异的需求修改、分阶段继续生成、更多搜索提供商；不属于首版交付范围。

## 贡献与提交

目录采用 `{GitHub用户名}-{项目名称}`，保留 `main.ipynb`、README 和完整依赖清单。提交前运行测试、清空 Notebook 输出、检查忽略项和体积，提交文件合计不超过 5 MB。

开发分支为 `feature/ai-product-manager`，与教程的 `feature/` 命名约定保持一致。如向教程上游提交，PR 标题使用：`[毕业设计] AIProductManager - 从想法澄清到产品需求文档`。当前项目的分阶段推送不自动意味着创建上游 PR。

## 许可证与致谢

代码与文档按仓库的 [CC BY-NC-SA 4.0](../../LICENSE.txt) 共享。Funnel Sans 字体单独遵循 [SIL Open Font License](web/FONT-LICENSE.txt)，来源为 Google Fonts。

感谢 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents)、[HelloAgents 框架](https://github.com/jjyaoao/HelloAgents)；工作流参考教程中的多智能体、工具调用和上下文管理思想。Tavily 接口依据其官方文档实现。

作者：[dandan1232](https://github.com/dandan1232)。
