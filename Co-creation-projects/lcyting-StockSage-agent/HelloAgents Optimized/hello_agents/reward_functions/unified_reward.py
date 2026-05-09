"""
统一奖励函数入口
用于 Agentic RL 训练的多种任务
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from fine_grained_reward import (
    FineGrainedRewardFunction,
    RewardConfig as GSM8KRewardConfig,
)
from code_gen_reward import CodeGenRewardFunction, CodeGenRewardConfig
from customer_support_reward import (
    CustomerSupportRewardFunction,
    CustomerSupportRewardConfig,
)
from game_ai_reward import GameAIRewardFunction, GameAIRewardConfig


@dataclass
class UnifiedRewardConfig:
    """统一奖励配置"""

    task_type: str = "gsm8k"  # gsm8k, code_gen, customer_support, game_ai

    # 任务特定配置
    gsm8k_config: Optional[GSM8KRewardConfig] = None
    code_gen_config: Optional[CodeGenRewardConfig] = None
    customer_support_config: Optional[CustomerSupportRewardConfig] = None
    game_ai_config: Optional[GameAIRewardConfig] = None


class UnifiedRewardFunction:
    """
    统一奖励函数接口

    支持多种任务的奖励计算:
    - gsm8k: GSM8K 数学推理
    - code_gen: 代码生成
    - customer_support: 客服对话
    - game_ai: 游戏 AI
    """

    def __init__(self, config: Optional[UnifiedRewardConfig] = None):
        self.config = config or UnifiedRewardConfig()
        self._init_task_functions()

    def _init_task_functions(self):
        """根据任务类型初始化对应的奖励函数"""
        task_type = self.config.task_type

        if task_type == "gsm8k":
            gsm8k_cfg = self.config.gsm8k_config or GSM8KRewardConfig()
            self.reward_fn = FineGrainedRewardFunction(gsm8k_cfg)
        elif task_type == "code_gen":
            code_cfg = self.config.code_gen_config or CodeGenRewardConfig()
            self.reward_fn = CodeGenRewardFunction(code_cfg)
        elif task_type == "customer_support":
            cs_cfg = (
                self.config.customer_support_config or CustomerSupportRewardConfig()
            )
            self.reward_fn = CustomerSupportRewardFunction(cs_cfg)
        elif task_type == "game_ai":
            game_cfg = self.config.game_ai_config or GameAIRewardConfig()
            self.reward_fn = GameAIRewardFunction(game_cfg)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def compute_reward(
        self,
        completion: Union[str, Dict, List[Dict]],
        ground_truth: Union[str, Dict, List],
        prompt: Union[str, Dict, List[Dict]] = "",
        **kwargs,
    ) -> Dict[str, float]:
        """
        计算奖励

        Args:
            completion: 任务输出（类型因任务而异）
            ground_truth: 正确答案/参考输出
            prompt: 任务提示
            **kwargs: 额外参数

        Returns:
            奖励字典
        """
        task_type = self.config.task_type

        if task_type == "gsm8k":
            # completion 是字符串
            return self.reward_fn.compute_reward(completion, ground_truth, prompt)

        elif task_type == "code_gen":
            # completion: 代码字符串, ground_truth: 测试结果, kwargs: perf_metrics
            test_results = (
                ground_truth
                if isinstance(ground_truth, dict)
                else kwargs.get("test_results", {})
            )
            perf_metrics = kwargs.get("perf_metrics", {"runtime_ms": 0, "memory_kb": 0})
            return self.reward_fn.compute_reward(
                completion, test_results, perf_metrics, prompt
            )

        elif task_type == "customer_support":
            # completion: 对话历史列表, ground_truth: 用户反馈, kwargs: response_time
            response_time = kwargs.get("response_time", 0.0)
            return self.reward_fn.compute_reward(
                completion, ground_truth, response_time, prompt
            )

        elif task_type == "game_ai":
            # completion: episode_result, ground_truth: action_history, kwargs: opponent_results
            action_history = (
                ground_truth
                if isinstance(ground_truth, list)
                else kwargs.get("action_history", [])
            )
            opponent_results = kwargs.get("opponent_results")
            return self.reward_fn.compute_reward(
                completion, action_history, opponent_results, prompt
            )

        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def compute_batch(
        self,
        completions: Union[List[str], List[Dict], List[List[Dict]]],
        ground_truths: Union[List[str], List[Dict], List[List]],
        prompts: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Dict[str, float]]:
        """批量计算奖励"""
        task_type = self.config.task_type

        if task_type == "gsm8k":
            return self.reward_fn.compute_batch(completions, ground_truths, prompts)

        elif task_type == "code_gen":
            test_results_list = kwargs.get("test_results_list", [{}] * len(completions))
            perf_metrics_list = kwargs.get(
                "perf_metrics_list",
                [{"runtime_ms": 0, "memory_kb": 0}] * len(completions),
            )
            return self.reward_fn.compute_batch(
                completions, test_results_list, perf_metrics_list, prompts
            )

        elif task_type == "customer_support":
            user_feedbacks = kwargs.get("user_feedbacks")
            response_times = kwargs.get("response_times", [0.0] * len(completions))
            return self.reward_fn.compute_batch(
                completions, user_feedbacks, response_times, prompts
            )

        elif task_type == "game_ai":
            action_histories = kwargs.get("action_histories", [[]] * len(completions))
            opponent_results_list = kwargs.get("opponent_results_list")
            return self.reward_fn.compute_batch(
                completions, action_histories, opponent_results_list, prompts
            )

        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def set_task_type(self, task_type: str):
        """切换任务类型"""
        self.config.task_type = task_type
        self._init_task_functions()


def example_usage():
    """使用示例"""
    print("=" * 60)
    print("统一奖励函数测试")
    print("=" * 60)

    # 1. GSM8K 数学任务
    print("\n[1] GSM8K 数学任务")
    gsm8k_config = UnifiedRewardConfig(task_type="gsm8k")
    gsm8k_reward = UnifiedRewardFunction(gsm8k_config)

    completion = "Step 1: 48 + 24 = 72\nStep 2: Final Answer: 72"
    ground_truth = "72"
    r = gsm8k_reward.compute_reward(completion, ground_truth)
    print(
        f"  奖励: total={r['total']:.3f}, acc={r['accuracy']:.3f}, reasoning={r['reasoning']:.3f}"
    )

    # 2. 代码生成任务
    print("\n[2] 代码生成任务")
    code_config = UnifiedRewardConfig(task_type="code_gen")
    code_reward = UnifiedRewardFunction(code_config)

    code = "def add(a, b):\n    return a + b"
    test_results = {"passed": 5, "total": 5, "compile_error": False}
    perf = {"runtime_ms": 50, "memory_kb": 1024}
    r = code_reward.compute_reward(code, test_results, perf)
    print(
        f"  奖励: total={r['total']:.3f}, acc={r['accuracy']:.3f}, read={r['readability']:.3f}"
    )

    # 3. 客服对话任务
    print("\n[3] 客服对话任务")
    cs_config = UnifiedRewardConfig(task_type="customer_support")
    cs_reward = UnifiedRewardFunction(cs_config)

    conversation = [
        {"role": "user", "content": "我的订单在哪？"},
        {"role": "assistant", "content": "我帮您查一下"},
        {"role": "assistant", "content": "订单已发货，请问还有其他问题吗？"},
    ]
    user_feedback = {"solved": True, "rating": 5}
    r = cs_reward.compute_reward(conversation, user_feedback)
    print(
        f"  奖励: total={r['total']:.3f}, res={r['resolution']:.3f}, sat={r['satisfaction']:.3f}"
    )

    # 4. 游戏 AI 任务
    print("\n[4] 游戏 AI 任务")
    game_config = UnifiedRewardConfig(task_type="game_ai")
    game_reward = UnifiedRewardFunction(game_config)

    episode = {"win": True, "score": 100, "survival_time": 120}
    history = ["attack", "defend", "move", "attack", "defend"]
    opponent_results = [{"win": True}, {"win": True}, {"win": False}]
    r = game_reward.compute_reward(episode, history, opponent_results=opponent_results)
    print(
        f"  奖励: total={r['total']:.3f}, win={r['win']:.3f}, div={r['diversity']:.3f}"
    )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    example_usage()
