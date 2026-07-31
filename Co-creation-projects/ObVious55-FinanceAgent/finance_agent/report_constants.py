from __future__ import annotations

from pathlib import Path

DEFAULT_CLASSIFICATION_INPUT = Path("data/processed/acceptance_classification.json")
DEFAULT_AGENT_OUTPUT = Path("data/processed/report_agent_outputs.json")
DEFAULT_AGENT_RUN_DIR = Path("data/processed/agent_runs")
DEFAULT_REPORT_OUTPUT = Path("data/reports/research_finance_acceptance_report.md")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_CALCULATED_DATA_KEYS: dict[str, set[str]] = {
    "ExpenseInsightAgent": {
        "total_record_count",
        "total_expense_amount",
        "category_summary",
        "project_summary",
        "fund_destination_summary",
        "large_voucher_records",
        "insights",
    },
    "BudgetVarianceAgent": {
        "status",
        "variance_available",
    },
    "AcceptanceReviewAgent": {
        "policy_version",
        "numeric_policy",
        "acceptance_required_count",
        "acceptance_required_amount",
        "large_voucher_records",
        "meeting_fee_required_records",
        "cost_type_sample_records",
        "missing_fund_info_records",
        "preparation_checklist",
    },
}


REQUIRED_ROW_KEYS: dict[tuple[str, str], set[str]] = {
    ("ExpenseInsightAgent", "category_summary"): {
        "budget_category_name",
        "record_count",
        "expense_amount",
        "amount_ratio",
        "large_voucher_count",
        "acceptance_required_count",
    },
    ("ExpenseInsightAgent", "fund_destination_summary"): {
        "project_code",
        "project_fund_no",
        "fund_owner",
        "record_count",
        "expense_amount",
        "amount_ratio",
    },
    ("BudgetVarianceAgent", "category_variance"): {
        "budget_category_name",
        "budget_amount",
        "actual_amount",
        "variance_amount",
        "execution_rate",
    },
}
