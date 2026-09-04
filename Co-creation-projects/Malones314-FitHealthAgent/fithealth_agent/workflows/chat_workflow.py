"""Chat orchestration without HTTP response objects (main.py split stage 4)."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from hello_agents.core.exceptions import HelloAgentsException
from starlette.concurrency import run_in_threadpool

from fithealth_agent.context_budget import AGENT_INPUT_MAX_CHARS, ContextInputError
from fithealth_agent.daily_checkin import CHECKIN_CATEGORY, is_training_record_item
from fithealth_agent.health_safety import (
    CAUTION, URGENT, RiskFinding, acute_pain_finding, emergency_reply,
    merge_findings, risk_directive, screen_health_risk, urgent_plan_block_note,
)
from fithealth_agent.info_store import (
    MemoryStoreDegradedError, fact_is_active, fact_retention_class,
    normalize_memory_facts, parse_weekly_schedule, resolve_confirmed_memory_facts,
)
from fithealth_agent.muscle_map import resolve_muscles_for_exercise
from fithealth_agent.muscle_recovery import (
    MuscleRecoverySnapshot, REGION_ALIASES, build_recovery_snapshot,
    soreness_reply_needs_clarification,
)
from fithealth_agent.plan_workflow import PlanWorkflowState, state_after_generation
from fithealth_agent.runtime import deps
from fithealth_agent.runtime.deps import logger
from fithealth_agent.domain.intent_rules import (
    _is_safety_bypass_request, current_instruction_override, is_profile_query,
    is_training_record_query, is_training_related, navigation_only_message,
)
from fithealth_agent.domain.memory_view import (
    _memory_confirmation_decision,
    active_temporary_health_facts as _active_temporary_health_facts,
    confirmed_memory_profile as _confirmed_memory_profile,
    confirmed_weekly_schedule as _confirmed_weekly_schedule,
    format_cross_session_memories as _format_cross_session_memories,
    temporary_constraint_for_message, youtube_channels_to_avoid as _youtube_channels_to_avoid,
)
from fithealth_agent.domain.plan_context import (
    confirmed_weekly_schedule_entry, daily_schedule_constraint as _daily_schedule_constraint,
    format_plan_context, resolve_plan_context as _resolve_plan_context,
    scheduled_plan_for_message, scheduled_weekly_entry_for_message,
)
from fithealth_agent.domain.plan_validation import (
    extract_plan_subject, infer_plan_title, is_generic_training_subject,
    looks_like_complete_training_plan, most_recent_complete_training_plan,
    plan_card_title, plan_validation_fact_usage, validate_generated_training_plan,
)
from fithealth_agent.domain.profile_rules import (
    equipment_change_preview, merge_profile_updates_with_existing, onboarding_reply,
    profile_summary, validate_profile_tool_updates,
)
from fithealth_agent.domain.recovery_view import (
    _recovery_context_payload, _subject_recovery_regions,
    explicitly_requested_recovery_regions,
)
from fithealth_agent.domain.record_view import (
    _nutrition_record_date, _nutrition_record_items, _requested_record_date,
    _training_record_items,
)


@dataclass
class ChatTurn:
    payload: dict[str, object]
    message: str
    history: list[dict]
    source: str
    profile: dict[str, object] = field(default_factory=dict)
    memories: list[dict] = field(default_factory=list)
    plan_context: dict[str, object] = field(default_factory=dict)
    artifacts: list[dict[str, object]] = field(default_factory=list)
    debug: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "ChatTurn":
        return cls(
            payload=payload,
            message=str(payload["message"]),
            history=list(payload["history"]),
            source=str(payload["source"]),
        )


@dataclass(frozen=True)
class ChatResult:
    body: dict[str, object]
    status_code: int = 200


def stage_request_context(turn: ChatTurn) -> ChatTurn:
    """Initialize store-backed state after the route has validated the request."""
    turn.profile = deps.profile_store.get_profile()
    turn.debug["external_models_enabled"] = deps.external_model_settings_store.get()[
        "external_models_enabled"
    ]
    return turn


def stage_health_safety(turn: ChatTurn) -> ChatTurn:
    """Named boundary for the health/soreness phase executed by the workflow."""
    return turn


def stage_local_navigation(turn: ChatTurn) -> ChatTurn:
    """Named boundary for local record/profile navigation short circuits."""
    return turn


def stage_intent_routing(turn: ChatTurn) -> ChatTurn:
    """Named boundary for constrained chat intent routing."""
    return turn


def stage_plan_context(turn: ChatTurn) -> ChatTurn:
    """Named boundary for plan-context resolution and agent input assembly."""
    return turn


def stage_postprocess(turn: ChatTurn) -> ChatTurn:
    """Named boundary for artifacts, validation and response metadata."""
    return turn


_DURABLE_MEMORY_CUE = re.compile(
    r"(?:以后|今后|从今往后|长期|一直|每周|每星期|周[一二三四五六日天]|"
    r"不喜欢|喜欢|讨厌|避免|不要|不做|不练|我有|我是|慢性|骨盆(?:前|后)倾|"
    r"下交叉|臀肌无力|髂腰肌|核心无力|腘绳肌|竖脊肌|腰肌劳损|体态矫正|久坐)"
)

def format_cross_session_memories(memories: list[dict] | None) -> str:
    return _format_cross_session_memories(
        memories, resolve_facts_fn=resolve_confirmed_memory_facts
    )

def youtube_channels_to_avoid(
    memories: list[dict] | None, current_message: str = ""
) -> list[str]:
    return _youtube_channels_to_avoid(
        memories,
        current_message,
        resolve_facts_fn=resolve_confirmed_memory_facts,
    )

def confirmed_memory_profile(memories: list[dict] | None) -> str:
    return _confirmed_memory_profile(
        memories, resolve_facts_fn=resolve_confirmed_memory_facts
    )

def confirmed_weekly_schedule(memories: list[dict] | None) -> dict[str, str]:
    return _confirmed_weekly_schedule(
        memories,
        resolve_facts_fn=resolve_confirmed_memory_facts,
        parse_schedule_fn=parse_weekly_schedule,
    )

def active_temporary_health_facts(
    memories: list[dict] | None,
) -> list[dict[str, object]]:
    return _active_temporary_health_facts(
        memories, resolve_facts_fn=resolve_confirmed_memory_facts
    )

def format_response(response: object) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return json.dumps(response, ensure_ascii=False, indent=2)
    return str(response)

def resolve_plan_context(
    message: str,
    profile: dict[str, object],
    memories: list[dict] | None,
    recovery: MuscleRecoverySnapshot | None = None,
    routed_intent: dict[str, object] | None = None,
    soreness_reports: list[object] | None = None,
) -> dict[str, object]:
    return _resolve_plan_context(
        message=message,
        profile=profile,
        memories=memories,
        recovery=recovery,
        routed_intent=routed_intent,
        soreness_reports=soreness_reports,
        current_instruction_override_fn=current_instruction_override,
        is_safety_bypass_request_fn=_is_safety_bypass_request,
        recovery_context_payload_fn=_recovery_context_payload,
        subject_recovery_regions_fn=_subject_recovery_regions,
        explicitly_requested_recovery_regions_fn=explicitly_requested_recovery_regions,
        scheduled_weekly_entry_for_message_fn=scheduled_weekly_entry_for_message,
    )

def daily_schedule_constraint(message: str, memories: list[dict] | None) -> str:
    return _daily_schedule_constraint(
        message,
        memories,
        current_instruction_override_fn=current_instruction_override,
        scheduled_weekly_entry_for_message_fn=scheduled_weekly_entry_for_message,
    )

def _plan_muscle_resolver(name: str) -> list:
    return resolve_muscles_for_exercise(
        name,
        allow_external_models=deps.external_model_settings_store.get()["external_models_enabled"],
    )

def build_agent_input(
    message: str,
    profile: dict[str, object],
    history: list[dict] = None,
    memories: list[dict] | None = None,
    risk: RiskFinding | None = None,
    plan_context: dict[str, object] | None = None,
) -> str:
    current_time = __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("Asia/Shanghai"))
    current_time_context = (
        "[Current time]\n"
        + f"Current date: {current_time.date().isoformat()}\n"
        + f"Current time: {current_time.isoformat(timespec='seconds')} (Asia/Shanghai)\n"
        + "Resolve today/now/this week from this anchor unless the user explicitly provides a date.\n\n"
    )
    history_str = ""
    if history:
        history_str = "【近期对话上下文】\n"
        for msg in history:
            role = "用户" if msg.get("role") == "user" else "助手"
            text = msg.get("text", "")
            history_str += f"{role}：{text}\n"
        history_str += "\n"

    goal = str(profile.get("goal") or "未设置").strip() or "未设置"
    plan_context = dict(plan_context or resolve_plan_context(message, profile, memories))
    plan_context["goal"] = goal
    result = (
        # 健康风险提示放在最前：它的优先级高于主目标、周计划和任何偏好，
        # 位置靠前也能降低被后续上下文冲淡的概率。
        f"{current_time_context}"
        f"{risk_directive(risk) if risk is not None else ''}"
        "【用户档案（稳定事实）】\n"
        f"{profile_summary(profile)}\n\n"
        # 优先级说明只此一段：原先这里另有一段【训练设计优先级】，与
        # format_plan_context 的一行版、以及从未被调用的 training_priority_context
        # 三处并存（BUG-03/BUG-04）。现在全部合并进 format_plan_context。
        f"{format_plan_context(plan_context)}"
        f"{daily_schedule_constraint(message, memories) if plan_context.get('decision') == 'follow_schedule' else ''}"
        f"{format_cross_session_memories(memories)}"
        f"{history_str}"
        f"【最新用户消息】：{message}"
    )
    if len(result) > AGENT_INPUT_MAX_CHARS:
        raise ContextInputError(
            "CONTEXT_BUDGET_EXCEEDED",
            "整理后的上下文仍然过长，请缩短当前消息或训练计划。",
            status_code=413,
        )
    return result

def _current_recovery_snapshot(garmin_recovery_hours: float) -> MuscleRecoverySnapshot:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    deps.soreness_store.cleanup_expired(now=now)
    return build_recovery_snapshot(
        deps.daily_record_store.list_records(),
        now=now,
        soreness=deps.soreness_store.list_reports(active_only=True, now=now),
        garmin_recovery_hours=garmin_recovery_hours,
        lookback_days=7,
        allow_external_models=deps.external_model_settings_store.get()["external_models_enabled"],
    )

def _soreness_report_payload(report: object) -> dict[str, object]:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    return {
        "id": report.id,
        "region": report.region,
        "muscle_ids": list(report.muscle_ids),
        "level": report.level,
        "reported_at": report.reported_at.isoformat(),
        "expires_at": report.expires_at.isoformat(),
        "evidence": report.evidence,
        "expired": bool(getattr(report, "expired", False)) or report.expires_at <= now,
    }

def _soreness_acknowledgement(reports: list[object]) -> str:
    labels = {
        "recovered": "已恢复",
        "sore": "酸痛，将相应减量",
        "painful": "疼痛，已升级为安全信号",
    }
    details = [f"{report.region}{labels.get(report.level, report.level)}" for report in reports]
    return "已记录：" + "；".join(details) + "。记录将在 72 小时后自动过期，可在数据管理中修改或删除。"

def _is_only_soreness_feedback(message: str) -> bool:
    normalized = re.sub(r"\s+", "", str(message or ""))
    stripped = normalized
    from fithealth_agent.muscle_recovery import REGION_ALIASES
    for aliases in REGION_ALIASES.values():
        for alias in aliases:
            stripped = stripped.replace(alias, "")
    stripped = re.sub(r"(?:有点|一点|稍微|轻微|很|非常|比较|还|又|酸痛|酸|疼痛|疼|痛|不酸|不疼|不痛|正常|好了|恢复了)", "", stripped)
    if re.search(r"怎么办|怎么处理|如何|建议|要不要|需要吗|能不能|可以吗", normalized):
        return False
    if len(re.sub(r"[，。！？、；;：:吗呢吧呀\?]", "", stripped)) < 4:
        return True
    return not bool(re.search(
        r"(?:训练计划|帮我|怎么练|如何练|能不能练|可以练|继续练|照常练|就要练|坚持练|"
        r"安排|推荐动作|生成计划|查看|查询|保存|修改|删除|怎么办|如何处理|建议|本周|这周)",
        re.sub(r"\s+", "", message),
    ))

def _immediate_memory_candidate(message: str, *, allow_external_models: bool) -> dict[str, object] | None:
    """Persist explicit durable facts as a pending candidate during chat.

    Logout remains a compatibility sweep, but durable facts must not depend on a
    browser close event.  This path intentionally uses the same information
    router and InfoStore normalisation as logout; it never auto-confirms facts.
    """
    if not allow_external_models or not _DURABLE_MEMORY_CUE.search(str(message or "")):
        return None
    decision = deps.route_information(
        [{"role": "user", "text": str(message)}],
        allow_external_models=True,
    )
    if not decision.get("save"):
        return None
    facts = [
        fact
        for fact in normalize_memory_facts(decision.get("facts"))
        if fact_retention_class(fact) in {"long_term", "medium"}
    ]
    if not facts:
        return None

    # Retries and later logout sweeps must not create another pending card for
    # the same active fact.  Different weekly schedules remain distinct here;
    # version conflict handling still applies when the user confirms them.
    deps.info_store.cleanup_expired()
    existing = {
        (str(fact.get("namespace")), str(fact.get("key")), str(fact.get("value")).casefold())
        for memory in deps.info_store.get_all()
        if isinstance(memory, dict)
        for fact in normalize_memory_facts(memory.get("facts"))
        if fact.get("status") in {"active", "rejected"} and fact_is_active(fact)
    }
    new_facts = [
        fact for fact in facts
        if (str(fact.get("namespace")), str(fact.get("key")), str(fact.get("value")).casefold())
        not in existing
    ]
    if not new_facts:
        return None
    memory_type = str(decision.get("type") or "training_feedback")
    entry = deps.info_store.add_entry(
        summary=str(decision.get("summary") or "")[:200],
        metadata={
            "reason": decision.get("reason", ""),
            "pipeline_stage": decision.get("pipeline_stage", "level3"),
            "capture": "chat_turn",
        },
        expires_at=None,
        memory_type=memory_type,
        importance=int(decision.get("importance", 1)),
        user_confirmed=False,
        facts=new_facts,
    )
    return {
        "entry_id": entry["id"],
        "summary": entry["summary"],
        "facts": [
            {"namespace": fact["namespace"], "key": fact["key"], "value": fact["value"]}
            for fact in entry["facts"]
        ],
    }

def _date_range_memory_candidate(constraint: dict[str, object]) -> dict[str, object] | None:
    if constraint.get("scope") != "date_range":
        return None
    fact = normalize_memory_facts([{
        "namespace": "health",
        "key": "injury_or_constraint",
        "status": "active",
        "evidence": str(constraint.get("value") or "")[:160],
        **constraint,
    }])
    if not fact:
        return None
    target = fact[0]
    identity = (target["namespace"], target["key"], str(target["value"]).casefold())
    for memory in deps.info_store.get_all():
        for existing in normalize_memory_facts(memory.get("facts") if isinstance(memory, dict) else None):
            if (
                existing.get("status") in {"active", "rejected"}
                and fact_is_active(existing)
                and (existing.get("namespace"), existing.get("key"), str(existing.get("value")).casefold()) == identity
            ):
                return None
    entry = deps.info_store.add_entry(
        summary=f"临时训练限制：{target['value']}",
        metadata={"capture": "chat_date_range"},
        expires_at=None,
        memory_type="constraint",
        importance=5,
        user_confirmed=False,
        facts=fact,
    )
    return {
        "entry_id": entry["id"],
        "summary": entry["summary"],
        "facts": [{
            "namespace": target["namespace"], "key": target["key"], "value": target["value"],
            "scope": target["scope"], "valid_from": target.get("valid_from"),
            "valid_until": target.get("valid_until"),
        }],
    }

def _acute_injury_memory_candidate(message: str, finding: RiskFinding) -> dict[str, object] | None:
    """Record an urgent, user-stated injury as a short-lived pending fact.

    This is deliberately local and deterministic.  An acute safety statement
    must survive an LLM timeout, but remains unconfirmed and expires under the
    existing recovery-status TTL unless the user confirms it.
    """
    if finding.level != "urgent":
        return None
    from fithealth_agent.muscle_recovery import REGION_ALIASES
    regions = [
        region for region, aliases in REGION_ALIASES.items()
        if any(alias in str(message or "") for alias in aliases)
    ]
    concise_value = "、".join(dict.fromkeys(regions)) + ("：" if regions else "") + finding.summary
    fact = normalize_memory_facts([{
        "namespace": "health",
        "key": "recovery_status",
        "value": concise_value[:120],
        "status": "active",
        "evidence": str(message or "").strip()[:160],
    }])
    if not fact:
        return None
    deps.info_store.cleanup_expired()
    candidate_fact = fact[0]
    identity = (
        str(candidate_fact["namespace"]),
        str(candidate_fact["key"]),
        str(candidate_fact["value"]).casefold(),
    )
    for memory in deps.info_store.get_all():
        if not isinstance(memory, dict):
            continue
        for existing in normalize_memory_facts(memory.get("facts")):
            existing_identity = (
                str(existing.get("namespace")), str(existing.get("key")),
                str(existing.get("value")).casefold(),
            )
            if existing.get("status") in {"active", "rejected"} and fact_is_active(existing) and existing_identity == identity:
                return None
    entry = deps.info_store.add_entry(
        summary=f"用户报告急性伤病信号：{finding.summary}",
        metadata={"capture": "chat_safety", "risk_level": finding.level, "risk_labels": list(finding.labels)},
        expires_at=None,
        memory_type="training_feedback",
        importance=5,
        user_confirmed=False,
        facts=fact,
    )
    return {
        "entry_id": entry["id"],
        "summary": entry["summary"],
        "facts": [{"namespace": "health", "key": "recovery_status", "value": candidate_fact["value"]}],
    }

async def chat(payload: dict[str, object]) -> ChatResult:
    turn = stage_request_context(ChatTurn.from_payload(payload))
    turn = stage_health_safety(turn)
    turn = stage_intent_routing(turn)
    turn = stage_local_navigation(turn)
    turn = stage_plan_context(turn)
    turn = stage_postprocess(turn)
    payload = turn.payload
    message = turn.message
    history = turn.history

    profile = turn.profile
    source = turn.source
    plan_context = payload["plan_context"]
    garmin_recovery_hours = payload["garmin_recovery_hours"]
    external_models_enabled = bool(turn.debug["external_models_enabled"])
    asked_regions = payload["soreness_prompt_regions"]
    pending_memory_entry_ids = payload["pending_memory_entry_ids"]
    saved_soreness: list[object] = []
    soreness_ack = ""
    memory_candidates: list[dict[str, object]] = []

    def _chat_response(
        reply: str,
        *,
        artifact: dict[str, object] | None = None,
        source: str | None = None,
        status_code: int = 200,
        include_soreness_ack: bool = True,
        **extra: object,
    ) -> ChatResult:
        final_reply = str(reply or "")
        if include_soreness_ack and soreness_ack:
            final_reply = soreness_ack + ("\n\n" + final_reply if final_reply else "")
        if memory_candidates:
            candidate_labels = [
                str(candidate.get("summary") or "检测到一条长期偏好或限制")
                for candidate in memory_candidates
            ]
            final_reply += (
                ("\n\n" if final_reply else "")
                + "检测到待确认的跨会话记忆："
                + "；".join(candidate_labels)
                + "。要加入跨会话记忆吗？"
            )
        body: dict[str, object] = {
            **extra,
            "reply": final_reply,
            "artifact": artifact,
            "soreness_saved": bool(saved_soreness),
            "soreness_reports": [
                _soreness_report_payload(item) for item in saved_soreness
            ],
            "asked_regions": asked_regions,
        }
        if source is not None:
            body["source"] = source
        if memory_candidates:
            body["memory_candidate"] = memory_candidates[0]
            body["memory_candidates"] = list(memory_candidates)
        return ChatResult(body=body, status_code=status_code)

    confirmation_decision = _memory_confirmation_decision(message)
    if pending_memory_entry_ids and confirmation_decision is not None:
        changed = 0
        try:
            for entry_id in pending_memory_entry_ids:
                result = (
                    deps.info_store.confirm_entry(entry_id)
                    if confirmation_decision
                    else deps.info_store.reject_entry(entry_id)
                )
                if result is not None:
                    changed += 1
        except ValueError as exc:
            return _chat_response(
                f"记忆确认失败：{exc}", source="memory_confirmation", status_code=409
            )
        if not changed:
            return _chat_response(
                "这些待确认记忆已不存在或已经处理。", source="memory_confirmation", status_code=404
            )
        return _chat_response(
            f"已{'加入' if confirmation_decision else '拒绝'} {changed} 条跨会话记忆。",
            source="memory_confirmation",
            memory_confirmation={"accepted": confirmation_decision, "count": changed},
        )

    user_health_statement = None
    if source == "chat":
        user_health_statement = await run_in_threadpool(deps.classify_user_health_statement, message)

    immediate_memory_candidate: dict[str, object] | None = None
    health_risk = None
    if source == "chat" and user_health_statement is not False:
        health_risk = screen_health_risk(message)

    recovery_snapshot = _current_recovery_snapshot(garmin_recovery_hours)
    temporary_constraint = temporary_constraint_for_message(message) if source == "chat" else None
    if temporary_constraint is not None and temporary_constraint.get("scope") == "date_range":
        try:
            date_range_candidate = _date_range_memory_candidate(temporary_constraint)
            if date_range_candidate is not None:
                memory_candidates.append(date_range_candidate)
        except (MemoryStoreDegradedError, OSError, ValueError):
            logger.exception("日期区间限制候选保存失败")
    soreness_reports = (
        deps.parse_soreness_reply(message, asked_regions)
        if source == "chat" and (bool(asked_regions) or user_health_statement is not False)
        else []
    )
    if (
        source == "chat"
        and not soreness_reports
        and not (health_risk is not None and health_risk.level in {"urgent", "emergency"})
        and soreness_reply_needs_clarification(message, asked_regions)
    ):
        return _chat_response(
            "你说了当前感受，但我刚才询问了多个部位。请明确是哪一个区域，例如“手臂有点酸”或“腿部正常”。",
            source="soreness_clarification",
        )

    if soreness_reports:
        try:
            saved_soreness = list(deps.soreness_store.add_reports(soreness_reports))
        except (OSError, ValueError) as exc:
            logger.exception("肌群酸痛反馈保存失败")
            return _chat_response(f"酸痛反馈未能保存：{exc}", status_code=503)
        soreness_ack = _soreness_acknowledgement(saved_soreness)
        recovery_snapshot = _current_recovery_snapshot(garmin_recovery_hours)
    active_soreness_reports = deps.soreness_store.list_reports(active_only=True)

    # AGENT-01：确定性健康风险筛查。
    # 放在意图路由之前有三个原因：(1) 急症不该等一次外部模型往返；
    # (2) 关闭联网模型或网络故障时同样要生效；(3) 这条判断不依赖任何
    # 已确认记忆——用户在**当前这条消息**里新出现的症状本来就不在记忆里。
    # 只筛查对话消息；上传的训练计划正文里出现症状词不算用户主诉。
    painful_regions = [report.region for report in soreness_reports if report.level == "painful"]
    if painful_regions:
        health_risk = merge_findings(health_risk, acute_pain_finding(painful_regions))
    if source == "chat" and health_risk is not None and health_risk.level == "urgent":
        try:
            acute_candidate = _acute_injury_memory_candidate(message, health_risk)
            if acute_candidate is not None:
                memory_candidates.append(acute_candidate)
        except (MemoryStoreDegradedError, OSError, ValueError):
            logger.exception("急性伤病候选保存失败")
    if health_risk is not None and health_risk.level == "emergency":
        # Emergency guidance stays visually undiluted. The structured flag still
        # tells the client that any soreness report from this turn was saved.
        return _chat_response(
            emergency_reply(health_risk),
            source="health_risk_block",
            include_soreness_ack=False,
            health_risk={"level": health_risk.level, "signals": list(health_risk.labels)},
            workflow_state=str(PlanWorkflowState.CONSTRAINT_CONFLICT),
        )
    if source == "chat" and (health_risk is None or health_risk.level in {CAUTION, URGENT}):
        try:
            durable_candidate = await run_in_threadpool(
                _immediate_memory_candidate,
                message,
                allow_external_models=external_models_enabled,
            )
            if durable_candidate is not None:
                memory_candidates.append(durable_candidate)
        except (MemoryStoreDegradedError, OSError, ValueError):
            logger.exception("即时长期记忆候选保存失败")
    immediate_memory_candidate = memory_candidates[0] if memory_candidates else None

    if soreness_reports and _is_only_soreness_feedback(message):
        deps.info_store.cleanup_expired()
        memories = deps.info_store.get_context_memories(n=5)
        resolved_plan_context = resolve_plan_context(
            message, profile, memories, recovery=recovery_snapshot,
            soreness_reports=active_soreness_reports,
        )
        reply = ""
        if painful_regions and health_risk is not None:
            reply = urgent_plan_block_note(health_risk)
        return _chat_response(
            reply,
            source="local_soreness_feedback",
            plan_context=resolved_plan_context,
            health_risk=(
                {"level": health_risk.level, "signals": list(health_risk.labels)}
                if health_risk is not None else None
            ),
            workflow_state=resolved_plan_context["workflow_state"],
            **({"memory_candidate": immediate_memory_candidate} if immediate_memory_candidate else {}),
            **({"memory_candidates": memory_candidates} if memory_candidates else {}),
        )

    if source == "uploaded_plan":
        updates, updated_fields = {}, []
        chat_intent = None
    else:
        chat_intent = await run_in_threadpool(
            deps.route_chat_intent,
            message,
            allow_external_models=external_models_enabled,
        )
        updates, updated_fields = validate_profile_tool_updates(
            chat_intent.profile_updates, message
        )

    profile_update_artifact = (
        {
            "type": "profile_update",
            "updates": updates,
            "fields": updated_fields,
            **(
                {"equipment_diff": equipment_change_preview(profile, updates)}
                if equipment_change_preview(profile, updates) is not None else {}
            ),
        }
        if updates
        else None
    )
    pending_view_artifact: dict[str, object] | None = None
    pending_reply_prefix = ""
    pending_view_source: str | None = None

    # BUG-02：外部意图路由不可用时（关闭联网模型、缺 API key、超时、网络抖动），
    # route_chat_intent 会返回一个所有位都为 False 的空 ChatIntent，于是
    # "查看训练记录"这类**纯本地读操作**一路掉到下面的 503——而欢迎语里
    # 明明写着可以这么输入。这里用已有的确定性规则兜底，让本地能力在离线
    # 状态下同样可用。
    wants_training_records = (
        chat_intent is not None and chat_intent.view_training_records
    ) or (source == "chat" and is_training_record_query(message))

    if wants_training_records:
        records = _training_record_items(deps.daily_record_store.list_records())
        default_date = (
            (chat_intent.training_records_date if chat_intent is not None else "")
            or _requested_record_date(message)
            or (
                records[0]["date"]
                if records
                else datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
            )
        )
        navigation_only = navigation_only_message(message)
        pending_view_artifact = {
            "type": "training_records",
            "default_date": default_date,
        }
        pending_reply_prefix = "已打开本地训练记录。选择日期后，可在右侧下拉框查看当天的每一条训练。"
        pending_view_source = "local_training_records"
        if navigation_only or not external_models_enabled:
            offline_note = (
                "\n\n外部模型当前已关闭，因此暂时无法继续回答同一条消息中的其他问题。"
                if not navigation_only and not external_models_enabled else ""
            )
            return _chat_response(
                pending_reply_prefix + offline_note,
                artifact=pending_view_artifact,
                source=pending_view_source,
            )

    wants_nutrition_records = (
        chat_intent is not None and chat_intent.view_nutrition_records
    ) or (
        source == "chat"
        and any(word in message for word in ("查看饮食", "查看营养", "营养数据", "饮食数据", "摄入数据"))
    )
    if wants_nutrition_records:
        default_date = (
            (chat_intent.nutrition_records_date if chat_intent is not None else "")
            or _nutrition_record_date(message)
            or datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        )
        navigation_only = navigation_only_message(message)
        pending_view_artifact = pending_view_artifact or {
            "type": "nutrition_records",
            "default_date": default_date,
        }
        nutrition_prefix = "已打开本地营养记录。选择日期后，可在右侧下拉框查看当天的不同饮食组。"
        pending_reply_prefix = "\n\n".join(filter(None, (pending_reply_prefix, nutrition_prefix)))
        pending_view_source = pending_view_source or "local_nutrition_records"
        if navigation_only or not external_models_enabled:
            offline_note = (
                "\n\n外部模型当前已关闭，因此暂时无法继续回答同一条消息中的其他问题。"
                if not navigation_only and not external_models_enabled else ""
            )
            return _chat_response(
                pending_reply_prefix + offline_note,
                artifact=pending_view_artifact,
                source=pending_view_source,
            )

    if chat_intent is not None and chat_intent.save_existing_training_plan:
        # BUG-05：优先用服务端缓存的完整正文。回捞聊天历史只作为进程重启
        # 后的兜底——history 已被上下文预算截断过，可能是残片。
        # 用 find() 而不是 latest()：一个会话里可能生成过多份计划，用户说
        # "保存那份腿的计划"时无条件取最后一份会静默存错。
        draft = deps.plan_draft_cache.find(
            subject=chat_intent.saved_plan_subject or "",
            suggested_date=chat_intent.saved_plan_date or "",
        )
        content = draft.content if draft is not None else most_recent_complete_training_plan(history)
        if not content:
            return _chat_response(
                "没有找到可保存的完整训练计划。\n\n"
                "可能的原因：还没有生成过计划；或者页面刷新过、服务重启过，"
                "导致上一份计划的正文已经不在。请让我重新生成一份，"
                "再点击计划下方的“保存计划”。",
                source="local_plan_save",
                status_code=400,
            )
        subject = (
            (draft.subject if draft is not None else "")
            or chat_intent.saved_plan_subject
            or extract_plan_subject(content)
        )

        title = plan_card_title(
            (draft.title if draft is not None else "")
            or infer_plan_title(content, subject),
            subject,
        )

        plan_date = (
            chat_intent.saved_plan_date
            or (draft.suggested_date if draft is not None else "")
            or datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        )
        deps.info_store.cleanup_expired()
        memories = deps.info_store.get_context_memories(n=5)
        expected_subject = subject
        try:
            saved_day = date.fromisoformat(plan_date)
            scheduled_entry = confirmed_weekly_schedule_entry(deps.info_store.get_all(), saved_day)
            if (
                (not subject or is_generic_training_subject(subject))
                and scheduled_entry is not None
                and scheduled_entry.get("type") != "rest"
            ):
                expected_subject = str(scheduled_entry.get("subject") or subject)
        except ValueError:
            pass
        safety_constraints = [
            str(fact.get("value") or "")
            for fact in resolve_confirmed_memory_facts(memories)
            if fact.get("status", "active") == "active"
            and fact.get("user_confirmed", True)
            and fact.get("namespace") == "health"
            and fact.get("key") in {"injury_or_constraint", "recovery_status"}
        ]
        plan_validation = validate_generated_training_plan(
            content,
            memories,
            expected_subject,
            recovery=recovery_snapshot,
            safety_constraints=safety_constraints,
            resolver=_plan_muscle_resolver,
            check_subject=False,
        )
        saved_goal_alignment = await run_in_threadpool(
            deps.validate_plan_goal_alignment,
            content,
            user_request=message,
            fallback_subject=expected_subject,
            weekly_subject=(
                str(scheduled_entry.get("subject") or "")
                if "scheduled_entry" in locals() and scheduled_entry is not None
                else ""
            ),
            schedule_decision="override_today" if subject and not is_generic_training_subject(subject) else "follow_schedule",
            allow_external_models=external_models_enabled,
        )
        if not saved_goal_alignment.get("passed"):
            missing = "、".join(saved_goal_alignment.get("missing_subjects") or [expected_subject])
            plan_validation.append(f"计划未覆盖用户要求的训练目标：{missing}")
        if plan_validation:
            return _chat_response(
                "该训练计划未通过已确认记忆的后端校验，因此不能保存。\n\n## 计划校验未通过\n"
                + "\n".join(f"- {item}" for item in plan_validation)
                + "\n请先修正以上问题，再保存训练计划。"
                "\n\n你还问了另一件事；处理完这项安全冲突后，我再继续回答。",
                source="local_plan_save",
                status_code=409,
                plan_validation={"passed": False, "violations": plan_validation},
            )
        return _chat_response(
            "已找到本次会话中最近生成的完整训练计划，请确认下方信息后保存。",
            artifact={
                "type": "training_plan",
                "subject": subject,
                "title": title,
                "content": content,
                "source": "agent_generated",
                "suggested_date": plan_date,
                # 带上 draft_id，让后续 /plans 也走"按 id 取服务端原文"这条路，
                # 而不是退回靠前端传值——否则这条路径只是碰巧内容完整才没出错。
                **({"draft_id": draft.id} if draft is not None else {}),
            },
            source="local_plan_save",
        )

    if (chat_intent is not None and chat_intent.view_profile) or (
        source == "chat" and is_profile_query(message)
    ):
        deps.info_store.cleanup_expired()
        navigation_only = navigation_only_message(message)
        profile_prefix = (
            "## 个人档案\n"
            + profile_summary(profile, include_birth_date=False)
            + "\n\n## 跨会话记忆\n"
            + confirmed_memory_profile(deps.info_store.get_all())
            + "\n\n待确认记忆不会用于后续对话；可在“数据管理 → 临时记忆”中查看、确认或删除。"
        )
        pending_reply_prefix = "\n\n".join(filter(None, (pending_reply_prefix, profile_prefix)))
        pending_view_source = pending_view_source or "local_profile"
        if navigation_only or not external_models_enabled:
            offline_note = (
                "\n\n外部模型当前已关闭，因此暂时无法继续回答同一条消息中的其他问题。"
                if not navigation_only and not external_models_enabled else ""
            )
            return _chat_response(
                pending_reply_prefix + offline_note,
                artifact=pending_view_artifact,
                source=pending_view_source,
            )

    projected = merge_profile_updates_with_existing(profile, updates) if updates else profile
    is_complete = deps.profile_store.is_complete(projected)
    if not is_complete:
        missing = deps.profile_store.missing_fields(projected)
        return _chat_response(
            onboarding_reply(projected, missing, updated_fields)
            + "\n\n你还问了另一件事；补完档案后，我再继续回答。",
            artifact=profile_update_artifact,
            source="onboarding",
        )

    if updated_fields:
        return _chat_response(
            "\u7528\u6237\u4fe1\u606f\u5df2\u5b8c\u5584\uff0c\u8bf7\u786e\u8ba4\u4e0b\u65b9\u53d8\u66f4\u540e\u7ee7\u7eed\u3002\n\n"
            + profile_summary(projected, include_birth_date=False),
            artifact=profile_update_artifact,
            source="profile_update",
        )

    try:
        weekly_reply = deps.build_current_week_reply(
            message,
            health_store=deps.health_store,
            daily_record_store=deps.daily_record_store,
            profile=profile,
            today=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
            recovery=recovery_snapshot,
            soreness_reports=active_soreness_reports,
        )
    except (OSError, ValueError, sqlite3.Error):
        logger.exception("本周数据本地查询失败")
        return _chat_response("本周数据读取失败，请检查已导入数据是否完整。", status_code=500)
    if weekly_reply is not None:
        return _chat_response(weekly_reply, source="local_weekly_summary")

    if not external_models_enabled:
        # BUG-02：以前这里只丢一句"外部模型已关闭"，用户不知道离线到底还能做什么。
        # 上面的本地分支（训练记录 / 个人档案 / 本周汇总）已经先行拦截，能走到
        # 这里说明确实需要模型；给出可直接照抄的本地指令，比空泛一句有用得多。
        local_commands = "「查看训练记录」「查看个人信息」「查看本周数据」"
        hint = (
            f"这类问题需要模型参与。不过你可以直接输入 {local_commands} 来查看已保存的本地数据；"
            "健康数据的导入、训练组编辑、备份与删除也都不受影响。"
            if is_training_related(message)
            else f"你仍可使用本地功能：输入 {local_commands}，以及健康数据导入、训练编辑、备份和删除。"
        )
        return _chat_response(
            "外部模型已关闭，因此不会发送你的对话、档案或记忆。" + hint,
            source="external_models_disabled",
            status_code=503,
        )

    try:
        deps.info_store.cleanup_expired()
        memory_intent = (
            "create_training_plan"
            if chat_intent is not None and chat_intent.create_training_plan
            else "search_youtube_video" if "youtube" in message.casefold() or "视频" in message else ""
        )
        memories = deps.info_store.get_context_memories(n=5, intent=memory_intent)
        candidate_memories = deps.info_store.get_enforceable_memories() if hasattr(deps.info_store, "get_enforceable_memories") else None
        enforceable_memories = candidate_memories if isinstance(candidate_memories, list) else memories
        routed_plan_intent = (
            {
                "schedule_decision": chat_intent.schedule_decision,
                "subject": chat_intent.training_plan_subject,
                "requested_subjects": getattr(chat_intent, "requested_subjects", []),
                "temporary_health_constraints": list(dict.fromkeys(
                    chat_intent.temporary_health_constraints
                    + ([str(temporary_constraint["value"])] if temporary_constraint else [])
                )),
                "excluded_subjects": chat_intent.excluded_subjects,
                "needs_clarification": chat_intent.needs_clarification,
            }
            if chat_intent is not None and chat_intent.create_training_plan
            else None
        )
        resolved_plan_context = resolve_plan_context(
            message,
            profile,
            enforceable_memories,
            recovery=recovery_snapshot,
            routed_intent=routed_plan_intent,
            soreness_reports=active_soreness_reports,
        )
        scheduled_plan = (
            scheduled_plan_for_message(message, deps.info_store.get_all())
            if resolved_plan_context.get("decision") == "follow_schedule"
            else None
        )
        if scheduled_plan is not None:
            scheduled_date, scheduled_subject = scheduled_plan
            resolved_plan_context.update({
                "scheduled_subject": scheduled_subject,
                "scheduled_date": scheduled_date.isoformat(),
                "effective_subject": scheduled_subject,
            })
        if (
            chat_intent is not None
            and chat_intent.create_training_plan
            and resolved_plan_context.get("blocking_reasons")
        ):
            return _chat_response(
                "当前请求与已确认的安全限制冲突，不能按原要求生成计划。"
                "请先说明是否要修改或清除该安全限制。\n\n"
                "当前生效的限制："
                + "；".join(resolved_plan_context.get("active_safety_constraints") or ["（未列出）"])
                + "\n\n你还问了另一件事；处理完这项安全冲突后，我再继续回答。",
                source="plan_context_safety_block",
                status_code=409,
                plan_context=resolved_plan_context,
                workflow_state=str(PlanWorkflowState.CONSTRAINT_CONFLICT),
            )
        if (
            chat_intent is not None
            and chat_intent.create_training_plan
            and resolved_plan_context.get("decision") == "rest_today"
        ):
            scheduled_subject = resolved_plan_context.get("scheduled_subject")
            scheduled_note = f"，原周计划科目为{scheduled_subject}" if scheduled_subject else ""
            rest_reply = "已将本次安排为休息" + scheduled_note + "。今天不生成训练计划；恢复后可再安排下一次训练。"
            return _chat_response(
                rest_reply,
                artifact=profile_update_artifact,
                source="plan_context_rest",
                plan_context=resolved_plan_context,
                workflow_state=str(resolved_plan_context["workflow_state"]),
            )
        if chat_intent is not None and chat_intent.create_training_plan and resolved_plan_context.get("clarification_required"):
            return _chat_response(
                "你已表示本次不按周计划训练，但还没有说明是休息还是更换训练科目。请明确选择后，我再生成计划。",
                source="plan_context_clarification",
                status_code=409,
                plan_context=resolved_plan_context,
                workflow_state=str(PlanWorkflowState.NEEDS_CLARIFICATION),
            )
        avoided_youtube_channels = youtube_channels_to_avoid(memories, message)
        agent = deps.create_fithealth_agent(
            avoid_youtube_channels=avoided_youtube_channels
        )
        try:
            agent_input = build_agent_input(message, profile, history, memories, risk=health_risk, plan_context=resolved_plan_context)
        except ContextInputError as exc:
            return context_error_response(exc)
        answer = format_response(await run_in_threadpool(agent.run, agent_input))
        if pending_reply_prefix:
            answer = pending_reply_prefix + "\n\n" + answer
        artifact = None
        if source == "uploaded_plan" and looks_like_complete_training_plan(answer):
            subject = extract_plan_subject(answer, str(plan_context.get("subject") or ""))
            artifact = {
                "type": "training_plan",
                "subject": subject,
                "title": infer_plan_title(answer, subject),
                "content": answer,
                "source": "uploaded_optimized",
                "suggested_date": str(plan_context.get("suggested_date") or ""),
            }
        elif (
            source == "chat"
            and chat_intent is not None
            and chat_intent.create_training_plan
            and looks_like_complete_training_plan(answer)
        ):
            if scheduled_plan is not None:
                scheduled_date, subject = scheduled_plan
                suggested_date = scheduled_date.isoformat()
            else:
                subject = chat_intent.training_plan_subject
                suggested_date = ""
            artifact = {
                "type": "training_plan",
                "subject": subject if subject.endswith(("训练", "计划")) else subject + "训练",
                "title": plan_card_title(chat_intent.training_plan_title, subject),
                "content": answer,
                "source": "agent_generated",
                "suggested_date": suggested_date,
            }

        elif scheduled_plan is not None and looks_like_complete_training_plan(answer):
            scheduled_date, scheduled_subject = scheduled_plan
            artifact = {
                "type": "training_plan",
                "subject": scheduled_subject,
                "title": infer_plan_title(answer, scheduled_subject),
                "content": answer,
                "source": "agent_generated",
                "suggested_date": scheduled_date.isoformat(),
            }
        plan_validation: list[str] = []
        first_plan_validation: list[str] = []
        plan_auto_correction: dict[str, object] = {
            "attempted": False,
            "passed": False,
            "first_violations": [],
            "final_violations": [],
        }
        # AGENT-01（urgent 档）：急性损伤信号下确定性地拒绝产出可保存的计划。
        # 放在计划校验之前——无论模型写了什么，后端都不放行这个 artifact。
        if (
            artifact
            and artifact.get("type") == "training_plan"
            and health_risk is not None
            and health_risk.blocks_training_plan()
        ):
            artifact = None
            answer += "\n\n" + urgent_plan_block_note(health_risk)
        if artifact and artifact.get("type") == "training_plan":
            expected_plan_subject = str(
                resolved_plan_context.get("effective_subject")
                or artifact.get("subject")
                or ""
            )
            plan_validation = validate_generated_training_plan(
                answer,
                enforceable_memories,
                expected_plan_subject,
                recovery=recovery_snapshot,
                safety_constraints=list(resolved_plan_context.get("active_safety_constraints") or []),
                explicitly_requested=set((resolved_plan_context.get("muscle_recovery") or {}).get("explicitly_requested") or []),
                resolver=_plan_muscle_resolver,
                check_subject=False,
            )
            goal_alignment = await run_in_threadpool(
                deps.validate_plan_goal_alignment,
                answer,
                user_request=message,
                requested_subjects=(getattr(chat_intent, "requested_subjects", []) if chat_intent is not None else []),
                fallback_subject=expected_plan_subject,
                weekly_subject=str(resolved_plan_context.get("scheduled_subject") or ""),
                schedule_decision=str(resolved_plan_context.get("decision") or "follow_schedule"),
                allow_external_models=external_models_enabled,
            )
            if not goal_alignment.get("passed"):
                missing = "、".join(goal_alignment.get("missing_subjects") or [expected_plan_subject])
                plan_validation.append(f"计划未覆盖用户要求的训练目标：{missing}")
            if plan_validation:
                first_plan_validation = list(plan_validation)
                plan_auto_correction.update({
                    "attempted": True,
                    "first_violations": first_plan_validation,
                })
                correction_prompt = (
                    "你刚才生成的训练计划未通过后端安全校验。请只输出一份完整、可直接使用的修正版训练计划，"
                    "不要解释校验过程，也不要遗漏原请求的训练目标。必须逐项消除以下违规：\n"
                    + "\n".join(f"- {item}" for item in first_plan_validation)
                    + "\n\n原始用户请求：\n" + message[:4000]
                    + "\n\n第一次计划：\n" + str(artifact.get("content") or answer)[:24000]
                )
                try:
                    correction_agent = deps.create_fithealth_agent(
                        avoid_youtube_channels=avoided_youtube_channels
                    )
                    corrected_answer = format_response(
                        await run_in_threadpool(correction_agent.run, correction_prompt)
                    )
                except Exception:  # noqa: BLE001 - 自动修正失败应降级为明确的校验失败，而非整次 500
                    logger.exception("训练计划自动修正调用失败")
                    corrected_answer = ""
                corrected_artifact = dict(artifact)
                corrected_artifact["content"] = corrected_answer
                corrected_artifact["source"] = "agent_auto_corrected"
                if not corrected_answer:
                    plan_validation = first_plan_validation + ["自动修正服务调用失败"]
                elif not looks_like_complete_training_plan(corrected_answer):
                    plan_validation = ["自动修正结果不是完整训练计划"]
                else:
                    plan_validation = validate_generated_training_plan(
                        corrected_answer,
                        enforceable_memories,
                        expected_plan_subject,
                        recovery=recovery_snapshot,
                        safety_constraints=list(resolved_plan_context.get("active_safety_constraints") or []),
                        explicitly_requested=set((resolved_plan_context.get("muscle_recovery") or {}).get("explicitly_requested") or []),
                        resolver=_plan_muscle_resolver,
                        check_subject=False,
                    )
                    corrected_alignment = await run_in_threadpool(
                        deps.validate_plan_goal_alignment,
                        corrected_answer,
                        user_request=message,
                        requested_subjects=(getattr(chat_intent, "requested_subjects", []) if chat_intent is not None else []),
                        fallback_subject=expected_plan_subject,
                        weekly_subject=str(resolved_plan_context.get("scheduled_subject") or ""),
                        schedule_decision=str(resolved_plan_context.get("decision") or "follow_schedule"),
                        allow_external_models=external_models_enabled,
                    )
                    if not corrected_alignment.get("passed"):
                        missing = "、".join(corrected_alignment.get("missing_subjects") or [expected_plan_subject])
                        plan_validation.append(f"计划未覆盖用户要求的训练目标：{missing}")
                plan_auto_correction["final_violations"] = list(plan_validation)
                plan_auto_correction["passed"] = not plan_validation
                if plan_validation:
                    artifact = None
                    answer = (corrected_answer or answer) + "\n\n## 自动修正后仍未通过计划校验\n" + "\n".join(
                        f"- {item}" for item in plan_validation
                    ) + "\n本次不提供可保存的训练计划，请调整限制或训练目标后重试。"
                else:
                    artifact = corrected_artifact
                    answer = corrected_answer
                if pending_reply_prefix:
                    answer = pending_reply_prefix + "\n\n" + answer
            if artifact is not None and not plan_validation:
                # BUG-05：校验通过后立刻在服务端留一份完整正文；自动修正通过
                # 的计划也必须走同一条服务端草稿链。
                draft = deps.plan_draft_cache.remember(
                    content=str(artifact.get("content") or ""),
                    subject=str(artifact.get("subject") or ""),
                    title=str(artifact.get("title") or ""),
                    suggested_date=str(artifact.get("suggested_date") or ""),
                )
                artifact["draft_id"] = draft.id
        if artifact is not None or first_plan_validation:
            try:
                usage_violations = first_plan_validation or plan_validation
                for fact_id, detail in plan_validation_fact_usage(
                    enforceable_memories, usage_violations
                ):
                    deps.info_store.log_fact_usage(
                        [fact_id],
                        action="plan_auto_correction" if first_plan_validation else "plan_validation",
                        detail=(detail + ("；自动修正通过" if first_plan_validation and not plan_validation else ""))[:500],
                    )
            except (MemoryStoreDegradedError, OSError):
                logger.exception("记忆使用日志保存失败")
        response_artifact = artifact or profile_update_artifact or pending_view_artifact
        if response_artifact is None and source == "chat" and any(
            word in message for word in ("饮食", "营养", "摄入", "碳水", "蛋白质", "脂肪", "热量")
        ):
            response_artifact = {
                "type": "nutrition_records",
                "default_date": datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
            }
        response_extra: dict[str, object] = {
            "plan_context": resolved_plan_context,
            "workflow_state": str(
                state_after_generation(artifact=artifact, validation_failed=bool(plan_validation))
            ),
        }
        if profile_update_artifact is not None:
            response_extra["profile_update"] = profile_update_artifact
        if health_risk is not None:
            response_extra["health_risk"] = {
                "level": health_risk.level,
                "signals": list(health_risk.labels),
            }
        if immediate_memory_candidate is not None:
            response_extra["memory_candidate"] = immediate_memory_candidate
        if memory_candidates:
            response_extra["memory_candidates"] = memory_candidates
        if plan_validation:
            response_extra["plan_validation"] = {"passed": False, "violations": plan_validation}
        elif artifact and artifact.get("type") == "training_plan":
            response_extra["plan_validation"] = {"passed": True, "violations": []}
        if plan_auto_correction["attempted"]:
            response_extra["plan_auto_correction"] = plan_auto_correction
        return _chat_response(
            answer,
            artifact=response_artifact,
            source=pending_view_source or "agent",
            **response_extra,
        )
    except HelloAgentsException:
        logger.exception("Agent 模型配置或调用失败")
        return _chat_response(
            "模型服务当前不可用；健康数据查询仍可通过“查看本周数据”使用本地汇总。",
            status_code=503,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Agent 对话处理失败")
        return _chat_response("服务暂时不可用，请稍后重试。", status_code=500)
