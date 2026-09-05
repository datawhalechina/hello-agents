# MathModelAgent 用户使用手册

## 欢迎使用 MathModelAgent

MathModelAgent 是一个智能数学建模助手，能够帮助您完成数学建模的全过程，包括问题分析、模型选择、数据处理、求解指导和论文生成。

## 快速开始

### 1. 环境准备

#### 系统要求

- Python 3.10 或更高版本
- 操作系统：Windows、macOS 或 Linux
- 内存：建议 8GB 以上
- 磁盘空间：建议 2GB 以上

#### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/16deng/hello-agents.git
cd hello-agents/Co-creation-projects/16deng-MathModelAgent
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **配置环境变量**

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥
```

### 2. 配置 API 密钥

#### 获取 API 密钥

1. **ModelScope（推荐）**
   - 访问 https://modelscope.cn
   - 注册并登录账号
   - 进入个人中心 → API密钥管理
   - 创建新的 API 密钥

2. **OpenAI**
   - 访问 https://platform.openai.com
   - 注册并登录账号
   - 进入 API Keys 页面
   - 创建新的 API 密钥

#### 配置 API 密钥

编辑 `.env` 文件，填入你的 API 密钥：

```env
# LLM配置
LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
LLM_TIMEOUT=60

# 搜索API配置（可选）
SEARCH_API_KEY=your_search_api_key_here
```

### 3. 运行项目

#### 启动 Jupyter Notebook

```bash
jupyter lab
```

#### 打开主程序

在 Jupyter Lab 中打开 `main.ipynb` 文件。

## 功能详解

### 1. 问题分析

**功能描述**：自动分析数学建模问题，提取关键信息。

**使用方法**：

1. 在代码单元格中输入问题描述：

```python
problem = """
某公司需要优化其物流配送路线。公司有10个配送点，每个配送点有一定数量的货物需要配送。
配送车辆从仓库出发，需要将货物送到各个配送点，然后返回仓库。
目标是找到最短的配送路线，使得总配送距离最短。
"""
```

2. 运行问题分析：

```python
agent = MathModelAgent()
analysis = agent.analyze_problem(problem)
print(analysis)
```

3. 系统会自动：
   - 从知识库检索相关知识
   - 使用 LLM 分析问题
   - 输出问题类型、关键变量、约束条件

### 2. 模型推荐

**功能描述**：根据问题类型推荐合适的数学模型。

**使用方法**：

```python
# 获取模型推荐
recommendation = agent.recommend_model(analysis)
print(recommendation)
```

系统会推荐 2-3 个模型，并说明：
- 模型名称
- 适用场景
- 优缺点
- 实现难度

### 3. 数据分析

**功能描述**：对数据进行清洗、统计分析和可视化。

**使用方法**：

1. 准备数据文件（CSV、Excel 等格式）

2. 加载数据：

```python
import pandas as pd

data = pd.read_csv("data/sample_data.csv")
print(data.head())
```

3. 数据分析：

```python
# 基本统计
print(data.describe())

# 数据可视化
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.scatter(data['x'], data['y'], s=data['demand']*10, alpha=0.6)
plt.xlabel('X 坐标')
plt.ylabel('Y 坐标')
plt.title('配送点分布图')
plt.grid(True)
plt.show()
```

### 4. 求解指导

**功能描述**：生成 Python 求解代码。

**使用方法**：

```python
# 生成求解代码
solution = agent.generate_solution("TSP", "配送点坐标数据")
print(solution)
```

系统会生成：
- 完整的 Python 代码
- 详细的注释
- 使用说明

### 5. RAG 知识库

**功能描述**：从本地知识库检索建模方法、代码模板、论文写作参考。

**使用方法**：

1. **添加知识文档**

在 `knowledge` 目录下创建 Markdown 文件：

```markdown
# 线性规划

## 定义
线性规划是数学规划的一个重要分支...

## 适用场景
- 资源分配问题
- 生产计划问题
- 运输问题

## Python 实现
```python
from scipy.optimize import linprog
# 代码示例...
```
```

2. **搜索知识**

```python
kb = RAGKnowledgeBase()
results = kb.search("线性规划", k=3)

for i, result in enumerate(results):
    print(f"结果 {i+1}:")
    print(result)
    print()
```

3. **添加新知识**

```python
kb.add_document("新的知识内容", "new_knowledge.md")
```

### 6. HIL 人机协作

**功能描述**：关键节点暂停等待用户审批，支持 6 种决策动作。

**决策动作**：

| 动作 | 说明 |
|------|------|
| `confirm` | 确认当前结果，继续下一步 |
| `edit` | 编辑修改当前结果 |
| `regenerate` | 重新生成结果 |
| `ask` | 向 AI 提问获取更多信息 |
| `skip` | 跳过当前步骤 |
| `abort` | 中止整个流程 |

**使用方法**：

```python
hil = HILCollaboration()

# 暂停等待用户审批
action = hil.pause_for_review("问题分析", analysis_result)

# 根据用户动作处理
if action == "confirm":
    print("已确认，继续下一步")
elif action == "edit":
    new_content = hil.get_user_input("请输入修改内容: ")
