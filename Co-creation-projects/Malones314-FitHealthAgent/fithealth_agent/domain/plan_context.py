"""训练计划上下文裁决、日期解析与渲染纯函数（阶段 3a）。

仍在阶段 3b/3c 的意图与恢复规则通过显式回调传入，避免 domain 反向导入 main。
"""

from __future__ import annotations

import re
from datetime import date
from typing import Callable

from fithealth_agent.health_safety import clause_bounds
from fithealth_agent.info_store import (
    resolve_confirmed_memory_facts,
    weekly_schedule_entry_for_date,
)
from fithealth_agent.muscle_recovery import MuscleRecoverySnapshot
from fithealth_agent.plan_workflow import state_for_context


_PLAN_DATE_INTENT = re.compile(
    r"计划|安排|排期|生成|制定|今天是|日期是|当天|这天|定在|改到|挪到|"
    r"练什么|练啥|要练|该练|怎么练|训练"
)


_PLAN_DATE_VETO_BEFORE = re.compile(
    r"上次|上一次|之前|前几天|那天|那次|已经|记录|查询|查看|回顾|统计|导入"
)


_PLAN_DATE_VETO_AFTER = re.compile(
    r"受伤|拉伤|扭伤|伤了|扭了|发烧|生病|感冒|体检|复查|住院|不适|疼|"
    r"那天|记录|查询|查看|回顾|统计"
)


_ISO_DATE_PATTERN = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")


def confirmed_weekly_schedule_entry(
    memories: list[dict] | None,
    requested_day: date,
) -> dict[str, str] | None:
    """Return the effective structured weekly entry for one requested date."""
    for fact in resolve_confirmed_memory_facts(memories):
        if fact.get("namespace") != "plan" or fact.get("key") != "weekly_schedule":
            continue
        entry = weekly_schedule_entry_for_date(fact.get("value"), requested_day)
        if entry is not None:
            return entry
    return None


