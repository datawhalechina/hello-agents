"""LLM test double: production has no offline route; tests avoid network calls."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable


@dataclass
class _Status:
    reason: str = "test Hello-Agents runtime"
    enabled: bool = True


class FakeRuntime:
    """Contract-level stand-in for HelloAgentsRuntime used only by unit tests."""

    def __init__(self) -> None:
        self.status = _Status()
        self.registered: tuple[str, ...] = ()

    def register_tool_functions(self, functions) -> None:
        self.registered = tuple(functions)

    def status_dict(self) -> dict:
        return {
            "available": True,
            "enabled": True,
            "reason": self.status.reason,
            "registry_name": "Fake ToolRegistry",
            "paradigms": ["ReActAgent", "PlanSolveAgent", "ReflectionAgent"],
            "registered_tools": list(self.registered),
        }

    def classify_uncertain(self, merchant: str, note: str, allowed_categories: list[str]) -> str:
        return "其他" if "其他" in allowed_categories else allowed_categories[0]

    @staticmethod
    def _quest_json(prompt: str) -> str:
        """Mirror only the strict JSON protocol, not production Quest logic."""
        marker = "SIGNAL_CATALOG_JSON:\n"
        catalog: list[dict] = []
        if marker in prompt:
            raw = prompt.split(marker, 1)[1]
            decoder = json.JSONDecoder()
            try:
                catalog, _ = decoder.raw_decode(raw.lstrip())
            except json.JSONDecodeError:
                catalog = []
        names = {
            "late_night": ("夜航冷静结界", "给深夜冲动留一段缓冲，不必用意志硬扛。", "先辨认触发场景，再为自己准备替代选项。"),
            "frequent_small": ("零钱能量巡逻", "把细碎消费当作线索，找回自己选择的节奏。", "出门前先想好今天最想守住的体验。"),
            "flexible_budget": ("弹性钱包护盾", "体验额度依然保留，只是让目标也拥有位置。", "付款前停一停，确认这次消费是否真的值得。"),
            "subscriptions": ("订阅遗迹寻宝", "把持续扣费翻出来，留下真正陪伴你的服务。", "从最近使用感受开始，逐项做一个保留决定。"),
            "weekend": ("周末钱包护盾", "周末可以尽兴，也可以留下一点可控的边界。", "安排活动前先选定最想投入的一件事。"),
            "payday": ("发薪冷静回合", "到账后的兴奋值得被看见，也值得多一点缓冲。", "先把想买的东西记下，稍后再决定是否结算。"),
            "learning_followthrough": ("学习战利品回访", "让学习消费继续产生陪伴感，而不只是一次付款。", "选一个最容易开始的学习入口，写下下次打开它的时机。"),
            "goal_transfer": ("目标补给路线", "让本月结余有一个温柔去处，持续靠近你的愿望。", "先确认最想推进的目标，再写下这次结余的安排。"),
            "balance": ("镜像决策日志", "消费没有标准答案，记录会帮你看见自己的偏好。", "挑一笔最近消费，写下它带来的真实感受。"),
        }
        quests = []
        for signal in catalog:
            signal_id = signal.get("signal_id")
            if signal_id in names:
                title, narrative, action_hint = names[signal_id]
                quests.append({"signal_id": signal_id, "title": title, "narrative": narrative, "action_hint": action_hint})
        return json.dumps({"quests": quests[:5]}, ensure_ascii=False)

    def explain(self, prompt: str, mode: str = "simple", evidence: Iterable[str] = (), memory: Iterable[str] = ()) -> str:
        if "SIGNAL_CATALOG_JSON:" in prompt or "Quest JSON" in prompt:
            return self._quest_json(prompt)
        if mode == "reflection":
            return "已根据验证的账单、预算和目标证据完成本轮反思；下一步选择一个低摩擦任务即可。"
        if mode == "plan":
            return "先阅读已验证的消费证据，再挑选一个能在本周完成的小行动。"
        return "这是一段基于已验证消费证据生成的 AI 引导文案。"

    def generate_quest_candidates(self, prompt: str) -> str:
        return self._quest_json(prompt)

    def generate_markdown(self, report_payload: str) -> str:
        return "# MoneyMirrorAgent 月度报告\n\n这是由测试 LLM 生成的 Markdown 报告。\n"

    def stream_user_guidance(self, question: str, report_payload: str, history):
        yield "🪞 先从一个小行动开始："
        yield "本周记录一次触发消费的场景，然后告诉我你的发现。"
