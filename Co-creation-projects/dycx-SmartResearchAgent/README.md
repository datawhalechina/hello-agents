# SmartResearchAgent - 智能研究助手

> 基于HelloAgents框架的多智能体研究工具

## 📝 项目简介

SmartResearchAgent 是一个智能研究助手，能够自动搜索互联网、分析信息、生成结构化的研究报告。它展示了如何使用 HelloAgents 框架构建一个实用的多工具智能体应用。

### 核心功能

- 🔍 **网络搜索** - 使用DuckDuckGo搜索获取最新信息
- 📊 **文本摘要** - 提取关键信息和要点
- 📝 **报告生成** - 整理为结构化的Markdown研究报告
- 💬 **智能问答** - 基于研究结果回答后续问题

### 解决的问题

在信息爆炸的时代，快速获取、整理和分析信息是一项重要但耗时的任务。SmartResearchAgent 通过自动化的方式，帮助研究者：

1. 从多个角度搜索相关资料
2. 提取关键信息和核心要点
3. 生成结构化的研究报告
4. 基于研究结果进行深入问答

## 🛠️ 技术栈

- **HelloAgents框架** - SimpleAgent + ToolRegistry
- **DuckDuckGo Search** - 免费网络搜索API
- **Python** - 核心开发语言
- **Jupyter Notebook** - 交互式开发环境

### 使用的智能体范式

- 工具调用（Tool Calling）：Agent根据任务自动选择和调用合适的工具
- 多工具协同：搜索 → 摘要 → 报告生成的完整流程

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 网络连接（用于搜索功能）
- LLM服务（本地LM Studio或云端API）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置LLM

**方式1：使用本地LM Studio（推荐，免费）**

1. 下载安装 [LM Studio](https://lmstudio.ai/)
2. 下载一个模型（如 qwen3.5-35b）
3. 启动本地服务（默认端口1234）
4. 项目已预配置为使用本地服务

**方式2：使用云端API**

复制 `.env.example` 为 `.env`，填入你的API密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，填入配置
```

### 运行项目

```bash
# 启动Jupyter Notebook
jupyter lab

# 打开 main.ipynb 并运行所有单元格
```

## 📖 使用示例

### 快速搜索

```python
from src.tools import WebSearchTool

search = WebSearchTool()
result = search.run({"query": "人工智能最新进展", "max_results": 5})
print(result)
```

### 完整研究流程

```python
from src.agent import SmartResearchAgent

# 创建研究助手
agent = SmartResearchAgent()

# 执行研究
report = agent.research("大语言模型Agent技术", max_searches=3)
print(report)

# 基于研究提问
answer = agent.ask("目前最流行的Agent框架有哪些？")
print(answer)
```

## 🎯 项目亮点

- **完全免费**：使用DuckDuckGo搜索和本地LLM，无需任何API费用
- **模块化设计**：工具和Agent分离，易于扩展和复用
- **开箱即用**：预配置本地LM Studio，克隆即用
- **教学友好**：代码清晰，注释完整，适合学习HelloAgents框架

## 📂 项目结构

```
dycx-SmartResearchAgent/
├── README.md              # 项目说明文档
├── requirements.txt       # 依赖列表
├── .env.example          # 环境变量示例
├── .gitignore            # Git忽略文件
├── main.ipynb            # 主程序（完整演示）
├── src/                  # 源代码
│   ├── __init__.py
│   ├── tools.py          # 自定义工具
│   └── agent.py          # 智能体实现
├── data/                 # 数据目录
└── outputs/              # 输出目录
    └── research_report.md # 生成的研究报告
```

## 🔧 扩展指南

### 添加新工具

```python
from hello_agents.tools import Tool, ToolParameter

class MyNewTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="工具描述"
        )

    def run(self, parameters):
        # 实现工具逻辑
        return "结果"

    def get_parameters(self):
        return [
            ToolParameter(
                name="param1",
                type="string",
                description="参数描述",
                required=True
            )
        ]
```

### 自定义Agent行为

修改 `src/agent.py` 中的 `system_prompt` 来改变Agent的行为模式。

## 📊 性能评估

- 搜索响应时间：2-5秒（取决于网络）
- 摘要生成时间：<1秒（本地处理）
- 完整研究流程：30-60秒（含LLM推理时间）

## 🔮 未来计划

- [ ] 添加更多搜索源（Google、Bing等）
- [ ] 实现网页内容抓取和解析
- [ ] 支持多轮对话和研究主题追踪
- [ ] 添加引用管理和来源验证
- [ ] 支持PDF/Word格式报告导出
- [ ] 集成RAG系统进行知识检索
- [ ] 添加研究历史记录功能

## 👤 作者

- GitHub: [@dycx](https://github.com/dycx)
- 项目链接: [SmartResearchAgent](https://github.com/datawhalechina/hello-agents/tree/main/Co-creation-projects/dycx-SmartResearchAgent)

## 🙏 致谢

- 感谢 [Datawhale](https://github.com/datawhalechina) 社区和 [Hello-Agents](https://github.com/datawhalechina/hello-agents) 项目
- 感谢 [HelloAgents框架](https://github.com/jjyaoao/helloagents) 提供的技术支持
- 感谢 [DuckDuckGo](https://duckduckgo.com/) 提供的免费搜索API

## 📄 许可证

本项目采用 MIT 许可证。
