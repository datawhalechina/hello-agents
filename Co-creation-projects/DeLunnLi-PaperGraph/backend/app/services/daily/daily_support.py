from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from typing import Any

from fastapi.concurrency import run_in_threadpool

from ...agents import get_search_agent
from ...core.search import _arxiv_canonical_from_paper
from ...settings import get_settings
from ...utils.common import suppress_exceptions, suppress_exceptions_async
from .daily_recommend_feedback import get_high_value_keywords_from_feedback, get_skipped_papers
from .user_behavior_analytics import get_user_interest_profile_for_daily_recommend
from ..llm.llm_service import coerce_hello_agents_llm_output_to_str

logger = logging.getLogger(__name__)

_DAILY_HTTP_TIMEOUT_SEC = 45
_DAILY_HTTP_MAX_ATTEMPTS = 3
_ARXIV_QUERY_NOISE = frozenset({
    "academicsearch", "tavilysearch", "refinequery", "parseintent", "filterresults",
    "explainresults", "diversifyresults", "proceedingsitesearch", "finish",
})
_OPENALEX_FALLBACK_QUERY = "machine learning neural network transformer deep learning"

_user_profile_cache: tuple[Any, ...] | None = None
_user_profile_cache_ts: float = 0.0
_USER_PROFILE_CACHE_TTL = 7200


@suppress_exceptions(default_return={"http_timeout_sec": float(_DAILY_HTTP_TIMEOUT_SEC), "http_max_attempts": int(_DAILY_HTTP_MAX_ATTEMPTS)})
def daily_arxiv_http_kw() -> dict[str, float | int]:
    s = get_settings()
    to = float(getattr(s, "papergraph_daily_arxiv_http_timeout_sec", _DAILY_HTTP_TIMEOUT_SEC))
    at = int(getattr(s, "papergraph_daily_arxiv_http_max_attempts", _DAILY_HTTP_MAX_ATTEMPTS))
    return {"http_timeout_sec": max(15.0, min(300.0, to)), "http_max_attempts": max(1, min(10, at))}


def prepare_memory_keywords(mem_kw: set[str], *, limit: int = 12, short_first: bool = False) -> tuple[list[str], int]:
    raw_items = {str(x).strip().lower() for x in (mem_kw or set()) if str(x).strip()}
    ranked = sorted(raw_items, key=lambda s: (len(s), s)) if short_first else sorted(raw_items)
    out, seen = [], set()
    for t in ranked:
        if t and t not in seen and len(t) > 2 and not (t.isdigit() and len(t) <= 4):
            out.append(t)
            seen.add(t)
            if len(out) >= limit:
                break
    return out, len(raw_items)


def collect_memory_store_texts(
    store: Any,
    lib_ids: list[int],
    *,
    global_limit: int = 28,
    snippets_per_paper: int = 5,
    max_papers: int = 60,
) -> list[str]:
    raw_texts: list[str] = []
    for line in store.list_recent_contents(
        scope="global", paper_id=None, kinds=["preference", "working", "short"], limit=global_limit
    ):
        s = str(line or "").strip()
        if s:
            raw_texts.append(s)
    seen: set[int] = set()
    n = 0
    for pid in lib_ids:
        try:
            i = int(pid)
        except Exception:
            continue
        if i <= 0 or i in seen:
            continue
        seen.add(i)
        n += 1
        if n > max_papers:
            break
        for line in store.list_recent_contents(
            scope="paper",
            paper_id=i,
            kinds=["short", "working", "paper_summary"],
            limit=snippets_per_paper,
        ):
            s = str(line or "").strip()
            if s:
                raw_texts.append(s)
    return raw_texts


def extract_library_characteristics(library_papers: list[Any]) -> tuple[int, set[str]]:
    """从用户文献库标题/摘要提取高频词，供每日推荐 arXiv 查询拼接。"""
    blobs: list[str] = []
    for p in library_papers or []:
        title = str(getattr(p, "title", "") or "").strip()
        abstract = str(getattr(p, "abstract", "") or "").strip()
        if title:
            blobs.append(title)
        if abstract:
            blobs.append(abstract[:800])
    return len(library_papers or []), memory_keywords_from_texts(blobs, tokens_cap=80)


def memory_keywords_from_texts(blobs: list[str], *, tokens_cap: int = 320) -> set[str]:
    if not blobs:
        return set()

    def _tok(text: str) -> list[str]:
        t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", (text or "").lower())
        return [x for x in (x.strip() for x in t.split() if x.strip()) if len(x) >= 3][:2000]

    freq: Counter[str] = Counter()
    for b in blobs:
        for w in _tok(b):
            freq[w] += 1
    return {w for w, _ in freq.most_common(tokens_cap) if 3 <= len(w) <= 28}


