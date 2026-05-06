"""
精细化奖励函数设计
用于 GSM8K 数学问题的 Agentic RL 训练
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RewardConfig:
    """奖励函数配置"""

    # 准确率相关
    exact_match_reward: float = 1.0
    partial_tolerance: float = 0.01  # 数值容差

    # 部分正确奖励
    use_partial_reward: bool = True
    error_tiers: List[Tuple[float, float]] = None  # (误差范围, 奖励比例)

    # 推理过程评分
    use_reasoning_reward: bool = True
    reasoning_weight: float = 0.3
    required_markers: List[str] = None  # 必需的推理标记

    # 效率惩罚
    use_efficiency_penalty: bool = True
    efficiency_weight: float = 0.2
    target_length: int = 200  # 目标长度（字符数）
    max_length: int = 1024  # 最大长度

    def __post_init__(self):
        if self.error_tiers is None:
            self.error_tiers = [
                (0.0, 1.0),  # 完全正确
                (0.01, 0.8),  # 误差 < 1%
                (0.05, 0.5),  # 误差 < 5%
                (0.1, 0.3),  # 误差 < 10%
                (float("inf"), 0.0),  # 其他
            ]
        if self.required_markers is None:
            self.required_markers = ["Step", "Final Answer", "####"]


class FineGrainedRewardFunction:
    """
    精细化奖励函数

    设计思路:
    1. 部分正确奖励: 允许数值误差，给予不同级别的部分奖励
    2. 推理过程评分: 检测推理步骤的清晰度和逻辑性
    3. 效率惩罚: 惩罚过长或过于简洁的回答
    """

    def __init__(self, config: Optional[RewardConfig] = None):
        self.config = config or RewardConfig()

    def compute_reward(
        self, completion: str, ground_truth: str, prompt: str = ""
    ) -> Dict[str, float]:
        """
        计算综合奖励

        Args:
            completion: 模型生成的完整回答
            ground_truth: 正确答案
            prompt: 问题提示（可选）

        Returns:
            包含各项奖励的字典
        """
        # 1. 计算准确率奖励（包括部分正确）
        accuracy_reward = self._compute_accuracy_reward(completion, ground_truth)

        # 2. 计算推理过程奖励
        reasoning_reward = 0.0
        if self.config.use_reasoning_reward:
            reasoning_reward = self._compute_reasoning_reward(completion, ground_truth)

        # 3. 计算效率惩罚
        efficiency_penalty = 0.0
        if self.config.use_efficiency_penalty:
            efficiency_penalty = self._compute_efficiency_penalty(
                completion, accuracy_reward
            )

        # 4. 计算总奖励
        total_reward = (
            accuracy_reward
            * (1.0 - self.config.reasoning_weight - self.config.efficiency_weight)
            + reasoning_reward * self.config.reasoning_weight
            + efficiency_penalty * self.config.efficiency_weight
        )

        # 确保奖励在 [0, 1] 范围内
        total_reward = max(0.0, min(1.0, total_reward))

        return {
            "total": total_reward,
            "accuracy": accuracy_reward,
            "reasoning": reasoning_reward,
            "efficiency": efficiency_penalty,
        }

    def _compute_accuracy_reward(self, completion: str, ground_truth: str) -> float:
        """
        计算准确率奖励（包括部分正确）

        设计思路:
        - 完全正确（误差为 0）: 奖励 = 1.0
        - 非常接近（误差 < 1%）: 奖励 = 0.8
        - 接近（误差 < 5%）: 奖励 = 0.5
        - 较接近（误差 < 10%）: 奖励 = 0.3
        - 错误: 奖励 = 0.0
        """
        # 提取预测答案
        pred_answer = self._extract_answer(completion)

        # 提取真实答案
        truth_answer = self._extract_answer(ground_truth)

        if pred_answer is None or truth_answer is None:
            return 0.0

        # 计算绝对误差
        try:
            pred_num = float(pred_answer)
            truth_num = float(truth_answer)

            if truth_num == 0:
                error = abs(pred_num) if pred_num != 0 else 0.0
            else:
                error = abs(pred_num - truth_num) / abs(truth_num)
        except (ValueError, TypeError):
            # 无法转换为数值，进行字符串比较
            if pred_answer.strip() == truth_answer.strip():
                return self.config.exact_match_reward
            return 0.0

        # 根据误差范围确定奖励
        for threshold, reward_ratio in self.config.error_tiers:
            if error <= threshold:
                return reward_ratio * self.config.exact_match_reward

        return 0.0

    def _compute_reasoning_reward(self, completion: str, ground_truth: str) -> float:
        """
        计算推理过程奖励

        设计思路:
        - 包含清晰推理步骤: +0.1 ~ +0.3
        - 使用结构化标记（Step 1, Step 2...）: +0.1
        - 包含中间计算过程: +0.1
        - 格式规范（有 Final Answer 标记）: +0.1
        """
        score = 0.0

        # 检查是否包含推理步骤标记
        step_pattern = r"Step\s*\d+"
        step_matches = re.findall(step_pattern, completion, re.IGNORECASE)

        if step_matches:
            num_steps = len(set(step_matches))
            # 给予步骤数量奖励（最多 3 步）
            score += min(0.15, num_steps * 0.05)

        # 检查是否有 Final Answer 标记
        if "final answer" in completion.lower() or "####" in completion:
            score += 0.1

        # 检查是否包含中间计算
        intermediate_calc = re.findall(r"<<[^>]+>>", completion)
        if intermediate_calc:
            score += 0.05

        # 奖励合理性：检查推理是否有逻辑连接词
        logical_words = ["so", "therefore", "thus", "hence", "because", "first", "then"]
        has_logical = any(word in completion.lower() for word in logical_words)
        if has_logical:
            score += 0.05

        return min(score, 0.3)  # 最高 0.3 分

    def _compute_efficiency_penalty(
        self, completion: str, accuracy_reward: float
    ) -> float:
        """
        计算效率惩罚

        设计思路:
        - 如果答案错误，不应用效率惩罚（避免模型走捷径）
        - 如果答案正确但过长，适当惩罚
        - 如果答案正确且长度适中，给予奖励
        - 如果答案正确但过短（可能跳过步骤），适当惩罚
        """
        # 只有在答案至少部分正确时才应用效率奖励/惩罚
        if accuracy_reward <= 0.0:
            return 0.0

        length = len(completion)

        if length > self.config.max_length:
            # 过长，惩罚
            penalty = -0.2 * (length - self.config.max_length) / 1000
            return max(-0.3, penalty)

        if length > self.config.target_length:
            # 略长，轻微惩罚
            excess = (length - self.config.target_length) / 100
            penalty = -excess * 0.1
            return max(-0.1, penalty)

        if length < 50:
            # 过短，可能跳过了推理步骤
            return -0.1

        # 长度适中，给予轻微奖励
        if length <= self.config.target_length:
            bonus = 0.05 * (1 - length / self.config.target_length)
            return min(0.05, bonus)

        return 0.0

    def _extract_answer(self, text: str) -> Optional[str]:
        """从文本中提取答案"""
        # 方法1: 查找 "Final Answer:" 后面的内容
        match = re.search(r"Final Answer:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 方法2: 查找 "####" 后面的内容
        match = re.search(r"####\s*(.+?)(?:\n|$)", text)
        if match:
            return match.group(1).strip()

        # 方法3: 查找最后一个数字
        numbers = re.findall(r"-?\d+\.?\d*", text)
        if numbers:
            return numbers[-1]

        return None

    def compute_batch(
        self,
        completions: List[str],
        ground_truths: List[str],
        prompts: Optional[List[str]] = None,
    ) -> List[Dict[str, float]]:
        """
        批量计算奖励

        Args:
            completions: 模型生成的回答列表
            ground_truths: 正确答案列表
            prompts: 问题提示列表（可选）

        Returns:
            奖励列表
        """
        if prompts is None:
            prompts = [""] * len(completions)

        rewards = []
        for completion, truth, prompt in zip(completions, ground_truths, prompts):
            reward = self.compute_reward(completion, truth, prompt)
            rewards.append(reward)

        return rewards


class GroupRelativeReward:
    """
    群组相对奖励（用于 GRPO 训练）

    设计思路:
    - 对同一问题生成的多个答案，计算组内相对奖励
    - 相对奖励 = 绝对奖励 - 组内平均奖励
    - 这样可以减少奖励方差，提高训练稳定性
    """

    def __init__(self, reward_function: FineGrainedRewardFunction):
        self.reward_function = reward_function

    def compute_group_reward(
        self, completions: List[str], ground_truth: str, prompt: str = ""
    ) -> List[float]:
        """
        计算群组相对奖励

        Args:
            completions: 对同一问题生成的多个答案
            ground_truth: 正确答案
            prompt: 问题提示

        Returns:
            相对奖励列表
        """
        # 计算每个答案的绝对奖励
        absolute_rewards = []
        for completion in completions:
            reward_dict = self.reward_function.compute_reward(
                completion, ground_truth, prompt
            )
            absolute_rewards.append(reward_dict["total"])

        # 计算组内平均奖励
        group_mean = sum(absolute_rewards) / len(absolute_rewards)

        # 计算相对奖励
        relative_rewards = [r - group_mean for r in absolute_rewards]

        return relative_rewards


def example_usage():
    """使用示例"""
    # 创建奖励函数
    config = RewardConfig()
    reward_fn = FineGrainedRewardFunction(config)
    group_reward = GroupRelativeReward(reward_fn)

    # 测试样本
    question = "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?"
    ground_truth = "72"

    # 生成的多个答案（模拟多次采样）
    completions = [
        """Step 1: Calculate clips sold in May
