# DataAnalysisAgent - 多数据集通用数据分析 Agent

> 基于 HelloAgents 框架的智能数据分析助手：输入一个数据文件，自动完成加载 → 概览 → 清洗 → 统计 → 分组 → 可视化 → 建模 → 报告的完整分析闭环。

## 📝 项目简介

本项目构建了一个**多数据集通用数据分析智能体**：用户只需提供 CSV / Excel 数据文件和一句自然语言需求，Agent 会自主规划分析步骤、调用数据分析工具逐步执行，最终生成带图表的 Markdown 分析报告。

**解决什么问题**：传统数据分析需要人工编写大量 pandas / sklearn 代码，门槛高、流程长。本系统把数据分析流程封装为 8 个可被 LLM 调用的工具，结合 **Plan-and-Solve 智能体范式**，让大模型自主完成规划与执行，**无需人工编写任何分析代码**。

**适用场景**：通用数据集的快速探索、自动化数据分析演示、教学与学习。

## ✨ 核心功能

- [x] **8 个数据分析工具**：加载 / 概览 / 清洗 / 统计 / 分组 / 可视化 / 建模 / 报告
- [x] **PlanSolveAgent 自主规划**：LLM 先生成 3~8 步分析计划，再逐步执行
- [x] **多数据集支持**：CSV / Excel（.xlsx/.xls），通用列结构自动适配
- [x] **防目标泄漏建模**：自动剔除标识符（student_id）与二值代理列（passed_exam）
- [x] **泄漏对照实验**：用无关目标验证建模流程可靠性
- [x] **全中文输出**：统计结论、图表、报告均为中文

## 🛠️ 技术栈

- **HelloAgents 框架**（1.0.1）：PlanSolveAgent（Plan-and-Solve 范式）+ ToolRegistry
- **LLM**：DeepSeek-flash（OpenAI 兼容 API）
- **数据分析**：pandas / numpy / scikit-learn / matplotlib
- **配置**：python-dotenv

## 🚀 快速开始

### 环境要求

- Python 3.12 ~ 3.13（hello-agents 1.0.1 要求 `<3.14`）
- 一个可用的 LLM API Key（DeepSeek）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env，填入你的 API 密钥
```

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb，依次运行所有单元格
```

## 📂 数据集说明

| 文件 | 内容 | 说明 |
|---|---|---|
| `data/python_learning_exam_performance.csv` | Python 学习与考试成绩（500×15） | 主演示数据集，随仓库提交 |
| `data/wdbc.csv` | 乳腺癌诊断（568×32，无表头） | 多数据集通用性验证 |
| `data/超市水果销售数据.xlsx` | 水果销售记录（中文列名） | 多数据集通用性验证 |
| `data/ai_student_impact_dataset.csv` | AI 工具使用对学业影响（约 5.7MB） | **因超过仓库 5MB 红线未随项目提交**；同类数据可在 Kaggle 检索 "AI Impact on Student Life Dataset" 获取：[Kaggle 链接](https://www.kaggle.com/datasets/sumeakash/how-ai-is-changing-student-life/data) |

## 📖 使用示例

1. 准备数据文件（CSV / Excel），放入 `data/` 目录
2. 打开 `main.ipynb`，在"功能演示"部分修改数据路径与分析需求
3. 运行 Notebook，Agent 自动完成全流程分析
4. 查看生成的报告与图表（`outputs/report.md` + `outputs/*.png`）

示例任务：
```
分析 data/python_learning_exam_performance.csv，找出影响期末成绩的关键因素，
并给出可视化图表和完整报告
```

## 🎯 项目亮点

- **零编码分析**：用户只需自然语言描述需求，无需编写任何 pandas / sklearn 代码
- **自主规划**：PlanSolveAgent 根据数据实际情况裁剪分析步骤，不写死流程
- **严谨建模**：内置防目标泄漏逻辑 + 泄漏对照实验，结论经得起推敲
- **可扩展**：新增分析能力只需在工具类中添加一个 `@tool_action` 方法

## 📊 性能评估

以 Python 学习考试成绩数据集（500 名学生 × 15 列）为例：

| 指标 | 结果 |
|---|---|
| 全流程步骤 | 8/8 全部完成 |
| 回归模型 R² | **0.7288** |
| 泄漏对照实验（无关目标 age） | **R² = -0.0167**（≈0，流程无泄漏） |
| 可视化图表 | 4 张 |

**关键发现**：编程基础（Advanced 组比 Beginner 组高 22.2 分）、每周学习时长（r=0.41）、完成项目数（r=0.37）是影响期末成绩的主导因素。

## 🔮 未来计划

- [ ] 支持更多图表类型（散点图、热力图）与自动化图表选择
- [ ] 接入更多模型（随机森林、XGBoost）与交叉验证
- [ ] 增加数据文件自动识别（列语义推断）
- [ ] 多数据集对比分析与综合报告
- [ ] 交互式前端（Streamlit / Gradio）

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@iamfine78](https://github.com/iamfine78)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
