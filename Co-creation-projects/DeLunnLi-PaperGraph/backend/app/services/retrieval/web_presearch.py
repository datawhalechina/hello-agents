"""Web 预搜索：在多源学术检索之前先做"锚点"召回。

目标：
- 解决短词/术语（如 patchcore）导致的多源召回噪声与歧义
- 先从 Web 搜索拿到最可信的论文标题/DOI/arXiv，再由 Agent 生成更精确的检索单元

说明：
- Settings 默认 ``tavily_presearch_enabled=true``；未配置 ``TAVILY_API_KEY`` 时不会发外呼。
- Tavily 会场→域名映射见 ``tavily_venue_domains.json``（``tavily_venue_config``），勿在此文件堆业务映射。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

from .tavily_venue_config import (  # noqa: E402
    get_official_proceedings_hosts,
)

# Tavily：query 超过 400 字符会返回 400（见官方文档与常见报错）
TAVILY_MAX_QUERY_CHARS = 400


def _normalize_tavily_query(query: str, *, max_chars: int = TAVILY_MAX_QUERY_CHARS) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    if len(q) <= max_chars:
        return q
    clipped = q[:max_chars].rstrip()
    logger.warning(
        "tavily: query 过长已截断 (%d -> %d 字符)，避免 Tavily 400",
        len(q),
        len(clipped),
    )
    return clipped


async def tavily_search_async(
    *,
    api_key: str,
    query: str,
    max_results: int = 5,
    timeout_sec: int = 20,
    include_domains: Optional[List[str]] = None,
    httpx_client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """Async Tavily Search API call. Reuses shared httpx client when available."""
    q = _normalize_tavily_query(query)
    if not q:
        return []
    if not (api_key or "").strip():
        return []

    n = max(1, min(10, int(max_results or 5)))
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": q,
        "max_results": n,
        "include_answer": True,
        "include_raw_content": True,
    }
    dom = [str(x).strip() for x in (include_domains or []) if str(x).strip()][:3]
    if dom:
        payload["include_domains"] = dom

    timeout = httpx.Timeout(timeout_sec)
    async def _do_post(client):
        resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            payload2 = dict(payload)
            payload2["include_raw_content"] = False
            resp = await client.post(url, json=payload2)
        resp.raise_for_status()
        return resp.json() or {}

    if httpx_client is not None:
        data = await _do_post(httpx_client)
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            data = await _do_post(client)

    out: List[Dict[str, Any]] = []
    ans = str(data.get("answer") or "").strip()
    if ans:
        out.append({"title": ans[:180], "link": "", "snippet": ans})
    for it in (data.get("results") or [])[:n]:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip()
        link = str(it.get("url") or "").strip()
        snippet = str(it.get("content") or "").strip()
        if not title and not link and not snippet:
            continue
        out.append({
            "title": title[:200] if title else "",
            "link": link,
            "snippet": snippet[:300] if snippet else "",
            "raw_content": str(it.get("raw_content") or "")[:20000],
        })
    return out


def pick_anchor_title(items: List[Dict[str, Any]]) -> Optional[str]:
    """Pick the best paper title from Tavily results. Prefer trusted academic sources."""
    if not items:
        return None

    trusted = ("arxiv.org", "doi.org", "neurips.cc", "openreview.net", "proceedings.")
    def _score(it: Dict[str, Any]) -> float:
        title = str(it.get("title") or "").strip()
        if not title or len(title) < 8:
            return -1e9
        link = str(it.get("link") or it.get("url") or "").lower()
        score = float(len(title))
        if any(h in link for h in trusted):
            score += 200.0
        if any(h in title.lower() for h in ("github", "repo", "awesome-")):
            score -= 500.0
        return score

    best = max(items, key=_score)
    title = str(best.get("title") or "").strip()
    title = re.sub(r"^\s*(\[PDF\]|\(PDF\))\s*", "", title, flags=re.I)
    return title or None

_ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)\s*([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", re.I)
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>]+", re.I)


def extract_anchor_ids(items: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """从 Tavily 返回里提取高置信 ID（arXiv / DOI）。

    用途：当 query 是短词/术语时，用这些 ID 作为"最匹配"的强证据加入候选集，
    但不绑定到某个具体 query（避免硬编码）。
    """
    arxiv_ids: List[str] = []
    dois: List[str] = []

    def _push_unique(buf: List[str], x: str, limit: int):
        t = (x or "").strip()
        if not t:
            return
        tl = t.lower()
        if any(y.lower() == tl for y in buf):
            return
        buf.append(t)
        if len(buf) > limit:
            del buf[limit:]

    for it in (items or [])[:10]:
        if not isinstance(it, dict):
            continue
        hay = " ".join(
            [
                str(it.get("title") or ""),
                str(it.get("link") or it.get("url") or ""),
                str(it.get("snippet") or it.get("content") or ""),
                str(it.get("raw_content") or ""),
            ]
        )
        for m in _ARXIV_ID_RE.finditer(hay):
            _push_unique(arxiv_ids, m.group(1), 5)
        for m in _DOI_RE.finditer(hay):
            doi = m.group(0).rstrip(").,;]")
            _push_unique(dois, doi, 5)

    return {"arxiv_ids": arxiv_ids, "dois": dois}


_NON_PAPER_HOSTS = ("youtube.com", "youtu.be", "reddit.com", "twitter.com", "x.com", "facebook.com", "instagram.com")


def _clean_keyword_phrase(s: str, max_len: int = 100) -> str:
    t = (s or "").strip()
    if not t:
        return ""
    t = re.sub(r"^\s*(\[\s*pdf\s*\]|\(\s*pdf\s*\)|【\s*pdf\s*】)\s*", "", t, flags=re.I)
    t = re.sub(r"^\s*pdf\s*[:：]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*[·|\-]\s*GitHub\s*$", "", t, flags=re.I)
    t = re.sub(r"\.pdf\s+at\s+main.*$", "", t, flags=re.I)
    t = re.sub(r"\s*\.\.\.$", "", t).strip()
    t = re.sub(r"^(?:[A-Z]{2,10})\s*[:：]\s+", "", t).strip()
    # 去掉多余空白与换行
    t = re.sub(r"\s+", " ", t).strip()
    # 限制长度
    if len(t) > max_len:
        t = t[:max_len-1].rstrip() + "…"
    return t


def _snippet_as_keyword(snippet: str, max_len: int = 140) -> str:
    s = (snippet or "").strip().replace("\n", " ")
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def _tavily_item_keyword_priority(it: Dict[str, Any]) -> int:
    """排序：优先无 URL 的 answer 摘要，其次 arXiv/DOI 等学术落地页，降低论坛/博客噪声顺序。"""
    if not isinstance(it, dict):
        return 0
    link = str(it.get("link") or it.get("url") or "").strip().lower()
    if not link:
        return 110
    if "arxiv.org" in link:
        return 100
    if "doi.org" in link or "openreview.net" in link:
        return 95
    if any(h in link for h in get_official_proceedings_hosts()):
        return 88
    if any(h in link for h in ("cv-foundation.org", "aclweb.org")):
        return 88
    if any(h in link for h in ("ieee.org", "acm.org", "springer", "nature.com", "science.org")):
        return 82
    if any(h in link for h in _NON_PAPER_HOSTS):
        return 0
    return 40


def tavily_items_to_llm_keywords(
    items: List[Dict[str, Any]],
    user_query: str,
    *,
    max_phrases: int = 16,
) -> List[str]:
    """把 Tavily 返回的论文标题/摘要片段转成后续学术检索用的 llm_keywords（去重、限长）。

    设计目标：用户希望「Tavily 搜到的论文名/内容」**直接**参与 arXiv/OpenAlex 等 OR 检索，
    而不是只选一个启发式锚点标题。
    """
    uq = (user_query or "").strip()
    out: List[str] = []
    seen: set[str] = set()

    def push(x: str) -> None:
        t = _clean_keyword_phrase(x)
        if not t or len(t) < 8:
            return
        low = t.lower()
        if low in seen:
            return
        # 过滤明显非论文页标题
        if any(h in low for h in ("github", "repo", "awesome-", "arxiv-sanity", "paperswithcode")):
            return
        out.append(t)
        seen.add(low)
        if len(out) >= max_phrases:
            return

    if uq:
        push(uq)

    pool = [x for x in (items or [])[:16] if isinstance(x, dict)]
    pool.sort(key=_tavily_item_keyword_priority, reverse=True)
    for it in pool[:12]:
        link = str(it.get("link") or it.get("url") or "").lower()
        if any(h in link for h in _NON_PAPER_HOSTS):
            continue
        title = str(it.get("title") or "").strip()
        if title:
            push(title)
        if len(out) >= max_phrases:
            break
        sn = str(it.get("snippet") or it.get("content") or "").strip()
        sk = _snippet_as_keyword(sn)
        if sk and sk.lower() not in seen and sk.lower() != (title or "").lower():
            push(sk)
        if len(out) >= max_phrases:
            break

    return out[:max_phrases]