def build_daily_arxiv_query(mem_kw: set[str], lib_kw: set[str] | list[str] | None, *, log: Any = None) -> str:
    try:
        merged = list(mem_kw or set()) + list(lib_kw or [])
        clean = [
            str(x).strip().lower()
            for x in merged
            if str(x).strip() and len(str(x).strip()) >= 3
            and str(x).strip().lower() not in _ARXIV_QUERY_NOISE
            and not str(x).strip().startswith("http")
        ]
        keywords = clean[:12]
        if not keywords:
            return ""

        if len(keywords) >= 3:
            llm_query = _llm_build_arxiv_query(keywords, log=log)
            if llm_query and len(llm_query) >= 10:
                return llm_query[:200]

        return " OR ".join(f'"{kw}"' for kw in keywords[:4])[:200]
    except Exception:
        return ""


def _llm_build_arxiv_query(keywords: list[str], *, log: Any = None) -> str:
    try:
        from ..llm.llm_service import get_llm, is_llm_configured, coerce_hello_agents_llm_output_to_str

        if not is_llm_configured():
            return ""
        kw_str = ", ".join(keywords[:12])
        prompt = (
            f"将用户研究关键词转为 arXiv API 搜索查询（ti_abs 模式，AND/OR 组合，不加 site: 或类别前缀）。"
            f"只输出纯文本查询，不要 JSON 包裹，不要解释。\n"
            f"关键词：{kw_str}\n"
            f"查询："
        )
        llm = get_llm()
        raw = coerce_hello_agents_llm_output_to_str(
            llm.invoke([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=128)
        )
        q = raw.strip().strip('"').strip("'")[:200]
        return q if len(q) >= 4 else ""
    except Exception as e:
        if log:
            log.debug("LLM arXiv query construction failed: %s", e)
        return ""


def append_unique_by_title(into: list[Any], extra: list[Any]) -> None:
    seen = {str(getattr(x, "title", "") or "").strip().lower() for x in into}
    for p in extra:
        tt = str(getattr(p, "title", "") or "").strip().lower()
        if tt and tt not in seen:
            seen.add(tt)
            into.append(p)


async def _safe_load_keywords(coro_or_func, *args, **kwargs) -> set[str]:
    try:
        result = await (coro_or_func(*args, **kwargs) if callable(coro_or_func) else coro_or_func)
        return result if isinstance(result, set) else set()
    except Exception:
        return set()


async def extract_memory_keywords_via_llm(raw_texts: list[str], log: Any) -> set[str]:
    if not raw_texts:
        return set()
    try:
        agent = get_search_agent()
        llm = getattr(agent, "llm", None)
        if not llm:
            return set()
        seen: set[str] = set()
        deduped: list[str] = []
        total_chars = 0
        for t in raw_texts:
            s = str(t).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            deduped.append(s)
            total_chars += len(s)
            if total_chars > 3000:
                break
        memory_block = "\n---\n".join(deduped[:60])
        prompt = (
            "Extract research keywords (methods, models, tasks, domain terms) from user memory fragments. "
            "Output JSON array only, no explanation. Skip stopwords, greetings, dates, URLs.\n\n"
            f"{memory_block}\n\n"
            'Format: ["keyword1", ...]'
        )
        raw = await run_in_threadpool(
            llm.invoke,
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=400,
        )
        txt = coerce_hello_agents_llm_output_to_str(raw).strip()
        try:
            parsed = json.loads(txt)
        except Exception:
            m = re.search(r"\[.*?\]", txt, re.DOTALL)
            if not m:
                return set()
            try:
                parsed = json.loads(m.group())
            except Exception:
                return set()
        if isinstance(parsed, list):
            return {str(x).strip().lower() for x in parsed if str(x).strip() and len(str(x).strip()) >= 2}
        return set()
    except Exception as e:
        log.warning("LLM 提取记忆关键词失败: %s", e)
        return set()


async def load_memory_keywords(*, db_path: str, lib_ids: list[int], log: Any) -> set[str]:
    mem_kw: set[str] = set()

    @suppress_exceptions_async(default_return=(None, None))
    async def _load_store_kw() -> tuple:
        from ..memory.memory_store import MemoryStore

        store = MemoryStore(str(db_path))
        raw_texts = collect_memory_store_texts(store, lib_ids)
        llm_kw = await extract_memory_keywords_via_llm(raw_texts, log)
        if llm_kw:
            return (llm_kw, None)
        return (None, memory_keywords_from_texts(raw_texts))

    llm_kw, store_kw = await _load_store_kw()
    if llm_kw:
        mem_kw.update(llm_kw)
        return mem_kw
    if store_kw:
        mem_kw.update(store_kw)

    @suppress_exceptions_async(default_return=None)
    async def _load_shared_kw() -> set[str] | None:
        from ..memory.agent_memory import get_agent_memory

        am = get_agent_memory()
        shared_lines = am.recent(agent_name="shared", memory_types=["working", "episodic"], limit=40, shared=True)
        if not shared_lines:
            return None
        shared_texts = [str(ln).strip() for ln in shared_lines if str(ln).strip()]
        shared_kw = await extract_memory_keywords_via_llm(shared_texts, log)
        return shared_kw or am.keywords_from_shared(limit_lines=50, tokens_cap=120)

    shared_kw = await _load_shared_kw()
    if shared_kw:
        mem_kw.update(shared_kw)
    return mem_kw


@suppress_exceptions_async(default_return=set())
async def load_feedback_keywords(*, db_path: str, mem_kw: set[str]) -> set[str]:
    feedback_keywords = await run_in_threadpool(
        get_high_value_keywords_from_feedback, db_path, days=21, top_n=15
    )
    mem_kw.update(feedback_keywords)
    return mem_kw


async def load_profile_keywords(*, db_path: str, mem_kw: set[str], log: Any) -> set[str]:
    try:
        user_profile = await run_in_threadpool(get_user_interest_profile_for_daily_recommend, db_path)
        mem_kw.update(kw.lower() for kw, weight in user_profile.top_keywords[:25] if weight >= 1.0)
    except Exception as e:
        log.debug("数据库行为画像提取失败: %s", e)
    return mem_kw


async def load_user_context(
    *,
    db_path: str,
    lib_ids: list[int],
    log: Any,
    include_shown_exclusions: bool = True,
) -> tuple[set[str], int, list[str], set[str]]:
    mem_kw = await load_memory_keywords(db_path=db_path, lib_ids=lib_ids, log=log)
    await load_feedback_keywords(db_path=db_path, mem_kw=mem_kw)
    await load_profile_keywords(db_path=db_path, mem_kw=mem_kw, log=log)
    skipped_papers = await _safe_load_keywords(
        run_in_threadpool(get_skipped_papers, db_path, days=14, include_shown=include_shown_exclusions)
    )
    mem_kw_list, mem_kw_n = prepare_memory_keywords(mem_kw)
    return mem_kw, mem_kw_n, mem_kw_list, skipped_papers


def invalidate_user_profile_cache() -> None:
    global _user_profile_cache, _user_profile_cache_ts
    _user_profile_cache = None
    _user_profile_cache_ts = 0.0


async def get_or_load_user_context(
    *,
    db_path: str,
    lib_ids: list[int],
    log: Any,
    force_reload: bool = False,
    include_shown_exclusions: bool = True,
) -> tuple[set[str], int, list[str], set[str]]:
    global _user_profile_cache, _user_profile_cache_ts
    now = time.time()
    if (
        not force_reload
        and _user_profile_cache is not None
        and (now - _user_profile_cache_ts) < _USER_PROFILE_CACHE_TTL
    ):
        return _user_profile_cache
    result = await load_user_context(
        db_path=db_path,
        lib_ids=lib_ids,
        log=log,
        include_shown_exclusions=include_shown_exclusions,
    )
    _user_profile_cache = result
    _user_profile_cache_ts = now
    return result


def daily_arxiv_category_list(daily_arxiv_cs_categories: list[str] | None) -> list[str]:
    cats = [str(c).strip() for c in (daily_arxiv_cs_categories or []) if str(c).strip()]
    return cats if cats else ["cs.CV", "cs.LG", "cs.AI", "cs.CL"]


def llm_arxiv_categories(agent: Any, user_keywords: list[str], all_categories: list[str]) -> list[str]:
    if not user_keywords or len(user_keywords) < 3:
        return all_categories[:4]
    kw_str = ", ".join(user_keywords[:10])
    cats_str = ", ".join(all_categories)
    prompt = f"用户研究兴趣: {kw_str}\narXiv分类: {cats_str}\n选出最相关的4-6个分类，只返回逗号分隔列表:"
    try:
        raw = agent.llm.invoke([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=60)
        result = coerce_hello_agents_llm_output_to_str(raw).strip()
        selected = [c.strip() for c in result.split(",") if c.strip() in all_categories]
        return selected[:6] if selected else all_categories[:4]
    except Exception:
        return all_categories[:4]


def append_arxiv_batch_filtered(
    batch: list[Any],
    *,
    arxiv_results: list[Any],
    seen_titles: set[str],
    exclude_sigs: set[str],
) -> None:
    for p in batch:
        t = str(getattr(p, "title", "") or "").strip().lower()
        if not t or t in seen_titles:
            continue
        pid = _arxiv_canonical_from_paper(p)
        doi = (getattr(p, "doi", "") or "").strip().lower()
        if (pid and f"arxiv:{pid}" in exclude_sigs) or (doi and f"doi:{doi}" in exclude_sigs):
            continue
        if f"ty:{t}|{getattr(p, 'year', '')}" in exclude_sigs:
            continue
        seen_titles.add(t)
        arxiv_results.append(p)


async def fetch_arxiv_candidates(
    *,
    searcher: Any,
    arxiv_query: str,
    days_back: int,
    daily_arxiv_cs_categories: list[str],
    log: Any,
    exclude_sigs: set[str] | None = None,
) -> tuple[list[Any], int]:
    cats = daily_arxiv_category_list(daily_arxiv_cs_categories)
    exclude_sigs = exclude_sigs or set()
    q = (arxiv_query or "").strip()
    http_kw = daily_arxiv_http_kw()
    arxiv_results: list[Any] = []
    seen_titles: set[str] = set()
    n_fail = 0
    # Widen the date window only when recent arXiv results are too sparse.
    days_tiers = [1, 3, 7] if days_back <= 7 else [days_back]
    if days_back > 7:
        days_tiers = [days_back, 14, 30]
    else:
        days_tiers = [d for d in [1, 3, 7] if d >= min(days_back, 7)] or [1, 3, 7]
    for dbk in days_tiers:
        if len(arxiv_results) >= 60:
            break
        for cat in cats:
            if len(arxiv_results) >= 60 or n_fail >= 3:
                break
            try:
                batch = await searcher.search_arxiv_async(
                    q, max_results=30, days_back=dbk, arxiv_categories=[cat],
                    arxiv_query_style="ti_abs", **http_kw,
                ) or []
            except Exception:
                n_fail += 1
                log.debug("每日论文：arXiv 请求失败 dbk=%s cat=%s", dbk, cat)
                continue
            n_fail = 0
            append_arxiv_batch_filtered(
                batch, arxiv_results=arxiv_results, seen_titles=seen_titles, exclude_sigs=exclude_sigs
            )
    if not arxiv_results:
        log.warning("每日论文：arXiv 未拉取到可用论文，将触发 OpenAlex 兜底")
    return arxiv_results, len(arxiv_results)


async def fetch_openalex_daily_fallback(
    *,
    searcher: Any,
    mem_kw: set[str],
    lib_kw: set[str] | list[str] | None,
    log: Any,
    max_results: int = 80,
) -> list[Any]:
    import datetime as _dt

    try:
        q = build_daily_arxiv_query(mem_kw, lib_kw, log=log)
        if len(q) < 4:
            bits = [
                t for t in prepare_memory_keywords(mem_kw, limit=12, short_first=True)[0]
                if len(t) >= 3 and not t.isdigit()
            ][:6]
            q = " ".join(bits).strip()
        if len(q) < 4:
            q = _OPENALEX_FALLBACK_QUERY
        yr = int(_dt.datetime.now(_dt.timezone.utc).year) - 2
        hits = list(
            await searcher.search_openalex_async(
                q[:220],
                max_results=max(40, min(120, max_results)),
                year_from=yr,
            )
            or []
        )
        if hits:
            log.info("每日论文：OpenAlex 兜底命中 %s 篇", len(hits))
        return hits
    except Exception as e:
        log.warning("每日论文：OpenAlex 兜底失败：%s", e)
        return []


async def fetch_external_candidates(
    *,
    searcher: Any,
    mem_kw: set[str],
    lib_kw: set[str] | list[str] | None,
    days_back: int,
    daily_arxiv_cs_categories: list[str],
    log: Any,
    exclude_sigs: set[str] | None = None,
) -> tuple[list[Any], dict[str, int], str]:
    arxiv_query = build_daily_arxiv_query(mem_kw, lib_kw, log=log)
    arxiv_results, arx_n = await fetch_arxiv_candidates(
        searcher=searcher,
        arxiv_query=arxiv_query,
        days_back=days_back,
        daily_arxiv_cs_categories=daily_arxiv_cs_categories,
        log=log,
        exclude_sigs=exclude_sigs,
    )
    if len(arxiv_results) < 16 and exclude_sigs:
        log.info(
            "每日论文：剔除已展示/跳过后过少(%s)，本轮忽略排除集再抓一批以便形成推荐池",
            len(arxiv_results),
        )
        rescue, _ = await fetch_arxiv_candidates(
            searcher=searcher,
            arxiv_query="",
            days_back=max(7, days_back),
            daily_arxiv_cs_categories=daily_arxiv_cs_categories,
            log=log,
            exclude_sigs=set(),
        )
        append_unique_by_title(arxiv_results, rescue)

    arxiv_results.sort(
        key=lambda p: (int(getattr(p, "year", 0) or 0), int(getattr(p, "citations", 0) or 0)),
        reverse=True,
    )
    arxiv_results = arxiv_results[:96]
    return arxiv_results, {"arxiv": len(arxiv_results)}, arxiv_query
