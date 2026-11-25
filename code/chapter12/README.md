# 第十二章示例代码

本目录包含第十二章《智能体性能评估》的所有示例代码，按照文档顺序编号，方便学习者跟随文档学习。

## 📁 文件列表

| 文件名 | 对应章节 | 说明 |
|--------|---------|------|
| `01_basic_agent_example.py` | 12.1.1 | 基础智能体示例，说明为何需要评估 |
| `02_bfcl_quick_start.py` | 12.2.5 | BFCL快速开始（一键评估） |
| `03_bfcl_custom_evaluation.py` | 12.2.5 | BFCL自定义评估（底层组件） |
| `04_run_bfcl_evaluation.py` | 12.2.9 | BFCL评估最佳实践 |
| `05_gaia_quick_start.py` | 12.3.5 | GAIA快速开始（一键评估） |
| `06_gaia_best_practices.py` | 12.3.9 | GAIA评估最佳实践 |
| `07_data_generation_complete_flow.py` | 12.4.6 | 数据生成完整评估流程 |
| `08_data_generation_llm_judge.py` | 12.4.3 | LLM Judge评估 |
| `09_data_generation_win_rate.py` | 12.4.4 | Win Rate评估 |

## 🚀 快速开始

### 环境准备

1. **安装HelloAgents框架**：
   ```bash
   pip install hello-agents[evaluation]==0.2.3
   ```

2. **设置环境变量**：
   ```bash
   # OpenAI API Key（用于GPT-4o）
   export OPENAI_API_KEY="your_openai_api_key"
   
   # HuggingFace Token（用于GAIA数据集）
   export HF_TOKEN="your_huggingface_token"
   ```

3. **为示例 3 和 4 准备 BFCL 数据集**。从本教程的仓库根目录执行一次：
   ```bash
   git clone --depth 1 https://github.com/ShishirPatil/gorilla.git code/temp_gorilla
   ```

### 运行示例

#### 1. 基础智能体示例

```bash
python 01_basic_agent_example.py
```

这个示例展示了一个基本的ReAct智能体，说明为何需要评估系统。

#### 2. BFCL快速开始

```bash
python 02_bfcl_quick_start.py
```

这是最简单的BFCL评估方式，一行代码完成评估。

**预期输出**：
```
准确率: 100.00%
正确数: 5/5
```

#### 3. BFCL自定义评估

从仓库的 `code` 目录运行，示例会从当前目录下的 `temp_gorilla` 加载数据：

```bash
python chapter12/03_bfcl_custom_evaluation.py
```

展示如何使用底层组件进行自定义评估流程。

#### 4. BFCL最佳实践

同样从 `code` 目录运行：

```bash
python chapter12/04_run_bfcl_evaluation.py
```

展示BFCL评估的最佳实践，包括：
- 渐进式评估
- 多类别评估
- 对比评估
- 错误分析

#### 5. GAIA快速开始

**重要提示**：GAIA是受限数据集，需要先申请访问权限。

1. 访问 https://huggingface.co/datasets/gaia-benchmark/GAIA
2. 点击"Request Access"申请访问权限
3. 等待审核通过（通常1-2天）
4. 设置HF_TOKEN环境变量

```bash
python 05_gaia_quick_start.py
```

**预期输出**：
```
精确匹配率: 100.00%
部分匹配率: 100.00%
正确数: 2/2
```

#### 6. GAIA最佳实践

```bash
python 06_gaia_best_practices.py
```

展示GAIA评估的最佳实践，包括：
- 分级评估
- 小样本快速测试
- 结果解读

#### 7. 数据生成完整评估流程

```bash
python 07_data_generation_complete_flow.py 30 3.0
```

参数说明：
- `30`：生成30道题目
- `3.0`：每道题目之间延迟3秒

这个示例展示了数据生成的完整评估流程：
1. 生成AIME题目
2. LLM Judge评估
3. Win Rate评估
4. 人工验证

