"""肌群恢复区域解析与展示纯规则（阶段 3c）。"""

from __future__ import annotations

import re

from fithealth_agent.health_safety import CLAUSE_SEPARATORS
from fithealth_agent.muscle_map import REGION_ALIASES
from fithealth_agent.muscle_recovery import normalise_garmin_hours


_REGION_VETO_PATTERN = re.compile(
    r"不想|不要|不用|别|不练|甭|避免|跳过|不安排|除外|不碰|休息|昨天|昨日|上次|之前|前天"
)


_REGION_REQUEST_VERB_FIRST = (
    r"(?:要|想|帮我|给我|安排|制定|生成|计划|今天|今日|这次|本次)"
    r".{0,8}(?:练|训练).{0,6}(?:%s)"
)


_REGION_REQUEST_NOUN_FIRST = r"(?:%s).{0,6}(?:训练|计划|日)"


_REGION_REQUEST_CUE = re.compile(r"安排|帮我|给我|想|要|制定|生成|怎么|如何|练什么")


def explicitly_requested_recovery_regions(message: str) -> list[str]:
    """Return regions the current message explicitly asks to train.

    BUG-25：按小句切分（复用 `health_safety.CLAUSE_SEPARATORS`，全仓库只有这一套
    小句定义），**先整句否决、再匹配肯定形态**，并且肯定形态必须带请求语气而不是
    裸的"练"。两个方向都错过：一是"今天不想练腿"曾被当成明确要求练腿，反而**解除**
    腿部的恢复压制；二是该区域若在 `avoid` 里还会 409 回"与已确认的安全限制冲突"，
    而用户说的正是不练。
    """

    normalized = re.sub(r"\s+", "", message)
    requested: set[str] = set()
    vetoed: set[str] = set()
    for clause in re.split(f"[{re.escape(CLAUSE_SEPARATORS)}]", normalized):
        if not clause:
            continue
        clause_vetoed = bool(_REGION_VETO_PATTERN.search(clause))
        has_cue = bool(_REGION_REQUEST_CUE.search(clause))
        for region, aliases in REGION_ALIASES.items():
            alias_pattern = "|".join(
                re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)
            )
            mentioned = re.search(alias_pattern, clause)
            if not mentioned:
                continue
            if clause_vetoed:
                vetoed.add(region)
                continue
            verb_first = re.search(_REGION_REQUEST_VERB_FIRST % alias_pattern, clause)
            noun_first = has_cue and re.search(_REGION_REQUEST_NOUN_FIRST % alias_pattern, clause)
            if verb_first or noun_first:
                requested.add(region)
    return sorted(requested - vetoed)


def _subject_recovery_regions(subject: str | None) -> set[str]:
    normalized = re.sub(r"\s+", "", str(subject or ""))
    return {
        region for region, aliases in REGION_ALIASES.items()
        if any(alias in normalized for alias in aliases)
    }


def _recovery_context_payload(
    snapshot: MuscleRecoverySnapshot | None,
    explicit_regions: list[str],
    soreness_reports: list[object] | None = None,
) -> dict[str, object]:
    if snapshot is None:
        return {
            "recovering": [], "reduce": [], "avoid": [], "ready": [],
            "load_warnings": [], "explicitly_requested": explicit_regions,
            "garmin_recovery_hours": 0.0,
        }
    recovering = [
        {
            "muscle_id": load.muscle_id,
            "region": load.region,
            "zh": load.zh,
            "weekday_zh": load.weekday_zh,
            "exercises": list(load.exercises),
            "hours_remaining": load.hours_remaining,
            # BUG-26 问题 1：带上角色，让下游能只按主项负荷做区域压制。次要负荷
            # （例如硬拉顺带练到的小臂）留在列表里当提示文本，但不该压掉周计划。
            "role": load.role,
        }
        for load in snapshot.recovering
    ]
    load_warnings = [
        {
            "muscle_id": warning.muscle_id,
            "region": warning.region,
            "zh": warning.zh,
            "kind": warning.kind,
            "message": warning.message,
            "latest_sets": warning.latest_sets,
            "baseline_sets": warning.baseline_sets,
            "ratio": warning.ratio,
            "consecutive_days": warning.consecutive_days,
        }
        for warning in snapshot.load_warnings
    ]
    reduce = {load.region for load in snapshot.loads if load.soreness_level == "sore"}
    reduce.update(warning.region for warning in snapshot.load_warnings)
    avoid = {load.region for load in snapshot.loads if load.soreness_level == "painful"}
    for report in soreness_reports or []:
        region = getattr(report, "region", "")
        level = getattr(report, "level", "")
        if level == "sore": reduce.add(region)
        if level == "painful": avoid.add(region)
    reduce = sorted(reduce)
    avoid = sorted(avoid)
    regions = {load.region for load in snapshot.loads}
    ready = sorted(
        region for region in regions
        if region not in reduce and region not in avoid
        and all(load.hours_remaining <= 0 for load in snapshot.for_region(region))
    )
    return {
        "recovering": recovering,
        "reduce": reduce,
        "avoid": avoid,
        "ready": ready,
        "load_warnings": load_warnings,
        "explicitly_requested": explicit_regions,
        "garmin_recovery_hours": snapshot.garmin_recovery_hours,
    }


