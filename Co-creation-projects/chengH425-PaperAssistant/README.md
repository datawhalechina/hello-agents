# PaperAssistant - 智能论文助手

> 基于 HelloAgents 框架 + DeepSeek 的多智能体学术辅助工具，集成 6 大学术数据源，覆盖文献检索、论文总结、引用生成、论文润色、大纲生成、论文写作和 PDF 处理。

## 📝 项目简介

PaperAssistant 是一个面向研究生和科研人员的智能论文助手，通过多智能体协作帮助用户高效完成从文献调研到论文撰写的全流程学术任务。

### 解决什么问题？

- 文献检索耗时，单一数据库覆盖不全 → **6 大数据源自由切换**
- 论文阅读量大，难以快速提取关键信息 → **LLM 结构化总结**
- 引用格式繁琐，容易出错 → **GB/T 7714 / APA / MLA 一键生成**
- 论文润色需要反复修改 → **多轮对话式润色，记住上下文持续优化**
- 论文大纲构思困难 → **多轮对话式大纲构建，持续调整细化**
- 论文写作难度大 → **根据大纲逐章撰写，引用真实文献**

## ✨ 核心功能

- [x] **文献检索**：集成 6 大学术数据源（Semantic Scholar / AMiner / OpenAlex / PubMed / CrossRef / arXiv），自由切换，支持学科和年份高级筛选
- [x] **论文总结**：结构化提取论文核心观点、方法和结论
- [x] **引用生成**：自动生成 GB/T 7714、APA 7th、MLA 9th 三种格式的参考文献
- [x] **论文润色**：多轮对话式润色，持续优化表达，记住上下文
- [x] **大纲生成**：多轮对话式大纲构建，随时细化调整
- [x] **论文写作**：根据大纲逐章撰写，引用真实文献（拒绝 AI 编造）
- [x] **PDF → Markdown**：上传 PDF 论文，自动识别章节结构，转换为 Markdown
- [x] **Gradio Web UI**：8 标签页图形化界面 + 对话记录自动保存 + 会话历史管理

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 智能体框架 | HelloAgents v1.0 |
| 智能体范式 | SimpleAgent（多轮对话记忆） |
| LLM 后端 | DeepSeek-Chat |
| Web 界面 | Gradio |
| 学术 API | Semantic Scholar / AMiner / OpenAlex / PubMed / CrossRef / arXiv |
| PDF 处理 | PyPDF2（文本提取 + Markdown 转换） |
| 对话管理 | JSON 持久化 + 多轮上下文记忆 + 会话历史 |

## 📁 项目结构

```
chengH425-PaperAssistant/
├── README.md              # 项目文档
├── requirements.txt        # 依赖列表
├── main.ipynb              # Jupyter Notebook（完整演示）
├── app.py                  # Gradio Web 界面（8 标签页）
├── .env / .env.example     # 环境变量
├── src/                    # 源代码模块（9 个工具）
│   ├── __init__.py
│   ├── literature_tool.py  # Semantic Scholar 全学科检索（2亿+）
│   ├── aminer_tool.py      # AMiner 中文学术检索（3.2亿+）
│   ├── openalex_tool.py    # OpenAlex 开放获取检索（2.5亿+）
│   ├── pubmed_tool.py      # PubMed 生物医学检索（3600万+）
│   ├── crossref_tool.py    # CrossRef 期刊论文检索（1.5亿+）
│   ├── arxiv_tool.py       # arXiv 预印本检索
│   ├── pdf_tool.py         # PDF 转 Markdown 工具
│   └── citation_tool.py    # 学术引用生成
├── data/                   # 示例数据
└── outputs/                # 输出结果、对话记录、会话存档
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- HelloAgents >= 1.0.0

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env 文件，填入 DeepSeek API Key
```

### 方式一：启动 Web 界面（推荐）

```bash
python app.py
# 浏览器打开 http://127.0.0.1:7860
```

### 方式二：Jupyter Notebook

```bash
jupyter lab
# 打开 main.ipynb 并运行所有单元格
```

## 📖 功能说明

### 界面标签页（8 个）

| 标签页 | 功能 | 技术实现 |
|--------|------|---------|
| 📚 文献检索 | 6 数据源自由切换 + 高级筛选（学科/年份） + API 重试 | SimpleAgent + 多工具路由 |
| 📝 论文总结 | 粘贴论文内容，生成结构化总结 | SimpleAgent |
| 📎 引用生成 | 填写表单，一键生成 3 种格式引用 | CitationTool（确定性计算） |
| ✍️ 论文润色 | 多轮对话式润色 + 会话历史加载 | SimpleAgent（对话记忆 + 会话持久化） |
| 📊 大纲生成 | 多轮对话式大纲构建 + 会话历史加载 | SimpleAgent（对话记忆 + 会话持久化） |
| 📝 论文写作 | 根据大纲逐章撰写，引用真实文献 + 会话历史加载 | SimpleAgent + 5 检索工具 |
| 📄 PDF → Markdown | 上传 PDF，自动识别标题/章节/段落，输出 Markdown | PDFExtractTool |
| 💬 对话记录 | 自动保存所有操作，每条记录独立删除，可回溯查看 | JSON 持久化 + HTML 卡片展示 |

### 6 大数据源对比

| 数据源 | 覆盖量 | 学科范围 | 特色 |
|--------|:-----:|---------|------|
| Semantic Scholar | 2亿+ | 全学科 | 推荐使用，覆盖广 |
| AMiner | 3.2亿+ | 全学科 | 中文论文最强，清华出品 |
| OpenAlex | 2.5亿+ | 全学科 | 开放获取、跨库聚合 |
| PubMed | 3600万+ | 生物医学 | 医学领域最权威 |
| CrossRef | 1.5亿+ | 全学科 | 期刊元数据最完整 |
| arXiv | 240万+ | CS/数学/物理 | 预印本最快 |

### 代码调用示例

```python
from hello_agents import HelloAgentsLLM, ToolRegistry
from src.literature_tool import LiteratureSearchTool

# 全学科检索
tool = LiteratureSearchTool()
result = tool.run({
    "keyword": "large language model agent",
    "field": "计算机科学",
    "year_from": "2023",
    "max_results": 5
})
print(result.text)
```

## 🎯 项目亮点

- **6 数据源集成**：自由切换，告别单一数据库，含中文文献支持
- **真实数据驱动**：文献检索和论文写作均基于学术 API，杜绝 LLM 幻觉
- **多轮对话记忆**：润色、大纲、写作支持上下文连续的对话式交互
- **会话历史管理**：自动保存对话，支持加载继续、删除历史
- **模块化工具系统**：9 个自定义 Tool，独立可测试
- **双入口设计**：Gradio Web UI + Jupyter Notebook
- **多格式引用**：GB/T 7714 / APA 7th / MLA 9th，规则引擎确定性生成

## 🔮 未来计划

- [ ] 接入 CNKI / 万方等中文数据库
- [ ] 支持 PDF 论文的图表识别与解析
- [ ] 增加论文查重分析功能
- [ ] 支持更多 LLM 后端（OpenAI / Claude / GLM）
- [ ] 支持 DOCX/LaTeX 格式导出

## 👤 作者

- GitHub: [@chengH425](https://github.com/chengH425)
- Email: 1793636425@qq.com

## 📄 许可证

MIT License

所使用的各学术 API（Semantic Scholar、OpenAlex、PubMed、CrossRef、arXiv、AMiner）均属于其各自所有者的财产，本项目仅通过其公开 API 进行非商业用途的学术检索。

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
