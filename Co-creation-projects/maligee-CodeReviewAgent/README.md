# CodeReviewAgent - 智能代码审查助手

> 基于HelloAgents框架的智能代码审查工具

## 📝 项目简介

CodeReviewAgent是一个智能代码审查助手,能够自动分析Python代码的质量、发现潜在问题并提供优化建议。

### 核心功能

- ✅ 代码结构分析：统计函数、类、代码行数等
- ✅ 风格检查：检查是否符合PEP 8规范
- ✅ 智能建议：基于LLM提供深度分析和优化建议
- ✅ 报告生成：生成Markdown格式的审查报告

## 🛠️ 技术栈

- HelloAgents框架（SimpleAgent）
- Python AST模块（代码解析）
- OpenAI API（智能分析）

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置LLM参数

**方式1: 使用.env文件(推荐)**

```bash
# 复制示例文件
cp .env.example .env

# 编辑.env文件,填入你的配置
# LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
# LLM_API_KEY=your_api_key_here
# LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
```

**方式2: 直接在Notebook中设置(已配置)**

项目已在`main.ipynb`中预配置了ModelScope的API,可以直接使用。如需修改,编辑第1部分的配置代码:

```python
os.environ["LLM_MODEL_ID"] = "your_model"
os.environ["LLM_API_KEY"] = "your_key"
os.environ["LLM_BASE_URL"] = "your_api_url"
```

### 运行项目

```bash
jupyter lab
# 打开main.ipynb并运行所有单元格
```

## 📖 使用示例

### 快速体验

打开`main.ipynb`,运行「第0部分：快速演示」,即可快速了解项目功能。

### 完整功能

1. 将待审查的代码放入`data/sample_code.py`
2. 依次运行`main.ipynb`的第1-7部分
3. 查看生成的审查报告`outputs/review_report.md`

## 🎯 项目亮点

- **自动化**：无需人工逐行检查,自动发现问题
- **智能化**：利用LLM理解代码语义,提供深度建议
- **可扩展**：易于添加新的检查规则和工具

## 📂 项目结构

```
jjyaoao-CodeReviewAgent/
├── README.md              # 项目说明文档
├── requirements.txt       # 依赖列表
├── .gitignore            # Git忽略文件
├── .env.example          # 环境变量示例
├── main.ipynb            # 主程序(包含快速演示和完整功能)
├── data/
│   └── sample_code.py    # 示例代码
└── outputs/
    └── review_report.md  # 审查报告
```

## 🔧 技术实现

### 工具系统

1. **CodeAnalysisTool**: 使用Python AST模块解析代码结构
2. **StyleCheckTool**: 检查PEP 8代码风格规范

### 智能体设计

使用HelloAgents的SimpleAgent,配合自定义工具实现智能代码审查。

## 📊 示例输出

```markdown
# 代码审查报告

## 代码结构分析
- 函数数量: 3
- 类数量: 1
- 代码行数: 45

## 风格问题
- 第12行：超过79个字符
- 第25行：缩进不规范

## 优化建议
1. 建议将长函数拆分为多个小函数
2. 添加类型注解提高代码可读性
3. 补充文档字符串
```

## 🚧 未来改进

- [ ] 支持更多编程语言（JavaScript、Java等）
- [ ] 添加安全漏洞检测
- [ ] 集成更多静态分析工具
- [ ] 支持批量文件审查
- [ ] 生成HTML格式报告

## 👤 作者

- GitHub: [@jjyaoao](https://github.com/jjyaoao)
- 项目链接：[CodeReviewAgent](https://github.com/datawhalechina/Hello-Agents/tree/main/Co-creation-projects/jjyaoao-CodeReviewAgent)

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！

## 📄 许可证

本项目采用MIT许可证。

