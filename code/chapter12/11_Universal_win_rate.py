"""
第十二章示例11：Universal Win Rate 评估 - 自定义维度案例

对应文档：12.4.4 Win Rate评估

这个示例展示如何使用底层 UniversalWinRateEvaluator，
结合自定义评估配置来对比数学题质量。

关键演示：
- 使用底层接口 UniversalWinRateEvaluator
- 自定义评估维度（dimension）
- 标准字段名（problem, answer）无需映射
- Win Rate 胜率对比评估
"""

import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from hello_agents import HelloAgentsLLM, UniversalWinRateEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
    EvaluationConfig,
)

# ============================================================================
# 测试数据准备
# ============================================================================

def prepare_math_data():
    """准备数学题对比的测试数据（生成数据和参考数据）"""

    math_generated = [
        {
            "id": "math_gen_001",
            "problem": "Find the number of positive integers $n$ such that $n^2 + 19n + 92$ is a perfect square.",
            "answer": "Using completing the square: $(2n+19)^2 - 4m^2 = -7$. Solve the Pell-like equation.",
        },
        {
            "id": "math_gen_002",
            "problem": "In triangle ABC with sides AB=13, BC=14, CA=15, find the area.",
            "answer": "Using Heron's formula: $s=21$, Area $= \\sqrt{21 \\cdot 8 \\cdot 7 \\cdot 6} = 84$.",
        },
    ]

    math_reference = [
        {
            "id": "math_ref_001",
            "problem": "Find the number of positive integers $n$ such that $n^2 + 19n + 92$ is a perfect square.",
            "answer": "Let $n^2 + 19n + 92 = m^2$. Complete the square and solve systematically.",
        },
        {
            "id": "math_ref_002",
            "problem": "In triangle ABC with sides AB=13, BC=14, CA=15, find the area.",
            "answer": "Use Heron's formula with semi-perimeter s=21.",
        },
    ]

    return math_generated, math_reference


# ============================================================================
# 主程序：数学题质量 Win Rate 对比（使用自定义维度）
# ============================================================================

def main():
    """
    使用 UniversalWinRateEvaluator 对比数学题质量

    演示特性：
    - 底层接口使用
    - 自定义评估维度（math 模板的维度）
    - 标准字段名（problem, answer）无需映射
    - Win Rate 胜率评估
    """
    print("\n" + "="*70)
    print("📌 Universal Win Rate 评估器 - 数学题质量对比（自定义维度）")
    print("="*70)

    math_gen, math_ref = prepare_math_data()

    # 创建 LLM 和评估器（使用 math 模板）
    print("\n[初始化] 创建 LLM 和评估器...")
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    eval_config = EvaluationConfig.load_template("math")

    print(f"✓ 评估模板: math")
    print(f"✓ 评估维度: {', '.join(eval_config.get_dimension_names())}")

    # 定义字段映射（math 模板使用标准字段名）
    field_mapping = {
        "problem": "problem",       # 源数据中的 "problem" 字段映射到 "problem"
        "answer": "answer",         # 源数据中的 "answer" 字段映射到 "answer"
    }
    print(f"✓ 字段映射: {field_mapping}")

    evaluator = UniversalWinRateEvaluator(
        llm=llm,
        eval_config=eval_config,
        field_mapping=field_mapping
    )

    # 进行 Win Rate 对比
    print("\n[评估] 开始进行 Win Rate 对比...")
    print("="*70)

    result = evaluator.evaluate_win_rate(math_gen, math_ref, num_comparisons=2)

    # 显示评估结果
    print("\n评估结果:")
    print(f"  胜率 (Win Rate): {result.get('win_rate', 'N/A')}")
    print(f"  胜场数: {result.get('wins', 'N/A')}")
    print(f"  平局数: {result.get('ties', 'N/A')}")
    print(f"  负场数: {result.get('losses', 'N/A')}")

    # Win Rate 解读
    print("\n[解读]")
    win_rate = result.get('win_rate', 0)
    if isinstance(win_rate, str):
        win_rate_float = float(win_rate.rstrip('%')) / 100
    else:
        win_rate_float = win_rate

    if 0.45 <= win_rate_float <= 0.55:
        print("✅ 生成质量接近参考数据水平（理想情况）")
    elif win_rate_float > 0.55:
        print("⭐ 生成质量优于参考数据（可能有评估偏差）")
    else:
        print("⚠️  生成质量低于参考数据（需要改进）")

    # 保存结果
    print("\n[保存] 保存评估结果...")
    os.makedirs("./evaluation_results", exist_ok=True)
    with open("./evaluation_results/math_winrate_results.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "scenario": "Math_Custom_Dimensions",
                "template": "math",
                "field_mapping": field_mapping,
                "dimensions": eval_config.get_dimension_names(),
                "generated_data": math_gen,
                "reference_data": math_ref,
                "results": result,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("✓ 结果已保存到 ./evaluation_results/math_winrate_results.json")
    print("\n✅ 评估完成！")


if __name__ == "__main__":
    main()


"""
**评估模板**: math
**对比次数**: 2

## 胜率统计

| 指标 | 数值 | 百分比 |
|------|------|--------|
| 生成数据胜出 | 1次 | 50.0% |
| 参考数据胜出 | 1次 | 50.0% |
| 平局 | 0次 | 0.0% |

<strong>Win Rate</strong>: 50.0%

✅ <strong>优秀</strong>: 生成数据质量优于参考数据（胜率≥50%）。

## 对比详情

### 对比 1

- **赢家**: Reference
- **原因**: 从各维度详细比较：1. correctness：两者数学逻辑都正确，但A的答案不完整，只给出思路没有具体数值结果；B使用海伦公式准确计算出面积=84。2. clarity：A的问题表述清晰，但解答过于简略，仅提到配方法和佩尔方程，缺乏具体推导；B的问题表述清晰，解答步骤明确，直接应用标准公式。3. completeness：A严重不完整，缺少具体求解过程和最终答案；B完整展示了从已知条件到最终结果的完整过程。4. difficulty_match：A作为数论问题难度较高，与中学生数学竞赛匹配；B作为几何问题难度适中，与中学数学课程匹配，两者都符合预期难度。5. originality：A展示了非标准的佩尔方程解法，具有一定启发性；B使用标准解法，缺乏创新性。综合来看，虽然A在原创性上稍优，但B在完整性、清晰度和答案准确性上显著优于A，特别是在解答的完整性方面差距明显，因此B整体质量更好。

### 对比 2

- **赢家**: Generated
- **原因**: 从各维度对比分析：1. correctness：两者数学逻辑都正确，最终答案准确无误，此维度相当；2. clarity：A的表述更清晰，直接给出了完整的计算过程和最终结果，而B只给出了半周长，没有完成面积计算，逻辑不完整；3. completeness：A提供了完整的解题步骤（s=21，面积公式代入计算，最终结果84），B只给出半周长，解答不完整；4. difficulty_match：两者问题难度相同，都匹配三角形面积计算的预期标准；5. originality：两者都使用标准的海伦公式，没有展示多种解法或创新思路，此维度相当。综合来看，虽然两个问题在正确性和难度匹配上相当，但A在清晰度和完整性上明显优于B，提供了完整的解答过程，因此A更好。



"""