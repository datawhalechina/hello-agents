# MathModelAgent 开发指南

## 项目架构

### 整体架构

```
MathModelAgent/
├── main.ipynb              # 主程序入口
├── knowledge/              # RAG知识库
│   └── *.md               # 知识文档（Markdown格式）
├── templates/              # LaTeX模板
│   └── *.tex              # LaTeX模板文件
├── data/                   # 数据文件
│   └── sample_data.csv    # 示例数据
├── outputs/                # 输出目录
│   └── *.pdf              # 生成的PDF文件
└── src/                    # 源代码（可选）
    ├── agents/            # 智能体定义
    ├── tools/             # 工具实现
    └── utils/             # 工具函数
```

### 核心模块

#### 1. RAG知识库模块

**文件位置**：`main.ipynb` 中的 `RAGKnowledgeBase` 类

**功能**：
- 加载本地知识文档
- 向量化存储
- 语义检索

**使用方法**：

```python
# 初始化知识库
kb = RAGKnowledgeBase(knowledge_dir="./knowledge")

# 搜索相关知识
results = kb.search("线性规划", k=3)

# 添加新文档
kb.add_document("新的知识内容", "new_knowledge.md")
```

**扩展建议**：
- 支持更多文档格式（PDF、Word等）
- 优化检索算法（混合检索）
- 添加知识图谱支持

#### 2. 多模型调度模块

**文件位置**：`main.ipynb` 中的 `ModelScheduler` 类

**功能**：
- 根据任务难度选择模型
- 节省token成本
- 保证输出质量

**使用方法**：

```python
# 初始化调度器
scheduler = ModelScheduler()

# 选择模型
model = scheduler.select_model("simple")  # 简单任务
model = scheduler.select_model("medium")  # 中等任务
model = scheduler.select_model("complex") # 复杂任务
```

**扩展建议**：
- 支持更多模型提供商
- 添加模型性能评估
- 实现自动模型选择

#### 3. HIL人机协作模块

**文件位置**：`main.ipynb` 中的 `HILCollaboration` 类

**功能**：
- 关键节点暂停等待用户审批
- 支持6种决策动作
- 灵活的人机交互

**决策动作**：
- `confirm`：确认当前结果
- `edit`：编辑修改当前结果
- `regenerate`：重新生成结果
- `ask`：向AI提问获取更多信息
- `skip`：跳过当前步骤
- `abort`：中止整个流程

**使用方法**：

```python
# 初始化HIL
hil = HILCollaboration()

# 暂停等待用户审批
action = hil.pause_for_review("问题分析", analysis_result)

# 根据用户动作处理
if action == "confirm":
    # 继续下一步
    pass
elif action == "edit":
    # 获取用户修改
    new_content = hil.get_user_input("请输入修改内容: ")
elif action == "regenerate":
    # 重新生成
    pass
elif action == "ask":
    # 向AI提问
    pass
elif action == "skip":
    # 跳过当前步骤
    pass
elif action == "abort":
    # 中止流程
    pass
```

#### 4. 联网搜索模块

**文件位置**：`main.ipynb` 中的 `WebSearch` 类

**功能**：
- 实时搜索最新信息
- 提取网页内容
- 整合搜索结果

**使用方法**：

```python
# 初始化搜索
search = WebSearch(api_key="your_api_key")

# 搜索
results = search.search("数学建模方法", num_results=5)

# 提取网页内容
content = search.extract_content("https://example.com")
```

**扩展建议**：
- 支持多个搜索引擎
- 添加结果缓存
- 实现内容摘要

#### 5. LaTeX论文生成模块

**文件位置**：`main.ipynb` 中的 `LatexGenerator` 类

**功能**：
- 生成LaTeX格式论文
- 支持自定义模板
- 编译为PDF

**使用方法**：

