# BFCL 扩展评估模块设计方案

## 1. 概述

BFCL (Berkeley Function Calling Leaderboard) 评估器的三个扩展功能，对智能体的工具调用能力进行多维评估：

- **顺序验证** — 多步调用中数据依赖顺序是否正确
- **效率评估** — 调用次数是否最优，是否存在冗余
- **错误分析** — 失败样本的分类统计与改进建议

## 2. 文件结构

```
evaluation/benchmarks/bfcl/
├── extended_evaluation.py    # 三个扩展组件的实现
├── evaluator.py              # BFCLEvaluator 集成
tests/
└── test_extended_evaluation.py  # 16 个测试用例
```

## 3. OrderValidator — 调用顺序验证

### 核心概念

`DependencyRule` 定义两个函数间的依赖关系：

```python
@dataclass
class DependencyRule:
    producer: str      # 先执行的函数（产出数据）
    consumer: str      # 后执行的函数（消费数据）
    param_mapping: Dict[str, str]  # 输出参数 → 输入参数的映射
```

### 预定义规则（9 条）

| producer | consumer | 说明 |
|---|---|---|
| `search_books` | `filter_books` | 搜索 → 过滤 |
| `search_flight` | `book_seat` | 搜索 → 预订 |
| `power` | `is_prime` | 幂 → 质数检查 |
| `power` | `factorize` | 幂 → 因数分解 |
| `is_prime` | `factorize` | 质数检查 → 因数分解 |
| `apply_discount` | `apply_tax` | 折扣 → 计税 |
| `apply_tax` | `round_price` | 计税 → 四舍五入 |

### 验证逻辑

1. 从 predicted 中提取函数名序列
2. 筛选当前序列适用的规则（producer 和 consumer 都出现）
3. 检查每条规则：producer 的最后出现位置 < consumer 的首次出现位置
4. 若违反则记录 violation

### 模式对比

| 模式 | strict | relaxed（默认） |
|---|---|---|
| expected 顺序检查 | 必须完全一致 | 不检查 |
| 缺少 consumer | 报错 | 忽略 |
| 适用场景 | 多步任务（multiple_edge_1） | 一般场景 |

## 4. EfficiencyAnalyzer — 调用效率评估

### 检测维度

**（1）冗余调用 — 纯查询函数重复**
- 识别 `PURE_QUERY_FUNCTIONS`（get_weather、get_local_time、search_books、search_flight、get_price）
- 签名匹配（函数名 + JSON 序列化的参数）
- 重复视为冗余（结果可缓存复用）

**（2）批量替代遗漏**
- 映射表 `BATCH_ALTERNATIVES`：

  | 个体调用 | 批量替代 |
  |---|---|
  | `send_email` | `send_bulk_email` |
  | `book_seat` | `book_seats` |

- 单个函数调用次数 > 1 时推荐批量 API

**（3）调用次数对比**
- actual_count > expected_count → 多余调用
- actual_count < expected_count → 遗漏调用（仅记录，不标记非最优）

### 评分逻辑

```
score = 1.0  (is_optimal)
score = 0.5  (有冗余)
```

## 5. ErrorAnalyzer — 错误分析报告

### 9 种错误类别

| 类别 | 检测条件 | 说明 |
|---|---|---|
| `missing_call` | predicted 比 expected 短 | 遗漏必要调用 |
| `extra_call` | predicted 比 expected 长 | 多余调用 |
| `wrong_function` | 函数名与 expected 不匹配 | 调用错误的函数 |
| `wrong_param_name` | predicted 参数名不在 expected 中 | 参数名错误 |
| `wrong_param_value` | 参数值不在 expected 允许值范围内 | 参数值错误 |
| `missing_param` | expected 中的参数在 predicted 中缺失 | 缺少必填参数 |
| `wrong_order` | 函数名集合相同但顺序不同 | 调用顺序错误 |
| `unnecessary_call` | predicted 非空但 expected 为空 | 无需工具调用 |
| `format_error` | predicted 为 None 或空列表但 expected 非空 | 输出格式错误 |

### 报告输出

Markdown 格式，包含 4 个部分：

