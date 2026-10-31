# UniversalAgent - 通用智能体系统

> 基于Hello-Agents框架的智能搜索和命令执行助手

## 📝 项目简介

这是一个基于 **Hello-Agents** 框架的通用智能体系统，采用 **单智能体 + 多工具** 设计。
智能体通过 ToolRegistry 注册并调用多个工具实现复杂任务处理。

### 核心功能
- ✅ **智能网络搜索**：支持多引擎搜索和内容提取
- ✅ **安全终端执行**：20+种安全命令，智能参数验证和错误提示
- ✅ **记忆功能**：支持用户偏好和重要信息记忆（未来）
- ✅ **多引擎支持**：DuckDuckGo、Brave、Ecosia、Searx

## 🛠️ 技术栈

- HelloAgents框架（SimpleAgent + ToolRegistry）
- Python AST模块（代码解析）
- ModelScope API（Qwen模型）
- Beautiful Soup（网页内容提取）


## 🚀 快速开始

### 环境要求

- Python 3.10+
- 其他要求见 requirements.txt

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API密钥

```bash
# 创建.env文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥
LLM_API_KEY=your_api_key_here
```

### 运行项目

**方式1: Jupyter Notebook（推荐）**
```bash
jupyter lab
# 打开main.ipynb并运行
```

**方式2: 命令行界面**
```bash
python main.py
```

## 📖 使用示例

### 1. 智能搜索
```
输入: 搜索Python人工智能最新发展
输出: 返回相关的搜索结果和内容摘要
```

### 2. 终端命令
```
输入: pwd
输出: /Users/qinbohua/Developing/universal_hello_agent_llm_decision

输入: ls -la
输出: total 48...（文件列表）

输入: mkdir test_project && cd test_project
输出: 目录创建成功并切换完成

输入: grep -n "import" src/
output: src/agents/agent_universal.py:1:from hello_agents
```

### 3. 复杂任务
```
输入: 搜索LangChain框架的最新版本信息，然后查看当前目录的文件列表
输出: 先执行搜索，然后列出文件，最后给出综合结果
```

## 📂 项目结构

```
universal_hello_agent_llm_decision/
├── README.md              # 项目说明文档
├── requirements.txt       # Python依赖列表
├── main.ipynb            # 主要的Jupyter Notebook
├── main.py               # 命令行入口（可选）
├── data/                 # 数据文件（可选）
│   └── sample_queries.txt
├── outputs/              # 输出结果（可选）
│   ├── demo_results.md
│   ├── docs/             # 文档文件
│   │   ├── CONTRIBUTING.md
│   │   └── IMPROVEMENTS_SUMMARY.md
│   └── tests/            # 测试文件
│       ├── test_agent_improvements.py
│       └── test_tools.py
└── src/                  # 源代码（可选，如果代码较多）
    ├── __init__.py
    ├── agents/           # 智能体模块
    │   ├── __init__.py
    │   ├── agent_universal.py
    │   └── config.py
    ├── tools/            # 工具定义
    │   ├── __init__.py
    │   ├── browser_tool.py
    │   └── terminal_tool.py
    └── utils/            # 工具函数
        └── __init__.py
```

## 🎯 项目亮点

- **模块化设计**: 工具和智能体分离，易于扩展
- **安全优先**: 多层安全策略保护系统安全
- **容错机制**: 智能降级和错误恢复策略
- **标准兼容**: 符合Hello-Agents框架标准
- **多引擎支持**: 4个搜索引擎智能切换

## 🔮 未来计划

- [ ] 添加更多工具（文件操作、数据库查询等）
- [ ] 实现真正的记忆功能集成
- [ ] 优化搜索引擎的响应速度
- [ ] 添加Web界面支持
- [ ] 实现多智能体协作

## 🤝 贡献指南

欢迎提出Issue和Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@haoye2](https://github.com/haoye2)
- 项目链接:[UniversalAgent](https://github.com/datawhalechina/Hello-Agents/tree/main/Co-creation-projects/haoye2-UnivesalAgent)

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！

---

## 📚 更多信息

### 浏览器搜索工具特性

#### 多引擎支持
- **DuckDuckGo**: 稳定的HTML解析搜索
- **Brave搜索**: 现代搜索引擎
- **Ecosia**: 环保友好搜索引擎  
- **Searx.xyz**: 开源元搜索引擎

#### 智能功能
- **8秒快速响应**: 统一超时设置，避免长时间等待
- **静默失败机制**: 快速切换引擎，优化用户体验
- **智能降级策略**: 搜索建议兜底，100%成功率
- **内容质量验证**: 多层过滤确保搜索结果准确性
- **智能内容提取**: 5层策略提取页面主要内容

### 配置文件说明

项目使用 `config.py` 统一管理工具配置，主要配置项：

#### 终端工具安全模式
```python
# config.py
TERMINAL_SECURITY_MODE = "strict"  # 或 "warning"
```
- **strict**（严格模式）：危险命令直接拒绝执行（推荐用于生产环境）
- **warning**（警告模式）：给出警告提示（适合开发调试）

详细说明请参考：[CONFIG_GUIDE.md](./CONFIG_GUIDE.md)

### 注意事项（安全）

- 请勿把真实 API Key 上传到公有仓库。
- `terminal_exec` 只执行列入白名单的命令，仍建议在容器或受控环境中运行。
- DuckDuckGo HTML 抓取仅用于演示，生产环境请使用正规 Search API（SerpApi/Tavily 等）。

### 问题排查

- 若 LLM 接口无法调用，请检查 `.env` 的 `LLM_API_BASE` 与 `LLM_API_KEY` 配置是否正确。
- 若需要把搜索替换为 SerpApi，请参考 `src/tools/browser_tool.py` 并添加 API key。
- 详细配置说明请查看：[CONFIG_GUIDE.md](./CONFIG_GUIDE.md)