```python
# 初始化生成器
generator = LatexGenerator(template_dir="./templates")

# 论文内容
content = {
    "title": "数学建模论文",
    "author": "作者",
    "abstract": "摘要内容",
    "problem_restatement": "问题重述",
    "problem_analysis": "问题分析",
    "model_assumptions": "模型假设",
    "symbol_description": "符号说明",
    "model_establishment": "模型建立与求解",
    "model_verification": "模型验证",
    "model_evaluation": "模型评价与改进",
    "references": "参考文献"
}

# 生成LaTeX文件
generator.generate(content, "output/paper.tex")

# 编译PDF
generator.compile_pdf("output/paper.tex")
```

**扩展建议**：
- 支持更多LaTeX模板
- 添加图表生成
- 实现自动参考文献管理

#### 6. 可行性检查模块

**文件位置**：`main.ipynb` 中的 `FeasibilityChecker` 类

**功能**：
- 技术可行性检查
- 数据可行性检查
- 时间可行性检查
- 资源可行性检查

**使用方法**：

```python
# 初始化检查器
checker = FeasibilityChecker()

# 检查需求
requirements = {
    "technical": {"libraries": ["hello-agents", "langchain"]},
    "data": {"format": "csv", "size": "100MB"},
    "time": {"deadline": "2026-09-01", "estimated_days": 7},
    "resource": {"api_calls": 1000, "compute": "CPU"}
}

# 执行检查
results = checker.check_all(requirements)
```

## 开发规范

### 代码风格

- 遵循PEP 8规范
- 使用类型注解
- 编写清晰的文档字符串

### 命名规范

- 类名：PascalCase（如 `RAGKnowledgeBase`）
- 函数名：snake_case（如 `search_knowledge`）
- 变量名：snake_case（如 `knowledge_base`）
- 常量名：UPPER_CASE（如 `MAX_RESULTS`）

### 文档规范

- 每个类和函数都要有文档字符串
- 文档字符串使用Google风格
- 包含参数说明和返回值说明

### 测试规范

- 编写单元测试
- 测试覆盖率 > 80%
- 使用pytest框架

## 扩展开发

### 添加新的智能体

1. 在 `main.ipynb` 中定义新的智能体类
2. 实现必要的方法
3. 在 `MathModelAgent` 中集成

### 添加新的工具

1. 继承 `Tool` 基类
2. 实现 `run` 方法
3. 定义参数列表
4. 注册到工具注册表

### 添加新的知识文档

1. 在 `knowledge` 目录下创建Markdown文件
2. 按照格式组织内容
3. 重启知识库加载

### 自定义LaTeX模板

1. 在 `templates` 目录下创建模板文件
2. 使用Jinja2语法定义变量
3. 在 `LatexGenerator` 中加载模板

## 常见问题

### Q: 如何添加新的模型提供商？

A: 在 `ModelScheduler` 类中添加新的模型配置，并实现相应的API调用逻辑。

### Q: 如何优化RAG检索效果？

A: 可以尝试以下方法：
- 调整文本分割参数
- 使用更好的嵌入模型
- 实现混合检索（向量+关键词）

### Q: 如何处理大文件？

A: 使用外部链接或独立仓库存储大文件，在README中提供下载链接。

### Q: 如何调试代码？

A: 使用Jupyter Notebook的调试功能，或添加print语句输出中间结果。

## 性能优化

### 1. 缓存优化

- 缓存LLM调用结果
- 缓存知识库检索结果
- 使用Redis或本地缓存

### 2. 并发处理

- 使用异步IO处理并发请求
- 批量处理多个任务
- 使用线程池或进程池

### 3. 内存优化

- 使用生成器处理大数据
- 及时释放不需要的资源
- 使用内存映射文件

## 部署指南

### 本地部署

1. 安装依赖
2. 配置环境变量
3. 运行Jupyter Notebook

### Docker部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
```

### 云平台部署

- 支持部署到各大云平台
- 使用容器服务
- 配置自动扩展

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 版本历史

- v1.0.0：初始版本
  - 实现基本功能
  - 支持多模型调度
  - 支持RAG知识库
  - 支持HIL人机协作
