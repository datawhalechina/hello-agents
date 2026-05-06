"""
代码生成助手奖励函数
用于 Agentic RL 训练
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CodeGenRewardConfig:
    """代码生成奖励配置"""

    # 正确性权重
    accuracy_weight: float = 0.5

    # 可读性权重
    readability_weight: float = 0.3

    # 效率权重
    efficiency_weight: float = 0.2

    # 编译通过基本奖励
    compile_success_reward: float = 0.5

    # 测试通过奖励
    test_success_reward: float = 0.5

    # 目标运行时间（毫秒）
    target_runtime: int = 1000

    # 最大允许运行时间（毫秒）
    max_runtime: int = 5000

    # 最小代码长度（防止空代码）
    min_code_length: int = 10


class CodeGenRewardFunction:
    """
    代码生成奖励函数

    设计思路:
    1. 正确性: 基于测试通过率和编译状态
    2. 可读性: 基于代码结构和注释
    3. 效率: 基于运行时间和内存使用
    """

    def __init__(self, config: Optional[CodeGenRewardConfig] = None):
        self.config = config or CodeGenRewardConfig()

    def compute_reward(
        self,
        generated_code: str,
        test_results: Dict,
        perf_metrics: Dict,
        prompt: str = "",
    ) -> Dict[str, float]:
        """
        计算代码生成奖励

        Args:
            generated_code: 生成的代码
            test_results: 测试结果 {'passed': int, 'total': int, 'compile_error': bool}
            perf_metrics: 性能指标 {'runtime_ms': float, 'memory_kb': float}
            prompt: 问题描述（可选）

        Returns:
            奖励字典
        """
        # 1. 计算正确性奖励
        accuracy_reward = self._compute_accuracy_reward(test_results)

        # 2. 计算可读性奖励
        readability_reward = self._compute_readability_reward(generated_code)

        # 3. 计算效率奖励
        efficiency_reward = self._compute_efficiency_reward(perf_metrics)

        # 4. 计算总奖励
        total_reward = (
            accuracy_reward * self.config.accuracy_weight
            + readability_reward * self.config.readability_weight
            + efficiency_reward * self.config.efficiency_weight
        )

        # 确保在 [0, 1] 范围内
        total_reward = max(0.0, min(1.0, total_reward))

        return {
            "total": total_reward,
            "accuracy": accuracy_reward,
            "readability": readability_reward,
            "efficiency": efficiency_reward,
        }

    def _compute_accuracy_reward(self, test_results: Dict) -> float:
        """计算正确性奖励"""
        # 编译失败
        if test_results.get("compile_error", False):
            return 0.0

        passed = test_results.get("passed", 0)
        total = test_results.get("total", 1)

        if total == 0:
            return 0.0

        test_pass_rate = passed / total

        # 组合编译奖励和测试奖励
        compile_reward = self.config.compile_success_reward
        test_reward = test_pass_rate * self.config.test_success_reward

        return compile_reward + test_reward

    def _compute_readability_reward(self, code: str) -> float:
        """计算可读性奖励"""
        if len(code) < self.config.min_code_length:
            return 0.0

        score = 0.0

        # 检查函数/类定义
        if re.search(r"(def|class|func|function)\s+\w+", code):
            score += 0.2

        # 检查注释
        comment_lines = len(re.findall(r'#.*$|"""[\s\S]*?"""', code, re.MULTILINE))
        if comment_lines > 0:
            score += min(0.3, comment_lines * 0.05)

        # 检查变量命名规范性（有意义的名字）
        meaningful_names = len(re.findall(r"\b[a-z_][a-z0-9_]{2,}\b", code))
        if meaningful_names > 3:
            score += 0.2

        # 检查缩进/格式
        if "    " in code or "\t" in code:
            score += 0.1

        # 检查空行（适当分隔）
        blank_lines = code.count("\n\n")
        if blank_lines > 0:
            score += 0.1

        return min(score, 1.0)

    def _compute_efficiency_reward(self, perf_metrics: Dict) -> float:
        """计算效率奖励"""
        runtime = perf_metrics.get("runtime_ms", 0)

        if runtime == 0:
            return 0.5  # 无测试数据时给中间分

        # 运行时间越短越好
        if runtime <= self.config.target_runtime:
            return 1.0
        elif runtime >= self.config.max_runtime:
            return 0.0
        else:
            # 线性惩罚
            ratio = (self.config.max_runtime - runtime) / (
                self.config.max_runtime - self.config.target_runtime
            )
            return max(0.0, ratio)

    def compute_batch(
        self,
        generated_codes: List[str],
        test_results_list: List[Dict],
        perf_metrics_list: List[Dict],
        prompts: Optional[List[str]] = None,
    ) -> List[Dict[str, float]]:
        """批量计算奖励"""
        if prompts is None:
            prompts = [""] * len(generated_codes)

        rewards = []
        for code, tests, perf in zip(
            generated_codes, test_results_list, perf_metrics_list
        ):
            rewards.append(self.compute_reward(code, tests, perf, ""))

        return rewards


def example_usage():
    """使用示例"""
    config = CodeGenRewardConfig()
    reward_fn = CodeGenRewardFunction(config)

    # 测试用例
    code_good = '''
def add(a, b):
    """Add two numbers"""
    return a + b
'''

    code_bad = """
def add(a,b):
return a+b
"""

    test_results_good = {"passed": 5, "total": 5, "compile_error": False}
    test_results_bad = {"passed": 2, "total": 5, "compile_error": False}

    perf_good = {"runtime_ms": 50, "memory_kb": 1024}
    perf_bad = {"runtime_ms": 3000, "memory_kb": 2048}

    print("=" * 50)
    print("代码生成奖励测试")
    print("=" * 50)

    # 好代码
    r = reward_fn.compute_reward(code_good, test_results_good, perf_good)
    print(
        f"好代码: total={r['total']:.3f}, acc={r['accuracy']:.3f}, read={r['readability']:.3f}, eff={r['efficiency']:.3f}"
    )

    # 差代码（测试失败）
    r = reward_fn.compute_reward(code_bad, test_results_bad, perf_good)
    print(
        f"差代码: total={r['total']:.3f}, acc={r['accuracy']:.3f}, read={r['readability']:.3f}, eff={r['efficiency']:.3f}"
    )

    # 慢代码（运行超时）
    r = reward_fn.compute_reward(code_good, test_results_good, perf_bad)
    print(
        f"慢代码: total={r['total']:.3f}, acc={r['accuracy']:.3f}, read={r['readability']:.3f}, eff={r['efficiency']:.3f}"
    )


if __name__ == "__main__":
    example_usage()
