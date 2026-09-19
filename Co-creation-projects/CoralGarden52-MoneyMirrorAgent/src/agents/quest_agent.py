"""LLM-orchestrated, evidence-locked Money Quest generation.

The QuestAgent intentionally separates three concerns:

1. Python rules discover auditable behavioural signals from the imported bill.
2. The configured LLM selects and narrates an RPG-style Quest plan as JSON.
3. Python validates every LLM field and derives all targets, progress, EXP and
   completion states from the original tool output.

That boundary keeps the interaction playful without allowing a model to invent
money amounts, completion evidence, or unrelated content.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from ..memory import SQLiteMemory
from ..models import Achievement, Quest, Transaction
from ..tools.quest_progress import QuestProgressTool
from .runtime import HelloAgentsRuntime, LLMCallError


@dataclass(frozen=True, slots=True)
class _QuestBlueprint:
    """A Python-owned Quest contract exposed to the LLM as an eligible signal."""

    signal_id: str
    quest_id: str
    quest_type: str
    target: float
    unit: str
    exp_reward: int
    constraint: str
    evidence: str
    priority: str = "optional"

    def public_signal(self) -> dict[str, Any]:
        """Return only selection context, never authority over numeric outcomes."""
        return {
            "signal_id": self.signal_id,
            "priority": self.priority,
            "verified_observation": self.evidence,
            "locked_constraint": self.constraint,
            "completion_source": "Python QuestProgressTool" if self.quest_type not in {"subscription_review", "manual"} else "用户 CLI 确认后由 SQLite Memory 记录",
        }


@dataclass(frozen=True, slots=True)
class _QuestCandidate:
    """The small, non-numeric portion the LLM is allowed to author."""

    signal_id: str
    title: str
    narrative: str
    action_hint: str


class QuestAgent:
    """Turn deterministic behaviour signals into validated LLM-designed Quests."""

    paradigm = "规则发现真实信号 → PlanSolveAgent 动态编排 → Python 强校验与进度计算"
    _MAX_QUESTS = 5

    def __init__(self, memory: SQLiteMemory, runtime: HelloAgentsRuntime | None = None) -> None:
        self.memory = memory
        self.runtime = runtime
        self.progress_tool = QuestProgressTool()

    def run(
        self,
        transactions: Iterable[Transaction],
        month: str,
        summary: dict,
        categories: dict[str, float],
        patterns: dict,
        subscriptions: list[dict],
        budget: dict,
        goals: list[dict] | None = None,
    ) -> tuple[list[Quest], list[Achievement], dict, dict]:
        """Create Quest objects through the LLM selection + Python validation path.

        ``goals`` is intentionally passed as an already projected deterministic
        result; the LLM can prioritize a goal signal but cannot change its
        feasibility or monthly amount.
        """
        transactions = list(transactions)
        blueprints = self._discover_signals(summary, categories, patterns, subscriptions, budget, goals or [])
        candidates, validation = self._orchestrate_candidates(blueprints, month)
        quests = [self._materialize(candidate, blueprints[candidate.signal_id]) for candidate in candidates]
        quests = [self.progress_tool.update(quest, transactions, month) for quest in quests]
        self._restore_manual_completions(quests, month)
        for quest in quests:
            self.memory.save_quest(quest)

        gamification = self._gamification(quests, transactions, month)
        achievements = self._achievements(summary, patterns, quests, gamification)
        for achievement in achievements:
            if achievement.unlocked:
                self.memory.save_achievement(achievement.to_dict())

        trace = {
            "agent": "QuestAgent",
            "paradigm": self.paradigm,
            "tools": ["StatisticsTool", "BudgetCalculatorTool", "SubscriptionDetectorTool", "QuestProgressTool"],
            "signal_catalog": [blueprint.public_signal() for blueprint in blueprints.values()],
            "llm_orchestration": {
                "candidate_count": len(candidates),
                "accepted_signal_ids": [candidate.signal_id for candidate in candidates],
                "validation": validation,
                "numeric_authority": "Python only: target / progress / EXP / status are derived from locked blueprints and QuestProgressTool.",
            },
            "quest_evidence": [quest.evidence for quest in quests],
        }
        return quests, achievements, gamification, trace

    def _discover_signals(
        self,
        summary: dict,
        categories: dict[str, float],
        patterns: dict,
        subscriptions: list[dict],
        budget: dict,
        goals: list[dict],
    ) -> dict[str, _QuestBlueprint]:
        """Discover only reproducible signals; no model is involved here."""
        signals: dict[str, _QuestBlueprint] = {}
        late_night = patterns.get("late_night", {})
        frequent_small = patterns.get("frequent_small", {})
        weekend = patterns.get("weekend", {})
        payday = patterns.get("payday_window", {})

        if int(late_night.get("count", 0)) >= 2:
            signals["late_night"] = _QuestBlueprint(
                "late_night", "late_night_guard", "late_night_limit", 1.0, "笔", 80,
                "22:00 后支出最多 1 笔。",
                f"深夜消费 {int(late_night['count'])} 笔，合计 ¥{float(late_night.get('amount', 0)):.2f}。",
                "required",
            )
        if int(frequent_small.get("count", 0)) >= 6:
            signals["frequent_small"] = _QuestBlueprint(
                "frequent_small", "zero_spend_scout", "zero_spend_days", 2.0, "天", 100,
                "在当前分析区间内完成 2 个无支出日。",
                f"发现 {int(frequent_small['count'])} 笔不高于 ¥50 的高频小额支出，合计 ¥{float(frequent_small.get('amount', 0)):.2f}。",
                "required",
            )

        flexible_categories = [category for category in ("娱乐", "购物") if float(categories.get(category, 0)) > 0]
        if flexible_categories:
            category = max(flexible_categories, key=lambda item: float(categories[item]))
            recommended = float(budget.get("categories", {}).get(category, {}).get("recommended", categories[category]))
            signals["flexible_budget"] = _QuestBlueprint(
                "flexible_budget", f"{category}_budget", "category_limit", recommended, category, 120,
                f"{category}支出不高于已核验的动态预算 ¥{recommended:.2f}。",
                f"{category}本月已支出 ¥{float(categories[category]):.2f}；动态预算为 ¥{recommended:.2f}。",
                "required",
            )
        if subscriptions:
            review_count = float(min(3, len(subscriptions)))
            signals["subscriptions"] = _QuestBlueprint(
                "subscriptions", "subscription_hunter", "subscription_review", review_count, "项", 90,
                f"检查 {int(review_count)} 项疑似连续扣费，并仅保留仍会使用的服务。",
                f"发现 {len(subscriptions)} 项疑似连续扣费。",
                "required",
            )
        if int(weekend.get("count", 0)) >= 3 and float(weekend.get("share", 0)) >= 30:
            target = round(max(1.0, float(weekend.get("amount", 0)) * 0.85), 2)
            signals["weekend"] = _QuestBlueprint(
                "weekend", "weekend_wallet_shield", "weekend_spend_limit", target, "元", 110,
                f"周末支出不高于已核验的温和目标 ¥{target:.2f}。",
                f"周末消费 {int(weekend['count'])} 笔，占本月支出 {float(weekend['share']):.2f}%。",
            )
        if int(payday.get("count", 0)) >= 3 and float(payday.get("share", 0)) >= 25:
            target = round(max(1.0, float(payday.get("amount", 0)) * 0.85), 2)
            signals["payday"] = _QuestBlueprint(
                "payday", "payday_cooldown", "payday_window_limit", target, "元", 110,
                f"工资到账后 3 天内支出不高于已核验的温和目标 ¥{target:.2f}。",
                f"工资到账后 3 天内发生 {int(payday['count'])} 笔支出，占本月支出 {float(payday['share']):.2f}%。",
            )
        learning = float(categories.get("学习", 0))
        expense = max(float(summary.get("expense", 0)), 1.0)
        if learning >= 100 and learning / expense >= 0.08:
            signals["learning_followthrough"] = _QuestBlueprint(
                "learning_followthrough", "learning_loot_log", "manual", 1.0, "次", 70,
                "记录 1 次学习服务是否真正被使用，并标注下次使用时间。",
                f"学习类支出为 ¥{learning:.2f}，占本月支出 {learning / expense * 100:.2f}%。",
            )
        actionable_goals = [goal for goal in goals if goal.get("feasible") and float(goal.get("required_monthly_amount", 0)) > 0]
        if actionable_goals and float(summary.get("balance", 0)) > 0:
            goal = min(actionable_goals, key=lambda item: float(item.get("required_monthly_amount", 0)))
            signals["goal_transfer"] = _QuestBlueprint(
                "goal_transfer", "goal_supply_line", "manual", 1.0, "次", 75,
                "确认 1 次本月结余如何服务于已设置的财务目标。",
                f"目标“{goal.get('title', '储蓄目标')}”每月仍需约 ¥{float(goal['required_monthly_amount']):.2f}；本月结余 ¥{float(summary.get('balance', 0)):.2f}。",
            )
        if not signals:
            signals["balance"] = _QuestBlueprint(
                "balance", "balance_builder", "manual", 1.0, "次", 60,
                "记录 1 次消费决策，并确认它是否服务于你的目标。",
                "尚未发现需要优先处理的高强度消费信号，适合建立一条自己的决策记录。",
                "required",
            )
        return signals

    def _orchestrate_candidates(
        self,
        blueprints: dict[str, _QuestBlueprint],
        month: str,
    ) -> tuple[list[_QuestCandidate], dict[str, Any]]:
        if self.runtime is None or not self.runtime.status.enabled:
            raise LLMCallError("Quest 动态编排必须使用已配置的 LLM，当前运行时不可用。")
        catalog = [blueprint.public_signal() for blueprint in blueprints.values()]
        prompt = (
            "你是 MoneyMirrorAgent 的 Quest 编排师。根据 Python 已核验的行为信号，为年轻用户选择并命名个性化 RPG Quest。"
            "这是严格的 JSON 协议：你只负责选择信号、标题、氛围叙述和一条可执行提示；不得创造金额、次数、日期、完成状态、EXP 或新的 signal_id。"
            "必须包含全部 priority=required 的信号；optional 信号可按相关性最多选 2 个；总数不超过 5。"
            "title 为 4-18 个中文字符、无数字；narrative 与 action_hint 各 8-90 字、无数字/金额/百分比，语气友好、轻松、不羞辱。"
            "只输出一个 JSON 对象，禁止 Markdown 代码块和任何解释，格式严格如下：\n"
            '{"quests":[{"signal_id":"...","title":"...","narrative":"...","action_hint":"..."}]}\n'
            f"分析月份：{month}\nSIGNAL_CATALOG_JSON:\n{json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))}"
        )
        first = self.runtime.generate_quest_candidates(prompt)
        candidates, problems = self._parse_and_validate_candidates(first, blueprints)
        if candidates:
            return candidates, {"attempts": 1, "repaired": False, "rejected": problems}

        repair_prompt = (
            "你的上一条 Quest JSON 未通过 Python 强校验。请立刻仅输出一个非空 JSON 对象，不要解释、不要 Markdown。"
            "字段必须严格为 {\"quests\":[{\"signal_id\":\"...\",\"title\":\"...\",\"narrative\":\"...\",\"action_hint\":\"...\"}]}。"
            "只可使用目录中的 signal_id，必须包含全部 priority=required 信号；不得出现金额、数字、日期、EXP、进度或完成状态。"
            f"校验问题：{'；'.join(problems[:6])}\n"
            f"允许信号：{', '.join(blueprints)}。必须包含：{', '.join(item.signal_id for item in blueprints.values() if item.priority == 'required')}。\n"
            f"SIGNAL_CATALOG_JSON:\n{json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))}"
        )
        repaired = self.runtime.generate_quest_candidates(repair_prompt)
        candidates, repair_problems = self._parse_and_validate_candidates(repaired, blueprints)
        if not candidates:
            details = "；".join(repair_problems[:8]) or "LLM 未返回可验证的 Quest JSON"
            raise LLMCallError(f"Quest 动态编排输出未通过 Python 强校验：{details}")
        return candidates, {"attempts": 2, "repaired": True, "rejected": problems, "repair_rejected": repair_problems}

    def _parse_and_validate_candidates(
        self,
        raw: str,
        blueprints: dict[str, _QuestBlueprint],
    ) -> tuple[list[_QuestCandidate], list[str]]:
        problems: list[str] = []
        try:
            payload = self._extract_json(raw)
        except ValueError as exc:
            return [], [str(exc)]
        rows = payload.get("quests") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            return [], ["根对象必须含有非空 quests 数组"]
        if len(rows) > self._MAX_QUESTS:
            return [], [f"Quest 数量超过上限 {self._MAX_QUESTS}"]

        candidates: list[_QuestCandidate] = []
        seen: set[str] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                problems.append(f"quests[{index}] 不是对象")
                continue
            required_keys = {"signal_id", "title", "narrative", "action_hint"}
            if set(row) != required_keys:
                problems.append(f"quests[{index}] 字段必须严格为 {sorted(required_keys)}")
                continue
            signal_id = str(row["signal_id"]).strip()
            if signal_id not in blueprints:
                problems.append(f"不允许的 signal_id：{signal_id}")
                continue
            if signal_id in seen:
                problems.append(f"signal_id 重复：{signal_id}")
                continue
            title = self._clean_copy(row["title"])
            narrative = self._clean_copy(row["narrative"])
            action_hint = self._clean_copy(row["action_hint"])
            if not (4 <= len(title) <= 18):
                problems.append(f"{signal_id} 的 title 长度不在 4-18")
                continue
            if not (8 <= len(narrative) <= 90 and 8 <= len(action_hint) <= 90):
                problems.append(f"{signal_id} 的 narrative/action_hint 长度不在 8-90")
                continue
            unsafe = self._unsafe_copy(title) or self._unsafe_copy(narrative) or self._unsafe_copy(action_hint)
            if unsafe:
                problems.append(f"{signal_id} 文案包含不允许内容：{unsafe}")
                continue
            seen.add(signal_id)
            candidates.append(_QuestCandidate(signal_id, title, narrative, action_hint))

        required = {item.signal_id for item in blueprints.values() if item.priority == "required"}
        missing = sorted(required - seen)
        if missing:
            problems.append(f"缺少 required 信号：{', '.join(missing)}")
        if problems or not candidates:
            return [], problems
        return candidates, []

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        text = str(raw).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("LLM 没有返回可解析的 Quest JSON") from None
            try:
                parsed = json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"LLM Quest JSON 格式错误：{exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM Quest JSON 根节点必须是对象")
        return parsed

    @staticmethod
    def _clean_copy(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value).strip())

    def _unsafe_copy(self, text: str) -> str | None:
        # Amounts, percentages, and Arabic-number commitments are prohibited
        # in model copy. Natural Chinese wording such as “每一笔” is allowed as
        # flavour only: it cannot alter the separately appended Python-owned
        # target, progress, EXP, status, or evidence.
        if any(character.isdigit() for character in text) or any(token in text for token in ("¥", "元", "%")):
            return "金额、百分比或阿拉伯数字只能由 Python 写入锁定约束"
        return None

    @staticmethod
    def _materialize(candidate: _QuestCandidate, blueprint: _QuestBlueprint) -> Quest:
        description = (
            f"{candidate.narrative}\n"
            f"🧩 小提示：{candidate.action_hint}\n"
            f"🎯 已核验目标：{blueprint.constraint}"
        )
        return Quest(
            blueprint.quest_id,
            candidate.title,
            description,
            blueprint.quest_type,
            blueprint.target,
            0,
            blueprint.unit,
            blueprint.exp_reward,
        )

    def _restore_manual_completions(self, quests: list[Quest], month: str) -> None:
        """Restore only CLI-confirmable outcomes from month-scoped Memory."""
        manually_completed = set(self.memory.get_preference(f"manual_completed_quests:{month}", []))
        for quest in quests:
            if quest.quest_id in manually_completed and quest.quest_type in {"subscription_review", "manual"}:
                quest.progress = quest.target
                quest.status = "completed"
                quest.evidence = f"用户已在 CLI 中确认完成（{month}）"

    def complete_manual_quest(self, quest: Quest, month: str, note: str = "") -> dict:
        """Record a user-confirmed Quest only where transactions cannot prove it."""
        if quest.quest_type not in {"subscription_review", "manual"}:
            raise ValueError(f"{quest.title} 的进度由账单自动计算，不能手动完成。")
        quest.progress = quest.target
        quest.status = "completed"
        detail = note.strip() or "用户已在 CLI 中确认完成"
        quest.evidence = f"{detail}（{month}）"
        self.memory.save_quest(quest)
        manual_key = f"manual_completed_quests:{month}"
        manual_completed = set(self.memory.get_preference(manual_key, []))
        manual_completed.add(quest.quest_id)
        self.memory.set_preference(manual_key, sorted(manual_completed))

        completed_ids = set(self.memory.get_preference("completed_quest_ids", []))
        gained_exp = 0
        if quest.quest_id not in completed_ids:
            completed_ids.add(quest.quest_id)
            gained_exp = quest.exp_reward
            self.memory.set_preference("completed_quest_ids", sorted(completed_ids))
            self.memory.set_preference("total_exp", int(self.memory.get_preference("total_exp", 0)) + gained_exp)
        return {
            "gained_exp": gained_exp,
            "total_exp": int(self.memory.get_preference("total_exp", 0)),
            "level": 1 + int(self.memory.get_preference("total_exp", 0)) // 200,
        }

    def _gamification(self, quests: list[Quest], transactions: list[Transaction], month: str) -> dict:
        completed_ids = set(self.memory.get_preference("completed_quest_ids", []))
        new_completed = [quest for quest in quests if quest.status == "completed" and quest.quest_id not in completed_ids]
        completed_ids.update(quest.quest_id for quest in new_completed)
        total_exp = int(self.memory.get_preference("total_exp", 0)) + sum(quest.exp_reward for quest in new_completed)
        current_streak = self.progress_tool.max_zero_spend_streak(transactions, month)
        longest_streak = max(int(self.memory.get_preference("longest_streak_days", 0)), current_streak)
        self.memory.set_preference("completed_quest_ids", sorted(completed_ids))
        self.memory.set_preference("total_exp", total_exp)
        self.memory.set_preference("longest_streak_days", longest_streak)
        return {
            "level": 1 + total_exp // 200,
            "total_exp": total_exp,
            "exp_gained_this_cycle": sum(quest.exp_reward for quest in new_completed),
            "current_streak_days": current_streak,
            "longest_streak_days": longest_streak,
        }

    @staticmethod
    def _achievements(summary: dict, patterns: dict, quests: list[Quest], gamification: dict) -> list[Achievement]:
        return [
            Achievement("savings_rate_20", "储蓄率破 20%", "储蓄率首次达到或超过 20%。", summary.get("savings_rate", 0) >= 20),
            Achievement("zero_spend_start", "零消费日初体验", "完成至少一个零消费日。", any(item.quest_type == "zero_spend_days" and item.progress >= 1 for item in quests)),
            Achievement("quest_ready", "任务上线", "已生成基于真实账单的 Money Quest。", bool(quests)),
            Achievement("late_night_awareness", "深夜雷达启动", "已识别深夜消费行为并生成应对任务。", patterns["late_night"]["count"] > 0),
            Achievement("zero_spend_streak_3", "三日无消费连击", "连续 3 天没有支出记录。", gamification.get("longest_streak_days", 0) >= 3),
        ]