def resolve_plan_context(
    message: str,
    profile: dict[str, object],
    memories: list[dict] | None,
    recovery: MuscleRecoverySnapshot | None = None,
    routed_intent: dict[str, object] | None = None,
    soreness_reports: list[object] | None = None,
    *,
    current_instruction_override_fn: Callable[[str], bool],
    is_safety_bypass_request_fn: Callable[[str], bool],
    recovery_context_payload_fn: Callable,
    subject_recovery_regions_fn: Callable,
    explicitly_requested_recovery_regions_fn: Callable,
    scheduled_weekly_entry_for_message_fn: Callable,
) -> dict[str, object]:
    """Resolve plan constraints deterministically before generation."""
    has_routed_intent = isinstance(routed_intent, dict)
    routed_intent = routed_intent if has_routed_intent else {}
    routed_decision = str(routed_intent.get("schedule_decision") or "follow")
    if routed_decision not in {"follow", "override", "rest"}:
        routed_decision = "follow"
    routed_subject = str(routed_intent.get("subject") or "").strip()[:40]
    raw_temporary_safety = routed_intent.get("temporary_health_constraints")
    temporary_safety = list(dict.fromkeys(
        str(item).strip()[:120]
        for item in (raw_temporary_safety if isinstance(raw_temporary_safety, list) else [])
        if isinstance(item, str) and item.strip()
    ))[:5]
    raw_excluded_subjects = routed_intent.get("excluded_subjects")
    excluded_subjects = list(dict.fromkeys(
        str(item).strip()[:40]
        for item in (raw_excluded_subjects if isinstance(raw_excluded_subjects, list) else [])
        if isinstance(item, str) and item.strip()
    ))[:5]
    routed_needs_clarification = bool(routed_intent.get("needs_clarification"))

    def subject_is_excluded(subject: str | None) -> bool:
        normalized_subject = re.sub(r"\s+", "", str(subject or "")).casefold()
        return bool(normalized_subject) and any(
            (normalized_exclusion := re.sub(r"\s+", "", item).casefold())
            and (
                normalized_exclusion in normalized_subject
                or normalized_subject in normalized_exclusion
            )
            for item in excluded_subjects
        )

    facts = resolve_confirmed_memory_facts(memories)
    safety = [str(fact.get("value") or "") for fact in facts if fact.get("namespace") == "health" and fact.get("key") in {"injury_or_constraint", "recovery_status"}]
    preferences = [str(fact.get("value") or "") for fact in facts if fact.get("namespace") in {"training", "youtube"} or (fact.get("namespace") == "plan" and fact.get("key") == "preference")]
    scheduled_entry = scheduled_weekly_entry_for_message_fn(message, memories)
    scheduled = (
        (scheduled_entry[0], str(scheduled_entry[1].get("subject") or ""))
        if scheduled_entry is not None and scheduled_entry[1].get("type") != "rest"
        else None
    )
    scheduled_rest = bool(
        scheduled_entry is not None and scheduled_entry[1].get("type") == "rest"
    )
    normalized_current_message = re.sub(r"\s+", "", message)
    affirmative_current_subject = bool(
        re.search(
            r"(?:今天|今日|这次|本次).{0,8}(?:"
            r"(?:想|要|准备|打算)?(?:练|做)(?!什么|啥|哪)|"
            r"(?:想|要|准备|打算)?(?:有氧|跑步|跳绳|瑜伽|普拉提)"
            r")",
            normalized_current_message,
        )
    ) and not bool(
        re.search(
            r"(?:今天|今日|这次|本次).{0,8}(?:不想|不要|不练|别练|休息|跳过)",
            normalized_current_message,
        )
    )
    explicit_current_subject = bool(routed_subject and affirmative_current_subject)
    override = (
        routed_decision == "override" or explicit_current_subject
        if has_routed_intent
        else current_instruction_override_fn(message)
    )
    normalized = re.sub(r"\s+", "", message)
    rest = (
        routed_decision == "rest"
        if has_routed_intent
        else bool(re.search(r"(?:今天|今日|这次|本次).{0,8}(?:休息|不训练|跳过训练)", normalized))
    ) or (scheduled_rest and not override)
    replacement = re.search(r"(?:改练|换成|改为)\s*([^，。；;\n]+)", message)
    replacement_subject = (
        routed_subject if has_routed_intent and override
        else replacement.group(1).strip()[:40] if replacement else ""
    )
    decision = "rest_today" if rest else "override_today" if override else "follow_schedule"
    suppressed = []
    if scheduled and decision != "follow_schedule":
        suppressed.append({"rule": f"周计划：{scheduled[1]}", "reason": "被当前消息临时覆盖", "scope": "today"})
    if scheduled_rest and decision == "override_today":
        suppressed.append({"rule": "周计划：休息日", "reason": "被当前消息临时覆盖", "scope": "today"})
    if scheduled and subject_is_excluded(scheduled[1]) and decision == "follow_schedule":
        decision = "override_today"
        suppressed.append({"rule": f"周计划：{scheduled[1]}", "reason": "被当前消息明确排除", "scope": "today"})
    explicit_regions = explicitly_requested_recovery_regions_fn(message)
    recovery_context = recovery_context_payload_fn(recovery, explicit_regions, soreness_reports)
    scheduled_regions = subject_recovery_regions_fn(scheduled[1] if scheduled else None)
    # BUG-26 问题 1：区域压制**只采纳主项负荷**。次要负荷（硬拉顺带练到的小臂、
    # 卧推顺带练到的前束）窗口本来就已折半，再让它压掉周计划的手臂日/肩部日就是
    # 纯误拦；它们仍出现在 recovering 提示文本里。
    recovering_regions = {
        str(item.get("region") or "")
        for item in recovery_context["recovering"]
        if isinstance(item, dict) and item.get("role", "primary") == "primary"
    }
    recovery_blocked_schedule = bool(
        any(
            region not in explicit_regions
            and (
                region in recovering_regions
                or region in recovery_context["reduce"]
                or region in recovery_context["avoid"]
            )
            for region in scheduled_regions
        )
    )
    if scheduled and recovery_blocked_schedule:
        blocked_regions = {
            region for region in scheduled_regions
            if region not in explicit_regions and (
                region in recovering_regions
                or region in recovery_context["reduce"]
                or region in recovery_context["avoid"]
            )
        }
        loads = [
            item for item in recovery_context["recovering"]
            if isinstance(item, dict) and item.get("region") in blocked_regions
        ]
        reason = (
            f"{loads[0]['zh']}预计还需 {float(loads[0]['hours_remaining']):g} 小时恢复"
            if loads else f"{'、'.join(sorted(blocked_regions))}当前有生效的酸痛反馈"
        )
        suppressed.append({"rule": f"周计划：{scheduled[1]}", "reason": reason, "scope": "today"})
        decision = "recovery_override"
    clarification = bool(
        scheduled_entry
        and decision == "override_today"
        and (routed_needs_clarification or not replacement_subject)
    )
    safety_bypass = bool(safety and is_safety_bypass_request_fn(message))
    # blocking_reasons 是**阻断生成**的确定性信号；调用方据此返回 409。
    # 以前这个 key 从未被填充，导致 main.py 里的拦截判断永远为假。
    blocking_reasons: list[dict[str, object]] = []
    if safety_bypass:
        blocking_reasons.append({
            "rule": "已确认的安全/伤病限制",
            "reason": "当前消息要求忽略或跳过安全限制",
            "constraints": safety,
        })
    painful_conflicts = sorted(set(explicit_regions) & set(recovery_context["avoid"]))
    if painful_conflicts:
        blocking_reasons.append({
            "rule": "肌群疼痛安全信号",
            "reason": "当前消息要求训练用户已报告疼痛的区域",
            "constraints": painful_conflicts,
        })
    dynamic_safety = list(dict.fromkeys(safety + temporary_safety + [
        f"{region}疼痛，停止该区域训练" for region in recovery_context["avoid"]
    ]))
    context: dict[str, object] = {
        "goal": str(profile.get("goal") or "未设置"),
        "scheduled_subject": scheduled[1] if scheduled else "休息日" if scheduled_rest else None,
        "scheduled_date": scheduled_entry[0].isoformat() if scheduled_entry else None,
        "effective_subject": scheduled[1] if scheduled and decision == "follow_schedule" else replacement_subject or None,
        "active_safety_constraints": dynamic_safety,
        "current_directives": [message.strip()] if override or rest else [],
        "active_preferences": preferences,
        "decision": decision,
        "routed_schedule_decision": routed_decision,
        "excluded_subjects": excluded_subjects,
        "suppressed_rules": suppressed,
        "clarification_required": clarification,
        "blocking_reasons": blocking_reasons,
        # 供 format_plan_context 提示模型"后端只是猜到可能覆盖，语义由你确认"。
        "override_detected": bool(override),
        "muscle_recovery": recovery_context,
        "recovery_conflicts": sorted(
            region for region in explicit_regions
            if region in recovering_regions or region in recovery_context["reduce"]
        ),
    }
    # 状态一律由 plan_workflow 推导，不再在 main.py 里手写状态字符串，
    # 避免两套状态机各写各的（这正是上面那个死代码 bug 的成因）。
    context["workflow_state"] = str(state_for_context(context))
    return context


