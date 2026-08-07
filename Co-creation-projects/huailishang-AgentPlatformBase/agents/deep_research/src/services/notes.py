"""Helpers for coordinating note tool usage instructions."""

from __future__ import annotations

import json

from models import TodoItem


def build_note_guidance(task: TodoItem) -> str:
    """Generate note tool usage guidance for a specific task."""

    tags_list = ["deep_research", f"task_{task.id}"]
    tags_literal = json.dumps(tags_list, ensure_ascii=False)

    if task.note_id:
        read_payload = json.dumps({"action": "read", "note_id": task.note_id}, ensure_ascii=False)
        update_payload = json.dumps(
            {
                "action": "update",
                "note_id": task.note_id,
                "task_id": task.id,
                "title": f"任务 {task.id}: {task.title}",
                "note_type": "task_state",
                "tags": tags_list,
                "content": "请将本轮新增信息补充到任务概览中",
            },
            ensure_ascii=False,
        )

        return (
            "笔记协作指引：\n"
            f"- 当前任务笔记 ID：{task.note_id}。\n"
            f"- 在书写总结前必须调用：[TOOL_CALL:note:{read_payload}] 获取最新内容。\n"
            f"- 完成分析后调用：[TOOL_CALL:note:{update_payload}] 同步增量信息。\n"
            "- 更新时保持原有段落结构，新增内容请在对应段落中补充。\n"
            f"- 建议 tags 保持为 {tags_literal}，保证其他 Agent 可快速定位。\n"
            "- 成功同步到笔记后，再输出面向用户的总结。\n"
        )

    create_payload = json.dumps(
        {
            "action": "create",
            "task_id": task.id,
            "title": f"任务 {task.id}: {task.title}",
            "note_type": "task_state",
            "tags": tags_list,
            "content": "请记录任务概览、来源概览",
        },
        ensure_ascii=False,
    )

    return (
        "笔记协作指引：\n"
        f"- 当前任务尚未建立笔记，请先调用：[TOOL_CALL:note:{create_payload}]。\n"
        "- 创建成功后记录返回的 note_id，并在后续所有更新中复用。\n"
        "- 同步笔记后，再输出面向用户的总结。\n"
    )

