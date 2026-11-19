"""把本地记忆渲染成会话小结。不调用模型，也不做诊断。"""

from __future__ import annotations

from src.utils.paths import outputs_dir


def render_session_summary(profile: dict, max_turns: int = 5) -> str:
    """根据已允许入库的倾诉轮次生成 Markdown。"""
    user_id = profile.get("user_id", "unknown")
    themes = profile.get("themes") or {}
    ranked = sorted(themes.items(), key=lambda item: (-item[1], item[0]))
    safe_turns = [
        turn for turn in profile.get("turns", [])
        if turn.get("guard") == "ok" and turn.get("user")
    ][-max_turns:]

    lines = [
        "# 会话小结（示例）",
        "",
        f"- 用户：`{user_id}`",
        "- 生成方式：本地主题统计（不调用大模型，不做心理或医疗诊断）",
        "",
        "## 常出现的主题",
        "",
    ]
    if ranked:
        lines.extend(f"- {name}（{count}）" for name, count in ranked)
    else:
        lines.append("- 还没有可统计的主题")

    lines.extend(["", "## 最近倾诉（截断）", ""])
    if safe_turns:
        for index, turn in enumerate(safe_turns, start=1):
            text = str(turn.get("user", "")).replace("\n", " ").strip()
            if len(text) > 80:
                text = text[:80] + "…"
            lines.append(f"{index}. {text}")
    else:
        lines.append("暂无已通过安全检查的倾诉记录。")

    lines.extend([
        "",
        "## 说明",
        "",
        "本文件来自示例或本地演示数据，不是临床记录。危机相关原文不会写入这份小结。",
        "",
    ])
    return "\n".join(lines)


def write_session_summary(profile: dict, filename: str = "session_summary.md") -> str:
    """写入 outputs/ 并返回文件路径。"""
    path = outputs_dir() / filename
    path.write_text(render_session_summary(profile), encoding="utf-8")
    return str(path)
