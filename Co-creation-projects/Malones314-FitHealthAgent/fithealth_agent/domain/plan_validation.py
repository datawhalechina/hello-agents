"""训练计划解析与确定性校验纯函数（main.py 拆分：阶段 3a）。"""

from __future__ import annotations

import re
from typing import Callable

from fithealth_agent.context_budget import contains_truncation_marker
from fithealth_agent.info_store import resolve_confirmed_memory_facts
from fithealth_agent.muscle_map import (
    MUSCLE_RULES,
    REGION_LEXICON,
    TRAINING_SUBJECT_RULES,
    muscles_for_exercise,
    regions_for_text,
)
from fithealth_agent.muscle_recovery import MuscleRecoverySnapshot


_SET_SUMMARY_LABEL = re.compile(r"总组数|总计|合计|共计|累计|总量|总共|小计")


_SET_COUNT_PATTERN = re.compile(r"([^\n：:]+)[：:]\s*(\d+)\s*组")


_GENERIC_TRAINING_SUBJECTS = {
    "训练",
    "训练计划",
    "今日训练",
    "今日计划",
    "今日训练计划",
    "今天训练",
    "今天计划",
    "今天训练计划",
    "当日训练",
    "当日计划",
    "当日训练计划",
}


def infer_training_subject(text: str) -> str:
    from fithealth_agent.muscle_map import TRAINING_SUBJECT_RULES

    scores = {
        subject: sum(text.count(keyword) for keyword in keywords)
        for subject, keywords in TRAINING_SUBJECT_RULES.items()
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    matched = [subject for subject, score in ranked if score > 0]
    if not matched:
        return "综合训练"
    if len(matched) >= 3 and scores[matched[2]] > 0:
        return "全身训练"
    return "+".join(matched[:2]) + "训练"


def infer_plan_title(text: str, subject: str) -> str:
    heading = re.search(r"^\s*#\s+(.+?)\s*$", text, re.MULTILINE)
    if heading:
        title = re.sub(r"[*_`#]+", "", heading.group(1)).strip()
        if title:
            return title[:100]
    return f"{subject}计划"


def _exercise_set_counts(answer: str) -> list[tuple[str, int]]:
    """提取计划正文里的「动作名：N 组」，跳过汇总行。

    返回 (动作名, 组数) 列表，供单动作上限与总组数两处校验共用，
    避免两边各写一套正则而行为不一致。
    """
    counts: list[tuple[str, int]] = []
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for match in _SET_COUNT_PATTERN.finditer(line):
            label = match.group(1).strip(" \t-*>#|·•")
            if not label or _SET_SUMMARY_LABEL.search(label):
                continue
            counts.append((label, int(match.group(2))))
    return counts


def validate_generated_training_plan(
    answer: str,
    memories: list[dict] | None,
    expected_subject: str = "",
    recovery: MuscleRecoverySnapshot | None = None,
    safety_constraints: list[str] | None = None,
    explicitly_requested: set[str] | None = None,
    resolver: Callable[[str], list] | None = None,
    check_subject: bool = True,
) -> list[str]:
    """Deterministically reject generated plans that violate confirmed facts."""
    from fithealth_agent.muscle_map import regions_for_text
    from fithealth_agent.youtube_search import channel_names_match

    def subject_core_terms(subject: str) -> list[str]:
        # Weekly schedule values may carry implementation hints, e.g.
        # ``腿（高脚杯深蹲+臀桥）``.  Those hints are not the subject name and
        # must not become mandatory substring matches.
        normalized = re.sub(r"[（(][^）)]*[）)]", "", subject.strip())
        normalized = re.sub(r"[\s·・/|、，,+＋&]+", " ", normalized)
        normalized = re.sub(r"(?:专项)?(?:训练|计划|课程|锻炼)$", "", normalized)
        # Split common concatenated compound subjects (e.g. 有氧跳绳) into semantic terms.
        compound_terms = {"\u6709\u6c27\u8df3\u7ef3": ("\u6709\u6c27", "\u8df3\u7ef3")}
        for compound, parts in compound_terms.items():
            if compound in normalized:
                normalized = normalized.replace(compound, " ".join(parts))
        aliases = {"胸": "胸部", "背": "背部", "腿": "腿部", "肩": "肩部", "腹": "核心"}
        terms: list[str] = []
        for token in normalized.split():
            token = re.sub(r"(?:专项)?(?:训练|计划|课程|锻炼)$", "", token)
            if token:
                terms.append(aliases.get(token, token))
                if token.endswith("部"):
                    terms.append(token[:-1])
        return list(dict.fromkeys(terms))
    violations: list[str] = []
    facts = [fact for fact in resolve_confirmed_memory_facts(memories) if fact.get("status", "active") == "active" and fact.get("user_confirmed", True)]
    def is_negated_line(line: str) -> bool:
        return bool(re.search(r"(?:避免|不做|不安排|已排除|替换为|替代|不建议|跳过|取消)", line))

    def canonical_exercise_label(label: str) -> str:
        text = re.sub(r"^\s*(?:\d+|[一二三四五六七八九十]+)[.、)）]\s*", "", label)
        return re.sub(r"[\s*_`#|·•]", "", text).casefold()

    # A plan may mention an avoided item as an instruction ("避免深蹲").
    # Only count positive occurrences in the line that contains the item.
    answer_lines = [line.strip() for line in answer.splitlines() if line.strip()]
    planned_exercises = _exercise_set_counts(str(answer))
    forbidden = [
        str(fact["value"]).strip()
        for fact in facts
        if fact.get("namespace") == "training" and fact.get("key") == "avoid_exercise"
    ]
    for exercise in forbidden:
        if exercise and any(exercise.casefold() in line.casefold() and not is_negated_line(line) for line in answer_lines):
            violations.append(f"包含被禁止动作：{exercise}")

    # A repeated action in a single plan is usually a generation mistake.
    # Treat Markdown decoration and list numbering as presentation, not a new
    # exercise, while allowing genuinely different exercise variants.
    seen_exercises: dict[str, str] = {}
    for label, sets in planned_exercises:
        canonical = canonical_exercise_label(label)
        if sets <= 0 or not canonical or is_negated_line(label):
            continue
        first_label = seen_exercises.get(canonical)
        if first_label is not None:
            violations.append(f"计划重复安排动作：{first_label}（重复出现为 {label}）")
        else:
            seen_exercises[canonical] = label

    # Confirmed health restrictions enter validation explicitly rather than
    # relying only on the model prompt.  Only direct action mentions or a
    # deterministic body-region match can block a plan; broad health facts
    # without an actionable mapping are left to the existing safety guidance.
    for raw_constraint in safety_constraints or ():
        constraint = str(raw_constraint or "").strip()
        if not constraint:
            continue
        normalized_constraint = re.sub(r"\s+", "", constraint).casefold()
        regions = regions_for_text(constraint, include_secondary=True)
        has_named_exercise = any(
            re.sub(r"\s+", "", keyword).casefold() in normalized_constraint
            for rule in MUSCLE_RULES
            for keyword in rule.keywords
        )
        for label, sets in planned_exercises:
            if sets <= 0 or is_negated_line(label):
                continue
            direct_match = canonical_exercise_label(label) in normalized_constraint
            region_match = bool(
                not has_named_exercise
                and regions
                and any(hit.region in regions for hit in (resolver or muscles_for_exercise)(label))
            )
            if direct_match or region_match:
                violations.append(f"已确认的健康限制“{constraint}”与计划动作 {label} 冲突")

    # Recovery is derived data, so this remains a pure, optional validation
    # rule.  User-reported soreness/pain is deliberately not hard-rejected
    # here; painful regions are blocked by the existing safety path, while
    # ordinary soreness is a qualitative reduction signal for the model.
    if recovery is not None:
        requested = explicitly_requested or set()
        # BUG-23：文档 §E 的例外是「同时属于 `reduce` **且** `explicitly_requested`」。
        # 上一版写成 `not load.needs_reduction and ... and not (load.needs_reduction
        # and region in requested)`——首个条件已经排除了全部 needs_reduction 负荷，
        # 追加的那半句永远为真，于是"只要该肌群有任何一条生效酸痛反馈，这条硬校验
        # 就对它彻底失效"这个原缺陷根本没被修掉。
        #
        # 正确的取舍：未恢复就该拦，**除非**用户明确要求练这个区域（此时按文档交给
        # 模型做减量）。`painful` 不在这里单列条件——它由 `dynamic_safety` 的区域
        # 限制负责，重复写一遍只会让两处口径分叉。
        blocked = {
            load.muscle_id: load
            for load in recovery.recovering
            if load.hours_remaining > 0
            and not (load.needs_reduction and load.region in requested)
        }
        for label, sets in _exercise_set_counts(str(answer)):
            if sets <= 0 or is_negated_line(label):
                continue
            for hit in (resolver or muscles_for_exercise)(label):
                load = blocked.get(hit.muscle_id)
                if load is None or hit.role != "primary":
                    continue
                violations.append(
                    f"{load.region}{load.zh}预计还需 {load.hours_remaining:g} 小时恢复，"
                    f"但计划包含{label}（主项 {sets} 组）"
                )

        warning_by_muscle = {
            warning.muscle_id: warning for warning in recovery.load_warnings
        }
        for label, sets in _exercise_set_counts(str(answer)):
            if sets <= 2 or is_negated_line(label):
                continue
            for hit in (resolver or muscles_for_exercise)(label):
                warning = warning_by_muscle.get(hit.muscle_id)
                if warning is None or hit.role != "primary":
                    continue
                violations.append(
                    f"{warning.message}，计划仍安排 {label} {sets} 组；"
                    "当前只允许不超过 2 组的低容量恢复训练"
                )

    max_sets_per_exercise = [
        float(fact["value"])
        for fact in facts
        if fact.get("namespace") == "training" and fact.get("key") == "max_sets_per_exercise"
        and isinstance(fact.get("value"), (int, float))
    ]
    if max_sets_per_exercise:
        limit = min(max_sets_per_exercise)
        for _label, sets in _exercise_set_counts(answer):
            if sets > limit:
                violations.append(f"单个动作组数 {sets} 超过已确认上限 {limit:g}")
                break

    max_total_sets = [
        float(fact["value"])
        for fact in facts
        if fact.get("namespace") == "training" and fact.get("key") == "max_total_sets"
        and isinstance(fact.get("value"), (int, float))
    ]
    if max_total_sets:
        limit = min(max_total_sets)
        total_sets = sum(sets for _label, sets in _exercise_set_counts(answer))
        if total_sets > limit:
            violations.append(f"训练总组数 {total_sets} 超过已确认上限 {limit:g}")
    max_rpe = [
        float(fact["value"])
        for fact in facts
        if fact.get("namespace") == "training" and fact.get("key") == "max_rpe"
        and isinstance(fact.get("value"), (int, float))
    ]
    if max_rpe:
        limit = min(max_rpe)
        for match in re.finditer(r"RPE\s*[：:]?\s*(\d+(?:\.\d+)?)(?:\s*[-–—~～至]\s*(\d+(?:\.\d+)?))?", answer, re.IGNORECASE):
            stated_max = max(float(value) for value in match.groups() if value is not None)
            if stated_max > limit:
                violations.append(f"RPE {stated_max:g} 超过已确认上限 {limit:g}")
                break
    required_elements = [
        str(fact.get("value") or "")
        for fact in facts
        if fact.get("namespace") == "training" and fact.get("key") == "required_plan_elements"
    ]
    for value in required_elements:
        elements = [item.strip() for item in re.split(r"[|,，、;；]+", value) if item.strip()]
        missing = [item for item in elements if item.casefold() not in answer.casefold()]
        if missing:
            violations.append("计划缺少已确认的必需元素：" + "、".join(missing))
    if check_subject and expected_subject and not is_generic_training_subject(expected_subject):
        subject_terms = subject_core_terms(expected_subject)
        if subject_terms and not all(term.casefold() in answer.casefold() for term in subject_terms):
            violations.append(f"计划内容未体现周计划科目：{expected_subject}")

    excluded_channels = [
        str(fact["value"]).strip()
        for fact in facts
        if fact.get("namespace") == "youtube" and fact.get("key") == "avoid_channel"
    ]
    for channel in excluded_channels:
        if channel and any(
            channel_names_match(channel, line) and not is_negated_line(line)
            for line in answer_lines
        ):
            violations.append(f"使用了被排除的 YouTube 频道：{channel}")
    return list(dict.fromkeys(violations))


def plan_validation_fact_usage(
    memories: list[dict] | None, violations: list[str]
) -> list[tuple[str, str]]:
    """Return (fact_id, detail) pairs for facts that materially affected validation."""
    facts = resolve_confirmed_memory_facts(memories)
    if not violations:
        return [
            (str(fact["fact_id"]), "用于计划校验，校验通过")
            for fact in facts
            if fact.get("fact_id") and (fact.get("namespace"), fact.get("key")) in {
                ("health", "injury_or_constraint"), ("health", "recovery_status"),
                ("training", "avoid_exercise"), ("training", "max_rpe"),
                ("training", "max_sets_per_exercise"), ("training", "max_total_sets"),
                ("training", "required_plan_elements"), ("youtube", "avoid_channel"),
                ("plan", "weekly_schedule"),
            }
        ]
    usage: list[tuple[str, str]] = []
    key_markers = {
        ("training", "max_rpe"): ("RPE",),
        ("training", "max_sets_per_exercise"): ("单个动作组数",),
        ("training", "max_total_sets"): ("训练总组数",),
        ("training", "required_plan_elements"): ("必需元素",),
        ("plan", "weekly_schedule"): ("周计划科目",),
    }
    for fact in facts:
        fact_id = str(fact.get("fact_id") or "")
        if not fact_id:
            continue
        slot = (str(fact.get("namespace") or ""), str(fact.get("key") or ""))
        value = str(fact.get("value") or "")
        matched = [
            item for item in violations
            if (value and value.casefold() in item.casefold())
            or any(marker in item for marker in key_markers.get(slot, ()))
        ]
        if matched:
            usage.append((fact_id, "；".join(matched)[:500]))
    return usage


def constraint_regions(constraint: str) -> set[str]:
    """Map a health constraint to direct and secondarily affected regions."""
    return regions_for_text(constraint, include_secondary=True)


def looks_like_complete_training_plan(text: str) -> bool:
    from fithealth_agent.muscle_map import TRAINING_SUBJECT_RULES

    # 被上下文预算裁剪过的残片一律不算完整计划（BUG-05）。放在最前面：
    # 一份被截断的计划长度往往仍有 4000 字符，下面三个条件全都会满足。
    if contains_truncation_marker(text):
        return False
    exercise_terms = sum(text.count(term) for terms in TRAINING_SUBJECT_RULES.values() for term in terms)
    structure_terms = sum(term in text for term in ("热身", "组", "次数", "拉伸", "训练计划"))
    return len(text) >= 300 and exercise_terms >= 2 and structure_terms >= 2


def most_recent_complete_training_plan(history: list[dict] | None) -> str:
    """Return the newest complete assistant plan, never a later acknowledgement."""
    if not isinstance(history, list):
        return ""
    for message in reversed(history):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = str(message.get("text") or "").strip()
        if looks_like_complete_training_plan(content):
            return content
    return ""


def extract_plan_subject(answer: str, fallback: str = "") -> str:
    match = re.search(
        r"(?:最终识别的?)?训练科目\s*[：:]\s*[`*“\"]*([^\n`*”\"]+)",
        answer,
    )
    if match:
        candidate = match.group(1).strip().rstrip("。；;")
        if 1 <= len(candidate) <= 40:
            return candidate if candidate.endswith("训练") else candidate + "训练"
    return fallback or infer_training_subject(answer)


def is_generic_training_subject(subject: str) -> bool:
    """Return whether a router subject describes a date, not a workout type."""
    normalized = re.sub(r"[\s的]+", "", str(subject or "")).strip("，。；;：:")
    return normalized in _GENERIC_TRAINING_SUBJECTS


def plan_card_title(title: str, subject: str) -> str:
    """Replace a generic router title once a concrete schedule subject is known."""
    candidate = str(title or "").strip()
    if not candidate or (
        is_generic_training_subject(candidate)
        and not is_generic_training_subject(subject)
    ):
        return f"{subject}计划"[:100]
    return candidate[:100]
