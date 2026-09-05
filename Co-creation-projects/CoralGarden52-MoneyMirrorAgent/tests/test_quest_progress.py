from src.models import Quest, Transaction
from src.tools.quest_progress import QuestProgressTool


def test_category_budget_quest_uses_real_spending() -> None:
    transaction = Transaction("1", "2026-07-01T12:00", "电影院", 80, "expense", "娱乐")
    quest = Quest("q", "娱乐预算", "", "category_limit", 100, 0, "娱乐", 10)
    updated = QuestProgressTool().update(quest, [transaction], "2026-07")
    assert updated.progress == 20
    assert updated.status == "active"
