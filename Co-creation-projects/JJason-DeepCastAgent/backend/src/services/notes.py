"""协调笔记工具使用说明的助手。"""

from __future__ import annotations

import json

from models import TodoItem


def build_note_guidance(task: TodoItem) -> str:
    """为特定任务生成笔记工具使用说明。"""
    tags_list = ["deep_research", f"task_{task.id}"]
    tags_literal = json.dumps(tags_list, ensure_ascii=False)

    if task.note_id:
        read_payload = json.dumps({"action": "read", "note_id": task.note_id}, ensure_ascii=False)
        # 只提供更新笔记的模板，让 LLM 自行填充实际研究内容
        update_template = json.dumps(
            {
                "action": "update",
                "note_id": task.note_id,
                "task_id": task.id,
                "title": f"任务 {task.id}: {task.title}",
                "note_type": "task_state",
                "tags": tags_list,
                "content": "<请在此填写更新后的完整内容>",
            },
            ensure_ascii=False,
        )

        return (
            "笔记协作指引：\n"
            f"- 当前任务笔记 ID：{task.note_id}。\n"
            f"- 在书写总结前必须调用：[TOOL_CALL:note:{read_payload}] 获取最新内容。\n"
            f"- 完成分析后更新笔记，参数模板如下（需将 content 替换为实际内容）：\n"
            f"  {update_template}\n"
            "- **重要**：content 字段必须包含原有内容加上本轮新增的研究发现，不要使用占位文本。\n"
            "- 更新时保持原有段落结构，新增内容请在对应段落中补充。\n"
            f"- 建议 tags 保持为 {tags_literal}，保证其他 Agent 可快速定位。\n"
            "- 成功同步到笔记后，再输出面向用户的总结。\n"
        )

    # 只提供创建笔记的模板，让 LLM 自行填充实际研究内容
    create_template = json.dumps(
        {
            "action": "create",
            "task_id": task.id,
            "title": f"任务 {task.id}: {task.title}",
            "note_type": "task_state",
            "tags": tags_list,
            "content": "<请在此填写任务总结内容>",
        },
        ensure_ascii=False,
    )

    return (
        "笔记协作指引：\n"
        f"- 当前任务尚未建立笔记。\n"
        f"- 创建笔记时请使用格式：[TOOL_CALL:note:{{...}}]，参数模板如下（需将 content 替换为实际研究总结）：\n"
        f"  {create_template}\n"
        "- **重要**：content 字段必须填写本次任务的实际研究发现和关键信息，不要使用占位文本。\n"
        "- 创建成功后记录返回的 note_id，并在后续所有更新中复用。\n"
        "- 同步笔记后，再输出面向用户的总结。\n"
    )

