"""
第十二章示例10：Universal LLM Judge 评估器 - 自定义维度案例

对应文档：12.4.2 LLM Judge评估

这个示例展示如何使用底层 UniversalLLMJudgeEvaluator，
结合自定义评估配置来评估代码质量。

关键演示：
- 使用底层接口 UniversalLLMJudgeEvaluator
- 自定义评估维度（dimension）
- 字段映射处理非标准数据格式
"""

import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
    EvaluationConfig,
)

# ============================================================================
# 测试数据准备
# ============================================================================

def prepare_code_data():
    """准备代码评估的测试数据"""
    code_problems = [
        {
            "id": "code_001",
            "code": """
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
            """,
            "expected_output": "Returns correct fibonacci numbers efficiently",
            "context": "Optimized fibonacci implementation",
        },
        {
            "id": "code_002",
            "code": """
def merge_sorted_arrays(arr1, arr2):
    result = []
    i = j = 0
    while i < len(arr1) and j < len(arr2):
        if arr1[i] <= arr2[j]:
            result.append(arr1[i])
            i += 1
        else:
            result.append(arr2[j])
            j += 1
    result.extend(arr1[i:])
    result.extend(arr2[j:])
    return result
            """,
            "expected_output": "Merge two sorted arrays in O(n+m) time",
            "context": "Two-pointer merge algorithm",
        }
    ]
    return code_problems


# ============================================================================
# 主程序：代码评估（使用自定义维度）
# ============================================================================

def main():
    """
    使用 UniversalLLMJudgeEvaluator 评估代码质量

    演示特性：
    - 底层接口使用
    - 自定义评估维度（code 模板的维度）
    - 非标准字段名（code, expected_output）
    - 需要字段映射：code → problem, expected_output → answer
    """
    print("\n" + "="*70)
    print("📌 Universal LLM Judge 评估器 - 代码质量评估（自定义维度）")
    print("="*70)

    code_data = prepare_code_data()

    # 创建 LLM 和评估器（使用 code 模板）
    print("\n[初始化] 创建 LLM 和评估器...")
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    eval_config = EvaluationConfig.load_template("code")

    print(f"✓ 评估模板: code")
    print(f"✓ 评估维度: {', '.join(eval_config.get_dimension_names())}")

    # 定义字段映射（适应非标准字段名）
    field_mapping = {
        "problem": "code",                  # 源数据中的 "code" 字段映射到 "problem"
        "answer": "expected_output",        # 源数据中的 "expected_output" 字段映射到 "answer"
    }
    print(f"✓ 字段映射: {field_mapping}")

    evaluator = UniversalLLMJudgeEvaluator(
        llm=llm,
        eval_config=eval_config,
        field_mapping=field_mapping
    )

    # 进行评估
    print("\n[评估] 开始评估代码...")
    print("="*70)

    all_scores = []
    for i, problem in enumerate(code_data, 1):
        print(f"\n评估代码 {i}/{len(code_data)}")
        print(f"ID: {problem['id']}")
        print(f"描述: {problem['context']}")

        result = evaluator.evaluate_single(problem)

        print(f"\n评估结果:")
        for dim, score in result['scores'].items():
            print(f"  {dim}: {score:.1f}/5")
        print(f"  平均分: {result['total_score']:.2f}/5")

        all_scores.append(result)

    # 统计汇总
    print("\n" + "="*70)
    print("总体统计")
    print("="*70)

    avg_total = sum(s['total_score'] for s in all_scores) / len(all_scores)
    print(f"\n平均总分: {avg_total:.2f}/5")

    # 按维度统计平均分
    if all_scores:
        dimension_names = list(all_scores[0]['scores'].keys())
        print("\n各维度平均分:")
        for dim in dimension_names:
            avg_dim = sum(s['scores'][dim] for s in all_scores) / len(all_scores)
            print(f"  {dim}: {avg_dim:.2f}/5")

    # 保存结果
    print("\n[保存] 保存评估结果...")
    os.makedirs("./evaluation_results", exist_ok=True)
    with open("./evaluation_results/code_judge_results.json", 'w', encoding='utf-8') as f:
        json.dump({
            'scenario': 'Code_Custom_Dimensions',
            'template': 'code',
            'field_mapping': field_mapping,
            'dimensions': dimension_names,
            'data': code_data,
            'results': all_scores,
            'avg_total_score': avg_total
        }, f, indent=2, ensure_ascii=False)

    print("✓ 结果已保存到 ./evaluation_results/code_judge_results.json")
    print("\n✅ 评估完成！")


if __name__ == "__main__":
    main()

"""
# LLM Judge 评估报告

**生成时间**: 2025-10-28 16:36:15
**评估模板**: code
**评估样本数**: 2

## 总体评分

- <strong>平均总分</strong>: 3.30/5.0
- <strong>通过率</strong>: 50.0% (≥3.5分)
- <strong>优秀率</strong>: 0.0% (≥4.5分)

## 各维度评分

| 维度 | 平均分 | 评级 |
|------|--------|------|
| correctness | 4.00/5.0 | 良好 ⭐⭐⭐⭐ |
| robustness | 3.00/5.0 | 及格 ⭐⭐ |
| efficiency | 2.50/5.0 | 待改进 ⭐ |
| readability | 4.50/5.0 | 优秀 ⭐⭐⭐⭐⭐ |
| style_compliance | 2.50/5.0 | 待改进 ⭐ |


"""