from __future__ import annotations

from copy import deepcopy
from typing import Any


_DEMO_RECORDS: list[dict[str, Any]] = [
    {
        "record_id": "DEMO-001",
        "voucher_date": "2026-01-08",
        "voucher_no": "DEMO-V-2026-001",
        "summary": "示例实验设备采购",
        "expense_amount": "68000.00",
        "budget_category_name": "设备费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-002",
        "voucher_date": "2026-01-15",
        "voucher_no": "DEMO-V-2026-002",
        "summary": "示例测试仪器采购",
        "expense_amount": "52000.00",
        "budget_category_name": "设备费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-003",
        "voucher_date": "2026-02-03",
        "voucher_no": "DEMO-V-2026-003",
        "summary": "示例实验耗材采购",
        "expense_amount": "36000.00",
        "budget_category_name": "材料费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-004",
        "voucher_date": "2026-02-18",
        "voucher_no": "DEMO-V-2026-004",
        "summary": "示例学术研讨会议支出",
        "expense_amount": "24500.00",
        "budget_category_name": "会议费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-005",
        "voucher_date": "2026-03-02",
        "voucher_no": "DEMO-V-2026-005",
        "summary": "示例调研差旅支出",
        "expense_amount": "18000.00",
        "budget_category_name": "差旅费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-006",
        "voucher_date": "2026-03-12",
        "voucher_no": "DEMO-V-2026-006",
        "summary": "示例专家咨询支出",
        "expense_amount": "9000.00",
        "budget_category_name": "专家咨询费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-007",
        "voucher_date": "2026-03-20",
        "voucher_no": "DEMO-V-2026-007",
        "summary": "示例小额耗材采购",
        "expense_amount": "6750.00",
        "budget_category_name": "材料费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
    {
        "record_id": "DEMO-008",
        "voucher_date": "2026-03-25",
        "voucher_no": "DEMO-V-2026-008",
        "summary": "示例市内交通支出",
        "expense_amount": "4500.00",
        "budget_category_name": "差旅费",
        "project_code": "DEMO-PROJECT-001",
        "project_fund_no": "DEMO-FUND-001",
        "fund_owner": "示例负责人",
        "parse_warnings": [],
    },
]


def build_demo_voucher_payload() -> dict[str, Any]:
    """Return deterministic, fully fictional vouchers for public demos and tests."""
    records = deepcopy(_DEMO_RECORDS)
    return {
        "schema": "SyntheticVoucherRecordCollection",
        "schema_version": "1.0",
        "generated_at": "2026-01-01T00:00:00",
        "source_document": "generated://synthetic_demo",
        "source_document_type": "generated",
        "record_count": len(records),
        "records": records,
        "privacy_notice": "All people, identifiers, descriptions, dates, and amounts are fictional demo data.",
    }
