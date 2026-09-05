# CodeTutorDemo

> 一个面向初学者的编程问答与代码点评智能体项目。

## 📝 项目简介

本项目基于 `LangChain + LangGraph` 实现了一个适合课程毕业设计展示的智能编程导师。

它主要解决两个常见学习问题：
- 初学者遇到编程概念时，不知道该怎么理解和入门；
- 初学者写出一段 Python 代码后，不知道问题出在哪里，也不知道怎么改。

项目支持输入自然语言编程问题，或者直接输入一段 Python 代码。系统会自动判断当前更适合走“问答辅导”还是“代码点评”分支，并输出教学式回答与课后练习建议。

适用于：
- Python 初学者课堂演示
- 智能体课程毕业设计展示
- LangGraph 基础工作流项目练习

## ✨ 核心功能

- [x] 自动识别“编程问答”与“代码点评”两种模式
- [x] 支持提取 Markdown 代码块中的 Python 代码
- [x] 问答模式输出概念解释、解题思路、简单示例、易错点
- [x] 代码点评模式输出主要问题、修改建议、参考改法、学习提醒
- [x] 保存最近几轮上下文，支持简易记忆
- [x] 提供 `pytest` 测试，保证核心逻辑可验证

## 🛠️ 技术栈

- Python 3.11+
- LangGraph
- LangChain
- langchain-openai
- python-dotenv
- pytest
- 智能体范式：单智能体工作流路由

## 🚀 快速开始

### 环境要求

- Python 3.11+
- 可用的大模型 API Key

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
cp .env.example .env
```

然后编辑 `.env` 文件：

```env
API_KEY=your_api_key_here
BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

注意：不要提交 `.env` 文件。

### 运行项目

命令行运行方式：

```bash
PYTHONPATH=src python -m tutor.main
```

Notebook 演示方式：

```bash
jupyter lab
```

然后打开 `main.ipynb`，按顺序运行即可。

### 运行测试

```bash
python -m pytest -q tests
```

## 📖 使用示例

### 示例一：编程问答

输入：

```text
Python 里的 for 循环和 while 循环有什么区别？
```

输出示例：

```text
【编程问题讲解】
for 循环更适合遍历已有范围或序列，while 循环更适合在条件满足时反复执行。

【练习建议】
请你分别用 for 和 while 写一个输出 1 到 5 的小程序。
```

### 示例二：代码点评

输入：

```python
def add(a,b)
    return a+b
```

输出示例：

```text
【代码点评结果】
这段代码的主要问题是函数定义后少了冒号，因此会出现语法错误，建议先修正函数头，再运行测试。

【练习建议】
请你自己写一个 subtract 函数，并故意制造一个缩进错误，再改正它。
```

## 🎯 项目亮点

- 用 LangGraph 清晰展示“识别 -> 路由 -> 生成 -> 总结”的智能体流程
- 同时覆盖“问答辅导”和“代码点评”两个真实学习场景
- 结构简单，适合初学者阅读、修改和答辩讲解

## 📊 性能评估

当前版本以教学演示和流程正确性为主：
- 本地测试：`16 passed`
- 支持无网络测试替身 `FakeLLMAdapter`
- 模型输出异常时提供兜底内容，保证演示稳定

## 🔮 未来计划

- [ ] 增加连续多轮对话界面
- [ ] 增加学习路径规划功能
- [ ] 增加本地知识库检索能力（RAG）
- [ ] 增加更多语言的代码点评支持

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request。

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@yangxiangyou](https://github.com/yangxiangyou)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目提供的学习资料与实践平台。
