from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class MoneyValue:
    amount: str
    currency: str = "CNY"


@dataclass(slots=True)
class SourceCell:
    sheet: str
    row: int
    column: int
    header: str | None
    raw_value: Any


@dataclass(slots=True)
class VoucherRecord:
    record_id: str
    source_file: str
    source_sheet: str
    source_row: int
    voucher_date: str | None
    voucher_no: str | None
    summary: str | None
    income_amount: MoneyValue | None
    expense_amount: MoneyValue | None
    signed_amount: MoneyValue | None
    direction: str | None
    budget_category_code: str | None
    budget_category_name: str | None
    project_code: str | None
    project_fund_no: str | None
    fund_owner: str | None
    bank_receipt_reference_numbers: list[str] = field(default_factory=list)
    attachment_note: str | None = None
    source_cells: dict[str, SourceCell] = field(default_factory=dict)
    raw_row: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_debug_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return _json_ready(payload)

    def to_agent_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "voucher_date": self.voucher_date,
            "voucher_no": self.voucher_no,
            "summary": self.summary,
            "expense_amount": _money_amount(self.expense_amount),
            "budget_category_name": self.budget_category_name,
            "project_code": self.project_code,
            "project_fund_no": self.project_fund_no,
            "fund_owner": self.fund_owner,
            "parse_warnings": self.warnings,
        }


def decimal_to_money(value: Decimal | None) -> MoneyValue | None:
    if value is None:
        return None
    return MoneyValue(amount=f"{value.quantize(Decimal('0.01'))}")


def _money_amount(value: MoneyValue | None) -> str | None:
    return value.amount if value else None


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    return value
