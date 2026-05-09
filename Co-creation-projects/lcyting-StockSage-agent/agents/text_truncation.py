"""文本截断工具：在长度上限内优先在段落、换行、句号等处断开，减少半句截断。"""

from __future__ import annotations


def truncate_at_natural_boundary(text: str, max_chars: int, suffix: str = "…") -> str:
    """
    将 text 截断至不超过 max_chars（含 suffix）。

    优先级：双换行段落 > 单换行 > 句末标点（。！？；.!?，跳过疑似小数点）> 空格 > 硬截断。
    """
    if max_chars <= 0:
        return ""

    raw = text or ""
    if len(raw) <= max_chars:
        return raw

    suf = suffix or ""
    limit = max_chars - len(suf)
    if limit <= 0:
        return suf[:max_chars]

    window = raw[:limit]
    # 句末/空格截断时避免只剩极短前缀；段落边界（\n\n）不受此限，以免首段很短时无法断段
    min_pos = max(1, int(limit * 0.35))

    def _fits(head_end: int) -> bool:
        head = raw[:head_end].rstrip()
        return len(head) + len(suf) <= max_chars

    para = window.rfind("\n\n")
    if para >= 1 and _fits(para) and raw[:para].strip():
        return raw[:para].rstrip() + suf

    nl = window.rfind("\n")
    if nl >= min_pos and _fits(nl) and raw[:nl].strip():
        return raw[:nl].rstrip() + suf

    sentence_ends = "。！？；.!?"
    cut = -1
    for i in range(len(window) - 1, -1, -1):
        ch = window[i]
        if ch not in sentence_ends:
            continue
        if ch == ".":
            if i > 0 and window[i - 1].isdigit():
                continue
            if i + 1 < len(window) and window[i + 1].isdigit():
                continue
        cut = i + 1
        break
    if cut >= min_pos and _fits(cut):
        return raw[:cut].rstrip() + suf

    sp = window.rfind(" ")
    if sp >= min_pos and _fits(sp):
        return raw[:sp].rstrip() + suf

    return raw[:limit].rstrip() + suf