def format_plan_context(context: dict[str, object]) -> str:
    """把已裁决的 PlanContext 渲染成送进模型的唯一一段优先级说明。

    BUG-03：完整的六级优先级阶梯原本写在 `training_priority_context` 里，
    但那个函数**定义 1 次、调用 0 次**，从未进入模型上下文；模型只看到这里
    原先那句压缩成一行的"安全限制 > 当前明确指令 > ..."，其中恰恰缺了最关键
    的一条语义澄清——"普通抱怨或提问不算覆盖当天周计划"。于是"今天有点累"
    这类话可能被当成覆盖周计划的指令。

    BUG-04 的教训是：同一件事有两处实现，就一定会有一处悄悄失效。所以这次
    不是把那段文本另外拼上去，而是**合并进这个已经接线的函数并删掉原函数**；
    `build_agent_input` 里那段独立的【训练设计优先级】也一并并入，全局只保留
    这一段优先级说明。
    """
    goal = context.get("goal") or "未设置"
    lines = [
        "【后端 PlanContext（已裁决优先级，必须遵守）】",
        "- 优先级由高到低：",
        "  1. 安全/伤病限制。",
        "  2. 用户当前明确指令；只有明确改练、休息、跳过或不执行才覆盖当天周计划，普通抱怨或提问不算。",
        "  3. 肌群恢复状态（未恢复或用户报告酸痛）。",
        "  4. 已确认周计划。",
        "  5. 健身目标。",
        "  6. 长期训练偏好。",
        "  7. 历史摘要，仅供参考。",
        f"- 工作流状态：{context.get('workflow_state')}",
        f"- 当前主目标：{goal}。除非用户明确说“健身目标改为/不再以…为目标”，否则必须持续保留该目标。",
        "- 用户的动作偏好、强度偏好、久坐状态、姿态或伤病限制仅调整训练的动作、容量和强度；不得覆盖、取消或替代当前主目标。",
        "- 输出计划或建议时，需同时满足主目标与已确认限制；若两者存在风险冲突，优先保证限制安全，并说明对主目标的调整。",
    ]
    if context.get("active_safety_constraints"):
        lines.append("- 当前安全限制：" + "；".join(context["active_safety_constraints"]))
    if context.get("scheduled_subject"):
        lines.append(f"- 周计划科目：{context['scheduled_subject']}（{context.get('scheduled_date') or '当前日期'}）")
    if context.get("current_directives"):
        lines.append("- 当前指令：" + "；".join(context["current_directives"]))
    if context.get("excluded_subjects"):
        lines.append("- 用户本次明确排除的训练科目，计划不得安排：" + "、".join(context["excluded_subjects"]))
    recovery = context.get("muscle_recovery")
    if isinstance(recovery, dict):
        recovering = recovery.get("recovering") or []
        if recovering:
            details = [
                f"{item.get('region')}·{item.get('zh')}还需 {float(item.get('hours_remaining') or 0):g} 小时"
                for item in recovering
                if isinstance(item, dict)
            ]
            if details:
                lines.append("- 当前肌群恢复状态：" + "；".join(details))
        if recovery.get("reduce"):
            lines.append(
                "- 用户报告普通酸痛，以下区域必须由你结合当天计划自由裁量减量，并在回复中说明调整："
                + "、".join(recovery["reduce"])
            )
        if recovery.get("avoid"):
            lines.append("- 疼痛安全信号，禁止安排以下区域训练：" + "、".join(recovery["avoid"]))
        if recovery.get("load_warnings"):
            warning_text = "；".join(
                str(item.get("message") or "")
                for item in recovery["load_warnings"]
                if isinstance(item, dict) and item.get("message")
            )
            if warning_text:
                lines.append(
                    "- 累积负荷预警：" + warning_text
                    + "。相同主肌群若必须安排，只能使用不超过 2 组的低容量恢复训练。"
                )
        if recovery.get("ready"):
            lines.append("- 可正常安排的候选区域：" + "、".join(recovery["ready"]))
        if recovery.get("explicitly_requested"):
            lines.append("- 用户本次明确要求训练：" + "、".join(recovery["explicitly_requested"]))
    if context.get("recovery_conflicts"):
        lines.append(
            "- 当前明确指令高于普通恢复状态：仍可按用户要求训练 "
            + "、".join(context["recovery_conflicts"])
            + "，但必须说明冲突并下调容量；用户可按训练时主观感受继续调整或停止。"
        )
    if context.get("suppressed_rules"):
        lines.append("- 本次临时覆盖：" + "；".join(item["rule"] for item in context["suppressed_rules"]))
    if context.get("clarification_required"):
        lines.append("- 需要澄清：用户未说明休息还是替换科目；不得擅自选择。")
    if context.get("override_detected"):
        lines.append(
            "- 后端检测到当前消息可能覆盖当天安排；由模型结合完整原文确认语义，"
            "不得因此修改长期档案。"
        )
    lines.append("- 冲突时按上述顺序决策，并说明采用的优先层级。")
    lines.append("- 长期档案不因本次覆盖而修改；安全限制不能被普通偏好绕过。")
    return "\n".join(lines) + "\n\n"