1. **概览** — 总样本数、正确数、错误数、准确率
2. **错误类型分布** — 按数量降序排列，含 ASCII 柱状图
3. **各类型详情** — 每个类型列出前 10 个样本（ID、问题、预测、期望）
4. **改进建议** — 根据 Top 错误类型生成针对性建议

### 输出示例

```markdown
# BFCL 错误分析报告

**总样本数**: 100
**错误数**: 23
**准确率**: 77.00%

## 错误类型分布

| 错误类型 | 数量 | 占比 | 说明 |
|----------|------|------|------|
| **missing_call** | 10 | 43.5% | 遗漏调用 |
| █████████████░░░░░░░░░░░░░░░░ | | | |
| **wrong_param_value** | 5 | 21.7% | 参数值错误 |
| ...

## 改进建议
- ⚠️ 主要问题: **missing_call** 占比 43%，建议优先解决
- 💡 **遗漏调用**: 检查智能体是否理解了问题的所有子任务
```

## 6. BFCLEvaluator 集成

### 初始化

```python
class BFCLEvaluator:
    def __init__(self):
        self.order_validator = OrderValidator()      # 顺序验证
        self.efficiency_analyzer = EfficiencyAnalyzer()  # 效率评估
        self.error_analyzer = ErrorAnalyzer()        # 错误分析
```

### evaluate() 返回结果新增字段

```python
{
    "extended_analysis": {
        "order_stats": {
            "total_samples": int,
            "correct_order_count": int,
            "correct_order_rate": float,
        },
        "efficiency_stats": {
            "total_samples": int,
            "optimal_count": int,
            "optimal_rate": float,
            "total_redundant_calls": int,
        },
        "error_categories": {
            "missing_call": int,
            "extra_call": int,
            ...
        },
    },
    "error_report": "markdown 字符串",
}
```

### evaluate_sample() 返回新增字段

```python
{
    "extended": {
        "order": {
            "correct": bool,
            "violations": [str],
            "score": float,
            "actual_order": [str],
            "expected_order": [str],
        },
        "efficiency": {
            "is_optimal": bool,
            "actual_calls": int,
            "optimal_calls": int,
            "redundant_calls": [dict],
            "score": float,
        },
    },
}
```

## 7. 测试覆盖

16 个测试用例：

| 测试 | 覆盖内容 |
|---|---|
| `test_order_correct_sequence` | 正确顺序通过 |
| `test_order_wrong_sequence` | 错误顺序被检测 |
| `test_order_missing_producer` | 缺少依赖提供者 |
| `test_order_no_rules` | 无依赖的单函数调用 |
| `test_order_strict_wrong` | strict 模式检查 |
| `test_efficiency_simple_optimal` | 最优调用 |
| `test_efficiency_redundant_query` | 纯查询函数重复 |
| `test_efficiency_batch_alternative` | 批量 API 替代提示 |
| `test_efficiency_no_redundancy` | 不同函数非冗余 |
| `test_efficiency_count_mismatch` | 调用次数多于期望 |
| `test_error_missing_call` | 遗漏调用分类 |
| `test_error_extra_call` | 多余调用分类 |
| `test_error_unnecessary_call` | 不必要调用分类 |
| `test_error_format_error` | 格式错误分类 |
| `test_error_report_generation` | 完整报告生成 |
| `test_integration_order_analysis` | 模块结构验证 |

## 8. 辅助函数

`_check_param_error` 和 `_check_order_error` 设计为**模块级函数**（非类方法），原因：
- lint 工具（pylint/mypy）会将未使用的 `self` 参数标记为 unused-warning
- 这些函数不依赖实例状态

## 9. 设计决策

| 决策 | 理由 |
|---|---|
| 预定义 9 条依赖规则 | 覆盖 current BFCL 多步任务中的典型顺序场景 |
| strict/relaxed 双模式 | strict 用于明确要求顺序的任务，relaxed 用于宽松场景 |
| 纯查询函数硬编码 | 反射检测不可靠且不安全，显式声明显式可靠 |
| 错误分类使用 lambda 检测 | 声明式风格，方便扩展新类别 |
| 报告输出 Markdown | 通用格式，可在 IDE、GitHub、CI 中直接渲染 |
