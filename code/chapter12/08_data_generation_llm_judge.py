"""
第十二章示例8：LLM Judge评估

对应文档：12.4.3 LLM Judge评估

这个示例展示如何使用LLM Judge评估生成的AIME题目质量。

LLM Judge从4个维度评估题目质量：
1. 正确性（Correctness）：题目和答案是否正确
2. 清晰度（Clarity）：题目表述是否清晰
3. 难度匹配（Difficulty Match）：难度是否符合AIME水平
4. 完整性（Completeness）：题目是否完整
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json

from hello_agents import HelloAgentsLLM
from hello_agents.evaluation import LLMJudgeEvaluator

# 1. 准备生成的题目数据
generated_problems = [
    {
        "problem_id": "generated_001",
        "problem": "Find the number of positive integers $n$ such that $n^2 + 19n + 92$ is a perfect square.",
        "answer": "4",
        "solution": "Let $n^2 + 19n + 92 = m^2$ for some positive integer $m$..."
    },
    {
        "problem_id": "generated_002",
        "problem": "In triangle $ABC$, $AB = 13$, $BC = 14$, and $CA = 15$. Find the area of the triangle.",
        "answer": "84",
        "solution": "Using Heron's formula, $s = (13+14+15)/2 = 21$..."
    }
]

# 2. 创建LLM Judge评估器（模型名与 .env 中 LLM_MODEL_ID / 网关一致，勿硬编码 gpt-4o）
llm = HelloAgentsLLM()
judge = LLMJudgeEvaluator(llm=llm)

# 3. 评估每道题目
print("="*60)
print("LLM Judge评估")
print("="*60)

all_scores = []

for i, problem in enumerate(generated_problems, 1):
    print(f"\n评估题目 {i}/{len(generated_problems)}")
    print(f"题目ID: {problem['problem_id']}")
    
    # 评估单道题目
    result = judge.evaluate_single(problem)
    
    # 显示评估结果
    print(f"\n评估结果:")
    scores = result.get("scores", {})
    print(f"  正确性: {scores.get('correctness', 0)}/5")
    print(f"  清晰度: {scores.get('clarity', 0)}/5")
    print(f"  难度匹配: {scores.get('difficulty_match', 0)}/5")
    print(f"  完整性: {scores.get('completeness', 0)}/5")
    print(f"  平均分: {result.get('total_score', 0):.2f}/5")
    print(f"\n评估原文:")
    print(result.get("evaluation_text", ""))
    
    all_scores.append(result)

# 4. 计算总体统计
print("\n" + "="*60)
print("总体统计")
print("="*60)

avg_correctness = sum(s.get("scores", {}).get("correctness", 0) for s in all_scores) / len(all_scores)
avg_clarity = sum(s.get("scores", {}).get("clarity", 0) for s in all_scores) / len(all_scores)
avg_difficulty = sum(s.get("scores", {}).get("difficulty_match", 0) for s in all_scores) / len(all_scores)
avg_completeness = sum(s.get("scores", {}).get("completeness", 0) for s in all_scores) / len(all_scores)
avg_overall = sum(s.get("total_score", 0) for s in all_scores) / len(all_scores)

print(f"\n平均分:")
print(f"  正确性: {avg_correctness:.2f}/5")
print(f"  清晰度: {avg_clarity:.2f}/5")
print(f"  难度匹配: {avg_difficulty:.2f}/5")
print(f"  完整性: {avg_completeness:.2f}/5")
print(f"  总体平均: {avg_overall:.2f}/5")

# 5. 质量评估
print(f"\n质量评估:")
if avg_overall >= 4.0:
    print("✅ 优秀 - 题目质量很高，可以直接使用")
elif avg_overall >= 3.0:
    print("⚠️ 良好 - 题目质量可用，建议人工审核")
elif avg_overall >= 2.0:
    print("⚠️ 一般 - 题目质量一般，需要大幅改进")
else:
    print("❌ 较差 - 题目质量差，需要重新生成")

# 6. 保存评估结果
output_file = "./evaluation_results/llm_judge_results.json"
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        'problems': generated_problems,
        'scores': all_scores,
        'statistics': {
            'avg_correctness': avg_correctness,
            'avg_clarity': avg_clarity,
            'avg_difficulty': avg_difficulty,
            'avg_completeness': avg_completeness,
            'avg_overall': avg_overall
        }
    }, f, indent=2, ensure_ascii=False)

print(f"\n✅ 评估结果已保存到 {output_file}")

# 运行输出示例：
# ============================================================
# LLM Judge评估
# ============================================================
# 
# 评估题目 1/2
# 题目ID: generated_001
# 
# 评估结果:
#   正确性: 5/5
#   清晰度: 4/5
#   难度匹配: 5/5
#   完整性: 5/5
#   平均分: 4.75/5
# 
# 评语:
#   This is an excellent AIME-level problem. The problem is well-posed,
#   the solution is correct, and the difficulty is appropriate.
# 
# 评估题目 2/2
# 题目ID: generated_002
# 
# 评估结果:
#   正确性: 5/5
#   清晰度: 5/5
#   难度匹配: 3/5
#   完整性: 5/5
#   平均分: 4.50/5
# 
# 评语:
#   The problem is correct and clear, but the difficulty is slightly
#   below AIME level. Consider adding more complexity.
# 
# ============================================================
# 总体统计
# ============================================================
# 
# 平均分:
#   正确性: 5.00/5
#   清晰度: 4.50/5
#   难度匹配: 4.00/5
#   完整性: 5.00/5
#   总体平均: 4.62/5
# 
# 质量评估:
# ✅ 优秀 - 题目质量很高，可以直接使用
# 
# ✅ 评估结果已保存到 ./evaluation_results/llm_judge_results.json

