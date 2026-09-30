"""Semantic alignment checks for generated training-plan goals.

Hard safety constraints remain in ``domain.plan_validation``.  This module only
answers whether the generated plan actually covers the user's requested workout
targets (or, when there is no override, the confirmed weekly subject).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


_SEPARATORS = re.compile(r"(?:和|与|及|以及|搭配|加上|配合|[\s·・/|、，,+＋&])+")
_TRAILING_WORDS = re.compile(r"(?:专项)?(?:训练|计划|课程|锻炼)$")

_TARGET_EVIDENCE: dict[str, tuple[str, ...]] = {
    "有氧": ("有氧", "心肺", "跑步", "慢跑", "快走", "跳绳", "骑行", "单车", "椭圆机", "划船机", "游泳"),
    "核心": ("核心", "腹部", "腹肌", "平板支撑", "死虫", "鸟狗", "卷腹", "俄罗斯转体", "侧桥"),
    "胸部": ("胸部", "练胸", "卧推", "飞鸟", "俯卧撑", "夹胸"),
    "背部": ("背部", "练背", "划船", "引体向上", "下拉"),
    "腿部": ("腿部", "练腿", "下肢", "深蹲", "腿举", "弓步", "硬拉"),
    "肩部": ("肩部", "练肩", "推举", "侧平举", "前平举"),
    "手臂": ("手臂", "练臂", "肱二头", "肱三头", "弯举", "臂屈伸"),
}

_ALIASES = {
    "胸": "胸部", "背": "背部", "腿": "腿部", "肩": "肩部", "腹": "核心",
    "腹部": "核心", "腹肌": "核心", "心肺": "有氧",
}


def normalize_requested_subjects(subjects: list[str] | None, fallback_subject: str = "") -> list[str]:
    """Return stable atomic targets from router output or its legacy subject string."""
    raw_items = subjects if isinstance(subjects, list) and subjects else [fallback_subject]
    normalized: list[str] = []
    for raw in raw_items:
        value = re.sub(r"[（(][^）)]*[）)]", "", str(raw or "").strip())
        for token in _SEPARATORS.split(value):
            token = _TRAILING_WORDS.sub("", token.strip())
            token = _ALIASES.get(token, token)
            if token and token not in {"训练", "今日", "今天", "当日", "综合"}:
                normalized.append(token)
    return list(dict.fromkeys(normalized))[:6]


def _local_alignment(plan: str, targets: list[str]) -> dict[str, Any]:
    normalized_plan = re.sub(r"\s+", "", str(plan or "")).casefold()
    matched: list[str] = []
    missing: list[str] = []
    for target in targets:
        evidence = _TARGET_EVIDENCE.get(target, (target,))
        if any(term.casefold() in normalized_plan for term in evidence):
            matched.append(target)
        else:
            missing.append(target)
    return {
        "passed": bool(targets) and not missing,
        "matched_subjects": matched,
        "missing_subjects": missing,
        "reason": "本地受限词表确认计划覆盖全部目标" if targets and not missing else "本地规则无法确认全部训练目标",
        "stage": "local_evidence",
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        match = re.search(r"\{[\s\S]*\}", str(text or ""))
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def validate_plan_goal_alignment(
    plan: str,
    *,
    user_request: str = "",
    requested_subjects: list[str] | None = None,
    fallback_subject: str = "",
    weekly_subject: str = "",
    schedule_decision: str = "follow",
    allow_external_models: bool = True,
    requester=None,
) -> dict[str, Any]:
    """Validate semantic goal coverage, using Lite LLM with a safe local fallback."""
    explicit_targets = normalize_requested_subjects(requested_subjects, fallback_subject)
    weekly_targets = normalize_requested_subjects(None, weekly_subject)
    targets = explicit_targets if schedule_decision in {"override", "override_today"} and explicit_targets else weekly_targets or explicit_targets
    if not targets:
        return {"passed": True, "matched_subjects": [], "missing_subjects": [], "reason": "没有需要核对的具体训练科目", "stage": "no_targets"}

    local = _local_alignment(plan, targets)
    api_key = os.getenv("LLM_LITE_API_KEY") or os.getenv("LLM_API_KEY")
    if not allow_external_models or not api_key:
        return local
    requester = requester or requests.post
    prompt = (
        "判断训练计划是否实际覆盖全部目标科目。允许同义词和具体动作作为证据，例如跑步可证明有氧，"
        "平板支撑可证明核心。不要检查伤病、组数、RPE 或其他安全规则。严格返回 JSON："
        '{"passed":true,"matched_subjects":["..."],"missing_subjects":["..."],"reason":"..."}。'
    )
    payload = {
        "user_request": user_request[:2000],
        "required_subjects": targets,
        "weekly_subject": weekly_subject,
        "schedule_decision": schedule_decision,
        "generated_plan": plan[:16000],
    }
    try:
        response = requester(
            f"{(os.getenv('LLM_LITE_BASE_URL') or os.getenv('LLM_BASE_URL') or 'https://api.deepseek.com').rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("LLM_LITE_MODE_ID") or os.getenv("LLM_MODEL_ID") or "deepseek-chat",
                "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
            timeout=10,
        )
        response.raise_for_status()
        parsed = _extract_json(response.json()["choices"][0]["message"]["content"])
        if parsed is None or not isinstance(parsed.get("passed"), bool):
            return local
        matched = [item for item in parsed.get("matched_subjects", []) if item in targets]
        missing = [item for item in parsed.get("missing_subjects", []) if item in targets]
        # A model may not silently drop a required target from both arrays.
        if set(matched) | set(missing) != set(targets):
            return local
        return {
            "passed": parsed["passed"] and not missing,
            "matched_subjects": matched,
            "missing_subjects": missing,
            "reason": str(parsed.get("reason") or "轻量模型完成语义校验")[:300],
            "stage": "lite_llm",
        }
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return local
