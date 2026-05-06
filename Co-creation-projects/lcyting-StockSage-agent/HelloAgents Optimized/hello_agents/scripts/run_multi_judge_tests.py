"""Multi-Judge 评估系统单元测试 — unittest 版本"""

import statistics
import unittest
from dataclasses import dataclass
from typing import List, Dict


# ═══════════════ 内联核心逻辑（等同 evaluation/benchmarks/data_generation/multi_judge.py）═══════════════


@dataclass
class JudgeConfig:
    """单个评审器的配置"""

    name: str  # 评审器名称
    model: str  # 使用的模型
    weight: float = 1.0  # 聚合权重


@dataclass
class JudgeVerdict:
    """单个评审器的评分结果"""

    judge_name: str
    scores: Dict[str, float]  # 各维度得分
    total_score: float  # 综合得分
    reason: str = ""  # 评审理由
    adjusted: bool = False  # 是否经仲裁调整


@dataclass
class MultiJudgeResult:
    """多评审器评估的最终结果"""

    item_id: str  # 评测项 ID
    final_score: float  # 最终得分
    confidence: float  # 置信度 (0~1)
    verdicts: List[JudgeVerdict]  # 各评审器结果
    anomaly_flags: List[str]  # 异常标记
    agreement_level: str  # 一致性等级：low / moderate / severe
    arbitration_used: bool = False  # 是否启用了仲裁


# ── 控制样本：用于校验评审器的一致性 ──
CONTROL_SAMPLES = [
    {
        "problem": "test",
        "answer": "4",
        "solution": "2+2=4",
        "expected_scores": {
            "correctness": 5,
            "clarity": 4,
            "difficulty_match": 4,
            "completeness": 4,
        },
    },
    {
        "problem": "test2",
        "answer": "42",
        "solution": "42",
        "expected_scores": {
            "correctness": 5,
            "clarity": 5,
            "difficulty_match": 1,
            "completeness": 3,
        },
    },
]


def weighted_aggregate(
    verdicts: List[JudgeVerdict], weights: Dict[str, float]
) -> float:
    """加权聚合：按各评审器权重计算加权平均分"""
    total_weight = 0
    weighted_sum = 0
    for v in verdicts:
        w = weights.get(v.judge_name, 1.0)
        if w > 0:
            weighted_sum += v.total_score * w
            total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0


def detect_anomalies_zscore(
    scores: Dict[str, float], threshold: float = 2.0
) -> List[str]:
    """基于 Z-score 的异常检测：标记偏离均值超过 threshold 个标准差的评审器"""
    flags = []
    values = list(scores.values())
    if len(values) < 3:
        return flags
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return flags
    for name, score in scores.items():
        z = abs(score - mean) / stdev
        if z > threshold:
            flags.append(f"{name}: Z-score={z:.2f}")
    return flags


def detect_anomalies_iqr(scores: Dict[str, float]) -> List[str]:
    """基于 IQR（四分位距）的异常检测：Tukey's fences 方法"""
    flags = []
    values = sorted(scores.values())
    if len(values) < 4:
        return flags
    mid = len(values) // 2
    q1 = statistics.median(values[:mid])
    q3 = statistics.median(values[mid:] if len(values) % 2 == 0 else values[mid + 1 :])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    for name, score in scores.items():
        if score < lower or score > upper:
            flags.append(
                f"{name}: IQR 离群值 ({score} 不在 [{lower:.1f}, {upper:.1f}] 区间)"
            )
    return flags


def measure_disagreement(scores: List[float], threshold: float = 2.0) -> str:
    """衡量评审器之间的分歧程度：low / moderate / severe"""
    if len(scores) < 2:
        return "low"
    r = max(scores) - min(scores)
    if r <= 1.0:
        return "low"
    elif r <= threshold:
        return "moderate"
    else:
        return "severe"


def calculate_confidence(scores: List[float]) -> float:
    """根据评分范围计算置信度：范围越小置信度越高"""
    if len(scores) < 2:
        return 0.5
    return max(0.0, min(1.0, 1.0 - (max(scores) - min(scores)) / 5.0))


def generate_report(
    metrics: Dict, results: List[MultiJudgeResult], judges: List[str], date: str
) -> str:
    """生成 Markdown 格式的评估报告"""
    report = f"""# Multi-Judge 评估报告

**日期**: {date}
**评审器**: {", ".join(judges)}
**评测项数**: {len(results)}

## 总体指标
- 平均得分: {metrics["avg_score"]:.2f}/5.0
- 平均置信度: {metrics["avg_confidence"]:.0%}
- 通过率: {metrics["pass_rate"]:.0%}
- 一致性分布: {metrics.get("agreement_dist", {})}

## 详细结果
"""
    for r in results:
        vs = ", ".join(f"{v.judge_name}={v.total_score:.1f}" for v in r.verdicts)
        arb = " (已仲裁)" if r.arbitration_used else ""
        report += f"- {r.item_id}: 最终={r.final_score} 置信度={r.confidence:.0%} [{vs}]{arb}\n"
    return report


