# DataAnalyst - 智能数据分析助手

> 基于 HelloAgents 框架的三阶段多智能体数据分析流水线：**规划 → 分析 → 报告**，一键把任意 CSV 变成图文并茂的数据分析报告。

## 📝 项目简介

数据分析是业务决策的重要环节，但人工分析耗时长、容易遗漏数据中的关键模式，现有的 BI 工具又需要手工拖拽配置。DataAnalyst 基于多智能体协作思路解决这个问题：你只需要**替换一个 CSV 文件**，智能体团队就会自动完成数据探查、分析规划、多维度统计、图表生成和报告撰写。

### 解决什么问题？

- 数据分析门槛高：不懂 pandas / 统计的业务人员也能获得专业分析
- 分析流程碎片化：探查、统计、绘图、写报告一步到位
- 分析深度不足：智能体主动规划任务，主动挖掘趋势、结构、相关性与异常

### 适用于什么场景？

电商/零售订单分析、运营数据周报、任何"一份 CSV + 想知道里面有什么"的场景。

## ✨ 核心功能

- ✅ **三阶段多智能体流水线**：分析规划师（ReActAgent）规划任务 → 数据分析员（ReActAgent）逐任务调用工具深度分析 → 报告撰写师（SimpleAgent）汇总成文
- ✅ **通用数据集支持**：任意 CSV 均可分析，字段自动识别，无需修改任何代码
- ✅ **6 个原子分析工具**：数据概览、单列画像、相关性分析、分组聚合、IQR 异常检测、6 种统计图表绘制
- ✅ **自动中文图表**：直方图/柱状图/箱线图/折线图/散点图/热力图，自动处理中文字体，保存 PNG 并嵌入报告
- ✅ **稳健的工程细节**：规划输出「JSON 优先 + 正则兜底」双解析、工具层参数校验与自纠错、异常处理

## 🛠️ 技术栈

- **HelloAgents 框架**：`ReActAgent`（基于 Function Calling 的推理与行动）、`SimpleAgent`、`ToolRegistry`、`Tool/ToolResponse` 工具体系
- **智能体范式**：Plan-and-Solve（三阶段任务分解）+ ReAct（工具调用循环）
- **数据分析**：pandas（统计聚合）、matplotlib（可视化）
- **LLM**：DeepSeek（`deepseek-chat`，OpenAI 兼容接口，任何兼容 API 均可通过 `.env` 切换）

## 🚀 快速开始

### 环境要求

- Python 3.10+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
# 1. 复制环境变量示例文件
cp .env.example .env

# 2. 编辑 .env，填入你的 DeepSeek API Key（https://platform.deepseek.com 申请）
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com/v1
```

> 使用其他 OpenAI 兼容 API（如 ModelScope、智谱）也可以，只需修改 `.env` 中的三个变量。

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb，从上到下运行所有单元格
```

运行结束后查看结果：

- 📄 分析报告：`outputs/analysis_report.md`
- 📊 分析图表：`outputs/charts/*.png`

## 📖 使用示例

1. 把你的数据集放到 `data/` 目录（项目自带一份 800 条的模拟电商销售数据 `data/sales_data.csv`）
2. 修改 Notebook 第 1 部分的 `DATA_PATH` 指向你的文件（默认即可）
3. 运行 `main.ipynb` 全部单元格

流水线运行过程（示例输出）：

```
============================================================
【阶段1/3】分析规划：探查数据并生成分析任务
✅ 规划完成，共 4 个分析任务:
   任务1: 销售额月度趋势分析
   任务2: 产品类别结构分析
   任务3: 地区与渠道销售对比
   任务4: 客户满意度影响因素与异常订单检测
============================================================
【阶段2/3】逐任务深度分析
>>> 执行任务1: 销售额月度趋势分析
...
============================================================
【阶段3/3】撰写分析报告
✅ 报告已保存: outputs/analysis_report.md
✅ 共生成图表 5 张，保存于 outputs/charts/
```

> 💡 没有配置 API 密钥？Notebook **第 7 部分「工具自检」**不消耗任何 LLM 调用，可直接运行体验工具层能力。

### 分析自己想分析的数据？

支持任意 CSV。例如把一份考试成绩表放到 `data/`，智能体会自动识别字段并围绕"分数分布、科目相关性、班级对比、异常值"等角度重新规划分析任务。

## 📊 示例输出

对自带电商数据集的一次完整分析（见 `outputs/` 目录）自动发现了：

- 销售额的**大促季节性**：6 月、11 月、12 月为全年峰值
- **品类集中度**：电子产品贡献约 75% 的销售额
- **体验短板**：客户满意度与配送天数呈中等负相关（r ≈ -0.59）
- **异常订单**：IQR 检出多笔疑似批发的异常大额订单

## 🎯 项目亮点

- **架构清晰**：规划/执行/撰写三阶段职责分离，范式对应教材第 4、7 章（Plan-and-Solve + ReAct）
- **真正通用**：工具层只依赖数据本身，换数据集即换分析主题
- **工程稳健**：双解析兜底、参数校验自纠错、图表文件名防冲突、中文渲染适配
- **易于评审**：工具层可独立运行自检，报告与图表全部落盘可追溯

## 📁 项目结构

```
minghaoxia61-web-DataAnalyst/
├── README.md              # 项目说明文档
├── requirements.txt       # Python 依赖列表
├── main.ipynb             # 主程序：6个工具 + 三智能体流水线 + 完整演示
├── .env.example           # 环境变量示例（复制为 .env 使用）
├── .gitignore             # Git 忽略规则（防止泄露 API Key）
├── data/
│   └── sales_data.csv     # 模拟电商销售数据集（800条，85KB）
└── outputs/               # 示例运行输出
    ├── analysis_report.md # 分析报告示例
    └── charts/            # 分析图表示例
```

## 🔮 未来计划

- [ ] 支持 Excel 多 Sheet 与数据库数据源
- [ ] 引入 ReflectionAgent 对报告质量自动复审
- [ ] 增加 Gradio 交互界面，支持拖拽上传
- [ ] 分析结果缓存与增量分析

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@minghaoxia61-web](https://github.com/minghaoxia61-web)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
