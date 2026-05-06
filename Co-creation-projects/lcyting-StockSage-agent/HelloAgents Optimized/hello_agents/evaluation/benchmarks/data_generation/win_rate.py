"""
Win Rate Evaluator

通过成对对比计算胜率
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from hello_agents.core.llm import HelloAgentsLLM


class WinRateEvaluator:
    """Win Rate评估器"""

    def __init__(
        self, llm: Optional[HelloAgentsLLM] = None, judge_model: str = "gpt-4o"
    ):
        """
        初始化Win Rate评估器

        Args:
            llm: LLM实例，如果为None则创建新实例
            judge_model: 评委模型名称
        """
        self.llm = llm or HelloAgentsLLM(model=judge_model)
        self.judge_model = judge_model

    def compare_pair(
        self,
        problem_a: Dict[str, Any],
        problem_b: Dict[str, Any],
        label_a: str = "A",
        label_b: str = "B",
    ) -> Dict[str, Any]:
        """
        对比两个问题，判断哪个更好

        Args:
            problem_a: 问题A
            problem_b: 问题B
            label_a: 问题A的标签
            label_b: 问题B的标签

        Returns:
            对比结果，包含胜者和理由
        """
        start_time = time.time()

        # 构建对比提示词
        prompt = self._build_comparison_prompt(problem_a, problem_b, label_a, label_b)

        # 调用LLM进行对比
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)

        # 解析对比结果
        winner, reason = self._parse_comparison_response(response, label_a, label_b)

        execution_time = time.time() - start_time

        return {
            "problem_a_id": problem_a.get("problem_id", "unknown"),
            "problem_b_id": problem_b.get("problem_id", "unknown"),
            "winner": winner,
            "reason": reason,
            "comparison_text": response,
            "execution_time": execution_time,
        }

    def evaluate_win_rate(
        self,
        generated_problems: List[Dict[str, Any]],
        reference_problems: List[Dict[str, Any]],
        num_comparisons: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        评估生成数据相对于参考数据的胜率

        Args:
            generated_problems: 生成的问题列表
            reference_problems: 参考问题列表（如AIME真题）
            num_comparisons: 对比次数，如果为None则对比所有可能的配对

        Returns:
            胜率评估结果
        """
        print("\n🏆 开始Win Rate评估")
        print(f"   评委模型: {self.judge_model}")
        print(f"   生成数据: {len(generated_problems)} 个")
        print(f"   参考数据: {len(reference_problems)} 个")

        # 确定对比次数
        if num_comparisons is None:
            num_comparisons = min(len(generated_problems), len(reference_problems))

        # 限制对比次数不超过生成题目数量
        num_comparisons = min(num_comparisons, len(generated_problems))

        print(f"   对比次数: {num_comparisons}")

        # 随机采样生成题目索引
        import random

        gen_indices = random.sample(range(len(generated_problems)), num_comparisons)

        print("   采样方式: 随机采样")

        # 进行成对对比
        comparisons = []
        wins = 0
        losses = 0
        ties = 0

        for i, gen_idx in enumerate(gen_indices):
            gen_problem = generated_problems[gen_idx]
            # 随机选择一个参考题目
            ref_idx = random.randint(0, len(reference_problems) - 1)
            ref_problem = reference_problems[ref_idx]

            print(f"\n   对比进度: {i + 1}/{num_comparisons}")
            print(f"   生成题目: #{gen_idx + 1}, 参考题目: #{ref_idx + 1}")

            # 随机化题目顺序以避免位置偏向
            if random.random() < 0.5:
                # Generated在前
                result = self.compare_pair(
                    gen_problem, ref_problem, label_a="Problem A", label_b="Problem B"
                )
                # 记录实际顺序
                result["actual_order"] = {"A": "Generated", "B": "Reference"}

                # 转换winner
                if result["winner"] == "Problem A":
                    actual_winner = "Generated"
                elif result["winner"] == "Problem B":
                    actual_winner = "Reference"
                else:
                    actual_winner = "Tie"
            else:
                # Reference在前
                result = self.compare_pair(
                    ref_problem, gen_problem, label_a="Problem A", label_b="Problem B"
                )
                # 记录实际顺序
                result["actual_order"] = {"A": "Reference", "B": "Generated"}

                # 转换winner
                if result["winner"] == "Problem A":
                    actual_winner = "Reference"
                elif result["winner"] == "Problem B":
                    actual_winner = "Generated"
                else:
                    actual_winner = "Tie"

            result["actual_winner"] = actual_winner
            comparisons.append(result)

            # 统计胜负
            if actual_winner == "Generated":
                wins += 1
                print("   ✓ Generated胜出")
            elif actual_winner == "Reference":
                losses += 1
                print("   ✗ Reference胜出")
            else:
                ties += 1
                print("   = 平局")

        # 计算胜率
        win_rate = wins / num_comparisons if num_comparisons > 0 else 0
        loss_rate = losses / num_comparisons if num_comparisons > 0 else 0
        tie_rate = ties / num_comparisons if num_comparisons > 0 else 0

        metrics = {
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "tie_rate": tie_rate,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "total_comparisons": num_comparisons,
        }

        print("\n📊 Win Rate评估结果:")
        print(f"   胜率: {win_rate:.2%}")
        print(f"   败率: {loss_rate:.2%}")
        print(f"   平局率: {tie_rate:.2%}")

        return {
            "comparisons": comparisons,
            "metrics": metrics,
            "evaluation_date": datetime.now().isoformat(),
            "judge_model": self.judge_model,
        }

    def _build_comparison_prompt(
        self,
        problem_a: Dict[str, Any],
        problem_b: Dict[str, Any],
        label_a: str,
        label_b: str,
    ) -> str:
        """构建对比提示词"""
        # 检查是否有solution字段
        has_solution_a = bool(problem_a.get("solution", "").strip())
        has_solution_b = bool(problem_b.get("solution", "").strip())

        # 构建题目展示
        problem_a_text = f"""**{label_a}**
Problem: {problem_a.get("problem", "")}
Answer: {problem_a.get("answer", "")}"""

        if has_solution_a:
            problem_a_text += f"\nSolution: {problem_a.get('solution', '')}"

        problem_b_text = f"""**{label_b}**
Problem: {problem_b.get("problem", "")}
Answer: {problem_b.get("answer", "")}"""

        if has_solution_b:
            problem_b_text += f"\nSolution: {problem_b.get('solution', '')}"

        # 根据是否有solution调整评估维度
        if has_solution_a and has_solution_b:
            criteria = """**Evaluation Criteria:**
Please evaluate comprehensively from the following dimensions:
1. **Mathematical Correctness**: Are the problem, solution, and answer mathematically correct?
2. **Clarity**: Is the problem statement clear and unambiguous?
3. **Difficulty Appropriateness**: Does the difficulty match AIME standards (challenging but solvable)?
4. **Solution Completeness**: Is the solution complete with clear reasoning steps?"""
        else:
            criteria = """**Evaluation Criteria:**
Please evaluate comprehensively from the following dimensions:
1. **Mathematical Correctness**: Are the problem and answer mathematically correct and reasonable?
2. **Clarity**: Is the problem statement clear and unambiguous?
3. **Difficulty Appropriateness**: Does the difficulty match AIME standards (challenging but solvable)?
4. **Problem Quality**: Is the problem well-designed with appropriate complexity?

Note: Some problems may not have solutions provided. Focus on the problem statement and answer quality."""

        prompt = f"""You are a professional mathematics problem evaluator. Please compare the following two AIME-style math problems and determine which one has higher quality.

{problem_a_text}

{problem_b_text}

{criteria}

**Important Guidelines:**
- Be objective and fair in your evaluation
- Consider all dimensions equally
- If both problems are of similar quality, choose "Tie"
- Do not favor one problem just because it appears first or second
- If one problem has a solution and the other doesn't, focus on the problem statement and answer quality

Please output your judgment in the following JSON format:
```json
{{
    "winner": "{label_a}",  // or "{label_b}" or "Tie"
    "reason": "Detailed explanation of why you chose this answer, covering the evaluation dimensions..."
}}
```
"""
        return prompt

    def _parse_comparison_response(
        self, response: str, label_a: str, label_b: str
    ) -> Tuple[str, str]:
        """解析对比响应"""
        try:
            # 提取JSON部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            # 修复LaTeX转义问题
            import re

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # 修复LaTeX转义：将 \frac 转为 \\frac
                fixed_json_str = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r"\\\\", json_str)
                data = json.loads(fixed_json_str)

            winner = data.get("winner", "Tie")
            reason = data.get("reason", "No reason provided")

            # 验证winner是否有效
            if winner not in [label_a, label_b, "Tie"]:
                winner = "Tie"

            return winner, reason

        except Exception as e:
            print(f"⚠️ 解析对比响应失败: {e}")
            return "Tie", "Failed to parse response"

    def export_results(self, results: Dict[str, Any], output_path: str):
        """导出评估结果"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Win Rate结果已保存: {output_path}")
