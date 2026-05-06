"""课程学习系统 - 动态难度适配器

根据智能体的实时表现动态调整任务难度。
维持目标成功率在 60% 左右，避免过难或过易。
"""

from __future__ import annotations

from typing import List, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class DifficultyConfig:
    """难度适配配置"""

    target_success_rate: float = 0.60
    """目标成功率"""
    adjustment_rate: float = 0.05
    """每次调整幅度"""
    min_difficulty: float = 0.0
    """最低难度"""
    max_difficulty: float = 1.0
    """最高难度"""
    window_size: int = 20
    """滑动窗口大小"""
    warmup_steps: int = 10
    """预热步数（期间不调整）"""


class DifficultyAdapter:
    """动态难度适配器

    工作原理：
    1. 维护一个滑动窗口，记录最近 N 次任务的成功/失败
    2. 计算窗口内的成功率
    3. 如果成功率 > 目标，增加难度；< 目标，降低难度
    4. 梯度调整，避免剧烈波动
    """

    def __init__(self, config: Optional[DifficultyConfig] = None):
        self.config = config or DifficultyConfig()
        self._window: deque = deque(maxlen=self.config.window_size)
        self._current_difficulty = 0.5
        self._step = 0

    def record_result(self, success: bool, difficulty: float):
        """记录一次任务结果"""
        self._window.append((success, difficulty))
        self._step += 1

    def get_adjusted_difficulty(self) -> float:
        """获取调整后的难度

        Returns:
            调整后的难度值 0.0~1.0
        """
        if self._step < self.config.warmup_steps:
            return self._current_difficulty

        recent = list(self._window)
        if len(recent) < 5:
            return self._current_difficulty

        # 计算滑动窗口内的成功率
        success_count = sum(1 for s, _ in recent)
        success_rate = success_count / len(recent)

        # 计算需要调整的方向和幅度
        gap = success_rate - self.config.target_success_rate
        adjustment = gap * self.config.adjustment_rate * 2

        # 应用调整
        self._current_difficulty = max(
            self.config.min_difficulty,
            min(
                self.config.max_difficulty,
                self._current_difficulty + adjustment,
            ),
        )

        return self._current_difficulty

    def get_success_rate(self) -> float:
        """获取当前窗口内的成功率"""
        if not self._window:
            return 0.0
        success_count = sum(1 for s, _ in self._window)
        return success_count / len(self._window)

    def get_adjustment_history(self) -> List[float]:
        """获取难度调整历史"""
        return [d for _, d in list(self._window)]

    def reset(self):
        """重置适配器状态"""
        self._window.clear()
        self._current_difficulty = 0.5
        self._step = 0
