"""RL训练奖励函数"""

import re
from typing import List, Callable, Dict, Any, Optional


class MathRewardFunction:
    """数学问题奖励函数

    用于评估模型生成的数学答案是否正确。
    """

    def __init__(self, tolerance: float = 1e-4):
        """
        初始化奖励函数

        Args:
            tolerance: 数值比较的容差
        """
        self.tolerance = tolerance
        self.__name__ = "MathRewardFunction"  # 添加__name__属性

    def extract_answer(self, text: str) -> Optional[str]:
        """
        从文本中提取答案

        Args:
            text: 生成的文本

        Returns:
            提取的答案字符串，如果未找到则返回None
        """
        # 尝试多种答案格式
        patterns = [
            r"Final Answer:\s*([^\n]+)",
            r"####\s*([^\n]+)",
            r"答案是?\s*[:：]?\s*([^\n]+)",
            r"Therefore,?\s*(?:the answer is)?\s*([^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # 如果没有找到特定格式，尝试提取最后一行的数字
        lines = text.strip().split("\n")
        for line in reversed(lines):
            numbers = re.findall(r"-?\d+\.?\d*", line)
            if numbers:
                return numbers[-1]

        return None

    def normalize_answer(self, answer: str) -> Optional[float]:
        """
        标准化答案为数值

        Args:
            answer: 答案字符串

        Returns:
            标准化后的数值，如果无法转换则返回None
        """
        if answer is None:
            return None

        # 移除常见的非数字字符
        answer = answer.strip()
        answer = answer.replace(",", "")  # 移除千位分隔符
        answer = answer.replace("$", "")  # 移除美元符号
        answer = answer.replace("%", "")  # 移除百分号

        # 提取数字
        numbers = re.findall(r"-?\d+\.?\d*", answer)
        if not numbers:
            return None

        try:
            return float(numbers[0])
        except ValueError:
            return None

    def compare_answers(self, pred: str, truth: str) -> bool:
        """
        比较预测答案和真实答案

        Args:
            pred: 预测答案
            truth: 真实答案

        Returns:
            是否匹配
        """
        pred_num = self.normalize_answer(pred)
        truth_num = self.normalize_answer(truth)

        if pred_num is None or truth_num is None:
            # 如果无法转换为数字，进行字符串比较
            return pred.strip().lower() == truth.strip().lower()

        # 数值比较（考虑容差）
        return abs(pred_num - truth_num) < self.tolerance

    def __call__(self, completions: List[str], **kwargs) -> List[float]:
        """
        计算奖励

        Args:
            completions: 模型生成的完成文本列表
            **kwargs: 其他参数,必须包含ground_truth列表

        Returns:
            奖励值列表（1.0表示正确，0.0表示错误）
        """
        # 从kwargs中获取ground_truth
        ground_truths = kwargs.get("ground_truth", [])
        if not ground_truths:
            raise ValueError("ground_truth必须在数据集中提供")

        rewards = []

        for completion, truth in zip(completions, ground_truths):
            # 提取预测答案
            pred_answer = self.extract_answer(completion)

            # 比较答案
            if pred_answer and self.compare_answers(pred_answer, truth):
                reward = 1.0
            else:
                reward = 0.0

            rewards.append(reward)

        return rewards


def create_accuracy_reward(tolerance: float = 1e-4) -> Callable:
    """
    创建准确性奖励函数（便捷函数）

    Args:
        tolerance: 数值比较的容差

    Returns:
        奖励函数
    """
    reward_fn = MathRewardFunction(tolerance=tolerance)
    return reward_fn


def create_length_penalty_reward(
    base_reward_fn: Callable, max_length: int = 1024, penalty_weight: float = 0.1
) -> Callable:
    """
    创建带长度惩罚的奖励函数

    Args:
        base_reward_fn: 基础奖励函数
        max_length: 最大长度
        penalty_weight: 惩罚权重

    Returns:
        带长度惩罚的奖励函数
    """

    def reward_fn(completions: List[str], **kwargs) -> List[float]:
        # 计算基础奖励
        base_rewards = base_reward_fn(completions, **kwargs)

        # 添加长度惩罚
        final_rewards = []
        for reward, completion in zip(base_rewards, completions):
            length = len(completion)
            if length > max_length:
                penalty = penalty_weight * (length - max_length) / max_length
                reward = max(0.0, reward - penalty)
            final_rewards.append(reward)

        return final_rewards

    return reward_fn


def create_step_reward(base_reward_fn: Callable, step_bonus: float = 0.1) -> Callable:
    """
    创建带步骤奖励的函数（鼓励详细的推理过程）

    Args:
        base_reward_fn: 基础奖励函数
        step_bonus: 每个推理步骤的奖励

    Returns:
        带步骤奖励的函数
    """

    def reward_fn(completions: List[str], **kwargs) -> List[float]:
        # 计算基础奖励
        base_rewards = base_reward_fn(completions, **kwargs)

        # 添加步骤奖励
        final_rewards = []
        for reward, completion in zip(base_rewards, completions):
            # 统计推理步骤（简单地统计换行符数量）
            num_steps = completion.count("\n")
            step_reward = min(step_bonus * num_steps, 0.5)  # 最多0.5的额外奖励
            final_rewards.append(reward + step_reward)

        return final_rewards

    return reward_fn


def evaluate_rewards(
    completions: List[str], ground_truths: List[str], reward_fn: Callable
) -> Dict[str, Any]:
    """
    评估奖励函数的性能

    Args:
        completions: 生成的完成文本列表
        ground_truths: 真实答案列表
        reward_fn: 奖励函数

    Returns:
        评估结果字典
    """
    rewards = reward_fn(completions, ground_truths=ground_truths)

    return {
        "mean_reward": sum(rewards) / len(rewards) if rewards else 0.0,
        "max_reward": max(rewards) if rewards else 0.0,
        "min_reward": min(rewards) if rewards else 0.0,
        "accuracy": sum(1 for r in rewards if r > 0.5) / len(rewards)
        if rewards
        else 0.0,
        "num_samples": len(rewards),
    }


# 示例用法
if __name__ == "__main__":
    # 创建奖励函数
    reward_fn = create_accuracy_reward()

    # 测试样例
    completions = [
        "Let's solve step by step:\n1 + 1 = 2\nFinal Answer: 2",
        "The answer is 3",
        "I don't know",
    ]
    ground_truths = ["2", "2", "2"]

    # 计算奖励
    rewards = reward_fn(completions, ground_truths)
    print("Rewards:", rewards)

    # 评估
    results = evaluate_rewards(completions, ground_truths, reward_fn)
    print("Evaluation:", results)