**预期输出**：
```
生成数量: 30道题目
LLM Judge平均分: 3.5/5.0
Win Rate: 45.0%
建议: 生成质量接近AIME真题水平
```

#### 8. LLM Judge评估

```bash
python 08_data_generation_llm_judge.py
```

展示如何使用LLM Judge评估生成的AIME题目质量。

**预期输出**：
```
平均分:
  正确性: 5.00/5
  清晰度: 4.50/5
  难度匹配: 4.00/5
  完整性: 5.00/5
  总体平均: 4.62/5

质量评估:
✅ 优秀 - 题目质量很高，可以直接使用
```

#### 9. Win Rate评估

```bash
python 09_data_generation_win_rate.py
```

展示如何使用Win Rate评估生成的AIME题目质量。

**预期输出**：
```
Win Rate: 45.00%
Tie Rate: 10.00%
Loss Rate: 45.00%

质量评估:
✅ 优秀 - 生成质量接近AIME真题水平
```

## 📊 学习路径

### 初学者路径

1. **了解评估的必要性**：
   - 运行 `01_basic_agent_example.py`

2. **学习BFCL评估**：
   - 运行 `02_bfcl_quick_start.py`（快速开始）
   - 运行 `04_run_bfcl_evaluation.py`（最佳实践）

3. **学习GAIA评估**：
   - 运行 `05_gaia_quick_start.py`（快速开始）
   - 运行 `06_gaia_best_practices.py`（最佳实践）

### 进阶路径

1. **自定义评估流程**：
   - 运行 `03_bfcl_custom_evaluation.py`

2. **数据生成评估**：
   - 运行 `08_data_generation_llm_judge.py`（LLM Judge）
   - 运行 `09_data_generation_win_rate.py`（Win Rate）
   - 运行 `07_data_generation_complete_flow.py`（完整流程）

## 💡 常见问题

### Q1: 运行示例时提示找不到模块？

A: 请确保已安装HelloAgents框架：
```bash
cd ../HelloAgents
pip install -e .
```

### Q2: BFCL评估提示找不到数据集？

A: 示例 3 和 4 需要本地数据。按上面的“环境准备”第 3 步克隆仓库，然后在 `code` 目录下确认 `temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data` 存在。

### Q3: GAIA评估提示没有访问权限？

A: GAIA是受限数据集，需要先申请访问权限：
1. 访问 https://huggingface.co/datasets/gaia-benchmark/GAIA
2. 点击"Request Access"
3. 等待审核通过
4. 设置HF_TOKEN环境变量

### Q4: 评估速度太慢？

A: 可以减少样本数量：
```python
# BFCL评估
results = bfcl_tool.run(agent, category="simple_python", max_samples=5)

# GAIA评估
results = gaia_tool.run(agent, level=1, max_samples=2)

# 数据生成评估
python 07_data_generation_complete_flow.py 10 3.0  # 只生成10道题目
```

### Q5: 如何估算评估成本？

A: 评估成本主要来自LLM API调用：

**BFCL评估**：
- 每个样本约1次API调用
- 成本约0.01-0.02元/样本
- 完整评估（400样本）约4-8元

**GAIA评估**：
- 每个样本约1-5次API调用（取决于任务复杂度）
- 成本约0.05-0.20元/样本
- 完整评估（466样本）约23-93元

**数据生成评估**：
- 生成：约0.05元/题
- LLM Judge：约0.02元/题
- Win Rate：约0.02元/对比
- 生成30道题目约2-3元

## 📚 相关资源

- **HelloAgents框架**：https://github.com/jjyaoao/HelloAgents
- **BFCL官方仓库**：https://github.com/ShishirPatil/gorilla
- **GAIA官方仓库**：https://huggingface.co/datasets/gaia-benchmark/GAIA

## 🤝 贡献

如果你发现示例代码有问题或有改进建议，欢迎提交Issue或Pull Request。

## 📄 许可证

本示例代码遵循与HelloAgents框架相同的许可证。