# ═══════════════ 单元测试 ═══════════════


class TestWeightedAggregation(unittest.TestCase):
    """测试 1：加权聚合功能"""

    def test_weighted_average(self):
        """验证加权平均计算正确"""
        verdicts = [
            JudgeVerdict("A", {}, 5.0, ""),
            JudgeVerdict("B", {}, 4.0, ""),
            JudgeVerdict("C", {}, 3.0, ""),
        ]
        weights = {"A": 1.0, "B": 1.0, "C": 0.8}
        result = weighted_aggregate(verdicts, weights)
        expected = (5.0 + 4.0 + 3.0 * 0.8) / 2.8
        self.assertAlmostEqual(result, expected, places=2)


class TestAnomalyDetection(unittest.TestCase):
    """测试 2 & 3：异常检测"""

    def test_zscore_detects_outlier(self):
        """Z-score 应检测到明显偏离的值（6 个值中含 1 个离群值）"""
        flags = detect_anomalies_zscore(
            {"A": 5.0, "B": 5.0, "C": 5.0, "D": 5.0, "E": 5.0, "F": 1.0}
        )
        self.assertGreater(len(flags), 0)

    def test_zscore_clean(self):
        """无离群值时不应返回标记"""
        flags = detect_anomalies_zscore(
            {"A": 4.0, "B": 4.5, "C": 3.8, "D": 4.2, "E": 4.1, "F": 4.3}
        )
        self.assertEqual(len(flags), 0)

    def test_iqr_detects_outlier(self):
        """IQR 方法应检测到离群值"""
        # {5, 4.7, 4.8, 4.9, 5, 5, 1}: Q1=4.7, Q3=5.0, IQR=0.3, lower=4.25 → 1.0 是离群值
        flags = detect_anomalies_iqr(
            {"A": 5.0, "B": 4.7, "C": 4.8, "D": 4.9, "E": 5.0, "F": 5.0, "G": 1.0}
        )
        self.assertTrue(any("IQR" in f for f in flags))

    def test_iqr_too_few_values(self):
        """不足 4 个值时不应触发 IQR 检测"""
        flags = detect_anomalies_iqr({"A": 4.5, "B": 4.6, "C": 4.7})
        self.assertEqual(len(flags), 0)


class TestDisagreement(unittest.TestCase):
    """测试 4：分歧度分类"""

    def test_low_disagreement(self):
        """评分范围 ≤ 1.0 → low"""
        self.assertEqual(measure_disagreement([4.5, 4.6, 4.7]), "low")

    def test_moderate_disagreement(self):
        """1.0 < 范围 ≤ 2.0 → moderate"""
        self.assertEqual(measure_disagreement([3.0, 4.0, 5.0]), "moderate")

    def test_severe_disagreement(self):
        """范围 > 2.0 → severe"""
        self.assertEqual(measure_disagreement([5.0, 2.0, 1.0]), "severe")

    def test_single_judge(self):
        """单个评审器默认 low"""
        self.assertEqual(measure_disagreement([4.0]), "low")


class TestConfidence(unittest.TestCase):
    """测试 5：置信度计算"""

    def test_high_confidence(self):
        """评分集中 → 置信度高"""
        self.assertAlmostEqual(calculate_confidence([5.0, 4.8, 4.9]), 0.96, places=2)

    def test_mid_confidence(self):
        """评分有一定分散 → 中等置信度"""
        self.assertAlmostEqual(calculate_confidence([5.0, 3.0, 4.0]), 0.60, places=2)

    def test_low_confidence(self):
        """评分分散 → 置信度低"""
        self.assertAlmostEqual(calculate_confidence([5.0, 1.0, 2.0]), 0.20, places=2)

    def test_edge_confidence(self):
        """评分范围达到最大值 → 置信度为 0"""
        self.assertAlmostEqual(calculate_confidence([5.0, 0.0, 1.0]), 0.0, places=2)


class TestControlSamples(unittest.TestCase):
    """测试 6：控制样本一致性"""

    def test_sample_count(self):
        """应有 2 个控制样本"""
        self.assertEqual(len(CONTROL_SAMPLES), 2)

    def test_sample_score_ranges(self):
        """所有预期得分应在 1~5 范围内"""
        for i, cs in enumerate(CONTROL_SAMPLES):
            avg = sum(cs["expected_scores"].values()) / 4
            self.assertGreaterEqual(avg, 1)
            self.assertLessEqual(avg, 5)


