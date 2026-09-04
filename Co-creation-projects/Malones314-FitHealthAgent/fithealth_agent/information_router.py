"""information_router.py

三级信息路由流水线，在用户点击退出后决定是否保存此次对话摘要。

Pipeline:
  Level 1 — 本地敏感信息拦截：禁止将敏感内容发送到外部模型
  Level 2 — Function Calling：仅限模型明确调用保存工具时生成待确认记忆
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fithealth_agent.info_store import is_negative_preference_value

# ---------------------------------------------------------------------------
# 环境配置
# ---------------------------------------------------------------------------
LLM_LITE_API_KEY: str | None = os.getenv("LLM_LITE_API_KEY") or os.getenv("LLM_API_KEY")
LLM_LITE_BASE_URL: str = (os.getenv("LLM_LITE_BASE_URL") or "https://api.deepseek.com").rstrip("/")
# 使用更快的 deepseek-chat
LLM_LITE_MODE: str = os.getenv("LLM_LITE_MODE_ID", "deepseek-chat")

# ---------------------------------------------------------------------------
# Level 1 — 敏感信息拦截
# ---------------------------------------------------------------------------
_SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?:(?:\+?86)?[\s\-_]?)1[3-9]\d{9}"),
    "idcard": re.compile(r"\b\d{17}[\dXx]\b"),
    "credit_card": re.compile(
        r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b"
    ),
}

_SENSITIVE_KEYWORDS: list[str] = [
    "密码",
    "银行卡",
    "信用卡",
    "身份证",
    "手机号",
    "家庭住址",
    "护照",
]


def _level1_sensitive_check(text: str) -> dict[str, Any]:
    """检测是否含有敏感个人信息，若有则直接拒绝保存。"""
    hits: list[str] = []
    for name, pattern in _SENSITIVE_PATTERNS.items():
        if pattern.search(text):
            hits.append(f"regex:{name}")
    for kw in _SENSITIVE_KEYWORDS:
        if kw in text:
            hits.append(f"keyword:{kw}")
    return {"sensitive": bool(hits), "hits": hits}


_MEMORY_TYPES = {"preference", "constraint", "plan_decision", "training_feedback"}
_FACT_NAMESPACES = ["youtube", "training", "health", "plan"]
_FACT_KEYS = [
    "avoid_channel", "avoid_exercise", "prefer_exercise", "max_rpe", "max_sets_per_exercise", "max_total_sets", "required_plan_elements",
    "injury_or_constraint", "recovery_status", "preference", "decision", "weekly_schedule",
]
# ---------------------------------------------------------------------------
# Level 2 — Function Calling 判断
# ---------------------------------------------------------------------------

MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": (
            "Save one durable user fact only when the user explicitly stated it in this "
            "conversation. Never call for questions, generic advice, assistant suggestions, "
            "or ambiguous information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Chinese factual summary, max 200 characters."},
                "type": {"type": "string", "enum": sorted(_MEMORY_TYPES)},
                "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                "avoid_youtube_channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Channels the user explicitly dislikes or asks not to recommend; otherwise an empty array.",
                },
                "facts": {
                    "type": "array",
                    "maxItems": 8,
                    "description": "Explicit durable facts only. Use an empty array if none apply.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "namespace": {"type": "string", "enum": _FACT_NAMESPACES},
                            "key": {"type": "string", "enum": _FACT_KEYS},
                            "value": {"oneOf": [{"type": "string", "maxLength": 500}, {"type": "number"}]},
                            "status": {"type": "string", "enum": ["active", "cleared"]},
                            "evidence": {"type": "string", "minLength": 2, "maxLength": 160, "description": "Exact short quote copied from the user message; never quote the assistant."},
                            "duration_type": {"type": "string", "enum": ["temporary", "long_term", "permanent"]},
                            "valid_from": {"type": "string", "description": "ISO date YYYY-MM-DD when the fact starts applying."},
                            "valid_until": {
                                "oneOf": [{"type": "string"}, {"type": "null"}],
                                "description": "Inclusive ISO end date for temporary facts; null for long-term facts.",
                            },
                        },
                        "required": ["namespace", "key", "value", "status", "evidence"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["summary", "type", "importance", "avoid_youtube_channels", "facts"],
            "additionalProperties": False,
        },
    },
}

_SYSTEM_PROMPT = """Route this Chinese fitness conversation to the save_memory tool only when it contains
an explicit, durable user fact: a stable preference, injury/non-negotiable constraint, agreed
plan change, or completed-training/recovery feedback. Never save questions, general advice,
model suggestions, examples, or a user's hypothetical statement. Call no tool when uncertain.
Stable posture or chronic conditions such as sedentary status or anterior pelvic tilt are
health.injury_or_constraint facts with duration_type=long_term and no valid_until. Recent or
today-only pain, soreness, fatigue, and recovery state are health.recovery_status facts with
duration_type=temporary, valid_from set to today's date, and a conservative valid_until based on
the user's explicit duration; when no duration is stated use 7 days. When they request a body-part intensity adjustment for future
training, save it as a plan.preference fact. When the user explicitly sets a maximum number of sets per exercise, save training.max_sets_per_exercise as a numeric fact. When the user explicitly sets a maximum total number of working sets, save training.max_total_sets as a numeric fact. When a confirmed constraint requires specific plan elements, save each required element as a training.required_plan_elements fact, using a concise separator such as |. Do not invent required elements without explaining them to the user and getting confirmation. Save current fatigue, soreness, or recovery state as health.recovery_status, not injury_or_constraint. A single tool call may include several explicit facts. Every fact must include evidence copied exactly from a user message; never infer evidence from assistant text.
Use training.prefer_exercise only for a positive action preference, with an action-only value such as "深蹲". If the user says they dislike, avoid, do not want, or cannot do an action, use training.avoid_exercise with the action-only value instead; never store a negative sentence as prefer_exercise.
For posture or muscle-condition facts, use these canonical values when applicable: 骨盆前倾、骨盆后倾、下交叉综合征、臀肌无力、髂腰肌紧张、腹部核心薄弱、腘绳肌紧张、竖脊肌紧张、体态矫正. Do not combine several conditions into one fact; emit separate facts when the user explicitly states several conditions.
When the user explicitly says a previously mentioned temporary symptom has recovered or no longer
hurts, emit the matching health.recovery_status fact with status=cleared. Do not replace it with a
new positive-sounding active symptom fact.
When the user explicitly agrees to a recurring weekly training schedule, save exactly one
plan.weekly_schedule fact. Its value may use the legacy compact form
{"mon":"胸部训练","tue":"背部训练"}, or the structured form
{"enabled":true,"effective_from":"2026-08-24","effective_until":"2026-10-31","days":{"mon":{"type":"training","subject":"胸部训练"},"wed":{"type":"rest"},"fri":{"type":"aerobic","subject":"跑步"}}}.
Use only mon/tue/wed/thu/fri/sat/sun under days. A rest day may also be written as null.
Use type=training for strength or other training, type=aerobic for an aerobic day, and type=rest
for rest. Include effective dates or enabled=false only when the user explicitly states them.
Use Function Calling only and do not produce prose."""


def _no_save(reason: str) -> dict[str, Any]:
    return {
        "save": False,
        "reason": reason,
        "summary": "",
        "type": "training_feedback",
        "importance": 1,
        "facts": [],
        "rejected_facts": 0,
        "fact_validation": "未生成可保存事实",
        "raw": None,
    }


def _tool_arguments(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}



def _user_evidence_text(transcript: str) -> str:
    return "\n".join(
        line.split("] ", 1)[1]
        for line in str(transcript or "").splitlines()
        if line.startswith("[user] ") and "] " in line
    )


def _evidence_supported(evidence: object, user_text: str) -> bool:
    if not isinstance(evidence, str):
        return False
    evidence = " ".join(evidence.split()).strip()
    if len(evidence) < 2:
        return False
    user_messages = [
        " ".join(part.split())
        for part in str(user_text or "").split("\n<USER_MESSAGE>\n")
        if part.strip()
    ]
    punctuation = " \t\r\n，。！？；：、“”’（）()[]【】"
    compact_evidence = "".join(char for char in evidence if char not in punctuation).casefold()
    for message in user_messages:
        if evidence.casefold() in message.casefold():
            return True
        compact_message = "".join(char for char in message if char not in punctuation).casefold()
        if len(compact_evidence) >= 2 and compact_evidence in compact_message:
            return True
    return False

def _validate_fact_evidence(facts: list[Any], user_text: str) -> tuple[list[dict[str, Any]], int]:
    valid: list[dict[str, Any]] = []
    rejected = 0
    for fact in facts[:8]:
        if not isinstance(fact, dict) or not _evidence_supported(fact.get("evidence"), user_text):
            rejected += 1
            continue
        if (
            fact.get("namespace") == "training"
            and fact.get("key") == "prefer_exercise"
            and is_negative_preference_value(fact.get("value"))
        ):
            rejected += 1
            continue
        copy = dict(fact)
        copy["evidence"] = " ".join(str(copy["evidence"]).split()).strip()[:160]
        valid.append(copy)
    return valid, rejected

def _level3_llm_decide(text: str, user_text: str = "") -> dict[str, Any]:
    """调用 DeepSeek（OpenAI 兼容接口）做最终判断。

    Only a valid save_memory tool call may opt in to saving.
    """
    if not LLM_LITE_API_KEY:
        return _no_save("未配置摘要模型，未保存对话")

    try:
        import requests  # noqa: PLC0415

        url = f"{LLM_LITE_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {LLM_LITE_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": LLM_LITE_MODE,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT + f"\nToday's date is {datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()}."},
                {"role": "user", "content": f"以下是本次对话记录：\n\n{text}"},
            ],
            "tools": [MEMORY_TOOL],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "temperature": 0.0,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=12)
        resp.raise_for_status()
        tool_calls = resp.json()["choices"][0]["message"].get("tool_calls") or []
        if len(tool_calls) != 1:
            return _no_save("摘要模型未明确请求保存")
        function = tool_calls[0].get("function") if isinstance(tool_calls[0], dict) else None
        if not isinstance(function, dict) or function.get("name") != "save_memory":
            return _no_save("摘要模型未明确请求保存")
        arguments = _tool_arguments(function.get("arguments"))
        summary = str(arguments.get("summary") or "").strip()
        memory_type = arguments.get("type")
        importance = arguments.get("importance")
        facts = arguments.get("facts")
        if not isinstance(facts, list):
            return _no_save("摘要工具事实参数无效，未保存对话")
        evidence_source = user_text or _user_evidence_text(text)
        facts, rejected_facts = _validate_fact_evidence(facts, evidence_source)
        if not facts:
            decision = _no_save(
                f"摘要模型返回的 {rejected_facts} 条事实均无法在用户原文中核实，未保存对话"
            )
            decision["rejected_facts"] = rejected_facts
            decision["fact_validation"] = "所有事实均无法从用户原文核实，整次记忆已拒绝"
            return decision
        # Keep compatibility with existing clients, but derive channel avoidance
        # exclusively from the validated structured-fact path downstream.
        avoid_channels = arguments.get("avoid_youtube_channels")
        if not isinstance(avoid_channels, list):
            avoid_channels = []
        avoid_channels = list(dict.fromkeys(
            channel.strip()[:80]
            for channel in avoid_channels
            if isinstance(channel, str) and channel.strip()
        ))
        if (
            not summary
            or len(summary) > 200
            or memory_type not in _MEMORY_TYPES
            or not isinstance(importance, int)
            or not 1 <= importance <= 5
        ):
            return _no_save("摘要工具参数无效，未保存对话")
        return {
            "save": True,
            "reason": "摘要模型明确请求保存",
            "summary": summary,
            "type": memory_type,
            "importance": importance,
            "avoid_youtube_channels": avoid_channels,
            "facts": facts,
            "rejected_facts": rejected_facts,
            "fact_validation": (
                f"已丢弃 {rejected_facts} 条无法从用户原文核实的事实"
                if rejected_facts else "全部事实均已通过用户原文核验"
            ),
            "raw": None,
        }

    except Exception as exc:  # noqa: BLE001
        return _no_save(f"摘要模型调用失败（{exc}），未保存对话")


# ---------------------------------------------------------------------------
# 公开入口
# ---------------------------------------------------------------------------

def route_information(
    messages: list[dict[str, str]], *, allow_external_models: bool = True
) -> dict[str, Any]:
    """对话信息路由主函数。

    Args:
        messages: 本次对话消息列表，格式 [{role: 'user'|'bot', text: '...'}]

    Returns:
        {
            save: bool,          # 是否需要保存
            reason: str,         # 判断理由
            summary: str,        # LLM 提炼的结构化摘要（save=True 时有值）
            pipeline_stage: str, # 在哪个阶段做出决定（level1/level3）
            details: dict,       # 各阶段原始结果
        }
    """
    if not messages:
        return {
            "save": False,
            "reason": "没有消息",
            "summary": "",
            "pipeline_stage": "early",
            "details": {},
        }

    # 将所有消息拼成一段文本供摘要模型分析
    joined = "\n".join(
        f"[{m.get('role', 'unknown')}] {m.get('text', '').strip()}"
        for m in messages
        if m.get("text", "").strip()
    )

    # --- Level 1：敏感信息拦截 ---
    user_sensitive_text = "\n".join(
        str(message.get("text", "")).strip()
        for message in messages
        if message.get("role") == "user" and str(message.get("text", "")).strip()
    )
    l1 = _level1_sensitive_check(user_sensitive_text)
    if l1["sensitive"]:
        return {
            "save": False,
            "reason": f"包含敏感个人信息，拒绝保存（{', '.join(l1['hits'][:3])}）",
            "summary": "",
            "pipeline_stage": "level1",
            "details": {"level1": l1},
        }

    if not allow_external_models:
        return {
            "save": False,
            "reason": "已关闭外部模型，未将对话发送到摘要服务",
            "summary": "",
            "type": "training_feedback",
            "importance": 1,
            "pipeline_stage": "external_models_disabled",
            "details": {"level1": l1},
        }

    # Function Calling is the sole durable-fact classifier. A no-tool response
    # simply means this conversation has no memory to save.
    user_text = "\n<USER_MESSAGE>\n".join(
        str(message.get("text", "")).strip()
        for message in messages
        if message.get("role") == "user" and str(message.get("text", "")).strip()
    )
    l3 = _level3_llm_decide(joined, user_text=user_text)
    return {
        "save": l3["save"],
        "reason": l3["reason"],
        "summary": l3.get("summary", ""),
        "type": l3.get("type", "training_feedback"),
        "importance": l3.get("importance", 1),
        "facts": l3.get("facts", []),
        "rejected_facts": l3.get("rejected_facts", 0),
        "fact_validation": l3.get("fact_validation", ""),
        "pipeline_stage": "level3",
        "details": {"level1": l1, "level3": l3},
    }