Natalia sold half as many clips in May as in April.
Clips in May = 48 / 2 = 24

Step 2: Calculate total clips
Total = 48 + 24 = 72

Final Answer: 72""",  # 正确答案，推理清晰
        """Step 1: Calculate May sales
48 / 2 = 24

Step 2: Add them up
48 + 24 = 72

Final Answer: 72""",  # 正确答案，推理简洁
        """Natalia sold 48 clips in April and 24 in May.
Total = 48 + 24 = 72

#### 72""",  # 正确答案，但缺少 Step 标记和 Final Answer
        """Let me think... In April 48, half in May is 24...
So total is 48 + 24 = 72

Yes, 72""",  # 答案正确但格式不规范
        """Step 1: April = 48
Step 2: May = 48/2 = 23 (错误计算)
Total = 48 + 23 = 71

Final Answer: 71""",  # 错误答案
    ]

    print("=" * 60)
    print("精细化奖励函数测试")
    print("=" * 60)
    print(f"问题: {question}")
    print(f"正确答案: {ground_truth}")
    print("=" * 60)

    # 计算每个答案的奖励
    for i, completion in enumerate(completions):
        reward_dict = reward_fn.compute_reward(completion, ground_truth, question)

        print(f"\n答案 {i + 1}:")
        print(f"  准确率奖励: {reward_dict['accuracy']:.3f}")
        print(f"  推理过程奖励: {reward_dict['reasoning']:.3f}")
        print(f"  效率惩罚: {reward_dict['efficiency']:.3f}")
        print(f"  总奖励: {reward_dict['total']:.3f}")

    # 计算群组相对奖励
    print("\n" + "=" * 60)
    print("群组相对奖励")
    print("=" * 60)

    relative_rewards = group_reward.compute_group_reward(
        completions, ground_truth, question
    )

    group_mean = sum(
        reward_fn.compute_reward(c, ground_truth, question)["total"]
        for c in completions
    ) / len(completions)

    print(f"组内平均奖励: {group_mean:.3f}")
    print("\n相对奖励:")
    for i, rel_reward in enumerate(relative_rewards):
        print(f"  答案 {i + 1}: {rel_reward:+.3f}")


if __name__ == "__main__":
    example_usage()