def daily_schedule_constraint(
    message: str,
    memories: list[dict] | None,
    *,
    current_instruction_override_fn: Callable[[str], bool],
    scheduled_weekly_entry_for_message_fn: Callable,
) -> str:
    """Map an explicitly supplied ISO date to the confirmed planned subject."""
    if current_instruction_override_fn(message):
        return ""
    scheduled_entry = scheduled_weekly_entry_for_message_fn(message, memories)
    if scheduled_entry is None:
        return ""
    requested_day, entry = scheduled_entry
    if entry.get("type") == "rest":
        return (
            "【已确认每周训练安排（硬约束）】\n"
            f"- {requested_day.isoformat()} 是周{('一', '二', '三', '四', '五', '六', '日')[requested_day.weekday()]}，"
            "当天是休息日，不得生成训练计划，除非用户当前消息明确要求改练。\n\n"
        )
    subject = str(entry.get("subject") or "")
    if not subject:
        return ""
    return (
        "【已确认每周训练安排（硬约束）】\n"
        f"- {requested_day.isoformat()} 是周{('一', '二', '三', '四', '五', '六', '日')[requested_day.weekday()]}，"
        f"当天训练科目必须为：{subject}。\n"
        "- 除非用户当前消息明确要求改期、休息或换科目，否则不得生成全身计划或其他科目来替代该安排。"
        "主目标与健康限制仅用于调整该科目的动作、容量、强度和恢复。\n\n"
    )


