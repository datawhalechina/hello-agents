"""TransactionAgent: rule/memory-first categorization, LLM only for uncertainty."""

from __future__ import annotations

from typing import Iterable

from ..memory import SQLiteMemory
from ..models import Transaction
from ..tools.transaction_category import CATEGORIES, TransactionCategoryTool
from .runtime import HelloAgentsRuntime


class TransactionAgent:
    paradigm = "ReActAgent-style: inspect transaction → consult memory/rules → resolve only uncertainty"

    def __init__(self, memory: SQLiteMemory, runtime: HelloAgentsRuntime, tool: TransactionCategoryTool | None = None) -> None:
        self.memory = memory
        self.runtime = runtime
        self.tool = tool or TransactionCategoryTool()

    def run(self, transactions: Iterable[Transaction]) -> tuple[list[Transaction], dict]:
        resolved: list[Transaction] = []
        source_counts: dict[str, int] = {}
        for item in transactions:
            result = self.tool.classify(item, self.memory.get_merchant_category)
            if result.confidence < 0.5 and item.kind == "expense":
                llm_category = self.runtime.classify_uncertain(item.merchant, item.note, list(CATEGORIES))
                if llm_category:
                    result.category = llm_category
                    result.confidence = 0.6
                    result.source = "hello_agents_llm"
            item.category = result.category
            item.category_confidence = result.confidence
            source_counts[result.source] = source_counts.get(result.source, 0) + 1
            resolved.append(item)
        return resolved, {"agent": "TransactionAgent", "paradigm": self.paradigm, "classification_sources": source_counts}

    def correct_category(self, merchant: str, category: str) -> None:
        if category not in CATEGORIES:
            raise ValueError(f"不支持的分类: {category}")
        self.memory.set_merchant_category(merchant, category)
