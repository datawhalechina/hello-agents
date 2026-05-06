"""分层奖励函数 (Hierarchical Reward Functions)

设计两层奖励机制：
1. 高层奖励 (High-Level Reward): 子目标规划的合理性、完整性
2. 低层奖励 (Low-Level Reward): 工具调用的正确性、效率

总分奖励机制防止两层目标冲突。
"""

from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass


@dataclass
class RewardComponent:
    """奖励分量的配置和计算结果"""

    name: str
    weight: float
    value: float = 0.0

    @property
    def weighted(self) -> float:
        return self.weight * self.value


@dataclass
class HierarchicalRewardResult:
    """分层奖励计算结果"""

    high_level: Dict[str, float]  # 高层奖励各分量
    low_level: Dict[str, float]  # 低层奖励各分量
    total: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        result = {"total": self.total}
        result.update({f"high_{k}": v for k, v in self.high_level.items()})
        result.update({f"low_{k}": v for k, v in self.low_level.items()})
        return result


class HierarchicalReward:
    """分层奖励函数

    设计原则：
    - 高层奖励关注"规划质量"，低层奖励关注"执行质量"
    - 总分 = 高层 × (1 + 低层完成度) ，确保高层目标主导
    - 防止低层"奖励黑客": 低层效率奖励仅在高层子目标完成时生效
    """

    def __init__(
        self,
        high_weights: Optional[Dict[str, float]] = None,
        low_weights: Optional[Dict[str, float]] = None,
    ):
        self.high_weights = high_weights or {
            "completeness": 0.4,  # 子目标覆盖率
            "dependency": 0.2,  # 依赖关系正确性
            "granularity": 0.2,  # 子目标粒度合理性
            "task_success": 0.2,  # 最终任务成功
        }
        self.low_weights = low_weights or {
            "tool_correctness": 0.4,  # 工具选择正确性
            "parameter_quality": 0.2,  # 参数构建质量
            "efficiency": 0.2,  # 步数效率
            "error_recovery": 0.2,  # 错误恢复能力
        }

    def compute_high_reward(
        self,
        predicted_subgoals: List[Any],
        optimal_subgoals: Optional[List[Any]] = None,
        execution_results: Optional[List[Dict]] = None,
        task_success: bool = False,
    ) -> Dict[str, float]:
        """计算高层奖励

        Args:
            predicted_subgoals: 模型预测的子目标列表
            optimal_subgoals: 最优子目标列表（如果已知）
            execution_results: 低层执行结果
            task_success: 最终任务是否成功

        Returns:
            高层奖励各分量
        """
        components = {}

        # 1. 完整性奖励: 子目标是否覆盖了所有必要步骤
        if optimal_subgoals:
            optimal_types = {sg.type.value for sg in optimal_subgoals}
            predicted_types = {
                sg.type.value if hasattr(sg, "type") else str(sg)
                for sg in predicted_subgoals
            }
            overlap = len(optimal_types & predicted_types)
            total = len(optimal_types)
            components["completeness"] = overlap / max(total, 1)
        else:
            # 无标准答案时，根据执行结果推断
            success_count = sum(
                1
                for r in (execution_results or [])
                if isinstance(r, dict) and r.get("completed", False)
            )
            total = len(execution_results or [1])
            components["completeness"] = success_count / max(total, 1)

        # 2. 依赖关系奖励: 子目标之间的依赖是否合理
        if len(predicted_subgoals) > 1:
            dependency_score = self._evaluate_dependencies(predicted_subgoals)
        else:
            dependency_score = 1.0  # 单子目标时满分
        components["dependency"] = dependency_score

        # 3. 粒度奖励: 子目标数量是否合理（2-8个为佳）
        n = len(predicted_subgoals)
        if 2 <= n <= 8:
            granularity = 1.0 - 0.1 * abs(n - 4)  # 4个为最优
        elif n == 1:
            granularity = 0.3  # 过粗
        else:
            granularity = max(0, 1.0 - 0.1 * (n - 8))  # 过细则惩罚
        components["granularity"] = max(0, granularity)

        # 4. 任务成功奖励
        components["task_success"] = 1.0 if task_success else 0.0

        return components

    def compute_low_reward(
        self,
        trajectory: List[Dict],
        subgoal_success: bool = False,
    ) -> Dict[str, float]:
        """计算低层奖励

        Args:
            trajectory: 工具调用轨迹列表
            subgoal_success: 子目标是否成功完成

        Returns:
            低层奖励各分量
        """
        components = {}

        # 1. 工具选择正确性
        correct_calls = sum(
            1
            for step in trajectory
            if isinstance(step, dict)
            and step.get("type") == "tool_call"
            and not str(step.get("observation", "")).startswith("Error")
        )
        total_calls = sum(
            1
            for step in trajectory
            if isinstance(step, dict) and step.get("type") == "tool_call"
        )
        components["tool_correctness"] = (
            correct_calls / max(total_calls, 1) if total_calls > 0 else 0.0
        )

        # 2. 参数构建质量（通过错误率估计）
        param_errors = sum(
            1
            for step in trajectory
            if isinstance(step, dict)
            and "argument" in str(step.get("observation", "")).lower()
            or "invalid" in str(step.get("observation", "")).lower()
        )
        components["parameter_quality"] = max(
            0, 1.0 - (param_errors / max(total_calls, 1))
        )

        # 3. 效率奖励：步数越少越好
        if subgoal_success:
            optimal_steps = max(1, total_calls // 2)
            components["efficiency"] = min(1.0, optimal_steps / max(total_calls, 1))
        else:
            components["efficiency"] = 0.0  # 子目标失败则效率为0

        # 4. 错误恢复能力
        error_count = sum(
            1
            for step in trajectory
            if isinstance(step, dict)
            and str(step.get("observation", "")).startswith("Error")
        )
        recovery_count = sum(
            1
            for i, step in enumerate(trajectory[:-1])
            if isinstance(step, dict)
            and str(step.get("observation", "")).startswith("Error")
            and isinstance(trajectory[i + 1], dict)
            and trajectory[i + 1].get("type") == "tool_call"
        )
        components["error_recovery"] = (
            recovery_count / max(error_count, 1) if error_count > 0 else 1.0
        )

        return components

    def compute_total_reward(
        self,
        high_rewards: Dict[str, float],
        low_rewards: Dict[str, float],
    ) -> HierarchicalRewardResult:
        """计算总奖励

        总奖励 = 高层总分 × (1 + 低层加权分)

        这种设计确保：
        - 高层目标主导（即使低层完美，高层为0则总分为0）
        - 低层执行质量用于缩放高层奖励
        """
        high_total = sum(
            self.high_weights.get(k, 0.2) * v for k, v in high_rewards.items()
        )
        low_total = sum(
            self.low_weights.get(k, 0.25) * v for k, v in low_rewards.items()
        )

        total = high_total * (1.0 + low_total * 0.5)

        return HierarchicalRewardResult(
            high_level=high_rewards,
            low_level=low_rewards,
            total=min(total, 2.0),  # 上限2.0
        )

    def compute_batch(
        self,
        high_inputs: List[Dict],
        low_inputs: List[Dict],
    ) -> List[float]:
        """批量计算奖励（用于GRPO训练）"""
        rewards = []
        for h_in, l_in in zip(high_inputs, low_inputs):
            high_r = self.compute_high_reward(**h_in)
            low_r = self.compute_low_reward(**l_in)
            result = self.compute_total_reward(high_r, low_r)
            rewards.append(result.total)
        return rewards

    def _evaluate_dependencies(self, subgoals: List) -> float:
        """评估依赖关系合理性"""
        if len(subgoals) < 2:
            return 1.0

        score = 1.0
        for i, sg in enumerate(subgoals):
            deps = getattr(sg, "depends_on", []) or []
            for dep_idx in deps:
                # 依赖不能指向自身或未来
                if dep_idx >= i or dep_idx < 0:
                    score -= 0.2
                # 依赖不能形成环（简化处理）
                if dep_idx == i:
                    score -= 0.3
        return max(0, score)


def create_hierarchical_reward_function(
    reward: Optional[HierarchicalReward] = None,
) -> Callable:
    """创建GRPO兼容的分层奖励函数"""
    hreward = reward or HierarchicalReward()

    def reward_fn(completions: List[str], **kwargs) -> List[float]:
        rewards = []
        for completion in completions:
            # 简化版：从completion提取信息计算奖励
            # 完整版需要解析completion中的子目标和工具调用
            result = hreward.compute_total_reward(
                {
                    "completeness": 0.5,
                    "dependency": 0.5,
                    "granularity": 0.5,
                    "task_success": 0.0,
                },
                {
                    "tool_correctness": 0.5,
                    "parameter_quality": 0.5,
                    "efficiency": 0.5,
                    "error_recovery": 0.5,
                },
            )
            rewards.append(result.total)
        return rewards

    return reward_fn
