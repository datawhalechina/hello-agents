"""课程学习系统 - 阶段过渡评估器

评估智能体是否准备好进入下一阶段。
使用多维度综合评分，自动识别瓶颈维度。
"""

from __future__ import annotations

from typing import List, Dict, Optional
from dataclasses import dataclass

from .types import StageProgress


@dataclass
class TransitionVerdict:
    """过渡判定结果"""

    can_advance: bool
    current_score: float
    threshold: float
    bottleneck: str
    dimension_scores: Dict[str, float]
    improvements: List[str]
    consecutive_count: int
    required_count: int
    message: str


class TransitionEvaluator:
    """阶段过渡评估器

    评定维度:
    - S_success (40%): 任务成功率
    - S_efficiency (25%): 步数效率
    - S_robustness (15%): 各工具使用均匀度
    - S_generalization (20%): 留出任务泛化能力

    过渡条件: 连续 N 次评估超过阈值 + 所有维度均不低于 0.5
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.75,
        consecutive_count: int = 3,
        min_dimension_score: float = 0.4,
    ):
        self.weights = weights or {
            "success_rate": 0.40,
            "efficiency": 0.25,
            "robustness": 0.15,
            "generalization": 0.20,
        }
        self.threshold = threshold
        self.consecutive_count = consecutive_count
        self.min_dimension_score = min_dimension_score
        self._history: Dict[str, List[Dict[str, float]]] = {}

    def evaluate_stage(
        self,
        progress: StageProgress,
        held_out_success_rate: Optional[float] = None,
    ) -> TransitionVerdict:
        """评估单个阶段的就绪度

        Args:
            progress: 当前阶段进度
            held_out_success_rate: 留出任务成功率（泛化能力评估）

        Returns:
            过渡判定结果
        """
        success_rate = progress.success_rate
        steps_taken = progress.total_steps
        optimal_steps = max(progress.optimal_steps, 1)
        tool_usage_counts = progress.tool_usage

        # ── 计算各维度评分 ──
        eff = min(1.0, optimal_steps / max(steps_taken, 1))
        rob = self._compute_robustness(tool_usage_counts, progress.tasks_completed)
        gen = (
            held_out_success_rate if held_out_success_rate is not None else success_rate
        )

        # 综合评分
        overall = (
            self.weights["success_rate"] * success_rate
            + self.weights["efficiency"] * eff
            + self.weights["robustness"] * rob
            + self.weights["generalization"] * gen
        )

        # 识别瓶颈
        dimension_scores = {
            "success_rate": success_rate,
            "efficiency": eff,
            "robustness": rob,
            "generalization": gen,
        }
        bottleneck = min(dimension_scores, key=dimension_scores.get)

        # ── 历史记录 ──
        if progress.stage_id not in self._history:
            self._history[progress.stage_id] = []
        self._history[progress.stage_id].append(dimension_scores)

        recent = self._history[progress.stage_id]
        consecutive = len(recent)

        # ── 判定 ──
        can_advance = self._check_can_advance(recent)

        # 改进建议
        improvements = self._generate_improvements(dimension_scores, bottleneck)

        return TransitionVerdict(
            can_advance=can_advance,
            current_score=overall,
            threshold=self.threshold,
            bottleneck=bottleneck,
            dimension_scores=dimension_scores,
            improvements=improvements,
            consecutive_count=consecutive,
            required_count=self.consecutive_count,
            message=self._build_message(
                can_advance, overall, bottleneck, dimension_scores
            ),
        )

    def _compute_robustness(
        self,
        tool_usage: Dict[str, int],
        total_tasks: int,
    ) -> float:
        """计算工具使用鲁棒性

        各工具使用次数越均匀，鲁棒性越高。
        完全不使用某工具会降低分数。
        """
        if not tool_usage or total_tasks == 0:
            return 0.0

        values = list(tool_usage.values())
        if not values:
            return 0.0

        # 使用变异系数（CV）衡量均匀度
        mean_val = sum(values) / len(values)
        if mean_val == 0:
            return 0.0

        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        cv = (variance**0.5) / mean_val

        # CV=0 表示完全均匀（1.0），CV越大越不均匀
        robustness = max(0.0, 1.0 - cv)

        # 惩罚未使用的工具
        n_expected = len(tool_usage)
        n_used = sum(1 for v in values if v > 0)
        usage_penalty = n_used / max(n_expected, 1)

        return robustness * usage_penalty

    def _check_can_advance(self, history: List[Dict[str, float]]) -> bool:
        """检查是否满足连续通过条件"""
        if len(history) < self.consecutive_count:
            return False

        recent = history[-self.consecutive_count :]
        for scores in recent:
            overall = sum(self.weights[k] * scores.get(k, 0.0) for k in self.weights)
            if overall < self.threshold:
                return False
            # 任何维度太低都不通过
            for k, v in scores.items():
                if v < self.min_dimension_score:
                    return False

        return True

    def _generate_improvements(
        self,
        scores: Dict[str, float],
        bottleneck: str,
    ) -> List[str]:
        """根据瓶颈维度生成改进建议"""
        suggestions = {
            "success_rate": [
                "增加任务成功率：检查推理链是否完整",
                "确保工具调用参数正确",
                "回顾工具文档确保正确使用",
            ],
            "efficiency": [
                "减少不必要的工具调用步骤",
                "提前规划好工具调用顺序",
                "避免重复调用相同工具获取相同信息",
            ],
            "robustness": [
                "均衡使用所有可用工具，避免偏废",
                "尝试用不同工具解决同一类问题",
                "确保每个工具都在不同场景下练习过",
            ],
            "generalization": [
                "增加任务多样性：尝试不同的组合方式",
                "在不同类型的问题上练习工具使用",
                "挑战未见过的工具组合场景",
            ],
        }

        return suggestions.get(bottleneck, ["继续练习当前阶段"])

    def _build_message(
        self,
        can_advance: bool,
        score: float,
        bottleneck: str,
        scores: Dict[str, float],
    ) -> str:
        """构建可读的判定消息"""
        dim_str = ", ".join(f"{k}={v:.2f}" for k, v in sorted(scores.items()))
        if can_advance:
            return (
                f"Ready to advance! Score={score:.3f} >= {self.threshold}. "
                f"Dims: [{dim_str}]"
            )
        return (
            f"Need more practice. Score={score:.3f} < {self.threshold}. "
            f"Bottleneck: {bottleneck}. Dims: [{dim_str}]"
        )

    def get_performance_trend(self, stage_id: str, window: int = 5) -> List[float]:
        """获取指定阶段的性能趋势"""
        if stage_id not in self._history:
            return []

        recent = self._history[stage_id][-window:]
        return [
            sum(self.weights[k] * s.get(k, 0.0) for k in self.weights) for s in recent
        ]

    def reset_history(self, stage_id: Optional[str] = None):
        """重置评估历史"""
        if stage_id:
            self._history.pop(stage_id, None)
        else:
            self._history.clear()
