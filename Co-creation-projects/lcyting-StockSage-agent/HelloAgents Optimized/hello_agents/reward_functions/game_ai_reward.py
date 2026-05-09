"""
游戏 AI 奖励函数
用于 Agentic RL 训练
"""

import math
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class GameAIRewardConfig:
    """游戏 AI 奖励配置"""

    # 胜率权重
    win_weight: float = 0.6

    # 策略多样性权重
    diversity_weight: float = 0.2

    # 对抗鲁棒性权重
    robustness_weight: float = 0.2

    # 用于计算多样性的历史步数
    diversity_history_steps: int = 10

    # 最小行动次数（避免空白策略）
    min_actions: int = 1

    # 是否考虑生存时间
    use_survival: bool = True

    # 生存时间权重
    survival_weight: float = 0.0


class GameAIRewardFunction:
    """
    游戏 AI 奖励函数

    设计思路:
    1. 胜率: 基于对战结果
    2. 策略多样性: 基于历史行动分布的熵
    3. 对抗鲁棒性: 对不同对手的平均表现
    """

    def __init__(self, config: Optional[GameAIRewardConfig] = None):
        self.config = config or GameAIRewardConfig()

    def compute_reward(
        self,
        episode_result: Dict,
        action_history: List[str],
        opponent_results: Optional[List[Dict]] = None,
        prompt: str = "",
    ) -> Dict[str, float]:
        """
        计算游戏 AI 奖励

        Args:
            episode_result: 当前对局结果 {'win': bool, 'score': float, 'survival_time': float}
            action_history: 历史行动列表 ['action1', 'action2', ...]
            opponent_results: 对不同对手的结果列表 [{'win': bool}, ...]
            prompt: 游戏描述（可选）

        Returns:
            奖励字典
        """
        # 1. 计算胜率奖励
        win_reward = self._compute_win_reward(episode_result)

        # 2. 计算多样性奖励
        diversity_reward = self._compute_diversity_reward(action_history)

        # 3. 计算鲁棒性奖励
        robustness_reward = self._compute_robustness_reward(opponent_results)

        # 4. 计算生存时间奖励（可选）
        survival_reward = 0.0
        if self.config.use_survival:
            survival_reward = self._compute_survival_reward(episode_result)

        # 5. 计算总奖励
        total_reward = (
            win_reward * self.config.win_weight
            + diversity_reward * self.config.diversity_weight
            + robustness_reward * self.config.robustness_weight
            + survival_reward * self.config.survival_weight
        )

        # 确保在 [0, 1] 范围内
        total_reward = max(0.0, min(1.0, total_reward))

        return {
            "total": total_reward,
            "win": win_reward,
            "diversity": diversity_reward,
            "robustness": robustness_reward,
            "survival": survival_reward,
        }

    def _compute_win_reward(self, episode_result: Dict) -> float:
        """计算胜率奖励"""
        if episode_result.get("win", False):
            return 1.0

        # 如果没有获胜但有分数，考虑分数奖励
        score = episode_result.get("score", 0.0)
        if score > 0:
            # 假设分数在 0-100 之间，归一化
            return min(1.0, score / 100.0)

        return 0.0

    def _compute_diversity_reward(self, action_history: List[str]) -> float:
        """计算策略多样性奖励（基于熵）"""
        if len(action_history) < self.config.min_actions:
            return 0.0

        # 使用最近的 N 步
        recent_actions = action_history[-self.config.diversity_history_steps :]

        # 计算每个行动的频率
        action_counts = {}
        for action in recent_actions:
            action_counts[action] = action_counts.get(action, 0) + 1

        # 计算熵
        n = len(recent_actions)
        entropy = 0.0
        for count in action_counts.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

        # 归一化熵（最大熵为 log2(行动数)）
        num_actions = len(action_counts)
        if num_actions > 1:
            max_entropy = math.log2(num_actions)
            normalized_entropy = entropy / max_entropy
        else:
            normalized_entropy = 0.0

        return normalized_entropy

    def _compute_robustness_reward(
        self, opponent_results: Optional[List[Dict]]
    ) -> float:
        """计算对抗鲁棒性奖励"""
        if not opponent_results:
            return 0.5  # 无数据时给中间分

        wins = sum(1 for r in opponent_results if r.get("win", False))
        total = len(opponent_results)

        if total == 0:
            return 0.5

        return wins / total

    def _compute_survival_reward(self, episode_result: Dict) -> float:
        """计算生存时间奖励"""
        survival_time = episode_result.get("survival_time", 0.0)

        if survival_time == 0:
            return 0.5

        # 假设最大生存时间为 300 秒（5分钟），归一化
        max_survival = 300.0
        normalized = min(1.0, survival_time / max_survival)

        return normalized

    def compute_batch(
        self,
        episode_results: List[Dict],
        action_histories: List[List[str]],
        opponent_results_list: Optional[List[List[Dict]]] = None,
        prompts: Optional[List[str]] = None,
    ) -> List[Dict[str, float]]:
        """批量计算奖励"""
        if opponent_results_list is None:
            opponent_results_list = [None] * len(episode_results)
        if prompts is None:
            prompts = [""] * len(episode_results)

        rewards = []
        for ep, hist, opp in zip(
            episode_results, action_histories, opponent_results_list
        ):
            rewards.append(self.compute_reward(ep, hist, opp, ""))

        return rewards


def example_usage():
    """使用示例"""
    config = GameAIRewardConfig()
    reward_fn = GameAIRewardFunction(config)

    # 测试用例：赢了对局
    episode_win = {"win": True, "score": 100, "survival_time": 120}
    history_good = ["attack", "defend", "move", "attack", "defend", "item", "attack"]
    opponent_results_good = [
        {"win": True},
        {"win": True},
        {"win": False},
        {"win": True},
    ]

    # 测试用例：输了对局
    episode_loss = {"win": False, "score": 10, "survival_time": 30}
    history_bad = ["attack", "attack", "attack"]  # 策略单一
    opponent_results_bad = [{"win": False}, {"win": False}, {"win": True}]

    print("=" * 50)
    print("游戏 AI 奖励测试")
    print("=" * 50)

    # 赢了对局
    r = reward_fn.compute_reward(episode_win, history_good, opponent_results_good)
    print(
        f"赢局: total={r['total']:.3f}, win={r['win']:.3f}, div={r['diversity']:.3f}, rob={r['robustness']:.3f}"
    )

    # 输了对局
    r = reward_fn.compute_reward(episode_loss, history_bad, opponent_results_bad)
    print(
        f"输局: total={r['total']:.3f}, win={r['win']:.3f}, div={r['diversity']:.3f}, rob={r['robustness']:.3f}"
    )


if __name__ == "__main__":
    example_usage()