elif action == "regenerate":
    # 重新生成
    pass
elif action == "ask":
    question = hil.get_user_input("请输入你的问题: ")
    # 向AI提问
    pass
elif action == "skip":
    print("已跳过当前步骤")
elif action == "abort":
    print("已中止流程")
```

### 7. 联网搜索

**功能描述**：实时搜索最新的建模方法和论文。

**使用方法**：

```python
search = WebSearch()

# 搜索
results = search.search("数学建模方法", num_results=5)

for result in results:
    print(f"标题: {result['title']}")
    print(f"链接: {result['url']}")
    print(f"摘要: {result['snippet']}")
    print()

# 提取网页内容
content = search.extract_content("https://example.com")
print(content)
```

### 8. LaTeX 论文生成

**功能描述**：自动生成符合格式的数学建模论文。

**使用方法**：

```python
generator = LatexGenerator()

# 论文内容
content = {
    "title": "物流配送路线优化研究",
    "author": "16deng",
    "abstract": "本文研究了物流配送路线优化问题...",
    "problem_restatement": "问题重述内容...",
    "problem_analysis": "问题分析内容...",
    "model_assumptions": "模型假设内容...",
    "symbol_description": "符号说明内容...",
    "model_establishment": "模型建立与求解内容...",
    "model_verification": "模型验证内容...",
    "model_evaluation": "模型评价与改进内容...",
    "references": "参考文献内容..."
}

# 生成LaTeX文件
generator.generate(content, "outputs/paper.tex")

# 编译PDF
generator.compile_pdf("outputs/paper.tex")
```

### 9. 可行性检查

**功能描述**：检查技术、数据、时间、资源可行性。

**使用方法**：

```python
checker = FeasibilityChecker()

requirements = {
    "technical": {"libraries": ["hello-agents", "langchain", "faiss"]},
    "data": {"format": "csv", "size": "100MB"},
    "time": {"deadline": "2026-09-01", "estimated_days": 7},
    "resource": {"api_calls": 1000, "compute": "CPU"}
}

results = checker.check_all(requirements)

for check_name, result in results.items():
    print(f"{check_name}: {result['status']} - {result['message']}")
```

## 完整建模流程

### 步骤 1：准备问题

```python
problem = """
某公司需要优化其物流配送路线。公司有10个配送点，每个配送点有一定数量的货物需要配送。
配送车辆从仓库出发，需要将货物送到各个配送点，然后返回仓库。
目标是找到最短的配送路线，使得总配送距离最短。
"""
```

### 步骤 2：运行建模助手

```python
agent = MathModelAgent()
agent.run(problem)
```

### 步骤 3：人机协作

系统会在关键节点暂停，等待您的审批：

1. **问题分析确认**
   - 查看分析结果
   - 选择确认、编辑或重新生成

2. **模型选择确认**
   - 查看推荐模型
   - 选择合适的模型

3. **求解代码确认**
   - 查看生成的代码
   - 编辑或确认代码

4. **论文生成确认**
   - 查看论文内容
   - 编辑或确认内容

### 步骤 4：查看结果

建模完成后，查看生成的文件：

- `outputs/paper.tex`：LaTeX 格式论文
- `outputs/paper.pdf`：PDF 格式论文（需要 LaTeX 编译器）

## 高级功能

### 1. 自定义模型

修改 `ModelScheduler` 类，添加新的模型：

```python
self.models["custom"] = {
    "name": "your-model-name",
    "description": "自定义模型"
}
```

### 2. 自定义模板

在 `templates` 目录下创建新的 LaTeX 模板：

```latex
\documentclass{article}
% 自定义模板内容...
```

### 3. 批量处理

处理多个问题：

```python
problems = ["问题1", "问题2", "问题3"]

for problem in problems:
    agent.run(problem)
```

### 4. 导出数据

导出分析结果：

```python
import json

results = {
    "analysis": analysis,
    "recommendation": recommendation,
    "solution": solution
}

with open("outputs/results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

## 常见问题

### Q1: 如何获取 API 密钥？

A: 参考"配置 API 密钥"章节，推荐使用 ModelScope 服务。

### Q2: 如何添加知识文档？

A: 在 `knowledge` 目录下创建 Markdown 文件，按照格式组织内容。

### Q3: 如何自定义论文模板？

A: 在 `templates` 目录下创建 LaTeX 模板文件，使用 Jinja2 语法定义变量。

### Q4: 如何处理大文件？

A: 使用外部链接或独立仓库存储大文件，在 README 中提供下载链接。

### Q5: 如何优化检索效果？

A: 调整文本分割参数，使用更好的嵌入模型，实现混合检索。

### Q6: 如何调试代码？

A: 使用 Jupyter Notebook 的调试功能，或添加 print 语句输出中间结果。

## 技术支持

- **GitHub Issues**：提交问题和建议
- **邮箱**：1946877661@q.com
- **文档**：查看 DEVELOPMENT.md 获取更多技术细节

## 版本历史

- **v1.0.0**（2026-08-22）
  - 初始版本
  - 实现基本功能
  - 支持多模型调度
  - 支持 RAG 知识库
  - 支持 HIL 人机协作

## 许可证

MIT License

## 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
