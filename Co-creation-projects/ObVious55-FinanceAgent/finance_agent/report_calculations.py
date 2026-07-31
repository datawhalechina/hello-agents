from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from finance_agent.acceptance_rule_engine import money_str, parse_money
from finance_agent.report_models import ReportContext, SharedCalculatedContext


def build_shared_calculated_context(
    classification: dict[str, Any],
    records: list[dict[str, Any]],
    budget_payload: dict[str, Any] | None,
) -> SharedCalculatedContext:
    total_amount = sum_amount(records)
    category_summary = add_amount_ratios(classification.get("category_summary", []), total_amount)
    large_records = sorted(
        [record for record in records if record.get("is_large_voucher")],
        key=lambda item: parse_money(item["expense_amount"]),
        reverse=True,
    )
    return SharedCalculatedContext(
        records=records,
        budget_payload=budget_payload,
        total_amount=total_amount,
        category_summary=category_summary,
        project_summary=summarize_by(records, "project_code", total_amount),
        fund_destination_summary=summarize_fund_destination(records, total_amount),
        large_voucher_records=large_records,
    )


def require_shared_context(context: ReportContext) -> SharedCalculatedContext:
    if context.shared is None:
        raise RuntimeError("ReportContext.shared is required for parallel report pipeline execution.")
    return context.shared


def build_shared_input_summary(context: ReportContext) -> dict[str, Any]:
    shared = require_shared_context(context)
    return {
        "total_record_count": len(shared.records),
        "total_expense_amount": money_str(shared.total_amount),
        "top_categories": shared.category_summary[:5],
        "large_voucher_count": len(shared.large_voucher_records),
        "budget_baseline_available": shared.budget_payload is not None,
    }


def calculate_budget_variance(context: ReportContext) -> dict[str, Any]:
    if not context.budget_payload:
        return {
            "status": "budget_baseline_missing",
            "variance_available": False,
            "message": "当前输入 JSON 未包含预算批复数或预算调整数，不能计算预算执行率、预算差异额和差异率。",
            "required_budget_fields": [
                "budget_category_name",
                "approved_budget_amount",
                "adjusted_budget_amount(optional)",
            ],
        }

    budget_by_category = {
        item["budget_category_name"]: parse_money(item.get("adjusted_budget_amount") or item["approved_budget_amount"])
        for item in context.budget_payload.get("category_budgets", [])
    }
    actual_by_category = {
        item["budget_category_name"]: parse_money(item["expense_amount"])
        for item in context.classification.get("category_summary", [])
    }
    rows = []
    for category, budget_amount in sorted(budget_by_category.items()):
        actual_amount = actual_by_category.get(category, Decimal("0.00"))
        variance = budget_amount - actual_amount
        execution_rate = actual_amount / budget_amount if budget_amount else Decimal("0")
        rows.append(
            {
                "budget_category_name": category,
                "budget_amount": money_str(budget_amount),
                "actual_amount": money_str(actual_amount),
                "variance_amount": money_str(variance),
                "execution_rate": percent_str(execution_rate),
            }
        )
    return {
        "status": "ok",
        "variance_available": True,
        "category_variance": rows,
    }


def calculate_acceptance_review(context: ReportContext) -> dict[str, Any]:
    records = context.records
    required = [record for record in records if record.get("acceptance_required")]
    by_reason: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in required:
        for reason in record.get("requirement_reasons", []):
            by_reason[reason].append(record)

    missing_fund_info = [
        record
        for record in records
        if not record.get("project_fund_no") or not record.get("fund_owner")
    ]
    return {
        "policy_version": context.classification.get("policy_version"),
        "numeric_policy": context.classification.get("numeric_policy"),
        "acceptance_required_count": len(required),
        "acceptance_required_amount": money_str(sum_amount(required)),
        "large_voucher_records": by_reason.get("large_voucher_gte_threshold", []),
        "meeting_fee_required_records": by_reason.get("meeting_fee_all_required", []),
        "cost_type_sample_records": by_reason.get("cost_type_20pct_sample", []),
        "missing_fund_info_records": missing_fund_info,
        "preparation_checklist": [
            "大额凭证需准备合同或采购依据、发票、银行回单、验收或入库证明等材料。",
            "会议费类凭证需准备会议通知、签到表、会议议程、费用明细、发票和支付凭证等材料。",
            "20%抽样凭证需按费用类别补齐原始凭证、审批记录和支付证明。",
            "项目号、经费号或负责人缺失的记录需先完成台账复核。",
        ],
    }


def add_amount_ratios(rows: list[dict[str, Any]], total_amount: Decimal) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        amount = parse_money(row["expense_amount"])
        enriched = dict(row)
        enriched["amount_ratio"] = percent_str(amount / total_amount if total_amount else Decimal("0"))
        result.append(enriched)
    return sorted(result, key=lambda item: parse_money(item["expense_amount"]), reverse=True)


def summarize_by(records: list[dict[str, Any]], field: str, total_amount: Decimal) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record.get(field) or "未识别"].append(record)

    rows = []
    for key, group in grouped.items():
        amount = sum_amount(group)
        rows.append(
            {
                field: key,
                "record_count": len(group),
                "expense_amount": money_str(amount),
                "amount_ratio": percent_str(amount / total_amount if total_amount else Decimal("0")),
            }
        )
    return sorted(rows, key=lambda item: parse_money(item["expense_amount"]), reverse=True)


def summarize_fund_destination(records: list[dict[str, Any]], total_amount: Decimal) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (
            record.get("project_code") or "未识别项目号",
            record.get("project_fund_no") or "未识别经费号",
            record.get("fund_owner") or "未识别负责人",
        )
        grouped[key].append(record)

    rows = []
    for (project_code, project_fund_no, fund_owner), group in grouped.items():
        amount = sum_amount(group)
        rows.append(
            {
                "project_code": project_code,
                "project_fund_no": project_fund_no,
                "fund_owner": fund_owner,
                "record_count": len(group),
                "expense_amount": money_str(amount),
                "amount_ratio": percent_str(amount / total_amount if total_amount else Decimal("0")),
            }
        )
    return sorted(rows, key=lambda item: parse_money(item["expense_amount"]), reverse=True)


def build_expense_insights(category_summary: list[dict[str, Any]], large_records: list[dict[str, Any]]) -> list[str]:
    insights = []
    if category_summary:
        top = category_summary[0]
        insights.append(
            f"支出金额最高的费用类别为{top['budget_category_name']}，金额{top['expense_amount']}元，占比{top['amount_ratio']}。"
        )
    if large_records:
        insights.append(f"单笔5万元及以上大额凭证共{len(large_records)}笔，应作为验收材料复核重点。")
    return insights


def sum_amount(records: list[dict[str, Any]]) -> Decimal:
    return sum((parse_money(record.get("expense_amount")) for record in records), Decimal("0.00"))


def percent_str(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"