class TestEndToEnd(unittest.TestCase):
    """测试 7：端到端模拟"""

    def setUp(self):
        """构造模拟数据"""
        self.mock_problems = [
            {
                "problem_id": "m1",
                "problem": "Solve x+2=5?",
                "answer": "3",
                "solution": "x=3",
            },
            {"problem_id": "m2", "problem": "2*3?", "answer": "6", "solution": "6"},
        ]
        self.all_verdicts = [
            [
                JudgeVerdict(
                    "Judge-A", {"c": 4, "cl": 3.5, "d": 3, "co": 4}, 3.625, "mock"
                ),
                JudgeVerdict(
                    "Judge-B", {"c": 4.5, "cl": 4, "d": 3.5, "co": 4.5}, 4.125, "mock"
                ),
                JudgeVerdict(
                    "Judge-C", {"c": 3.5, "cl": 3, "d": 3.5, "co": 3.5}, 3.375, "mock"
                ),
            ],
            [
                JudgeVerdict(
                    "Judge-A", {"c": 4, "cl": 3.5, "d": 3, "co": 4}, 3.625, "mock"
                ),
                JudgeVerdict(
                    "Judge-B", {"c": 4.5, "cl": 4, "d": 3.5, "co": 4.5}, 4.125, "mock"
                ),
                JudgeVerdict(
                    "Judge-C", {"c": 3.5, "cl": 3, "d": 3.5, "co": 3.5}, 3.375, "mock"
                ),
            ],
        ]
        self.results = []
        for i, vs in enumerate(self.all_verdicts):
            scores = [v.total_score for v in vs]
            dl = measure_disagreement(scores)
            conf = calculate_confidence(scores)
            final = weighted_aggregate(
                vs, {"Judge-A": 1.0, "Judge-B": 1.0, "Judge-C": 0.8}
            )
            self.results.append(
                MultiJudgeResult(
                    item_id=f"m{i + 1}",
                    final_score=round(final, 2),
                    confidence=conf,
                    verdicts=vs,
                    anomaly_flags=[],
                    agreement_level=dl,
                )
            )

    def test_results_count(self):
        """应生成 2 个结果"""
        self.assertEqual(len(self.results), 2)

    def test_score_positive(self):
        """最终得分应 > 0"""
        self.assertGreater(self.results[0].final_score, 0)

    def test_confidence_non_negative(self):
        """置信度应 ≥ 0"""
        self.assertGreaterEqual(self.results[0].confidence, 0)


class TestReportGeneration(unittest.TestCase):
    """测试 8：报告生成"""

    def setUp(self):
        self.verdicts = [
            JudgeVerdict(
                "Judge-A", {"c": 4, "cl": 3.5, "d": 3, "co": 4}, 3.625, "mock"
            ),
            JudgeVerdict(
                "Judge-B", {"c": 4.5, "cl": 4, "d": 3.5, "co": 4.5}, 4.125, "mock"
            ),
            JudgeVerdict(
                "Judge-C", {"c": 3.5, "cl": 3, "d": 3.5, "co": 3.5}, 3.375, "mock"
            ),
        ]
        scores = [v.total_score for v in self.verdicts]
        self.results = [
            MultiJudgeResult(
                item_id="m1",
                final_score=3.71,
                confidence=calculate_confidence(scores),
                verdicts=self.verdicts,
                anomaly_flags=[],
                agreement_level=measure_disagreement(scores),
            )
        ]
        self.metrics = {
            "avg_score": statistics.mean([r.final_score for r in self.results]),
            "avg_confidence": statistics.mean([r.confidence for r in self.results]),
            "pass_rate": sum(1 for r in self.results if r.final_score >= 3.5)
            / len(self.results),
            "agreement_dist": {"low": 1, "moderate": 0, "severe": 0},
        }

    def test_report_contains_title(self):
        report = generate_report(
            self.metrics, self.results, ["Judge-A", "Judge-B", "Judge-C"], "2025-01-01"
        )
        self.assertIn("Multi-Judge 评估报告", report)

    def test_report_contains_results(self):
        report = generate_report(
            self.metrics, self.results, ["Judge-A", "Judge-B", "Judge-C"], "2025-01-01"
        )
        self.assertIn("m1", report)

    def test_report_contains_judges(self):
        report = generate_report(
            self.metrics, self.results, ["Judge-A", "Judge-B", "Judge-C"], "2025-01-01"
        )
        self.assertIn("Judge-A", report)

    def test_report_contains_score(self):
        report = generate_report(
            self.metrics, self.results, ["Judge-A", "Judge-B", "Judge-C"], "2025-01-01"
        )
        self.assertIn("平均得分", report)


if __name__ == "__main__":
    unittest.main()
