"""
Multi-Judge Evaluation System

使用多个LLM作为"评审团"进行综合评估，支持：
- 多评委独立评分与加权聚合
- 异常评分检测与过滤（Z-score / IQR）
- 分歧检测与讨论轮协议
- 对照样本一致性校验
"""

import json
import statistics
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from hello_agents.core.llm import HelloAgentsLLM


@dataclass
class JudgeConfig:
    name: str
    model: str
    weight: float = 1.0
    temperature: float = 0.2
    max_tokens: int = 1024


@dataclass
class JudgeVerdict:
    judge_name: str
    scores: Dict[str, float]
    total_score: float
    reason: str = ""
    adjusted: bool = False
    adjustment_reason: str = ""


@dataclass
class DiscussionRound:
    round_number: int
    verdicts: List[JudgeVerdict]
    disagreement_level: str


@dataclass
class MultiJudgeResult:
    item_id: str
    final_score: float
    confidence: float
    verdicts: List[JudgeVerdict]
    discussion_rounds: List[DiscussionRound]
    anomaly_flags: List[str]
    agreement_level: str
    arbitration_used: bool = False
    arbitrator_verdict: Optional[JudgeVerdict] = None


CONTROL_SAMPLES = [
    {
        "problem": "Find the sum of all positive integers n such that n^2 - 10n + 21 is a prime number.",
        "answer": "15",
        "solution": "We have n^2 - 10n + 21 = (n-3)(n-7). For this product to be prime, one factor must be 1 and the other prime. Case 1: n-3=1 => n=4 => product=1*(-3)=-3 (not prime). Case 2: n-7=1 => n=8 => product=5*1=5 (prime). Case 3: n-3=-1 => n=2 => product=(-1)*(-5)=5 (prime). Case 4: n-7=-1 => n=6 => product=3*(-1)=-3 (not prime). So n=2 or n=8, sum=10.",
        "expected_scores": {
            "correctness": 5,
            "clarity": 4,
            "difficulty_match": 4,
            "completeness": 4,
        },
    },
    {
        "problem": "What is 2+2?",
        "answer": "4",
        "solution": "2+2 = 4.",
        "expected_scores": {
            "correctness": 5,
            "clarity": 5,
            "difficulty_match": 1,
            "completeness": 3,
        },
    },
]


