from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


DEFAULT_POLICY = Path("config/demo_acceptance_policy.json")
DEFAULT_INPUT = Path("data/processed/voucher_records.json")
DEFAULT_OUTPUT = Path("data/processed/acceptance_classification.json")


def resolve_policy_path(project_root: Path | None = None) -> Path:
    """Resolve the public demo policy or an explicitly configured local policy."""
    configured = os.getenv("FINANCE_ACCEPTANCE_POLICY", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
    else:
        root = project_root or Path.cwd()
        path = (root / DEFAULT_POLICY).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Acceptance policy file not found: {path}")
    return path


def classify_vouchers(voucher_payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    records = voucher_payload.get("records", [])
    policy_version = policy["policy_version"]
    large_threshold = parse_money(policy["large_voucher"]["amount_gte"])
    sample_ratio = Decimal(str(policy["cost_type_sampling"]["sample_ratio"]))
    meeting_keywords = policy["meeting_fee"].get("category_keywords", [])

    enriched_records: list[dict[str, Any]] = []
    eligible_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, record in enumerate(records):
        amount = parse_money(record.get("expense_amount"))
        category = record.get("budget_category_name") or "未分类"
        is_large = policy["large_voucher"]["enabled"] and amount >= large_threshold
        is_meeting_fee = is_meeting_fee_record(category, meeting_keywords) if policy["meeting_fee"]["enabled"] else False

        classified = {
            "record_id": record.get("record_id"),
            "voucher_date": record.get("voucher_date"),
            "voucher_no": record.get("voucher_no"),
            "summary": record.get("summary"),
            "expense_amount": money_str(amount),
            "budget_category_name": category,
            "project_code": record.get("project_code"),
            "project_fund_no": record.get("project_fund_no"),
            "fund_owner": record.get("fund_owner"),
            "is_large_voucher": is_large,
            "is_meeting_fee_required": is_meeting_fee,
            "is_cost_type_sample": False,
            "acceptance_required": False,
            "requirement_reasons": [],
            "parse_warnings": record.get("parse_warnings", []),
            "_source_index": index,
            "_amount_decimal": amount,
        }

        if is_large and policy["acceptance_scope"]["include_large_vouchers"]:
            classified["requirement_reasons"].append("large_voucher_gte_threshold")
        if is_meeting_fee and policy["acceptance_scope"]["include_meeting_fee_records"]:
            classified["requirement_reasons"].append("meeting_fee_all_required")

        exclude_meeting = policy["cost_type_sampling"].get("exclude_meeting_fee_records", True)
        if not (exclude_meeting and is_meeting_fee):
            eligible_by_category[category].append(classified)

        enriched_records.append(classified)

    sample_record_ids = select_cost_type_samples(eligible_by_category, sample_ratio, policy)
    for record in enriched_records:
        if record["record_id"] in sample_record_ids:
            record["is_cost_type_sample"] = True
            if policy["acceptance_scope"]["include_cost_type_samples"]:
                record["requirement_reasons"].append("cost_type_20pct_sample")
        record["acceptance_required"] = bool(record["requirement_reasons"])

    output_records = [strip_internal_fields(record) for record in enriched_records]
    return {
        "schema": "ResearchFinanceAcceptanceClassification",
        "schema_version": "1.0",
        "policy_version": policy_version,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_record_count": len(records),
        "numeric_policy": {
            "large_voucher_amount_gte": money_str(large_threshold),
            "cost_type_sample_ratio": str(sample_ratio),
            "minimum_sample_count_when_eligible": policy["cost_type_sampling"]["minimum_sample_count_when_eligible"],
        },
        "summary": build_summary(output_records),
        "category_summary": build_category_summary(output_records),
        "records": output_records,
    }


def select_cost_type_samples(
    eligible_by_category: dict[str, list[dict[str, Any]]],
    sample_ratio: Decimal,
    policy: dict[str, Any],
) -> set[str]:
    selected: set[str] = set()
    minimum = int(policy["cost_type_sampling"].get("minimum_sample_count_when_eligible", 1))
    for records in eligible_by_category.values():
        if not records:
            continue
        sample_count = calculate_sample_count(len(records), sample_ratio, minimum)
        sorted_records = sorted(
            records,
            key=lambda item: (-item["_amount_decimal"], item.get("voucher_date") or "", item.get("record_id") or ""),
        )
        selected.update(record["record_id"] for record in sorted_records[:sample_count])
    return selected


def calculate_sample_count(eligible_count: int, sample_ratio: Decimal, minimum: int) -> int:
    if eligible_count <= 0:
        return 0
    count = math.ceil(Decimal(eligible_count) * sample_ratio)
    return min(eligible_count, max(minimum, count))


def is_meeting_fee_record(category: str, keywords: list[str]) -> bool:
    return any(keyword in category for keyword in keywords)


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    total_amount = sum(parse_money(record["expense_amount"]) for record in records)
    acceptance_records = [record for record in records if record["acceptance_required"]]
    return {
        "total_record_count": len(records),
        "total_expense_amount": money_str(total_amount),
        "acceptance_required_count": len(acceptance_records),
        "acceptance_required_amount": money_str(sum(parse_money(record["expense_amount"]) for record in acceptance_records)),
        "large_voucher_count": sum(1 for record in records if record["is_large_voucher"]),
        "meeting_fee_required_count": sum(1 for record in records if record["is_meeting_fee_required"]),
        "cost_type_sample_count": sum(1 for record in records if record["is_cost_type_sample"]),
    }


def build_category_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["budget_category_name"]].append(record)

    summaries = []
    for category, category_records in sorted(grouped.items()):
        amount = sum(parse_money(record["expense_amount"]) for record in category_records)
        summaries.append(
            {
                "budget_category_name": category,
                "record_count": len(category_records),
                "expense_amount": money_str(amount),
                "large_voucher_count": sum(1 for record in category_records if record["is_large_voucher"]),
                "meeting_fee_required_count": sum(1 for record in category_records if record["is_meeting_fee_required"]),
                "cost_type_sample_count": sum(1 for record in category_records if record["is_cost_type_sample"]),
                "acceptance_required_count": sum(1 for record in category_records if record["acceptance_required"]),
            }
        )
    return summaries


def strip_internal_fields(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(record)
    cleaned.pop("_source_index", None)
    cleaned.pop("_amount_decimal", None)
    return cleaned


def parse_money(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid money value: {value}") from exc


def money_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify voucher JSON with research finance acceptance policy rules.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT, help="VoucherRecord JSON path.")
    parser.add_argument("-p", "--policy", type=Path, default=DEFAULT_POLICY, help="Policy JSON path.")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="Classification output JSON path.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    result = classify_vouchers(read_json(args.input), read_json(args.policy))
    write_json(result, args.output)
    print(f"Wrote {result['source_record_count']} classified records to {args.output}")


if __name__ == "__main__":
    main()