def extract_iso_dates(text: str) -> list[tuple[date, int, int]]:
    """抽出文本里所有合法 ISO 日期及其位置。

    BUG-07：以前 `scheduled_plan_for_message` 用严格补零的 `20\\d{2}-\\d{2}-\\d{2}`，
    而 `_requested_record_date` 用宽松的 `\\d{4}-\\d{1,2}-\\d{1,2}`，于是
    "2026-8-9" 只被后者识别——查记录正常，生成计划时周计划约束却静默不生效。
    两处统一走这里。
    """
    if not isinstance(text, str):
        return []
    found: list[tuple[date, int, int]] = []
    for match in _ISO_DATE_PATTERN.finditer(text):
        year, month, day = match.groups()
        try:
            # 显式补零后再解析：date.fromisoformat 只有 Python 3.11+ 才接受
            # "2026-8-9" 这种非补零写法，不能依赖它。
            parsed = date.fromisoformat(f"{year}-{int(month):02d}-{int(day):02d}")
        except ValueError:
            continue
        if not 2000 <= parsed.year <= 2100:
            continue
        found.append((parsed, match.start(), match.end()))
    return found


def requested_plan_date(message: str) -> date | None:
    """只在语境确实是"为某一天出计划"时才返回该日期（BUG-07）。

    取的是**第一个语境通过的日期**，而不是第一个日期。
    """
    if not isinstance(message, str):
        return None
    dates = extract_iso_dates(message)
    if not dates:
        normalized = re.sub(r"\s+", "", message)
        relative_plan_request = bool(
            re.search(
                r"(?:生成|制定|创建|设计|安排).{0,8}(?:今天|今日)(?:的)?(?:训练(?:计划)?|计划)"
                r"|(?:今天|今日)(?:的)?(?:训练)?计划",
                normalized,
            )
        )
        if relative_plan_request:
            return __import__("datetime").datetime.now(
                __import__("zoneinfo").ZoneInfo("Asia/Shanghai")
            ).date()
        return None
    stripped = re.sub(r"\s+", "", message)
    # 整条消息就是一个日期时不需要意图词——那本身就是明确的指定
    if _ISO_DATE_PATTERN.fullmatch(stripped):
        return dates[0][0]
    for parsed, start, end in dates:
        # Cross-clause history markers must not veto the requested date.
        clause_start, clause_end = clause_bounds(message, start, end)
        before = re.sub(r"\s+", "", message[clause_start:start])[-24:]
        after = re.sub(r"\s+", "", message[end:clause_end])[:24]
        if _PLAN_DATE_VETO_BEFORE.search(before) or _PLAN_DATE_VETO_AFTER.search(after):
            continue
        if _PLAN_DATE_INTENT.search(before) or _PLAN_DATE_INTENT.search(after):
            return parsed
    return None


def scheduled_plan_for_message(
    message: str, memories: list[dict] | None
) -> tuple[date, str] | None:
    """Resolve an explicitly dated daily-plan request against confirmed schedule facts."""
    requested_day = requested_plan_date(message)
    if requested_day is None:
        return None
    entry = confirmed_weekly_schedule_entry(memories, requested_day)
    if entry is None or entry.get("type") == "rest":
        return None
    subject = entry.get("subject")
    return (requested_day, subject) if isinstance(subject, str) and subject else None


def scheduled_weekly_entry_for_message(
    message: str,
    memories: list[dict] | None,
) -> tuple[date, dict[str, str]] | None:
    """Resolve any active weekly entry, including an explicitly scheduled rest day."""
    requested_day = requested_plan_date(message)
    if requested_day is None:
        return None
    entry = confirmed_weekly_schedule_entry(memories, requested_day)
    return (requested_day, entry) if entry is not None else None
