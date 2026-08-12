"""可选：从公开网络拉取简报，作为辩论的「考据附录」（模型仍以自身知识为主）。"""

from __future__ import annotations

from .ddg_search import duckduckgo_search_text
from .wiki_tools import wiki_multiview


def build_evidence_bundle(topic: str, *, max_chars: int = 5500) -> str:
    """
    聚合维基多语种摘录 + 少量检索结果，失败时返回说明性短文本。
    """
    chunks: list[str] = []
    try:
        w = wiki_multiview(topic.strip())
        if len(w) > 4000:
            w = w[:4000] + "\n... [维基部分已截断]"
        chunks.append("【维基多语种摘录】\n" + w)
    except Exception as e:  # pragma: no cover
        chunks.append(f"【维基】抓取失败：{e}")

    try:
        q = f"{topic.strip()} 历史 笔记 野史 争议 研究"
        chunks.append(duckduckgo_search_text(q, max_results=4, max_body_chars=600))
    except Exception as e:  # pragma: no cover
        chunks.append(f"【检索】失败：{e}")

    text = "\n\n---\n\n".join(chunks)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [总附录已截断]"
    return text