class MultiJudgeEvaluator:
    EVALUATION_DIMENSIONS = [
        "correctness",
        "clarity",
        "difficulty_match",
        "completeness",
    ]

    DISCUSSION_PROMPT = """You are a judge in a multi-judge evaluation panel. The other judges have provided different scores for the item below.

Your previous score: {judge_prev_score}
Your previous reason: {judge_prev_reason}

Other judges' scores:
{other_scores}

Item being evaluated:
Problem: {problem}
Answer: {answer}
Solution: {solution}

Review the other judges' perspectives. You may keep or adjust your score.
If you adjust, explain why the other perspectives changed your mind.

Output JSON:
```json
{{
    "score": <kept or adjusted score>,
    "reason": "<your reasoning>",
    "adjusted": true/false
}}
```
"""

    def __init__(
        self,
        judges: List[JudgeConfig],
        llm_provider: Optional[Callable[[str, str, float, int], str]] = None,
        z_score_threshold: float = 2.0,
        disagreement_threshold: float = 2.0,
        enable_control_check: bool = True,
        max_discussion_rounds: int = 2,
        arbitrator_config: Optional[JudgeConfig] = None,
    ):
        self.judges = judges
        self.llm_provider = llm_provider or self._default_llm_invoke
        self.z_score_threshold = z_score_threshold
        self.disagreement_threshold = disagreement_threshold
        self.enable_control_check = enable_control_check
        self.max_discussion_rounds = max_discussion_rounds
        self.arbitrator_config = arbitrator_config or JudgeConfig(
            name="Arbitrator", model="gpt-4o"
        )

        self._judge_instances = {}
        self._judge_histories = defaultdict(list)
        self._control_history = defaultdict(list)

    def _default_llm_invoke(
        self, model: str, prompt: str, temperature: float = 0.2, max_tokens: int = 1024
    ) -> str:
        llm = HelloAgentsLLM(model=model)
        messages = [{"role": "user", "content": prompt}]
        return llm.invoke(messages, temperature=temperature, max_tokens=max_tokens)

    def evaluate(
        self, problem: Dict[str, Any], reference: Optional[Dict[str, Any]] = None
    ) -> MultiJudgeResult:
        item_id = problem.get("problem_id", "unknown")

        # Phase 1: Independent scoring
        verdicts = self._independent_scoring(problem, reference)
        anomaly_flags = []

        # Phase 2: Control sample consistency check
        if self.enable_control_check:
            control_penalties = self._check_control_consistency(verdicts)
            for v in verdicts:
                if v.judge_name in control_penalties:
                    anomaly_flags.append(
                        f"{v.judge_name}: control deviation {control_penalties[v.judge_name]:.1f} pts"
                    )

        # Phase 3: Anomaly detection
        scores_map = {v.judge_name: v.total_score for v in verdicts}
        anomaly_flags += self._detect_anomalies(scores_map)

        # Phase 4: Discussion rounds if disagreement
        discussion_rounds = []
        disagreement_level = self._measure_disagreement(
            [v.total_score for v in verdicts]
        )
        arbitration_used = False
        arbitrator_verdict = None

        if disagreement_level == "severe" and self.max_discussion_rounds > 0:
            verdicts, discussion_rounds = self._discussion_protocol(
                problem, verdicts, max_rounds=self.max_discussion_rounds
            )
            disagreement_level = self._measure_disagreement(
                [v.total_score for v in verdicts]
            )

        # Phase 5: Arbitrate if still severe
        if disagreement_level == "severe" and self.arbitrator_config:
            arbitration_used = True
            arbitrator_verdict = self._get_arbitrator_verdict(
                problem, reference, verdicts
            )
            final_score = arbitrator_verdict.total_score
        else:
            final_score = self._weighted_aggregate(verdicts)

        # Phase 6: Confidence calculation
        final_scores = [v.total_score for v in verdicts]
        confidence = self._calculate_confidence(final_scores)

        # Update history
        for v in verdicts:
            self._judge_histories[v.judge_name].append(v.total_score)

        return MultiJudgeResult(
            item_id=item_id,
            final_score=round(final_score, 2),
            confidence=confidence,
            verdicts=verdicts,
            discussion_rounds=discussion_rounds,
            anomaly_flags=anomaly_flags,
            agreement_level=disagreement_level,
            arbitration_used=arbitration_used,
            arbitrator_verdict=arbitrator_verdict,
        )

    def evaluate_batch(
        self,
        problems: List[Dict[str, Any]],
        references: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        print("\n🎯 多评委评估开始")
        print(f"   评委: {', '.join(c.name for c in self.judges)}")
        print(f"   评估数量: {len(problems)}")
        print(f"   异常检测阈值: Z-score > {self.z_score_threshold}")
        print(f"   分歧阈值: range > {self.disagreement_threshold}")
        print(f"   最大讨论轮次: {self.max_discussion_rounds}")
        print(f"   对照样本校验: {'启用' if self.enable_control_check else '禁用'}")

        results = []
        for idx, problem in enumerate(problems):
            ref = references[idx] if references and idx < len(references) else None
            result = self.evaluate(problem, ref)
            results.append(result)

            flags_str = (
                f" | flags: {result.anomaly_flags}" if result.anomaly_flags else ""
            )
            arb_str = " [仲裁]" if result.arbitration_used else ""
            print(
                f"   {idx + 1}/{len(problems)} | id={result.item_id} | score={result.final_score} | conf={result.confidence:.0%}{arb_str}{flags_str}"
            )

        metrics = self._compute_metrics(results)
        return {
            "results": results,
            "metrics": metrics,
            "evaluation_date": datetime.now().isoformat(),
            "judges": [c.name for c in self.judges],
            "num_problems": len(problems),
        }

    def _independent_scoring(
        self, problem: Dict, reference: Optional[Dict]
    ) -> List[JudgeVerdict]:
        verdicts = []
        prompt = self._build_evaluation_prompt(problem, reference)

        for config in self.judges:
            response = self.llm_provider(
                config.model, prompt, config.temperature, config.max_tokens
            )
            scores = self._parse_scores(response)
            total = sum(scores.values()) / len(scores)
            verdicts.append(
                JudgeVerdict(
                    judge_name=config.name,
                    scores=scores,
                    total_score=total,
                    reason=scores.get("comments", ""),
                )
            )
        return verdicts

    def _discussion_protocol(
        self,
        problem: Dict,
        verdicts: List[JudgeVerdict],
        max_rounds: int = 2,
    ) -> Tuple[List[JudgeVerdict], List[DiscussionRound]]:
        discussion_rounds = []

        for round_num in range(1, max_rounds + 1):
            new_verdicts = []
            for v in verdicts:
                other_scores_lines = []
                for ov in verdicts:
                    if ov.judge_name != v.judge_name:
                        other_scores_lines.append(
                            f"- {ov.judge_name}: {ov.total_score:.1f} | reason: {ov.reason[:200]}"
                        )
                other_scores_text = "\n".join(other_scores_lines)

                prompt = self.DISCUSSION_PROMPT.format(
                    judge_prev_score=v.total_score,
                    judge_prev_reason=v.reason,
                    other_scores=other_scores_text,
                    problem=problem.get("problem", ""),
                    answer=problem.get("answer", ""),
                    solution=problem.get("solution", ""),
                )

                response = self.llm_provider(
                    self._get_judge_config(v.judge_name).model, prompt, 0.3, 1024
                )

                try:
                    data = self._extract_json(response)
                    new_score = float(data.get("score", v.total_score))
                    adjusted = data.get("adjusted", False)
                    adj_reason = data.get("reason", "")
                except Exception:
                    new_score = v.total_score
                    adjusted = False
                    adj_reason = ""

                new_verdicts.append(
                    JudgeVerdict(
                        judge_name=v.judge_name,
                        scores=v.scores,
                        total_score=new_score if adjusted else v.total_score,
                        reason=adj_reason if adjusted else v.reason,
                        adjusted=adjusted,
                        adjustment_reason=adj_reason,
                    )
                )

            verdicts = new_verdicts
            dl = self._measure_disagreement([v.total_score for v in verdicts])
            discussion_rounds.append(
                DiscussionRound(
                    round_number=round_num,
                    verdicts=list(verdicts),
                    disagreement_level=dl,
                )
            )

            if dl in ("low", "moderate"):
                break

        return verdicts, discussion_rounds

    def _get_arbitrator_verdict(
        self,
        problem: Dict,
        reference: Optional[Dict],
        verdicts: List[JudgeVerdict],
    ) -> JudgeVerdict:
        prompt = f"""You are the chief arbitrator. A panel of judges disagreed on the following item.

Judge scores:
{chr(10).join(f"- {v.judge_name}: {v.total_score}/5 | reason: {v.reason}" for v in verdicts)}

Item:
Problem: {problem.get("problem", "")}
Answer: {problem.get("answer", "")}
Solution: {problem.get("solution", "")}

Give your final score (1-5) with reasoning.
```json
{{
    "correctness": 5,
    "clarity": 4,
    "difficulty_match": 4,
    "completeness": 5,
    "comments": "Arbitration reasoning..."
}}
```"""
        response = self.llm_provider(self.arbitrator_config.model, prompt, 0.2, 1024)
        scores = self._parse_scores(response)
        total = sum(scores.values()) / len(scores)
        return JudgeVerdict(
            judge_name=self.arbitrator_config.name,
            scores=scores,
            total_score=total,
            reason=scores.get("comments", ""),
        )

    def _detect_anomalies(self, scores_map: Dict[str, float]) -> List[str]:
        flags = []
        values = list(scores_map.values())
        if len(values) < 3:
            return flags

        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            return flags

        for name, score in scores_map.items():
            z = abs(score - mean) / stdev
            if z > self.z_score_threshold:
                flags.append(f"{name}: Z-score={z:.2f}")

        sorted_vals = sorted(values)
        q1 = statistics.median(sorted_vals[: len(sorted_vals) // 2])
        q3 = statistics.median(sorted_vals[(len(sorted_vals) + 1) // 2 :])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        for name, score in scores_map.items():
            if score < lower or score > upper:
                if not any(name in f for f in flags):
                    flags.append(
                        f"{name}: IQR outlier ({score} outside [{lower:.1f}, {upper:.1f}])"
                    )

        return flags

    def _check_control_consistency(
        self, verdicts: List[JudgeVerdict]
    ) -> Dict[str, float]:
        penalties = {}
        for v in verdicts:
            hist = self._judge_histories.get(v.judge_name, [])
            if len(hist) < len(CONTROL_SAMPLES):
                continue
            recent_control_scores = hist[-len(CONTROL_SAMPLES) :]
            expected = [
                sum(c["expected_scores"].values()) / len(c["expected_scores"])
                for c in CONTROL_SAMPLES
            ]
            deviations = [
                abs(actual - exp)
                for actual, exp in zip(recent_control_scores, expected)
            ]
            avg_dev = statistics.mean(deviations)
            if avg_dev > 1.0:
                penalties[v.judge_name] = avg_dev
        return penalties

    def _measure_disagreement(self, scores: List[float]) -> str:
        if len(scores) < 2:
            return "low"
        score_range = max(scores) - min(scores)
        if score_range <= 1.0:
            return "low"
        elif score_range <= self.disagreement_threshold:
            return "moderate"
        else:
            return "severe"

    def _weighted_aggregate(self, verdicts: List[JudgeVerdict]) -> float:
        total_weight = 0
        weighted_sum = 0
        for v in verdicts:
            config = self._get_judge_config(v.judge_name)
            if config and config.weight > 0:
                weighted_sum += v.total_score * config.weight
                total_weight += config.weight
        return weighted_sum / total_weight if total_weight > 0 else 0

    def _calculate_confidence(self, scores: List[float]) -> float:
        if len(scores) < 2:
            return 0.5
        score_range = max(scores) - min(scores)
        agreement = 1.0 - (score_range / 5.0)
        return max(0.0, min(1.0, agreement))

    def _get_judge_config(self, name: str) -> Optional[JudgeConfig]:
        for c in self.judges:
            if c.name == name:
                return c
        return None

    def _build_evaluation_prompt(self, problem: Dict, reference: Optional[Dict]) -> str:
        prompt = f"""You are a professional mathematics problem evaluator. Evaluate the following AIME-style problem.

Problem: {problem.get("problem", "")}
Answer: {problem.get("answer", "")}
Solution: {problem.get("solution", "")}
"""
        if reference:
            prompt += f"""
Reference (AIME exam problem):
Problem: {reference.get("problem", "")}
Answer: {reference.get("answer", "")}
Solution: {reference.get("solution", "")}
"""
        prompt += """
Rate each dimension 1-5:
1. correctness: Is the math correct?
2. clarity: Is the problem clear and well-stated?
3. difficulty_match: Does it match AIME difficulty (medium-hard)?
4. completeness: Are all reasoning steps provided?

```json
{
    "correctness": 5,
    "clarity": 4,
    "difficulty_match": 4,
    "completeness": 5,
    "comments": "Brief evaluation reason."
}
```"""
        return prompt

    def _parse_scores(self, response: str) -> Dict[str, float]:
        try:
            data = self._extract_json(response)
            scores = {}
            for dim in self.EVALUATION_DIMENSIONS:
                scores[dim] = float(data.get(dim, 3.0))
            if "comments" in data:
                scores["comments"] = data["comments"]
            return scores
        except Exception:
            return {dim: 3.0 for dim in self.EVALUATION_DIMENSIONS}

    def _extract_json(self, response: str) -> Dict:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
        import re

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r"\\\\", json_str)
            return json.loads(fixed)

    def _compute_metrics(self, results: List[MultiJudgeResult]) -> Dict[str, Any]:
        if not results:
            return {}

        final_scores = [r.final_score for r in results]
        confidences = [r.confidence for r in results]
        anomaly_counts = defaultdict(int)
        agreement_counts = defaultdict(int)
        arbitration_count = 0

        for r in results:
            agreement_counts[r.agreement_level] += 1
            if r.arbitration_used:
                arbitration_count += 1
            for flag in r.anomaly_flags:
                judge_name = flag.split(":")[0]
                anomaly_counts[judge_name] += 1

        dimension_scores = {dim: [] for dim in self.EVALUATION_DIMENSIONS}
        for r in results:
            for v in r.verdicts:
                if (
                    v.judge_name not in anomaly_counts
                    or anomaly_counts[v.judge_name] <= len(results) * 0.5
                ):
                    for dim in self.EVALUATION_DIMENSIONS:
                        if dim in v.scores:
                            dimension_scores[dim].append(v.scores[dim])

        return {
            "average_final_score": statistics.mean(final_scores) if final_scores else 0,
            "average_confidence": statistics.mean(confidences) if confidences else 0,
            "pass_rate": sum(1 for s in final_scores if s >= 3.5) / len(final_scores)
            if final_scores
            else 0,
            "excellent_rate": sum(1 for s in final_scores if s >= 4.5)
            / len(final_scores)
            if final_scores
            else 0,
            "dimension_averages": {
                dim: statistics.mean(scores) if scores else 0
                for dim, scores in dimension_scores.items()
            },
            "agreement_distribution": dict(agreement_counts),
            "arbitration_rate": arbitration_count / len(results) if results else 0,
            "anomaly_counts": dict(anomaly_counts),
            "total_evaluated": len(results),
        }


def generate_report(results: Dict[str, Any]) -> str:
    metrics = results["metrics"]
    detailed = results["results"]

    report = f"""# 多评委评估综合报告

## 基本信息
- **评估日期**: {results["evaluation_date"]}
- **评委**: {", ".join(results["judges"])}
- **评估数量**: {results["num_problems"]} 个

## 总体评分
- **平均分**: {metrics["average_final_score"]:.2f}/5.0
- **平均置信度**: {metrics["average_confidence"]:.0%}
- **通过率**: {metrics["pass_rate"]:.0%} (≥3.5分)
- **优秀率**: {metrics["excellent_rate"]:.0%} (≥4.5分)
- **仲裁率**: {metrics["arbitration_rate"]:.0%}

## 各维度评分
| 维度 | 平均分 |
|------|--------|
"""
    for dim, score in metrics["dimension_averages"].items():
        report += f"| {dim} | {score:.2f}/5.0 |\n"

    report += f"""
## 一致性分布
- **低分歧 (≤1.0)**: {metrics["agreement_distribution"].get("low", 0)}
- **中等分歧 (≤2.0)**: {metrics["agreement_distribution"].get("moderate", 0)}
- **严重分歧 (>2.0)**: {metrics["agreement_distribution"].get("severe", 0)}

## 异常评分统计
"""
    if metrics["anomaly_counts"]:
        for judge, count in metrics["anomaly_counts"].items():
            report += f"- **{judge}**: {count} 次异常\n"
    else:
        report += "- 无异常检测\n"

    report += "\n## 详细结果\n"
    for idx, r in enumerate(detailed[:15]):
        judge_scores = ", ".join(
            f"{v.judge_name}={v.total_score:.1f}" for v in r.verdicts
        )
        flags = "; ".join(r.anomaly_flags) if r.anomaly_flags else "无"
        arb = " (仲裁)" if r.arbitration_used else ""
        report += f"""
### {idx + 1}. {r.item_id}
- **最终分**: {r.final_score}/5.0 (置信度: {r.confidence:.0%}){arb}
- **评委评分**: {judge_scores}
- **一致性**: {r.agreement_level}
- **异常标记**: {flags}
"""
    if len(detailed) > 15:
        report += "\n*（仅显示前15个）*\n"

    return report
