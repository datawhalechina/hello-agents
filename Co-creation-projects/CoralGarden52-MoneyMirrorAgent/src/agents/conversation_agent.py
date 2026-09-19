"""Stateful guided conversation before the final report is generated."""

from __future__ import annotations

import json
from typing import Any, Iterable

from .runtime import HelloAgentsRuntime


class ConversationAgent:
    """Turn a static analysis into a step-by-step financial coaching session.

    The conversation deliberately receives a *presentation payload*, not the
    complete ``AnalysisReport``.  Transactions and agent traces are useful for
    local debugging, but sending them on every turn makes the LLM context noisy
    and can hide the verified facts that the coach must use.
    """

    paradigm = "Interactive Hello-Agents coaching: observe → suggest → ask → reflect"
    MAX_HISTORY_ITEMS = 6
    MAX_MESSAGE_CHARS = 600
    MAX_ANOMALIES = 6
    MAX_QUESTS = 6
    MAX_SUBSCRIPTIONS = 8

    def __init__(self, runtime: HelloAgentsRuntime) -> None:
        self.runtime = runtime

    @classmethod
    def compact_report(cls, report: Any, conversation: Iterable[dict[str, str]] | None = None) -> dict[str, Any]:
        """Create the small, verified fact packet used by conversational LLM calls.

        Numeric values are copied from deterministic tools; this method only
        removes high-volume detail and never calculates a replacement number.
        In particular, raw transactions and ``agent_trace`` are intentionally
        excluded from prompts to avoid context truncation and accidental model
        hallucinations.
        """
        category_breakdown = dict(getattr(report, "category_breakdown", {}) or {})
        # Keep all categories: the demo has only a small fixed category set and
        # the user should be able to ask about any one of them.
        trends = dict(getattr(report, "trends", {}) or {})
        trend_summary: dict[str, Any] = {}
        for key in ("weekly", "monthly"):
            values = trends.get(key)
            if isinstance(values, dict):
                trend_summary[key] = values
        patterns = dict(getattr(report, "patterns", {}) or {})
        # These pattern objects are already compact deterministic summaries.
        selected_patterns = {
            key: patterns[key]
            for key in ("late_night", "weekend", "payday_window", "frequent_small", "category_spikes")
            if key in patterns
        }
        budget = getattr(report, "budget", {}) or {}
        compact_budget = dict(budget)
        if isinstance(budget, dict) and isinstance(budget.get("categories"), dict):
            compact_budget["categories"] = budget["categories"]

        def item_dict(item: Any) -> dict[str, Any]:
            if hasattr(item, "to_dict"):
                return item.to_dict()
            return dict(item) if isinstance(item, dict) else {"value": str(item)}

        compact: dict[str, Any] = {
            "month": getattr(report, "month", ""),
            "summary": getattr(report, "summary", {}) or {},
            "category_breakdown": category_breakdown,
            "trends": trend_summary,
            "patterns": selected_patterns,
            "anomalies": [item_dict(item) for item in list(getattr(report, "anomalies", []) or [])[: cls.MAX_ANOMALIES]],
            "subscriptions": list(getattr(report, "subscriptions", []) or [])[: cls.MAX_SUBSCRIPTIONS],
            "persona": getattr(report, "persona", {}) or {},
            "budget": compact_budget,
            "goals": list(getattr(report, "goals", []) or []),
            "quests": [item_dict(item) for item in list(getattr(report, "quests", []) or [])[: cls.MAX_QUESTS]],
            "achievements": [item_dict(item) for item in list(getattr(report, "achievements", []) or [])],
            "gamification": getattr(report, "gamification", {}) or {},
            "reflection": getattr(report, "reflection", {}) or {},
        }
        if conversation:
            compact["guided_conversation"] = cls.compact_conversation(conversation)
        return compact

    @classmethod
    def compact_conversation(cls, conversation: Iterable[dict[str, str]]) -> list[dict[str, str]]:
        """Keep the most recent dialogue turns within a predictable size."""
        items = list(conversation)[-cls.MAX_HISTORY_ITEMS :]
        result: list[dict[str, str]] = []
        for item in items:
            content = str(item.get("content", "")).strip()
            if len(content) > cls.MAX_MESSAGE_CHARS:
                content = content[: cls.MAX_MESSAGE_CHARS].rstrip() + "…"
            result.append({"role": str(item.get("role", "user")), "content": content})
        return result

    @classmethod
    def payload(cls, report: Any, conversation: Iterable[dict[str, str]] | None = None) -> str:
        """Serialize a compact packet with an explicit verified-facts marker."""
        return json.dumps(
            {"[Verified tool output]": cls.compact_report(report, conversation)},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def opening(self, report: Any) -> str:
        compact = self.compact_report(report)
        summary = compact.get("summary", {})
        patterns = compact.get("patterns", {})
        persona = compact.get("persona", {})
        focus = (
            f"当前分析月份={compact.get('month')}；收入={summary.get('income')}；"
            f"支出={summary.get('expense')}；结余={summary.get('balance')}；"
            f"储蓄率={summary.get('savings_rate')}%；消费人格={persona.get('primary')}；"
            f"深夜消费={patterns.get('late_night')}；周末消费={patterns.get('weekend')}。"
        )
        return self.runtime.explain(
            "为用户开启 MoneyMirror 的第一关引导，而不是生成报告。你必须使用下面这行已核验焦点中的至少一个真实数字，"
            "不能说‘没有数据’或要求用户重新上传账单。请严格按顺序输出："
            "(1) 用一个有趣的镜像/RPG昵称，引用真实消费现象；"
            "(2) 给一个今天就能完成、不会一刀切的微行动；"
            "(3) 只问一个选择题式追问，让用户选择最想先改善的消费场景。"
            "不要输出‘结论/依据/风险/下一步’的机械模板，不要生成最终 Markdown 报告，"
            "控制在 100-160 字，使用少量 emoji。\n"
            f"已核验焦点：{focus}",
            mode="simple",
            evidence=[self.payload(report)],
        )

    def respond(self, report: Any, question: str, history: Iterable[dict[str, str]]) -> str:
        """Non-streaming counterpart used by CLI and tests."""
        chunks = self.runtime.stream_user_guidance(question, self.payload(report), self.compact_conversation(history))
        return "".join(chunks).strip()
