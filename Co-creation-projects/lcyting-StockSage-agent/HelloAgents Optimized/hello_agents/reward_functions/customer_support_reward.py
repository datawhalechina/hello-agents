"""
客服对话智能体奖励函数
用于 Agentic RL 训练
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CustomerSupportRewardConfig:
    """客服对话奖励配置"""

    # 问题解决率权重
    resolution_weight: float = 0.4

    # 用户满意度权重
    satisfaction_weight: float = 0.4

    # 响应时间权重
    time_weight: float = 0.2

    # 目标平均响应时间（秒）
    target_response_time: float = 2.0

    # 最大响应时间（秒）
    max_response_time: float = 30.0

    # 最小对话轮次（避免过短）
    min_turns: int = 1

    # 是否考虑情感分析
    use_sentiment: bool = True


class CustomerSupportRewardFunction:
    """
    客服对话奖励函数

    设计思路:
    1. 问题解决率: 基于对话结束时的问题是否解决
    2. 用户满意度: 基于用户反馈或情感分析
    3. 响应效率: 基于响应时间的紧凑度
    """

    def __init__(self, config: Optional[CustomerSupportRewardConfig] = None):
        self.config = config or CustomerSupportRewardConfig()

    def compute_reward(
        self,
        conversation: List[Dict],
        user_feedback: Optional[Dict] = None,
        response_time: float = 0.0,
        prompt: str = "",
    ) -> Dict[str, float]:
        """
        计算客服对话奖励

        Args:
            conversation: 对话历史 [{'role': 'user'/'assistant', 'content': str}, ...]
            user_feedback: 用户反馈 {'solved': bool, 'rating': float, 'comment': str}
            response_time: 响应时间（秒）
            prompt: 问题描述（可选）

        Returns:
            奖励字典
        """
        # 1. 计算问题解决率
        resolution_reward = self._compute_resolution_reward(conversation, user_feedback)

        # 2. 计算满意度
        satisfaction_reward = self._compute_satisfaction_reward(
            user_feedback, conversation
        )

        # 3. 计算时间效率
        time_reward = self._compute_time_reward(response_time)

        # 4. 计算总奖励
        total_reward = (
            resolution_reward * self.config.resolution_weight
            + satisfaction_reward * self.config.satisfaction_weight
            + time_reward * self.config.time_weight
        )

        # 确保在 [0, 1] 范围内
        total_reward = max(0.0, min(1.0, total_reward))

        return {
            "total": total_reward,
            "resolution": resolution_reward,
            "satisfaction": satisfaction_reward,
            "time": time_reward,
        }

    def _compute_resolution_reward(
        self, conversation: List[Dict], user_feedback: Optional[Dict]
    ) -> float:
        """计算问题解决率"""
        # 优先使用用户反馈
        if user_feedback is not None:
            if user_feedback.get("solved", False):
                return 1.0
            elif user_feedback.get("solved") is False:
                return 0.0

        # 通过对话内容推断是否解决
        # 检查是否有解决方案类关键词
        solution_keywords = [
            "已经解决",
            "已经帮您",
            "请问还有其他问题吗",
            "please let me know if you need anything else",
            "is there anything else i can help with",
        ]

        assistant_msgs = [
            msg["content"].lower()
            for msg in conversation
            if msg.get("role") == "assistant"
        ]

        # 检查最后一条助手消息
        if assistant_msgs:
            last_msg = assistant_msgs[-1]
            if any(kw.lower() in last_msg for kw in solution_keywords):
                return 0.8  # 推定已解决

        return 0.5  # 无法确定时给中间分

    def _compute_satisfaction_reward(
        self, user_feedback: Optional[Dict], conversation: List[Dict]
    ) -> float:
        """计算用户满意度"""
        # 优先使用用户评分
        if user_feedback is not None:
            rating = user_feedback.get("rating")
            if rating is not None:
                # 假设 rating 在 0-5 之间，归一化到 0-1
                return min(1.0, rating / 5.0)

        # 使用情感分析
        if self.config.use_sentiment:
            sentiment_score = self._compute_sentiment(conversation)
            return sentiment_score

        # 无法确定时给中间分
        return 0.5

    def _compute_sentiment(self, conversation: List[Dict]) -> float:
        """基于对话内容计算情感分数（简化版）"""
        all_text = " ".join([msg.get("content", "") for msg in conversation]).lower()

        positive_words = [
            "thank",
            "thanks",
            "great",
            "perfect",
            "awesome",
            "helpful",
            "excellent",
            "nice",
            "good",
            "喜欢",
            "谢谢",
            "棒",
        ]
        negative_words = [
            "bad",
            "terrible",
            "worst",
            "hate",
            "angry",
            "frustrated",
            "useless",
            "stupid",
            "差",
            "垃圾",
            "生气",
            "失望",
        ]

        pos_count = sum(1 for w in positive_words if w in all_text)
        neg_count = sum(1 for w in negative_words if w in all_text)

        if pos_count + neg_count == 0:
            return 0.5

        return pos_count / (pos_count + neg_count)

    def _compute_time_reward(self, response_time: float) -> float:
        """计算响应时间效率"""
        if response_time == 0:
            return 0.5  # 无数据时给中间分

        if response_time <= self.config.target_response_time:
            return 1.0
        elif response_time >= self.config.max_response_time:
            return 0.0
        else:
            # 线性惩罚
            ratio = (self.config.max_response_time - response_time) / (
                self.config.max_response_time - self.config.target_response_time
            )
            return max(0.0, ratio)

    def compute_batch(
        self,
        conversations: List[List[Dict]],
        user_feedbacks: Optional[List[Dict]] = None,
        response_times: Optional[List[float]] = None,
        prompts: Optional[List[str]] = None,
    ) -> List[Dict[str, float]]:
        """批量计算奖励"""
        if user_feedbacks is None:
            user_feedbacks = [None] * len(conversations)
        if response_times is None:
            response_times = [0.0] * len(conversations)
        if prompts is None:
            prompts = [""] * len(conversations)

        rewards = []
        for conv, fb, t in zip(conversations, user_feedbacks, response_times):
            rewards.append(self.compute_reward(conv, fb, t, ""))

        return rewards


def example_usage():
    """使用示例"""
    config = CustomerSupportRewardConfig()
    reward_fn = CustomerSupportRewardFunction(config)

    # 测试用例：好的对话
    conversation_good = [
        {"role": "user", "content": "我的订单怎么还没到？"},
        {"role": "assistant", "content": "抱歉让您久等了，我帮您查一下订单状态。"},
        {
            "role": "assistant",
            "content": "您的订单已经在派送中，预计今天下午送达。请问还有其他问题吗？",
        },
    ]
    user_feedback_good = {"solved": True, "rating": 5}
    response_time_good = 1.5

    # 测试用例：差的对话
    conversation_bad = [
        {"role": "user", "content": "我的账户登录不了"},
        {"role": "assistant", "content": "抱歉，我不太清楚"},
    ]
    user_feedback_bad = {"solved": False, "rating": 1}
    response_time_bad = 5.0

    print("=" * 50)
    print("客服对话奖励测试")
    print("=" * 50)

    # 好对话
    r = reward_fn.compute_reward(
        conversation_good, user_feedback_good, response_time_good
    )
    print(
        f"好对话: total={r['total']:.3f}, res={r['resolution']:.3f}, sat={r['satisfaction']:.3f}, time={r['time']:.3f}"
    )

    # 差对话
    r = reward_fn.compute_reward(conversation_bad, user_feedback_bad, response_time_bad)
    print(
        f"差对话: total={r['total']:.3f}, res={r['resolution']:.3f}, sat={r['satisfaction']:.3f}, time={r['time']:.3f}"
    )


if __name__ == "__main__":
    example_usage()
