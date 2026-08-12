"""
饮食推荐入口：阶段 2 默认使用多 Agent 流水线（Nutritionist / Coach / Habit）。
"""

from __future__ import annotations

from typing import Any, Dict

from memory.store import get_diet_run
from service.diet_pipeline import DietMultiAgentPipeline


class DietRecommendService:
    """对外稳定接口；实现细节见 `diet_pipeline.DietMultiAgentPipeline`。"""

    async def run(
        self,
        user_id: str,
        context: Dict[str, Any],
        *,
        replayed_from_run_id: str | None = None,
    ) -> Dict[str, Any]:
        pipeline = DietMultiAgentPipeline()
        return await pipeline.run(
            user_id, context, replayed_from_run_id=replayed_from_run_id
        )


async def replay_diet_run(original_run_id: str) -> Dict[str, Any]:
    """阶段 3：用历史 run 的 input 重跑流水线（新 run_id；溯源 replayed_from）。"""
    row = get_diet_run(original_run_id.strip())
    if not row or not isinstance(row.get("input"), dict):
        raise ValueError("diet run 不存在或缺少 input")
    svc = DietRecommendService()
    return await svc.run(
        row["user_id"],
        row["input"],
        replayed_from_run_id=original_run_id.strip(),
    )
