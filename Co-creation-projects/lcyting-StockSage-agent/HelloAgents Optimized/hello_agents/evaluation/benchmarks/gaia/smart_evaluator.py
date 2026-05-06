"""
增强版 GAIA 评估器（SmartGAIAEvaluator）

继承 GAIAEvaluator，使用 SmartAnswerMatcher 替代准精确匹配，
支持数值等价、单位换算、数学表达式、语义等价和 LLM 兜底裁决。
"""

from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from hello_agents.evaluation.benchmarks.gaia.evaluator import GAIAEvaluator
from hello_agents.evaluation.benchmarks.gaia.dataset import GAIADataset
from hello_agents.evaluation.benchmarks.gaia.smart_answer_matcher import (
    SmartAnswerMatcher,
)


class SmartGAIAEvaluator(GAIAEvaluator):
    """使用智能匹配的增强版 GAIA 评估器"""

    def __init__(
        self,
        dataset: Optional[GAIADataset] = None,
        level: Optional[int] = None,
        local_data_dir: Optional[str] = None,
        llm=None,
        use_semantic: bool = True,
        use_llm_judge: bool = False,
    ):
        super().__init__(dataset=dataset, level=level, local_data_dir=local_data_dir)
        self.matcher = SmartAnswerMatcher(
            llm=llm,
            use_semantic=use_semantic,
            use_llm_judge=use_llm_judge,
        )

    def evaluate_sample(self, agent: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
        """重写：使用智能匹配评估单个样本"""
        try:
            question = sample.get("question", "")
            expected_answer = sample.get("final_answer", "")
            level = sample.get("level", 1)
            task_id = sample.get("task_id", "")

            prompt = self._build_prompt(question, sample)
            start_time = __import__("time").time()
            response = agent.run(prompt)
            execution_time = __import__("time").time() - start_time

            predicted_answer = self._extract_answer(response)

            # 原有精确匹配
            exact_match = self._check_exact_match(predicted_answer, expected_answer)
            partial_match = self._check_partial_match(predicted_answer, expected_answer)

            # 智能匹配
            smart_result = self.matcher.match(predicted_answer, expected_answer)

            if exact_match:
                score = 1.0
            elif smart_result.match:
                score = 0.9
            elif partial_match:
                score = 0.5
            else:
                score = 0.0

            return {
                "task_id": task_id,
                "level": level,
                "exact_match": exact_match,
                "partial_match": partial_match,
                "smart_match": smart_result.match,
                "smart_method": smart_result.method,
                "smart_confidence": smart_result.confidence,
                "score": score,
                "predicted": predicted_answer,
                "expected": expected_answer,
                "response": response,
                "execution_time": execution_time,
            }

        except Exception as e:
            return {
                "task_id": sample.get("task_id", ""),
                "level": sample.get("level", 1),
                "exact_match": False,
                "partial_match": False,
                "smart_match": False,
                "score": 0.0,
                "predicted": None,
                "expected": sample.get("final_answer", ""),
                "error": str(e),
            }

    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """重写 evaluate，添加智能匹配统计"""
        results = super().evaluate(agent, max_samples)

        detailed = results.get("detailed_results", [])
        smart_matches = sum(1 for r in detailed if r.get("smart_match", False))
        total = len(detailed)

        # 匹配方法分布统计
        method_stats = {}
        for r in detailed:
            m = r.get("smart_method", "none")
            method_stats[m] = method_stats.get(m, 0) + 1

        results["smart_match_rate"] = smart_matches / total if total > 0 else 0.0
        results["smart_method_stats"] = method_stats
        results["improvement"] = {
            "extra_matches_via_smart": smart_matches - results.get("exact_matches", 0),
            "exact_match_rate": results.get("exact_match_rate", 0),
            "smart_match_rate": results["smart_match_rate"],
        }

        print("\n📊 智能匹配结果:")
        print(f"   精确匹配率: {results.get('exact_match_rate', 0):.2%}")
        print(f"   智能匹配率: {results['smart_match_rate']:.2%}")
        print(f"   额外匹配: {results['improvement']['extra_matches_via_smart']}")
        print(f"   匹配方法分布: {method_stats}")

        return results

    def generate_smart_report(
        self, results: Dict[str, Any], output_file: Optional[Union[str, Path]] = None
    ) -> str:
        """生成包含智能匹配详情的报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建方法分布可视化
        method_stats = results.get("smart_method_stats", {})
        method_chart = (
            "\n".join(
                f"  - **{m}**: {c} 次 ({c / total * 100:.1f}%)"
                for m, c in sorted(method_stats.items(), key=lambda x: -x[1])
            )
            if (total := sum(method_stats.values())) > 0
            else "  - (无数据)"
        )

        # 构建样本详情表
        detailed = results.get("detailed_results", [])[:20]
        sample_rows = []
        for r in detailed:
            em = "✅" if r.get("exact_match") else "❌"
            sm = "✅" if r.get("smart_match") else "❌"
            method = r.get("smart_method", "-")
            conf = f"{r.get('smart_confidence', 0):.2f}"
            pred = (r.get("predicted") or "")[:40]
            exp = (r.get("expected") or "")[:40]
            sample_rows.append(
                f"| {r.get('task_id', '-')[:20]} | {em} | {sm} | {method} | {conf} | {pred}... | {exp}... |"
            )

        sample_table = "\n".join(sample_rows) if sample_rows else "  - (无样本数据)"

        improvement = results.get("improvement", {})
        newline = "\n"
        method_chart_lines = newline.join(
            "  {m:20s} {bar} {c}".format(
                m=m,
                bar="█"
                * int(
                    c / max(method_stats.values()) * 30
                    if max(method_stats.values()) > 0
                    else 0
                ),
                c=c,
            )
            for m, c in sorted(method_stats.items(), key=lambda x: -x[1])
        )
        report = f"""# SmartGAIA 评估报告

**生成时间**: {now}

## 📊 评估概览

| 指标 | 数值 |
|------|------|
| **智能体** | {results.get("agent_name", "Unknown")} |
| **难度级别** | {results.get("level_filter") or "全部"} |
| **总样本数** | {results.get("total_samples", 0)} |
| **精确匹配率** | {results.get("exact_match_rate", 0):.2%} |
| **智能匹配率** | {results["smart_match_rate"]:.2%} |
| **额外匹配（智能vs精确）** | {improvement.get("extra_matches_via_smart", 0)} |

## 📈 匹配方法分布

```
{method_chart_lines}
```

{method_chart}

## 📝 样本详情（前20个）

| 任务ID | 精确 | 智能 | 方法 | 置信度 | 预测答案 | 标准答案 |
|--------|------|------|------|--------|----------|----------|
{sample_table}

## 💡 改进建议

{self._format_smart_suggestions(results)}

---

*报告由 SmartGAIAEvaluator 自动生成*
"""
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report

    def _format_smart_suggestions(self, results: Dict) -> str:
        suggestions = []
        rate = results.get("smart_match_rate", 0)
        if rate >= 0.9:
            suggestions.append("✅ 表现优秀！智能体回答质量很高。")
        elif rate >= 0.7:
            suggestions.append("⚠️ 表现良好，仍有提升空间。")
        else:
            suggestions.append("❌ 需要大幅改进。")

        method_stats = results.get("smart_method_stats", {})
        no_match = method_stats.get("no_match", 0)
        if no_match > 0:
            suggestions.append(
                f"💡 {no_match} 个样本未能匹配，建议检查这些样本的答案格式。"
            )

        llm_judge = method_stats.get("llm_judge", 0)
        if llm_judge > 0:
            suggestions.append(
                f"🤖 {llm_judge} 个样本通过 LLM Judge 匹配（兜底策略），考虑优化提示词。"
            )

        return "\n".join(f"  {s}" for s in suggestions)
