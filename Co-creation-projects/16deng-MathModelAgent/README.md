# MathModelAgent - 智能数学建模助手

> 基于HelloAgents框架的智能数学建模辅助系统

## 项目简介

MathModelAgent是一个智能数学建模助手，能够帮助用户完成数学建模的全过程，包括问题分析、模型选择、数据处理、求解指导和论文生成。

### 核心功能

- ✅ 多模型智能调度：根据任务难度选择不同模型，节省token
- ✅ RAG知识库：从本地知识库检索建模方法、代码模板、论文写作参考
- ✅ HIL人机协作：关键节点暂停等待用户审批，支持6种决策动作
- ✅ 联网搜索：获取最新的建模方法和论文
- ✅ LaTeX论文生成：自动生成符合格式的数学建模论文
- ✅ 可行性检查：技术、数据、时间、资源可行性评估

## 技术栈

- HelloAgents框架（多智能体协作）
- LangChain + FAISS（RAG知识库）
- Pandas + NumPy + Matplotlib（数据分析）
- 多模型接入（Qwen2.5-72B, GPT-4, Claude等）
- 联网搜索（Google/Bing API）
- LaTeX论文生成（Jinja2模板 + PDF编译）

## 快速开始

### 环境要求

- Python 3.10+
- LaTeX编译器（如TeX Live、MiKTeX）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API密钥

```bash
# 创建.env文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥
```

### 运行项目

```bash
# 启动Jupyter Notebook
jupyter lab

# 打开main.ipynb并运行
```

## 使用示例

1. 准备数学建模问题描述
2. 运行main.ipynb
3. 按照提示进行人机协作
4. 生成LaTeX论文和PDF

## 项目亮点

- **多模型调度**：智能选择模型，平衡效果和成本
- **RAG知识库**：本地知识检索，提高回答准确性
- **人机协作**：关键节点可控，保证结果质量
- **LaTeX输出**：专业论文格式，直接可用

## 作者

- GitHub: [@16deng](https://github.com/16deng)

## 致谢

感谢Datawhale社区和Hello-Agents项目！
