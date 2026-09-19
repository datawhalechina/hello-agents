"""MoneyMirrorCoordinator orchestrates specialized agents around deterministic tools."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..memory import SQLiteMemory
from ..models import AnalysisReport, Goal
from ..tools import BudgetCalculatorTool, CSVImportTool, StatisticsTool
from ..tools.anomaly_detection import AnomalyDetectionTool
from ..tools.goal_projection import GoalProjectionTool
from ..tools.hello_agents_registry import build_registry_functions
from ..tools.quest_progress import QuestProgressTool
from ..tools.subscription_detector import SubscriptionDetectorTool
from ..tools.transaction_category import TransactionCategoryTool
from .conversation_agent import ConversationAgent
from .goal_agent import GoalAgent
from .pattern_agent import PatternAgent
from .persona_agent import PersonaAgent
from .quest_agent import QuestAgent
from .reflection_agent import ReflectionAgent
from .runtime import HelloAgentsRuntime
from .transaction_agent import TransactionAgent


class MoneyMirrorCoordinator:
    """A multi-agent pipeline that keeps numeric work local and reproducible.

    Flow: CSV import → TransactionAgent → PatternAgent → PersonaAgent → GoalAgent
    → QuestAgent → ReflectionAgent. Each agent adds either planning, context, or
    interpretation; all calculation-heavy decisions come from explicit tools.
    """

    def __init__(
        self,
        db_path: str | Path = "outputs/moneymirror.db",
        user_id: str = "local_user",
        runtime: HelloAgentsRuntime | None = None,
    ) -> None:
        self.memory = SQLiteMemory(db_path, user_id)
        self.runtime = runtime or HelloAgentsRuntime()
        self.csv_import = CSVImportTool()
        self.statistics = StatisticsTool()
        self.budget_tool = BudgetCalculatorTool()
        self.transaction_agent = TransactionAgent(self.memory, self.runtime)
        self.conversation_agent = ConversationAgent(self.runtime)
        self.pattern_agent = PatternAgent(self.runtime)
        self.persona_agent = PersonaAgent(self.runtime)
        self.goal_agent = GoalAgent(self.memory, self.runtime)
        self.quest_agent = QuestAgent(self.memory, self.runtime)
        self.reflection_agent = ReflectionAgent(self.memory, self.runtime)
        # Expose the deterministic tools to an optional Hello-Agents ReAct
        # agent. The coordinator still invokes these tools directly, so an LLM
        # cannot alter financial arithmetic or bypass Memory precedence.
        self.runtime.register_tool_functions(build_registry_functions(
            self.csv_import,
            TransactionCategoryTool(),
            self.statistics,
            AnomalyDetectionTool(),
            self.budget_tool,
            GoalProjectionTool(),
            SubscriptionDetectorTool(),
            QuestProgressTool(),
            self.memory.get_merchant_category,
        ))

    def close(self) -> None:
        self.memory.close()

    def correct_merchant_category(self, merchant: str, category: str) -> None:
        """Persist a user correction so identical merchants use Memory next time."""
        self.transaction_agent.correct_category(merchant, category)

    def add_goal(self, goal: Goal) -> None:
        self.memory.save_goal(goal)

    def complete_quest(self, report: AnalysisReport, quest_id: str, note: str = "") -> dict:
        """Persist a user-confirmed non-transactional Quest from the CLI."""
        quest = next((item for item in report.quests if item.quest_id == quest_id), None)
        if quest is None:
            available = ", ".join(item.quest_id for item in report.quests)
            raise ValueError(f"未找到 Quest：{quest_id}。可用 Quest ID：{available}")
        result = self.quest_agent.complete_manual_quest(quest, report.month, note)
        report.gamification["total_exp"] = result["total_exp"]
        report.gamification["exp_gained_this_cycle"] = report.gamification.get("exp_gained_this_cycle", 0) + result["gained_exp"]
        report.gamification["level"] = result["level"]
        return result

    def analyze_csv(self, csv_path: str | Path, month: str | None = None) -> AnalysisReport:
        imported = self.csv_import.load(csv_path)
        return self.analyze_transactions(imported, month, import_errors=self.csv_import.last_errors)

    def analyze_transactions(
        self,
        imported: list,
        month: str | None = None,
        import_errors: list[str] | None = None,
    ) -> AnalysisReport:
        transactions, transaction_trace = self.transaction_agent.run(imported)
        if import_errors:
            transaction_trace["csv_import_warnings"] = list(import_errors)
        months = self.statistics.month_keys(transactions)
        if not months:
            raise ValueError("没有可用于分析的交易记录")
        active_month = month or months[-1]
        if active_month not in months:
            raise ValueError(f"账单中不存在月份 {active_month}")
        summary = self.statistics.summarize(transactions, active_month)
        categories = self.statistics.category_breakdown(transactions, active_month)
        trends = self.statistics.trends(transactions, active_month)
        patterns, anomalies, subscriptions, pattern_trace = self.pattern_agent.run(transactions, active_month)
        budget = self.budget_tool.calculate(transactions, active_month)
        self.memory.save_budget(active_month, budget)
        persona, persona_trace = self.persona_agent.run(summary, categories, patterns, subscriptions, transactions)
        goals, goal_trace = self.goal_agent.run(transactions, active_month)
        quests, achievements, gamification, quest_trace = self.quest_agent.run(
            transactions, active_month, summary, categories, patterns, subscriptions, budget, goals
        )

        # Create a historical baseline snapshot before reflecting on the latest month.
        previous_month = self.reflection_agent._previous_month(active_month)
        if previous_month in months and not self.memory.get_snapshot(previous_month):
            previous_summary = self.statistics.summarize(transactions, previous_month)
            previous_categories = self.statistics.category_breakdown(transactions, previous_month)
            self.memory.save_snapshot(previous_month, {"summary": previous_summary, "category_breakdown": previous_categories, "source": "auto_baseline"})

        reflection, reflection_trace = self.reflection_agent.run(active_month, summary, categories, budget, quests, goals)
        report = AnalysisReport(
            user_id=self.memory.user_id,
            month=active_month,
            transactions=transactions,
            summary=summary,
            category_breakdown=categories,
            trends=trends,
            patterns=patterns,
            anomalies=anomalies,
            subscriptions=subscriptions,
            persona=persona,
            budget=budget,
            goals=goals,
            quests=quests,
            achievements=achievements,
            gamification=gamification,
            reflection=reflection,
            agent_trace=[
                {"agent": "MoneyMirrorCoordinator", "architecture": "Transaction → Pattern → Persona → Goal → Quest → Reflection", "runtime": self.runtime.status_dict()},
                transaction_trace,
                pattern_trace,
                persona_trace,
                goal_trace,
                quest_trace,
                reflection_trace,
            ],
        )
        self.memory.save_snapshot(active_month, {"summary": summary, "category_breakdown": categories, "persona": persona, "budget": budget, "goal_projections": goals, "quest_completion": reflection["quest_completion"], "reflection": reflection})
        return report

    @staticmethod
    def _output_stem(source_csv: str | Path | None) -> str:
        """Build a readable, filesystem-safe report stem from the input CSV."""
        if source_csv is None:
            return "money_mirror_report"
        stem = Path(source_csv).stem.strip()
        safe_stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._")
        return f"{safe_stem or 'transactions'}_money_mirror_report"

    def write_outputs(
        self,
        report: AnalysisReport,
        output_dir: str | Path = "outputs",
        conversation: list[dict[str, str]] | None = None,
        source_csv: str | Path | None = None,
    ) -> tuple[Path, Path]:
        """Persist JSON facts and an LLM-authored Markdown report.

        The Markdown file is intentionally generated only here, after the
        user finishes the guided conversation. There is no local template
        fallback: a report is never presented as LLM-generated unless the
        configured Hello-Agents model actually returned it.
        """
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        output_stem = self._output_stem(source_csv)
        json_path = directory / f"{output_stem}.json"
        markdown_path = directory / f"{output_stem}.md"
        # Keep the persisted JSON complete for auditability, but send only a
        # compact verified presentation packet to the LLM. Raw transactions and
        # agent traces are not needed for narrative generation and can crowd out
        # the facts the model must cite.
        payload = report.to_dict()
        if conversation:
            payload["guided_conversation"] = self.conversation_agent.compact_conversation(conversation)
            self.memory.set_preference("last_guided_conversation", payload["guided_conversation"])
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown = self.runtime.generate_markdown(
            self.conversation_agent.payload(report, conversation)
        )
        markdown_path.write_text(markdown, encoding="utf-8")
        return json_path, markdown_path
