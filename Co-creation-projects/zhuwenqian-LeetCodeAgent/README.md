# LeetCodeAgent - 智能算法导师

> 基于 HelloAgents 框架构建的沉浸式编程学习与算法练习助手。

## 📝 项目简介

本项目作为 `Hello-Agents` 教程的毕业设计，旨在解决编程学习者在刷 LeetCode 时的核心痛点：“**直接看题解容易忘，自己硬憋又太浪费时间**”。

**LeetCodeAgent** 扮演了一位苏格拉底式的专业算法导师。它不会直接给你最终代码，而是通过：
1. 帮你理清题意与**边界测试用例**。
2. 启发式地提供**算法思路提示**（如从暴力解法引导至哈希表/双指针最优解）。
3. 对你的代码进行**复杂度分析**和 **Code Review**，指出 Bug 并建议优化方向。

非常适合想要系统学习数据结构与算法、提升编程能力的开发者！

## ✨ 核心功能

- [x] **题目解析与边缘测试用例生成**：使用 `TestCaseGeneratorTool` 引导用户关注容易出错的边界条件。
- [x] **启发式提示机制**：拒绝直接给答案，采用苏格拉底提问法，引导用户自己思考。
- [x] **代码复杂度分析 (Code Review)**：使用 `ComplexityAnalyzerTool` 自动识别循环嵌套，评估时间/空间复杂度，并提出优化建议。
- [x] **Markdown 格式报告**：每次辅导自动保存为结构化的辅导记录文档。

## 🛠️ 技术栈

- **框架**: `HelloAgents` 核心组件 (`SimpleAgent`, `ToolRegistry`, `Tool`)
- **智能体范式**: 基于 ReAct / Tool-Use 的工具调用与多步思维
- **LLM**: 默认兼容兼容 OpenAI API 标准的模型（如 ModelScope Qwen2.5-72B-Instruct）
- **开发环境**: Jupyter Notebook / Python 3.10+

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API 密钥

创建 `.env` 文件并填入你的模型 API 密钥（本项目默认使用 ModelScope 接口，也可以改成 OpenAI 或 DeepSeek 等）：

```bash
cp .env.example .env
```

打开 `.env` 并填写：
```ini
LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
```

### 4. 运行项目

```bash
# 启动 Jupyter Lab
jupyter lab

# 打开 main.ipynb 并运行单元格
```

## 📖 使用示例

### 场景 1：没有思路求提示
输入：两数之和（Two Sum）的题目描述。
输出：智能体会调用工具为你生成空数组、包含负数等边界测试用例，并提示你可以先考虑双层循环暴力解法。

### 场景 2：代码 Review 与优化
输入：提交了一个 $O(n^2)$ 的暴力解法代码。
输出：智能体会调用 `analyze_complexity` 工具，指出时间复杂度较高，启发你：“在遍历时，是否可以使用字典(Hash Map)记录已经见过的数字，从而将时间复杂度降至 $O(n)$？”

（具体演示请运行 `main.ipynb` 获取，结果会保存至 `outputs/tutor_report.md`）

## 🎯 为什么选择这个项目作为毕业设计？

- 完美契合了 **"学习辅助类"** (Intelligent Programming Tutor) 这一命题。
- 使用了真实有价值的 **Tool (工具调用)** 场景：静态分析与测试用例生成。
- 能够切实提高个人或团队的算法基本功，具有极高的实用落地价值。

## 👤 作者

- GitHub: [@zhuwenqian](https://github.com/zhuwenqian)

## 🙏 致谢

感谢 Datawhale 社区和 `Hello-Agents` 项目提供的详尽教程与开源框架！