def parse_garmin_recovery_hours(value: object) -> float:
    """Validate the per-session Garmin recovery-hours override.

    ``0`` means no override.  Fractional values below one hour are rejected so
    the API has the same contract as the onboarding control (``0.0–96.0``).
    The value is intentionally not stored anywhere.
    """

    number = normalise_garmin_hours(value)
    if number is None:
        raise ValueError("Garmin 恢复时间必须是 0–96.0 之间的数字")
    return number


def _recovery_checkin_items(snapshot: object) -> list[dict[str, object]]:
    """Convert a snapshot into the stable `/session/intro` response shape."""

    loads = getattr(snapshot, "muscle_loads", getattr(snapshot, "loads", ()))
    items: list[dict[str, object]] = []
    for load in loads:
        items.append({
            "muscle_id": load.muscle_id,
            "zh": load.zh,
            "region": load.region,
            "weekday_zh": load.weekday_zh,
            "exercises": list(load.exercises),
            "effective_sets": load.effective_sets,
            "recovery_hours": load.recovery_hours,
            "hours_remaining": load.hours_remaining,
            "recovered": load.hours_remaining <= 0,
            "needs_reduction": load.needs_reduction,
            "soreness_level": load.soreness_level,
            "role": load.role,
            "raw_sets": load.raw_sets,
            "history": [
                {
                    "trained_at": trained_at.isoformat(),
                    "effective_sets": effective_sets,
                    "exercises": list(exercises),
                }
                for trained_at, effective_sets, exercises in getattr(load, "history", ())
            ],
        })
    skipped_future = int(getattr(snapshot, "skipped_future", 0) or 0)
    if skipped_future:
        items.append({
            "warning": "future_timestamp",
            "skipped_records": skipped_future,
            "message": f"跳过 {skipped_future} 条未来时间戳训练记录，请检查设备时间或时区。",
        })
    for warning in getattr(snapshot, "load_warnings", ()):
        items.append({
            "warning": warning.kind,
            "muscle_id": warning.muscle_id,
            "region": warning.region,
            "zh": warning.zh,
            "latest_sets": warning.latest_sets,
            "baseline_sets": warning.baseline_sets,
            "ratio": warning.ratio,
            "consecutive_days": warning.consecutive_days,
            "message": warning.message,
        })
    return items


def _format_muscle_recovery_lines(loads: object) -> list[str]:
    """Render recovering muscles before recovered muscles in the welcome text."""

    ordered_loads = sorted(
        loads or (),
        key=lambda load: (load.hours_remaining <= 0, load.region, load.muscle_id),
    )
    lines: list[str] = []
    for load in ordered_loads:
        exercises = "、".join(load.exercises) if load.exercises else "动作未识别"
        role_text = "主项" if getattr(load, "role", "primary") == "primary" else "次要"
        sets_text = f"有效容量 {load.effective_sets:g}，{role_text}"
        if load.hours_remaining <= 0:
            recovery_text = "已恢复"
        else:
            remaining_text = f"{round(load.hours_remaining, 1):.1f}".rstrip("0").rstrip(".")
            recovery_text = f"预计还需 {remaining_text} 小时"
        soreness_level = getattr(load, "soreness_level", "unknown")
        if soreness_level == "sore":
            recovery_text += "；用户报告酸痛，当前需要减量"
        elif soreness_level == "painful":
            recovery_text += "；用户报告疼痛，当前禁止安排该区域训练"
        content = (
            f"**{load.region} · {load.zh}**：{load.weekday_zh}训练过"
            f"（{exercises}，{sets_text}），{recovery_text}"
        )
        history = getattr(load, "history", ())
        if len(history) > 1:
            older = "；".join(
                f"{_weekday}（{'、'.join(exercises) or '动作未识别'}，有效容量 {sets:g}）"
                for trained_at, sets, exercises in history[1:]
                for _weekday in [("周一", "周二", "周三", "周四", "周五", "周六", "周日")[trained_at.weekday()]]
            )
            content += f"；此前：{older}"
        if load.hours_remaining <= 0:
            lines.append(f"- ~~{content}~~")
        else:
            lines.append(f"- {content}")
    return lines


