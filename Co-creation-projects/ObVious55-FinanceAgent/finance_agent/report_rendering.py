from __future__ import annotations

from typing import Any

from finance_agent.report_models import ReportContext


def build_deterministic_report(
    context: ReportContext,
    expense: dict[str, Any],
    variance: dict[str, Any],
    acceptance: dict[str, Any],
) -> str:
    summary = context.classification["summary"]
    sections = [
        "# 科研项目经费使用及验收准备分析报告",
        "",
        "## 一、基本情况",
        (
            f"本报告基于凭证清单标准化 JSON 及规则引擎分类结果生成。"
            f"本次纳入分析凭证 {summary['total_record_count']} 笔，"
            f"支出金额合计 {summary['total_expense_amount']} 元。"
            f"规则版本为 {context.classification.get('policy_version')}。"
        ),
        "",
        "## 二、项目主要研制情况",
        (
            "当前输入数据主要反映项目经费支出和凭证准备情况，未包含项目任务书、技术指标、"
            "研制节点或成果交付材料。因此本节仅作为报告占位，后续应接入项目任务书、阶段总结、"
            "验收申请书等材料后补充研制内容、完成情况和成果说明。"
        ),
        "",
        "## 三、项目经费总体使用情况",
        (
            f"经费支出合计 {expense['total_expense_amount']} 元，涉及凭证 {expense['total_record_count']} 笔。"
            f"其中进入验收凭证准备范围 {summary['acceptance_required_count']} 笔，"
            f"金额 {summary['acceptance_required_amount']} 元。"
        ),
        "",
        "## 四、项目经费支出结构分析",
        render_category_table(expense["category_summary"]),
        "",
        "\n".join(f"- {item}" for item in expense["insights"]),
        "",
        "## 五、项目资金去向分析",
        render_fund_destination(expense["fund_destination_summary"]),
        "",
        "## 六、预算执行及差异分析",
        render_budget_variance(variance),
        "",
        "## 七、验收凭证准备情况",
        render_acceptance_review(acceptance),
        "",
        "## 八、存在问题及复核建议",
        render_risk_suggestions(expense, variance, acceptance),
        "",
        "## 九、其他事项",
        (
            "本报告由规则引擎和多 Agent 管道生成。金额阈值、抽样比例、会议费必备规则等均来自配置文件；"
            "如政策口径调整，应优先修改 policy 配置并重新运行规则引擎和报告管道。"
        ),
        "",
    ]
    return "\n".join(sections)


def render_category_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| 费用类别 | 笔数 | 金额 | 金额占比 | 大额笔数 | 验收准备笔数 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['budget_category_name']} | {row['record_count']} | {row['expense_amount']} | "
            f"{row['amount_ratio']} | {row['large_voucher_count']} | {row['acceptance_required_count']} |"
        )
    return "\n".join(lines)


def render_fund_destination(rows: list[dict[str, Any]], limit: int = 12) -> str:
    lines = [
        "| 项目号 | 经费号 | 负责人 | 笔数 | 金额 | 金额占比 |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows[:limit]:
        lines.append(
            f"| {row['project_code']} | {row['project_fund_no']} | {row['fund_owner']} | "
            f"{row['record_count']} | {row['expense_amount']} | {row['amount_ratio']} |"
        )
    if len(rows) > limit:
        lines.append(f"| 其余 {len(rows) - limit} 项 |  |  |  |  |  |")
    return "\n".join(lines)


def render_budget_variance(variance: dict[str, Any]) -> str:
    if not variance.get("variance_available"):
        return (
            f"{variance['message']}\n\n"
            "建议补充预算批复表或预算调整表，至少包含费用类别、批复预算金额、调整后预算金额等字段，"
            "再计算预算执行率、差异额和差异率。"
        )

    lines = [
        "| 费用类别 | 预算金额 | 实际支出 | 差异金额 | 执行率 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in variance["category_variance"]:
        lines.append(
            f"| {row['budget_category_name']} | {row['budget_amount']} | {row['actual_amount']} | "
            f"{row['variance_amount']} | {row['execution_rate']} |"
        )
    return "\n".join(lines)


def render_acceptance_review(acceptance: dict[str, Any]) -> str:
    lines = [
        (
            f"按规则版本 {acceptance['policy_version']}，进入验收凭证准备范围 "
            f"{acceptance['acceptance_required_count']} 笔，金额 {acceptance['acceptance_required_amount']} 元。"
        ),
        "",
        f"- 大额凭证：{len(acceptance['large_voucher_records'])} 笔。",
        f"- 会议费必备凭证：{len(acceptance['meeting_fee_required_records'])} 笔。",
        f"- 成本类型20%抽样凭证：{len(acceptance['cost_type_sample_records'])} 笔。",
        f"- 项目经费号或负责人缺失记录：{len(acceptance['missing_fund_info_records'])} 笔。",
        "",
        "验收材料准备清单：",
    ]
    lines.extend(f"- {item}" for item in acceptance["preparation_checklist"])
    return "\n".join(lines)


def render_risk_suggestions(expense: dict[str, Any], variance: dict[str, Any], acceptance: dict[str, Any]) -> str:
    suggestions = []
    if acceptance["missing_fund_info_records"]:
        suggestions.append("部分凭证缺少项目经费号或负责人信息，建议先与财务台账、项目任务书或经费卡进行复核。")
    if not variance.get("variance_available"):
        suggestions.append("当前缺少预算基准数据，预算执行差异和差异率无法形成可审计结论。")
    if expense["large_voucher_records"]:
        suggestions.append("大额凭证金额占比较高的类别应重点检查采购、合同、验收和支付材料的一致性。")
    if not suggestions:
        suggestions.append("未发现显著结构性问题，建议按验收材料清单继续补齐佐证文件。")
    return "\n".join(f"- {item}" for item in suggestions)
