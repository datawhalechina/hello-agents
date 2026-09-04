"""Constrained Function Calling router for chat-side local actions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import requests


ROUTER_API_KEY = os.getenv("LLM_LITE_API_KEY") or os.getenv("LLM_API_KEY")
ROUTER_BASE_URL = (
    os.getenv("LLM_LITE_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.deepseek.com"
).rstrip("/")
ROUTER_MODEL = os.getenv("LLM_LITE_MODE_ID") or os.getenv("LLM_MODEL_ID") or "deepseek-chat"


@dataclass
class ChatIntent:
    profile_updates: dict[str, Any] = field(default_factory=dict)
    view_profile: bool = False
    view_training_records: bool = False
    training_records_date: str | None = None
    view_nutrition_records: bool = False
    nutrition_records_date: str | None = None
    create_training_plan: bool = False
    training_plan_subject: str = ""
    requested_subjects: list[str] = field(default_factory=list)
    training_plan_title: str = ""
    save_existing_training_plan: bool = False
    saved_plan_date: str | None = None
    saved_plan_subject: str = ""
    schedule_decision: str = "follow"
    temporary_health_constraints: list[str] = field(default_factory=list)
    excluded_subjects: list[str] = field(default_factory=list)
    needs_clarification: bool = False


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "view_profile",
            "description": "Show the user's local profile and confirmed long-term preferences or constraints when explicitly requested.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": (
                "Update user profile only when the user explicitly supplies the new value. "
                "Never call for questions, recommendations, examples, assumptions, or ambiguity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "weekly_weight_kg": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Explicitly stated recent body weights in kilograms.",
                    },
                    "height_cm": {"type": "number"},
                    "birth_date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD only when explicitly stated.",
                    },
                    "sex": {"type": "string", "enum": ["male", "female"]},
                    "goal": {"type": "string"},
                    "equipment_change": {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "enum": ["add", "remove", "replace"]},
                            "items": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["mode", "items"],
                        "additionalProperties": False,
                        "description": "An explicit equipment change. Use add for newly acquired equipment, remove for unavailable equipment, and replace only when the user explicitly provides a complete list.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_training_records",
            "description": (
                "Open the local saved training-record viewer when the user asks to view, "
                "query, review, or inspect workout/training/exercise data or records. "
                "Do not use this to create a training plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Optional requested ISO date YYYY-MM-DD.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_nutrition_records",
            "description": (
                "Open the local nutrition viewer when the user asks to view, query, review, "
                "or inspect food, diet, calorie, carbohydrate, protein, or fat intake data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Optional requested ISO date YYYY-MM-DD.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_existing_training_plan",
            "description": (
                "Show the save card for the most recent complete training plan already produced "
                "in this conversation. Use when the user asks to save that plan, not to create a new plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Optional explicit ISO date YYYY-MM-DD for the saved plan."},
                    "subject": {"type": "string", "description": "Optional training subject stated by the user."},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_training_plan",
            "description": (
                "Mark an explicit user request to create or design a new training plan. "
                "Do not call for viewing training records, historical data, or general questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Short training subject, for example 胸部训练 or 跳绳训练.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short saved-plan title based on the explicit request.",
                    },
                    "requested_subjects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 6,
                        "description": "Atomic workout targets explicitly requested, for example [有氧, 核心].",
                    },
                    "schedule_decision": {
                        "type": "string",
                        "enum": ["follow", "override", "rest"],
                        "description": "For a dated request, follow the weekly schedule, override it, or rest.",
                    },
                    "temporary_health_constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5,
                        "description": "Current-message health constraints that should affect only this plan; never infer or persist them.",
                    },
                    "excluded_subjects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5,
                        "description": "Training subjects the user explicitly excludes for this plan or date.",
                    },
                    "needs_clarification": {
                        "type": "boolean",
                        "description": "True only when the user explicitly overrides a scheduled plan but does not choose rest or a replacement subject.",
                    },
                },
                "required": ["subject", "title"],
                "additionalProperties": False,
            },
        },
    },
]

SYSTEM_PROMPT = """You route one Chinese fitness-chat message to optional local actions.
Use Function Calling only. Do not produce prose.
Use no tool when uncertain.
Call at most one tool for each message. Never combine profile updates with navigation
or plan creation in the same response.
Questions never update profile values. For example, “我的可用器械有哪些？” and
“我的器械是不是只有哑铃和跳绳？” are questions and must not call update_profile.
For equipment, use equipment_change with an explicit add/remove/replace mode;
replace is allowed only when the user explicitly supplies a complete list.
When the user asks to see, query, review, or list their personal information, profile, preferences,
or constraints, call view_profile. This is read-only and must not update the profile.
Viewing “训练数据”, “训练记录”, “运动数据”, or “锻炼记录” means
view_training_records, not create_training_plan. Viewing food, diet, nutrition, calorie,
carbohydrate, protein, or fat intake means view_nutrition_records. Only explicit requests to make a new
plan call create_training_plan. For create_training_plan, always provide both a concise
subject and a concise title in the tool arguments; do not derive them from the reply.
For a plan-related scheduling decision, provide schedule_decision: use follow when the
weekly schedule should stand, override when the user explicitly requests a current-session
subject (for example “今天想练腿” or “今天想有氧”) that differs from it, and rest
when the user explicitly chooses rest.
For a compound request, also provide requested_subjects as atomic targets; for example
“今天做有氧和核心训练” becomes [“有氧”, “核心”].
Include temporary_health_constraints and
excluded_subjects only when the user explicitly states them; they apply to this request
only and must not be persisted. Set needs_clarification only for an unresolved override.
When the user says “保存这份/刚才/上面的训练计划” or asks to save an already generated
plan, call save_existing_training_plan instead of create_training_plan."""


def _arguments(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _bounded_strings(value: Any, *, max_items: int, max_length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item.strip()[:max_length]
        for item in value
        if isinstance(item, str) and item.strip()
    ][:max_items]


def route_chat_intent(message: str, *, allow_external_models: bool = True) -> ChatIntent:
    """Classify one message through a limited tool-call contract.

    Failure intentionally returns no action: local data must never be modified based on
    a guessed intent.
    """
    if not allow_external_models or not ROUTER_API_KEY or not message.strip():
        return ChatIntent()
    try:
        response = requests.post(
            f"{ROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {ROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": ROUTER_MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message[:4_000]},
                ],
                "tools": TOOLS,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
            },
            timeout=12,
        )
        response.raise_for_status()
        tool_calls = response.json()["choices"][0]["message"].get("tool_calls") or []
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return ChatIntent()

    supported_calls: list[tuple[str, dict[str, Any]]] = []
    for call in tool_calls:
        function = call.get("function") if isinstance(call, dict) else None
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if name in {
            "update_profile", "view_profile", "view_training_records", "view_nutrition_records",
            "save_existing_training_plan", "create_training_plan",
        }:
            supported_calls.append((name, _arguments(function.get("arguments"))))

    if len(supported_calls) != 1:
        return ChatIntent()

    name, arguments = supported_calls[0]
    if name == "update_profile":
        return ChatIntent(profile_updates=arguments)
    if name == "view_profile":
        return ChatIntent(view_profile=True)
    if name == "view_training_records":
        requested_date = arguments.get("date")
        if isinstance(requested_date, str):
            try:
                requested_date = date.fromisoformat(requested_date).isoformat()
            except ValueError:
                requested_date = None
        return ChatIntent(
            view_training_records=True,
            training_records_date=requested_date,
        )
    if name == "view_nutrition_records":
        requested_date = arguments.get("date")
        if isinstance(requested_date, str):
            try:
                requested_date = date.fromisoformat(requested_date).isoformat()
            except ValueError:
                requested_date = None
        return ChatIntent(
            view_nutrition_records=True,
            nutrition_records_date=requested_date,
        )
    if name == "save_existing_training_plan":
        requested_date = arguments.get("date")
        if isinstance(requested_date, str):
            try:
                requested_date = date.fromisoformat(requested_date).isoformat()
            except ValueError:
                requested_date = None
        else:
            requested_date = None
        subject = arguments.get("subject")
        return ChatIntent(
            save_existing_training_plan=True,
            saved_plan_date=requested_date,
            saved_plan_subject=subject.strip()[:40] if isinstance(subject, str) else "",
        )
    subject = arguments.get("subject")
    title = arguments.get("title")
    if not isinstance(subject, str) or not isinstance(title, str):
        return ChatIntent()
    subject = subject.strip()
    title = title.strip()
    if not subject or not title:
        return ChatIntent()
    return ChatIntent(
        create_training_plan=True,
        training_plan_subject=subject[:40],
        training_plan_title=title[:100],
        requested_subjects=_bounded_strings(
            arguments.get("requested_subjects"), max_items=6, max_length=40
        ),
        schedule_decision=arguments.get("schedule_decision") if arguments.get("schedule_decision") in {"follow", "override", "rest"} else "follow",
        temporary_health_constraints=_bounded_strings(
            arguments.get("temporary_health_constraints"), max_items=5, max_length=120
        ),
        excluded_subjects=_bounded_strings(
            arguments.get("excluded_subjects"), max_items=5, max_length=40
        ),
        needs_clarification=bool(arguments.get("needs_clarification")),
    )
