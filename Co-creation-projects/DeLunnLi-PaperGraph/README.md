# PaperGraph（知脉）- 面向研究者的智能文献工作台

<div align="center">

**Academic Paper Search, Reading, Recommendation and Knowledge Graph Workspace**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-DeLunnLi/PaperGraph-black.svg)](https://github.com/DeLunnLi/PaperGraph)

*基于 HelloAgents 构建的学术文献搜索、阅读、推荐与知识图谱系统*

*把找论文、读论文、管理论文和沉淀研究脉络串成一个连续工作流*

</div>

---

## 项目简介

PaperGraph（知脉）是一个面向科研学习、论文调研和研究方向跟踪的智能文献工作台。系统以 SearchAgent、PaperAnalysisAgent 和 KnowledgeGraphAgent 为核心，将自然语言检索、多源论文召回、PDF 阅读问答、每日推荐、文献保存和知识图谱构建整合到同一个 Web 应用中。

它希望解决研究者在日常文献工作中的几个高频痛点：

- 关键词检索分散在多个平台，结果需要手动筛选、去重和排序
- 阅读论文时缺少上下文辅助，方法、实验、引用关系难以持续沉淀
- 每日新论文、个人文献库和知识图谱彼此割裂，难以形成长期研究记忆
- 从发现论文到保存、阅读、追问、归类之间缺少一条顺滑的工作流

### 核心特性

- **自然语言文献搜索**：输入研究问题、论文标题、作者或会议线索，由 LLM 解析意图并生成 SearchRecipe
- **多源并行召回与精排**：整合 arXiv、DBLP、OpenAlex 与 Tavily 线索，完成去重、过滤、排序和兜底召回
- **论文阅读助手**：支持 PDF 正文抽取、AI 导读、阅读对话、参考文献查找和表格上下文辅助
- **每日论文推荐**：根据用户兴趣选择 arXiv 分类，生成个性化候选论文与推荐理由
- **我的文献库**：支持论文保存、PDF 下载、分类管理、阅读记录和阅读日历
- **知识图谱构建**：从已保存论文中抽取主题、方法、引用和相关关系，并进行可视化浏览
- **多智能体共享记忆**：通过 GSSC（Gather -> Score -> Select）流水线选择上下文，减少重复信息干扰

### 技术亮点

- **Recipe 驱动检索**：将 LLM 对用户意图的理解转成可执行检索计划，降低硬编码特殊路径依赖
- **多源召回与优雅降级**：arXiv、DBLP、OpenAlex 和 Tavily 互为补充，单一来源失败时仍尽量返回可用结果
- **流式过程反馈**：搜索过程通过 SSE 返回阶段状态和工具调用摘要，便于用户理解结果来源
- **阅读上下文增强**：阅读器结合论文正文、表格、参考文献和历史记忆回答问题，而不只是展示 PDF
- **共享记忆机制**：多个 Agent 共享论文、偏好和反馈上下文，让后续搜索与推荐更贴近用户兴趣
- **前后端契约生成**：通过 OpenAPI 导出前端类型，减少接口字段漂移

## 应用场景

### 适合谁使用？

- **研究生/博士生**：快速进入新方向，建立论文阅读和调研脉络
- **科研工作者**：跟踪每日新论文，沉淀个人文献库和主题关系
- **AI/工程研发人员**：围绕技术问题快速查找论文、保存证据和复盘方法
- **课程学习者**：用对话式阅读辅助理解论文方法、实验和引用背景

### 典型使用场景

1. **主题调研**：输入研究问题 -> 多源召回论文 -> 保存候选论文 -> 形成阅读列表
2. **论文精读**：打开 PDF -> 获取 AI 导读 -> 围绕方法、实验和局限继续追问
3. **每日跟踪**：系统拉取新论文 -> 个性化推荐 -> 保存感兴趣论文 -> 反馈偏好
4. **知识沉淀**：从文献库抽取关系 -> 生成图谱 -> 观察主题、作者和论文之间的连接

## 系统架构

### 整体架构

```text
┌──────────────────────────────────────────────────────────────┐
│                         前端界面层                            │
│  文献搜索 | 每日论文 | 我的文献库 | 论文阅读助手 | 知识图谱       │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ REST + SSE
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         API 接口层                            │
│              FastAPI Routes + OpenAPI + Tool Events           │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       智能体编排层                             │
│  SearchAgent | PaperAnalysisAgent | KnowledgeGraphAgent        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         核心服务层                            │
│  Search Pipeline | PDF Parser | Daily Recommend | AgentMemory  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         数据持久层                            │
│       SQLite 文献库 | PDF 文件存储 | 阅读记录 | 反馈记忆          │
└──────────────────────────────────────────────────────────────┘
```

### 三类智能体

| 智能体 | 职责 | 核心能力 |
|--------|------|----------|
| **SearchAgent** | 文献搜索与结果解释 | 意图解析、SearchRecipe、多源召回、LLM 精排 |
| **PaperAnalysisAgent** | 论文阅读与分析 | 摘要生成、标签归类、阅读问答、引用查找 |
| **KnowledgeGraphAgent** | 知识图谱构建 | 论文关系抽取、图谱数据生成、节点详情解释 |

### 搜索链路

```text
用户问题
  -> LLM 意图解析
  -> SearchRecipe
  -> arXiv / DBLP / OpenAlex / Tavily 多源召回
  -> 去重与过滤
  -> LLM 精排
  -> 结果解释与保存
```

## Quick Start

### 1. 环境要求

- Python 3.10+
- Node.js 20+
- 可用的 OpenAI 兼容 LLM 服务

### 2. 后端安装与配置

```bash
cd backend
pip install -r requirements.txt
```

在 `backend/.env` 中配置模型信息：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL_ID=your_model_id
```

启动后端：

```bash
python run.py
```

默认访问地址：`http://localhost:8000`

### 3. 前端安装与启动

```bash
cd frontend
npm ci
npm run dev
```

默认访问地址：`http://localhost:5173`

### 4. 一键启动

也可以在项目根目录执行：

```bash
./start.sh
```

### 5. 回归检查

后端测试使用临时数据库、合成 PDF 和模拟模型，不需要 API 密钥：

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q tests
```

前端检查：

```bash
cd frontend
npm ci
npm run typecheck
npm test
npm run build
```

这些检查覆盖真实代理/工具调用链、并发阅读隔离、引用来源核验、记忆压缩、搜索 HTTP/SSE 错误传递、推荐反馈与跨日缓存、文献库分页、PDF 表格/范围请求、图谱生成，以及前端会话切换和阅读时长提交。测试只替换模型、论文提供方等外部边界；前端异步行为通过真实 Vue 组件验证。

具体行为、输入预算、数据兼容和未验收范围见[功能修复与验证记录](docs/regression-validation.md)。

离线通过不代表真实搜索相关性或模型回答质量已经通过验收。在线验证所需信息：

| 配置或材料 | 用途 | 是否必需 |
| --- | --- | --- |
| 同一服务商的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_ID` | 模型问答、意图解析、分类、关系生成；模型需支持工具调用 | 在线模型验证必需，不能仅凭密钥推断服务商 |
| `TAVILY_API_KEY` | 网页预检索、会议论文集发现 | 验证此功能时需要，普通离线自检无需 |
| `OPENALEX_MAILTO`、`NCBI_EMAIL` / `NCBI_API_KEY` | 对应论文提供方的联系信息/访问配置 | 按所用来源和账户要求配置 |
| Embedding 服务配置 | 可选记忆向量能力 | 不影响本项目的基础离线回归检查 |
| 少量可公开访问的论文与预期问题/引用 | 验证真实 PDF、论文相关性和回答证据 | 真实效果验收需要，不需要提供私人文献库 |

`backend/.env.example` 中的服务地址和模型名仅为示例，使用时应替换为实际账号提供的信息；不要把密钥写入提交或测试夹具。

### 数据兼容与行为说明

- 重复保存相同标识的论文会保留缺失字段对应的旧分类、标签和链接；主动清空字段仍通过更新接口完成。
- 缺少 ORCID/邮箱等稳定身份的同名作者按论文分别保存，避免将不同作者连成一人；显示姓名相同不再作为跨论文身份相同的证据。
- 阅读记录每 30 秒保存累计时长，关页时补交；同一会话的重复或乱序提交不会重复累计。旧阅读记录表会自动增补可选会话字段，旧客户端仍可提交不带该字段的记录。
- 导读随论文证据版本失效，模型失败消息不会缓存为成功导读。PDF/参考文献工具返回有限证据片段；章节工具可分页读取，未核验的主题检索结果不会标成原文引用。
- 同步调用超时会及时结束等待，但无法强行终止已经执行的 Python/网络调用；仍依赖提供方网络超时收尾。

已有数据库中此前被覆盖的分类、标签或作者机构，无法仅凭当前记录推断恢复；如需恢复，应使用原始题录或备份。升级前可保留本地数据目录备份。

## 使用流程

1. 在 **文献搜索** 页面输入自然语言问题，例如“2024 年视觉语言模型中的 grounding 相关论文”。
2. SearchAgent 解析检索意图，选择关键词、来源、年份、会议等约束，并执行多源召回。
3. 用户将有价值的论文保存到 **我的文献库**，必要时下载 PDF。
4. 在 **我的文献库** 中打开某篇论文，进入 **论文阅读助手** 页面查看 AI 导读，并围绕方法、实验、局限和参考文献继续提问。
5. 在 **每日论文** 页面追踪新论文，在 **知识图谱** 页面观察主题和论文之间的关系。

### 论文分析 Skills

在 **论文阅读助手** 中直接提出下列任务，助手可按需加载对应技能，再结合当前论文材料和 PDF 工具回答：

| 技能 | 用途 | 提问示例 |
| --- | --- | --- |
| `paper-reading` | 梳理研究问题、方法、实验依据和局限 | “精读这篇论文，解释核心方法，并标注支持结论的章节或表格。” |
| `paper-comparison` | 对照多篇论文的方法、证据与实验设置 | “对比当前论文与我提供的另一篇摘要；把有全文依据和只有摘要的信息分开。” |
| `literature-review` | 按研究问题组织已有文献，形成有出处的综述草稿 | “基于当前材料整理相关工作综述，列出主题、分歧和待补证据。” |
| `reproducibility-check` | 检查数据、实现、训练和评估细节，形成复现清单 | “检查这篇论文的复现条件，区分已给出的参数和需要向作者确认的信息。” |

内置技能位于 [`backend/skills/`](backend/skills/)，由 HelloAgents 的 `SkillLoader` / `SkillTool` 通过 `PaperSkill` 工具按需加载。模型先看到名称和描述，选中后才收到技能正文。原有 `Skill` 工具及 `DATA_DIR/memory/skills` 自定义目录继续保留；内置技能不会覆盖其中的文件。

当前 PDF 工具只解析打开的论文，检索结果不等于其他论文的全文。多篇对比和综述会使用已提供的材料，并说明缺少的证据；复现检查输出计划，不会自动下载或执行第三方代码。这些技能不需要新增专用 API 密钥，实际调用仍使用项目配置的、支持工具调用的模型。

离线回归覆盖技能发现、按需加载与阅读工具衔接；模型是否准确选择技能、回答质量仍需真实模型验收。

## 演示效果

文献搜索、每日论文推荐、文献库、论文阅读助手和知识图谱等界面截图，请参见 [毕业设计提交 PR #614](https://github.com/datawhalechina/hello-agents/pull/614)。

## 技术栈

| 层级 | 技术 |
|------|------|
| **智能体框架** | HelloAgents（SimpleAgent + ToolRegistry + CircuitBreaker + ContextBuilder） |
| **后端服务** | FastAPI + SQLite + Pydantic |
| **前端应用** | Vue 3 + Vite + Ant Design Vue + KaTeX + PDF.js |
| **LLM 接入** | DeepSeek-V4 / OpenAI 兼容接口 |
| **论文数据源** | arXiv + DBLP + OpenAlex + Tavily |
| **PDF 处理** | PyMuPDF（fitz） |

## 工程指标

- **搜索链路**：意图解析 + SearchRecipe + 多源召回 + LLM 精排
- **推荐链路**：arXiv 候选拉取 + 用户兴趣词 + 个性化筛选 + 反馈记忆
- **阅读链路**：PDF 解析 + 正文上下文 + 对话历史 + 参考文献查找
- **交互方式**：REST API + SSE 流式状态更新
- **数据存储**：SQLite 文献库 + 本地 PDF 文件 + 阅读记录

## 项目结构

```text
.
├─ backend/                 # FastAPI 后端与智能体服务
│  ├─ app/agents/           # SearchAgent / PaperAnalysisAgent / KnowledgeGraphAgent
│  ├─ app/api/              # API 路由、依赖和 SSE 工具事件
│  ├─ app/core/             # Paper 模型、PDF 下载、搜索源适配
│  ├─ app/services/         # 检索、阅读、推荐、记忆、图谱等业务服务
│  ├─ skills/               # 论文精读、对比、综述与复现检查技能
│  ├─ data/                 # 本地数据库与运行数据（不提交）
│  └─ downloads/            # PDF 下载目录（不提交）
├─ frontend/                # Vue 3 前端应用
│  ├─ src/views/            # 搜索、每日论文、文献库、阅读器、知识图谱页面
│  ├─ src/components/       # 论文卡片、搜索结果、工具轨迹、阅读日历等组件
│  ├─ src/composables/      # 搜索对话、历史记录、标题关键词等组合逻辑
│  └─ src/services/         # API 客户端与接口封装
├─ ports.env                # 本地端口配置
├─ start.sh                 # 一键启动脚本
└─ README.md
```

## 开发路线图

### v1.0（当前版本）

- [x] 自然语言文献搜索
- [x] 多源论文召回与 LLM 精排
- [x] PDF 阅读助手
- [x] 每日论文推荐
- [x] 我的文献库与阅读日历
- [x] 知识图谱可视化

### v1.1（计划中）

- [x] 补充搜索、阅读和推荐链路的离线集成测试
- [ ] 完成真实模型/提供方的效果验收与可复现实验样例
- [ ] 增加搜索结果缓存和可复现实验样例
- [ ] 优化搜索过程可观测性和错误提示
- [ ] 增强知识图谱的关系过滤、编辑和导出能力

### v2.0（未来）

- [ ] 支持 Docker 一键部署
- [ ] 优化移动端与小屏阅读体验
- [ ] 引入向量检索或本地语义索引
- [ ] 支持团队共享文献库和多用户偏好

## 许可证

MIT License

## 作者

GitHub: [@DeLunnLi](https://github.com/DeLunnLi)  
项目地址: [github.com/DeLunnLi/PaperGraph](https://github.com/DeLunnLi/PaperGraph)

## 致谢

感谢 Datawhale 社区和 Hello-Agents 项目。本项目基于 HelloAgents 的智能体、工具注册、上下文构建和熔断能力完成实践探索。

记忆模块恢复与 PDF 阅读器修复参考作者的 [PaperGraph 原项目](https://github.com/DeLunnLi/PaperGraph/tree/2b6c81bc34865df1b55dd1a1ef30da2c7f45ee5b)，并针对本共创目录的依赖和运行方式做了适配。项目级 `.gitignore` 保留记忆源码和回归测试，避免被上游通用忽略规则漏掉。