def render_session_intro(
    *,
    garmin_recovery_hours: float,
    profile_text: str,
    missing_field_labels: list[str],
    external_models_enabled: bool,
    model_names: dict[str, str],
    records_count: int,
    plans_count: int,
    memories_count: int,
    health_imports_count: int,
    temporary_health: list[dict[str, object]],
    recovery_snapshot: object,
) -> str:
    """Render the local welcome text from already-collected state."""
    model_state = "已开启（相关内容可能发送到外部服务）" if external_models_enabled else (
        "已关闭（不会向外部模型发送内容）"
    )
    if missing_field_labels:
        profile_text += "\n- 待补充：" + "、".join(missing_field_labels)

    health_checkin = ""
    if temporary_health:
        details = []
        for fact in temporary_health:
            valid_until = fact.get("valid_until")
            suffix = f"（记录有效至 {valid_until}）" if valid_until else ""
            details.append(f"- {fact.get('value')}{suffix}")
        health_checkin = (
            "\n\n### 今日健康复查\n"
            + "\n".join(details)
            + "\n- 今天感觉怎么样？请告诉我这些症状是已恢复、减轻、无变化还是加重，我会生成待确认的更新；在你确认前不会改动长期上下文。"
        )

    recovery_lines: list[str] = [
        "\n\n### 肌群恢复状态",
        f"- Garmin 恢复时间加成：{garmin_recovery_hours:g} 小时（仅当前会话）",
    ]
    if recovery_snapshot.loads:
        recovery_lines.extend(_format_muscle_recovery_lines(recovery_snapshot.loads))
    else:
        recovery_lines.append("- 最近 7 天没有可识别的训练动作，暂时没有可展示的肌群恢复记录。")
    if getattr(recovery_snapshot, "load_warnings", ()):
        recovery_lines.append("- **累积负荷预警**：" + "；".join(
            warning.message for warning in recovery_snapshot.load_warnings
        ))
        recovery_lines.append(
            "- 预警肌群暂不继续堆叠常规容量；如仍需训练，只安排不超过 2 组的低容量恢复练习。"
        )
    recovery_lines.append(
        "- 以上恢复时间是按动作与组数估算，不是医学测量；Garmin 小时是本次进入系统时的输入。"
    )
    recovery_lines.append(
        "- 这些恢复状态会参与训练裁决：酸痛区域会减量，疼痛或未恢复的高风险区域可能阻断计划并返回 409。"
        "如识别不准确，可在对话中明确部位和感受，或到“数据管理 → 肌群酸痛记录”修改、删除。"
    )
    muscle_recovery_text = "\n".join(recovery_lines)

    return (
        "## 欢迎回来\n\n"
        "### 模型与隐私\n"
        f"- 外部模型：{model_state}\n"
        f"- 主对话模型：{model_names['main']}\n"
        f"- 摘要/计划鉴定模型：{model_names['lite']}\n"
        f"- 餐盘视觉模型：{model_names['vision']}\n"
        "- 可在“数据管理 → 外部模型与数据外发”查看说明或随时关闭。\n\n"
        "### 个人档案\n"
        f"{profile_text}\n\n"
        "### 本地数据概况\n"
        f"- 训练记录：{records_count} 条\n"
        f"- 训练计划：{plans_count} 份\n"
        f"- 临时记忆：{memories_count} 条\n"
        f"- 健康/睡眠导入：{health_imports_count} 次"
        f"{health_checkin}{muscle_recovery_text}\n\n"
        "### 可使用功能\n"
        "- 查看训练记录：输入“查看训练记录”或“查看 2026-08-19 的训练记录”。\n"
        "- 查看训练计划：在“数据管理 → 训练计划”中查看、编辑或删除已保存计划。\n"
        "- 生成训练计划：输入“我想练背，帮我生成训练计划”。\n"
        "- 更改周计划：直接说明新的安排，例如“以后周二练腿、周四练背”。\n"
        "- 更新今天的状态：直接说“今天腰部不适”“膝盖已经不疼了”或“今天想休息”。\n\n"
        "你可以继续对话，或使用上方按钮导入健康数据、记录当天状态。"
    )
