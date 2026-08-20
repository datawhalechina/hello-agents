from src.memory import SQLiteMemory
from src.models import Transaction
from src.tools.transaction_category import TransactionCategoryTool


def test_manual_category_correction_overrides_rule() -> None:
    memory = SQLiteMemory(":memory:")
    try:
        memory.set_merchant_category("星巴克", "学习")
        transaction = Transaction("id", "2026-07-01T09:00", "星巴克", 35, "expense")
        result = TransactionCategoryTool().classify(transaction, memory.get_merchant_category)
        assert result.category == "学习"
        assert result.source == "memory"
    finally:
        memory.close()
