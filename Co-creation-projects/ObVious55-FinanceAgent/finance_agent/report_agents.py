from __future__ import annotations

from typing import Any

from finance_agent.acceptance_rule_engine import money_str
from finance_agent.report_calculations import (
    build_expense_insights,
    build_shared_input_summary,
    calculate_acceptance_review,
    calculate_budget_variance,
    require_shared_context,
)
from finance_agent.report_io import extract_agent_data, normalize_agent_output, parse_llm_json
from finance_agent.report_llm import LLMClient
from finance_agent.report_models import ReportContext
from finance_agent.report_rendering import build_deterministic_report


class AgentNode:
    name: str
    output_format = "json"
    prompt = ""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def build_input(self, context: ReportContext, previous_outputs: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def run(self, context: ReportContext, previous_outputs: dict[str, Any]) -> dict[str, Any] | str:
        input_json = self.build_input(context, previous_outputs)
        raw_output = self.llm_client.generate(self.name, self.prompt, input_json, self.output_format)
        if self.output_format == "markdown":
            return raw_output
        return parse_llm_json(raw_output, self.name)


class ExpenseInsightAgent(AgentNode):
    name = "ExpenseInsightAgent"
    prompt = """You are ExpenseInsightAgent, responsible for expense execution analysis.
Use only deterministic calculated_data from the input. Do not recalculate amounts,
invent vouchers, or add new structured data fields.
Return strict JSON only. Prefer omitting the data field; the runtime injects
calculated_data into data after validation. If you include data, it must copy
calculated_data exactly without extra keys or renamed fields."""

    def build_input(self, context: ReportContext, previous_outputs: dict[str, Any]) -> dict[str, Any]:
        shared = require_shared_context(context)
        calculated = {
            "total_record_count": len(shared.records),
            "total_expense_amount": money_str(shared.total_amount),
            "category_summary": shared.category_summary,
            "project_summary": shared.project_summary,
            "fund_destination_summary": shared.fund_destination_summary,
            "large_voucher_records": shared.large_voucher_records,
            "insights": build_expense_insights(shared.category_summary, shared.large_voucher_records),
        }
        return {
            "agent": self.name,
            "task": "Explain expense execution, spending structure, fund destination, and large-voucher characteristics.",
            "calculated_data": calculated,
            "deterministic_narrative": (
                "Expense execution analysis is complete. Spending structure and fund destination are based on "
                "deterministic calculations."
            ),
            "output_contract": build_output_contract(
                self.name,
                calculated,
                narrative_fields=["narrative", "key_findings"],
            ),
            "next_input": {
                "expense_summary": {
                    "total_record_count": calculated["total_record_count"],
                    "total_expense_amount": calculated["total_expense_amount"],
                    "top_categories": calculated["category_summary"][:5],
                    "large_voucher_count": len(shared.large_voucher_records),
                }
            },
        }


class BudgetVarianceAgent(AgentNode):
    name = "BudgetVarianceAgent"
    prompt = """You are BudgetVarianceAgent, responsible only for budget variance analysis.
Use calculated_data.category_variance directly when variance_available is true.
When variance_available is false, explain that no budget baseline is available.
Do not output expense-summary fields such as total_expense, total_record_count,
large_voucher_count, or category_expenses. Those belong to ExpenseInsightAgent.
Return strict JSON only. Prefer omitting the data field; the runtime injects
calculated_data into data after validation. If you include data, it must copy
calculated_data exactly without extra keys or renamed fields."""

    def build_input(self, context: ReportContext, previous_outputs: dict[str, Any]) -> dict[str, Any]:
        calculated = calculate_budget_variance(context)
        return {
            "agent": self.name,
            "task": "Explain budget execution and variance analysis results.",
            "shared_context": build_shared_input_summary(context),
            "calculated_data": calculated,
            "deterministic_narrative": calculated.get("message", "Budget variance analysis is complete."),
            "output_contract": build_output_contract(
                self.name,
                calculated,
                narrative_fields=["narrative"],
                forbidden_data_keys=[
                    "category_expenses",
                    "large_voucher_count",
                    "total_expense",
                    "total_record_count",
                ],
            ),
            "next_input": {
                "budget_variance_status": calculated.get("status"),
                "variance_available": calculated.get("variance_available"),
                "category_variance": calculated.get("category_variance", []),
                "message": calculated.get("message"),
            },
        }


class AcceptanceReviewAgent(AgentNode):
    name = "AcceptanceReviewAgent"
    prompt = """You are AcceptanceReviewAgent, responsible for acceptance-material readiness review.
The acceptance scope is determined by deterministic rules in calculated_data.
Do not change acceptance_required, is_large_voucher, is_meeting_fee_required, or
is_cost_type_sample classifications. Explain preparation scope, material checklist,
and review focus. If calculated_data.material_folder_scan is available, perform
file-name keyword matching only. Do not parse files. Do not judge authenticity,
compliance, amount consistency, signature validity, or material sufficiency.
Output candidate materials, missing items, and human verification items as
review leads only; final material validity remains a human decision.
Return strict JSON only. Prefer omitting the data field; the runtime injects
calculated_data into data after validation. If you include data, it must copy
calculated_data exactly without extra keys or renamed fields."""

    def build_input(self, context: ReportContext, previous_outputs: dict[str, Any]) -> dict[str, Any]:
        calculated = calculate_acceptance_review(context)
        return {
            "agent": self.name,
            "task": "Explain acceptance voucher preparation scope and material-readiness focus.",
            "shared_context": build_shared_input_summary(context),
            "calculated_data": calculated,
            "deterministic_narrative": (
                "Acceptance preparation scope is determined by the rule engine. This node only explains "
                "classifications, material-readiness focus, and file-name-level material existence leads."
            ),
            "output_contract": build_output_contract(
                self.name,
                calculated,
                narrative_fields=[
                    "narrative",
                    "preparation_focus",
                    "candidate_materials",
                    "missing_items",
                    "human_verification_items",
                ],
            ),
            "next_input": {
                "acceptance_summary": {
                    "acceptance_required_count": calculated["acceptance_required_count"],
                    "acceptance_required_amount": calculated["acceptance_required_amount"],
                    "large_voucher_count": len(calculated["large_voucher_records"]),
                    "meeting_fee_required_count": len(calculated["meeting_fee_required_records"]),
                    "cost_type_sample_count": len(calculated["cost_type_sample_records"]),
                    "missing_fund_info_count": len(calculated["missing_fund_info_records"]),
                },
                "preparation_checklist": calculated["preparation_checklist"],
                "material_folder_scan": calculated.get("material_folder_scan"),
            },
        }


class FinalReportAgent(AgentNode):
    name = "FinalReportAgent"
    output_format = "markdown"
    prompt = """You are FinalReportAgent, responsible for generating the final Markdown report.
Generate the report from the input JSON, upstream agent outputs, and human review
context. Human review notes take precedence over agent narrative text, but they
must not directly rewrite deterministic amounts, rule-engine classifications, or
raw evidence. If no budget baseline is provided, do not invent budget execution
rates, variance amounts, or variance ratios. If human_review is HUMAN_REJECTED
or rerun_required is true, do not generate a final report."""

    def build_input(self, context: ReportContext, previous_outputs: dict[str, Any]) -> dict[str, Any]:
        expense_data = extract_agent_data(previous_outputs["ExpenseInsightAgent"])
        variance_data = extract_agent_data(previous_outputs["BudgetVarianceAgent"])
        acceptance_data = extract_agent_data(previous_outputs["AcceptanceReviewAgent"])
        draft_report = build_deterministic_report(context, expense_data, variance_data, acceptance_data)
        return {
            "agent": self.name,
            "task": "Generate the fixed-section research finance expense and acceptance-readiness report.",
            "classification_summary": context.classification.get("summary"),
            "policy_version": context.classification.get("policy_version"),
            "upstream_agent_outputs": previous_outputs,
            "human_review": previous_outputs.get("human_review"),
            "effective_outputs": previous_outputs.get("effective_outputs"),
            "human_review_policy": {
                "priority": "Human review notes override agent narrative only; deterministic data remains locked.",
                "locked_fields": [
                    "amount",
                    "computed_total",
                    "rule_hit_ids",
                    "acceptance_required",
                    "is_large_voucher",
                    "is_meeting_fee_required",
                    "is_cost_type_sample",
                ],
                "blocked_statuses": ["HUMAN_REJECTED"],
                "blocked_when_rerun_required": True,
            },
            "draft_report": draft_report,
        }


def run_agent_node(
    agent: AgentNode,
    context: ReportContext,
    previous_outputs: dict[str, Any],
) -> tuple[dict[str, Any], str, dict[str, Any] | str]:
    input_json = agent.build_input(context, previous_outputs)
    raw_output = agent.llm_client.generate(agent.name, agent.prompt, input_json, agent.output_format)
    if agent.output_format == "markdown":
        return input_json, raw_output, raw_output

    parsed_output = parse_llm_json(raw_output, agent.name)
    return input_json, raw_output, normalize_agent_output(agent.name, parsed_output, input_json)


def build_output_contract(
    agent_name: str,
    calculated_data: dict[str, Any],
    narrative_fields: list[str],
    forbidden_data_keys: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "required_top_level_keys": ["agent", "status", *narrative_fields],
        "optional_top_level_keys": ["next_input"],
        "data_policy": "Do not include data. The runtime injects deterministic calculated_data into data after validation.",
        "allowed_data_keys_if_data_is_included": sorted(calculated_data.keys()),
        "forbidden_data_keys": sorted(forbidden_data_keys or []),
        "agent_boundary": f"{agent_name} may explain calculated_data but must not invent or rename structured fields.",
    }
