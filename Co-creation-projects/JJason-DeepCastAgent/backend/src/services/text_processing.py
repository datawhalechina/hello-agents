"""用于标准化代理生成文本的实用助手。"""

from __future__ import annotations


def strip_tool_calls(text: str) -> str:
    """移除文本中的工具调用标记。

    支持嵌套方括号，例如:
    [TOOL_CALL:note:{"tags":["deep_research","task_1"]}]
    """
    if not text:
        return text

    # 找到 [TOOL_CALL: 起始标记，然后手动匹配到对应的闭合 ]
    result: list[str] = []
    i = 0
    marker = "[TOOL_CALL:"
    while i < len(text):
        pos = text.find(marker, i)
        if pos == -1:
            result.append(text[i:])
            break
        result.append(text[i:pos])
        # 从 marker 起始位置向后扫描，跟踪方括号深度
        depth = 0
        j = pos
        while j < len(text):
            if text[j] == "[":
                depth += 1
            elif text[j] == "]":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        i = j + 1  # 跳过闭合的 ]
    return "".join(result)

