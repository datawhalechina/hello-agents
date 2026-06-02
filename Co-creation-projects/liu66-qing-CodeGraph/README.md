# CodeGraph - AI 代码仓库学习地图

> 将复杂 GitHub 仓库转化为可视化学习地图的 AI 代码理解平台，让开发者像闯关一样快速读懂项目架构、主流程和核心实现。

## 项目简介

CodeGraph 是一个面向开源项目学习和代码仓库理解的 Agentic RAG 应用。它不是只做“代码问答”，而是把仓库解析、图增强检索、阶段化学习路径和像素风可视化界面结合起来，帮助新贡献者从一个陌生仓库中快速建立全局认知。

项目围绕四阶段学习路径展开：

1. **先看门道**：理解项目定位、目录结构、技术栈和核心模块。
2. **跑通主线**：追踪入口、主流程、关键调用链和执行路径。
3. **拆它绝活**：分析值得学习的实现模式、抽象设计和工程取舍。
4. **抄走一招**：沉淀可复用技巧，转化为自己的项目实践。

适用场景：

- 开源项目新贡献者 onboarding
- 大型代码仓库学习与架构梳理
- Code Agent / RAG Agent 项目实践
- 面向代码理解的知识图谱与混合检索实验

## 核心功能

- [x] **仓库学习路径生成**：将仓库拆解为四阶段学习路线，降低进入复杂项目的门槛。
- [x] **代码结构分析**：围绕文件、模块、函数、调用链和架构层次组织代码上下文。
- [x] **图增强 RAG**：结合图谱关系、关键词检索和向量召回，提高代码问答的结构感。
- [x] **阶段化 Agent 分析**：针对总览、主流程、实现亮点和可迁移经验生成不同类型的解释。
- [x] **可视化学习界面**：用学习地图、阶段卡片、进度和成就系统呈现仓库理解过程。

## 技术栈

- **后端**：FastAPI、Python、Agentic RAG pipeline
- **检索与存储**：Neo4j、向量检索、关键词检索、混合召回
- **代码理解**：代码解析、模块关系抽取、调用链分析
- **前端**：React、TypeScript、Vite、像素风学习地图
- **Agent 范式**：多阶段分析 Agent、任务编排、结构化输出

## 在线体验

- 在线 Demo：https://code-graph-five.vercel.app/
- 学习地图：https://code-graph-five.vercel.app/map
- GitHub 仓库：https://github.com/liu66-qing/CodeGraph

> 当前在线 Demo 主要用于展示前端学习体验和产品形态；完整仓库分析、AI 问答和图谱能力需要配合后端服务运行。

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker / Docker Compose
- Neo4j、Redis 等基础服务
- OpenAI 兼容模型 API Key

### 克隆项目

```bash
git clone https://github.com/liu66-qing/CodeGraph.git
cd CodeGraph
```

### 启动基础服务

```bash
docker-compose up -d
```

### 启动后端

```bash
pip install -e ".[dev]"
uvicorn evograph.main:app --reload --host 0.0.0.0 --port 8000
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173` 开始体验。

## 使用示例

1. 打开 CodeGraph 首页。
2. 输入一个 GitHub 仓库地址，例如 `facebook/react`、`microsoft/vscode` 或课程中的 Agent 示例项目。
3. 系统生成学习地图，并按阶段给出：
   - 项目总览
   - 主流程路线
   - 核心实现拆解
   - 可复用实践建议
4. 学习者可以沿着阶段卡片逐步推进，也可以进入问答界面询问代码细节。

## 项目亮点

- **面向学习而不是只面向问答**：输出目标是帮助人读懂仓库，而不只是回答孤立问题。
- **图结构优先**：关注代码实体之间的关系，适合解释调用链、依赖、模块职责和架构边界。
- **适合开源贡献场景**：可以作为新贡献者理解项目、准备 PR、梳理 issue 背景的辅助工具。
- **可视化体验友好**：通过学习地图和阶段进度，让代码仓库探索更像一条明确路线。

## 与 Hello-Agents 的关系

Hello-Agents 教程强调从 Agent 原理、经典范式、记忆检索、上下文工程到综合项目实践的完整学习路径。CodeGraph 可以作为“毕业设计/社区共创项目”中的一个代码理解类 Agent 实践案例：

- 对应 **记忆与检索**：使用 RAG 和结构化上下文组织代码知识。
- 对应 **上下文工程**：将仓库结构、文件元数据、调用关系和学习阶段组合进提示上下文。
- 对应 **综合案例**：面向真实开源项目，构建可使用的 Agentic 应用。

## 未来计划

- [ ] 增强多语言代码解析能力
- [ ] 增加更细粒度的调用链和依赖图谱展示
- [ ] 支持 GitHub issue / PR 上下文辅助理解
- [ ] 增加学习报告导出能力
- [ ] 将后端完整部署为可公开体验的长期 Demo

## 作者

- GitHub：[@liu66-qing](https://github.com/liu66-qing)
- 项目地址：https://github.com/liu66-qing/CodeGraph

## 致谢

感谢 Datawhale 社区和 Hello-Agents 项目提供系统化的 Agent 学习资料。CodeGraph 的实践思路也受到 Hello-Agents 中记忆检索、上下文工程和综合项目章节启发。

## 许可证

CodeGraph 项目使用 Apache-2.0 License。

