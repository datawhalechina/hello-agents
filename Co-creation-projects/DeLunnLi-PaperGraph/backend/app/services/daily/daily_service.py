
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from fastapi import HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from ...agents import get_search_agent
from ...core.storage import PaperDatabase
from ...models.schemas import DailyPapersRequest, DailyPapersResponse
from ..daily.daily_cache_store import get_cache, set_cache
from ..daily.daily_recommend_store import record_arxiv_recommendations
from ..daily.daily_recommend_feedback import record_feedback
from ..daily.daily_support import (
    extract_library_characteristics,
    fetch_external_candidates,
    get_or_load_user_context,
    llm_arxiv_categories,
)
from ..feedback.negative_feedback_memory import (
    maybe_promote_longterm_from_recent_skips,
    record_skip_negative_pref,
)
from ..llm.llm_service import coerce_hello_agents_llm_output_to_str, get_llm, is_llm_configured
from ..retrieval.recall_jobs import dedupe_papers

logger = logging.getLogger(__name__)


def _select_personalized_and_general(
    *,
    candidates: list[Any],
    external_unique: list[Any],
    personalized_k: int,
    general_k: int,
    skipped_papers: set[str],
    mem_kw: set[str],
    daily_paper_identity_sig_fn: Any,
    diversify: bool = False,
) -> tuple[list[Any], list[Any]]:
    _identity = daily_paper_identity_sig_fn
    skip_sigs = set(skipped_papers or set())
    pool = [p for p in (candidates or []) if _identity(p) not in skip_sigs]
    if len(pool) < personalized_k + general_k:
        for p in external_unique or []:
            if _identity(p) not in skip_sigs:
                pool.append(p)
    if not pool:
        return [], []

    if diversify:
        import random

        random.shuffle(pool)
    else:
        pool.sort(key=lambda p: getattr(p, "year", 0) or 0, reverse=True)
    p_idxs = list(range(min(personalized_k, len(pool))))
    g_idxs = list(range(min(personalized_k, len(pool)), min(personalized_k + general_k, len(pool))))
    try:
        if is_llm_configured():
            papers_info = [
                {
                    "idx": i,
                    "title": str(getattr(p, "title", "") or "")[:200],
                    "abstract": str(getattr(p, "abstract", "") or "")[:400],
                    "year": getattr(p, "year", None),
                }
                for i, p in enumerate(pool)
            ]
            pref_keywords = sorted({str(k).strip().lower() for k in (mem_kw or set()) if str(k).strip()})[:30]
            prompt = json.dumps(
                {
                    "task": f"Select {personalized_k} personalized and {general_k} exploration papers",
                    "interests": pref_keywords,
                    "candidates": papers_info,
                },
                ensure_ascii=False,
            )
            pick_temp = 0.55 if diversify else 0.2
            raw = coerce_hello_agents_llm_output_to_str(
                get_llm().invoke([{"role": "user", "content": prompt}], temperature=pick_temp, max_tokens=400)
            )
            data = json.loads(raw.strip().lstrip("```json").rstrip("```").strip())
            llm_p = [int(i) for i in (data.get("personalized") or [])[:personalized_k] if 0 <= int(i) < len(pool)]
            llm_g = [
                int(i)
                for i in (data.get("general") or [])[:general_k]
                if 0 <= int(i) < len(pool) and int(i) not in llm_p
            ]
            if llm_p or llm_g:
                p_idxs, g_idxs = llm_p, llm_g
    except Exception:
        pass
    return [pool[i] for i in p_idxs], [pool[i] for i in g_idxs]


async def _record_daily_recommendations(
    *,
    db_path: str,
    date_key: str,
    personalized_final: list[Any],
    general_selected: list[Any],
    log: Any,
) -> None:
    try:
        items: list[tuple[str | None, str]] = []
        for p in personalized_final:
            items.append((getattr(p, "arxiv_id", None), f"[P] {getattr(p, 'title', '') or ''}"))
        for p in general_selected:
            items.append((getattr(p, "arxiv_id", None), f"[G] {getattr(p, 'title', '') or ''}"))
        if items:
            await run_in_threadpool(
                record_arxiv_recommendations, db_path, date_key=str(date_key), items=items,
            )
    except Exception as ex:
        log.debug("记录推荐列表失败: %s", ex)


_MAX_TITLES = 18
_TITLE_MAX_CHARS = 220
_TAG_MAX_LEN = 28
_TAGS_MAX_EACH = 5


def titles_for_daily_theme_prompt(papers: list[Any]) -> list[str]:
    out: list[str] = []
    for p in papers[:_MAX_TITLES]:
        t = str(getattr(p, "title", None) or "").strip()
        if not t:
            continue
        if len(t) > _TITLE_MAX_CHARS:
            t = t[: _TITLE_MAX_CHARS - 1] + "\u2026"
        out.append(t)
    return out


def _strip_json_fence(text: str) -> str:
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    return m.group(1).strip() if m else s


def _sanitize_tags(raw: Any, *, max_n: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen, out = set(), []
    for x in raw:
        if not isinstance(x, str):
            continue
        s = " ".join(x.split())
        if len(s) < 2 or len(s) > _TAG_MAX_LEN or s.casefold() in seen:
            continue
        seen.add(s.casefold())
        out.append(s)
        if len(out) >= max_n:
            break
    return out


def summarize_daily_theme_keywords_sync(
    *,
    personalized_titles: list[str],
    general_titles: list[str],
    max_each: int = _TAGS_MAX_EACH,
) -> tuple[list[str], list[str]]:
    if not is_llm_configured() or (not personalized_titles and not general_titles):
        return [], []
    try:
        llm = get_llm()
    except Exception as e:
        logger.warning("daily_theme_keywords: llm init failed: %s", e)
        return [], []

    lines_p = "\n".join(f"- {t}" for t in personalized_titles) or "\uff08\u65e0\uff09"
    lines_g = "\n".join(f"- {t}" for t in general_titles) or "\uff08\u65e0\uff09"
    prompt = f"""\u4f60\u662f\u5b66\u672f\u6587\u732e\u63a8\u8350\u4ea7\u54c1\u7684\u6587\u6848\u52a9\u624b\u3002\u4e0b\u9762\u4e24\u7ec4\u6807\u9898\u5206\u522b\u6765\u81ea\u300c\u4e2a\u6027\u5316\u63a8\u8350\u300d\u4e0e\u300c\u5f53\u65e5\u7cbe\u9009\uff08\u968f\u673a\u63a2\u7d22\uff09\u300d\u4e24\u680f\u8bba\u6587\u3002

\u3010\u4e2a\u6027\u5316\u63a8\u8350\u3011\u9898\u540d\uff1a
{lines_p}

\u3010\u5f53\u65e5\u7cbe\u9009\u3011\u9898\u540d\uff1a
{lines_g}

\u8bf7\u4e3a\u6bcf\u4e00\u7ec4\u5404\u63d0\u70bc\u4e0d\u8d85\u8fc7 {max_each} \u4e2a\u300c\u4e3b\u9898\u6807\u7b7e\u300d\uff0c\u7528\u4e8e\u754c\u9762\u6807\u7b7e\u5c55\u793a\u3002
\u89c4\u5219\uff1a
1. \u6bcf\u4e2a\u6807\u7b7e 2\uff5e14 \u4e2a\u6c49\u5b57\u6216\u76f8\u5f53\u957f\u5ea6\uff1b\u53ef\u542b\u5fc5\u8981\u82f1\u6587\u7f29\u7565\u8bcd\uff08\u5982 LLM\u3001RL\u3001GNN\uff09\uff1b\u4e0d\u8981\u6574\u53e5\u590d\u5236\u539f\u6807\u9898\u3002
2. \u6982\u62ec\u8be5\u7ec4\u5171\u540c\u7684\u7814\u7a76\u65b9\u5411\u6216\u65b9\u6cd5\uff1b\u7ec4\u5185\u6807\u7b7e\u5c3d\u91cf\u4e0d\u91cd\u590d\u3002
3. \u53ea\u8f93\u51fa\u4e00\u6bb5\u4e25\u683c JSON\uff08\u4e0d\u8981 markdown \u56f4\u680f\u3001\u4e0d\u8981\u524d\u540e\u8bf4\u660e\uff09\uff0c\u683c\u5f0f\u56fa\u5b9a\u4e3a\uff1a
{{\\"personalized\\":[\\"\u2026\\"],\\"general\\":[\\"\u2026\\"]}}
\u952e\u540d\u5fc5\u987b\u4e3a\u82f1\u6587\uff1b\u82e5\u67d0\u7ec4\u65e0\u6709\u6548\u6807\u9898\u5219\u5bf9\u5e94\u6570\u7ec4\u4e3a []\u3002"""
    try:
        raw = coerce_hello_agents_llm_output_to_str(
            llm.invoke([{"role": "user", "content": prompt}], temperature=0.15, max_tokens=420)
        )
    except Exception as e:
        logger.warning("daily_theme_keywords: invoke failed: %s", e)
        return [], []

    try:
        data = json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError:
        logger.warning("daily_theme_keywords: json parse failed, head=%r", (raw or "")[:240])
        return [], []
    if not isinstance(data, dict):
        return [], []
    return (
        _sanitize_tags(data.get("personalized"), max_n=max_each),
        _sanitize_tags(data.get("general"), max_n=max_each),
    )


def _build_strategy_explanation(
    *, agent: Any, n_personalized: int, n_general: int, n_candidates: int, n_memory_kw: int,
) -> str:
    fallback = f"个性化{n_personalized}篇 · 通用{n_general}篇 · 候选{n_candidates}篇"
    if not is_llm_configured():
        return fallback
    prompt = (
        f"用一句话中文概括今日论文推荐策略：个性化{n_personalized}篇、通用{n_general}篇，"
        f"候选池{n_candidates}篇，记忆词{n_memory_kw}条参与"
    )
    try:
        raw = agent.llm.invoke([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=80)
        return coerce_hello_agents_llm_output_to_str(raw).strip()[:200]
    except Exception:
        return fallback


def _build_pick_hints(personalized_final, general_selected, _identity):
    from ...models.schemas import DailyPaperPickHint

    hints_p = [
        DailyPaperPickHint(identity_key=_identity(p), pick_kind="personalized", explanation="基于用户兴趣匹配")
        for p in personalized_final
    ]
    hints_g = [
        DailyPaperPickHint(identity_key=_identity(p), pick_kind="general", explanation="多样性探索推荐")
        for p in general_selected
    ]
    return hints_p, hints_g


async def _build_daily_response(
    *,
    date_key,
    external_unique,
    general_selected,
    personalized_final,
    candidates,
    personalized_k,
    mem_kw_n,
    mem_kw_list,
    use_llm_theme_keywords,
    agent,
    daily_paper_identity_sig_fn,
    papergraph_to_api_fn,
    db_path,
) -> DailyPapersResponse:
    _to_api = papergraph_to_api_fn
    _identity = daily_paper_identity_sig_fn
    strategy_explanation = _build_strategy_explanation(
        agent=agent,
        n_personalized=len(personalized_final),
        n_general=len(general_selected),
        n_candidates=len(candidates),
        n_memory_kw=mem_kw_n,
    )
    hints_p, hints_g = _build_pick_hints(personalized_final, general_selected, _identity)

    p_theme: list[str] = []
    g_theme: list[str] = []
    if use_llm_theme_keywords:
        try:
            p_theme, g_theme = await run_in_threadpool(
                summarize_daily_theme_keywords_sync,
                personalized_titles=titles_for_daily_theme_prompt(personalized_final),
                general_titles=titles_for_daily_theme_prompt(general_selected),
            )
        except Exception as ex:
            logger.warning("每日主题关键词 LLM 总结失败: %s", ex)

    resp = DailyPapersResponse(
        success=True,
        date_key=date_key,
        arxiv_latest_total=len(external_unique),
        arxiv_selected_total=len(general_selected),
        personalized_total=len(personalized_final),
        arxiv_latest=[_to_api(p) for p in external_unique[:20]],
        arxiv_selected=[_to_api(p) for p in general_selected],
        personalized=[_to_api(p) for p in personalized_final],
        message=(
            f"候选 {len(candidates)} · 个性化 {len(personalized_final)}/{personalized_k} · "
            f"通用 {len(general_selected)}"
            + (f" · 记忆词 {mem_kw_n}" if mem_kw_n else "")
        ),
        memory_keywords_used=mem_kw_list,
        strategy_explanation=strategy_explanation,
        personalized_theme_keywords=p_theme,
        general_theme_keywords=g_theme,
        personalized_pick_hints=hints_p,
        general_pick_hints=hints_g,
    )

    try:
        from .daily_recommend_feedback import record_daily_shown_papers

        shown: list[dict[str, str]] = []
        for p in (resp.arxiv_selected or []) + (resp.personalized or []):
            title = (getattr(p, "title", None) or "").strip()
            if not title and isinstance(p, dict):
                title = str(p.get("title", "") or "").strip()
            if title:
                shown.append({"identity_key": str(_identity(p)), "title": title})
        if shown:
            logger.info("记录 %d 篇已推荐论文，下次刷新将排除", len(shown))
            await run_in_threadpool(record_daily_shown_papers, str(db_path), date_key, shown)
    except Exception as ex:
        logger.warning("记录已推荐论文失败: %s", ex)

    try:
        await run_in_threadpool(
            set_cache, db_path, date_key=date_key, cache_key="default", payload=resp.model_dump(mode="json")
        )
    except Exception as ex:
        logger.warning("每日论文缓存写入失败: %s", ex)

    return resp


async def read_daily_cached_or_204(*, db_path: str) -> Response:
    import datetime as _dt

    date_key = _dt.datetime.now().strftime("%Y-%m-%d")
    try:
        cached = await run_in_threadpool(get_cache, db_path, date_key=date_key, cache_key="default")
        if not cached:
            return Response(status_code=204)
        return DailyPapersResponse(**cached)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def compute_daily_papers(
    *,
    body: DailyPapersRequest,
    db_path: str,
    searcher: Any,
    daily_paper_identity_sig_fn: Any,
    logger: Any,
    daily_arxiv_cs_categories: list[str],
    papergraph_to_api_fn: Any,
) -> DailyPapersResponse:
    _identity = daily_paper_identity_sig_fn
    try:
        import datetime

        date_key = datetime.datetime.now().strftime("%Y-%m-%d")
        force_refresh = bool(getattr(body, "force_refresh", False))
        try:
            _dbv = int(body.days_back if body.days_back is not None else 0)
        except (TypeError, ValueError):
            _dbv = 0
        days_back = max(0, min(9999, _dbv)) if _dbv > 0 else 1
        total_target = 30
        try:
            personalized_k = max(0, min(int(body.personalized_k if body.personalized_k is not None else 20), total_target))
        except (TypeError, ValueError):
            personalized_k = 20
        general_k = max(0, min(25, total_target - personalized_k))

        agent = get_search_agent()
        try:
            lib_lim = max(50, min(3000, int(body.library_limit if body.library_limit is not None else 800)))
        except (TypeError, ValueError):
            lib_lim = 800

        logger.info(
            "每日论文：开始计算 date=%s force_refresh=%s lib_limit=%s",
            date_key, force_refresh, lib_lim,
        )
        if force_refresh:
            from .daily_support import invalidate_user_profile_cache
            from .daily_recommend_feedback import clear_daily_shown_for_date

            invalidate_user_profile_cache()
            cleared = await run_in_threadpool(clear_daily_shown_for_date, str(db_path), date_key)
            if cleared:
                logger.info("每日论文：force_refresh 已清除当日 shown 记录 %s 条", cleared)

        library_papers = await run_in_threadpool(
            PaperDatabase(db_path).get_all_papers, limit=lib_lim, order_by="created_at DESC",
        )
        lib_ids = [int(getattr(p, "id", 0) or 0) for p in library_papers if int(getattr(p, "id", 0) or 0) > 0]

        (mem_kw, mem_kw_n, mem_kw_list, skipped_papers), (_, lib_kw) = await asyncio.gather(
            get_or_load_user_context(
                db_path=db_path,
                lib_ids=lib_ids,
                log=logger,
                force_reload=force_refresh,
                include_shown_exclusions=not force_refresh,
            ),
            run_in_threadpool(extract_library_characteristics, library_papers),
        )
        llm_categories = llm_arxiv_categories(agent, mem_kw_list, daily_arxiv_cs_categories)

        all_external, source_counts, _arxiv_query = await fetch_external_candidates(
            searcher=searcher,
            mem_kw=mem_kw,
            lib_kw=lib_kw,
            days_back=days_back,
            daily_arxiv_cs_categories=llm_categories,
            log=logger,
            exclude_sigs=skipped_papers,
        )
        logger.info(
            "每日论文：外源拉取完成 arxiv=%s external_raw=%s",
            source_counts.get("arxiv"),
            len(all_external),
        )
        external_unique = [
            p for p in dedupe_papers(all_external, identity_fn=_identity) if getattr(p, "title", None)
        ]
        candidates = list(external_unique)

        if len(candidates) < 30:
            logger.info("每日论文：候选不足(%s)，放宽条件重新拉取", len(candidates))
            all_external2, _, _ = await fetch_external_candidates(
                searcher=searcher,
                mem_kw=mem_kw,
                lib_kw=lib_kw,
                days_back=max(7, days_back * 2),
                daily_arxiv_cs_categories=llm_categories,
                log=logger,
                exclude_sigs=skipped_papers,
            )
            seen_sigs = {_identity(p) for p in candidates}
            for p in dedupe_papers(all_external2, identity_fn=_identity):
                if getattr(p, "title", None) and _identity(p) not in seen_sigs:
                    seen_sigs.add(_identity(p))
                    candidates.append(p)
            logger.info("每日论文：补充拉取后候选=%s", len(candidates))

        if not candidates:
            return DailyPapersResponse(
                success=True,
                date_key=date_key,
                arxiv_latest_total=0,
                arxiv_selected_total=0,
                personalized_total=0,
                arxiv_latest=[],
                arxiv_selected=[],
                personalized=[],
                message="暂无可用论文推荐",
                memory_keywords_used=mem_kw_list,
                strategy_explanation="\n".join(
                    [
                        "候选不足，未形成当日推荐池",
                        (f"记忆词约 {mem_kw_n} 个（下列为短词优先）" if mem_kw_n else "记忆词：无"),
                    ]
                ),
                personalized_pick_hints=[],
                general_pick_hints=[],
            )

        personalized_final, general_selected = await run_in_threadpool(
            _select_personalized_and_general,
            candidates=candidates,
            external_unique=external_unique,
            personalized_k=personalized_k,
            general_k=general_k,
            skipped_papers=skipped_papers,
            mem_kw=mem_kw,
            daily_paper_identity_sig_fn=_identity,
            diversify=force_refresh,
        )

        await _record_daily_recommendations(
            db_path=db_path,
            date_key=date_key,
            personalized_final=personalized_final,
            general_selected=general_selected,
            log=logger,
        )

        return await _build_daily_response(
            date_key=date_key,
            external_unique=external_unique,
            general_selected=general_selected,
            personalized_final=personalized_final,
            candidates=candidates,
            personalized_k=personalized_k,
            mem_kw_n=mem_kw_n,
            mem_kw_list=mem_kw_list,
            use_llm_theme_keywords=getattr(body, "use_llm_theme_keywords", True),
            agent=agent,
            daily_paper_identity_sig_fn=_identity,
            papergraph_to_api_fn=papergraph_to_api_fn,
            db_path=db_path,
        )
    except Exception:
        logger.exception("daily_service.compute_daily_papers_failed")
        raise HTTPException(status_code=500, detail="daily papers failed")


async def record_user_daily_feedback(*, body, db_path) -> Any:
    import datetime
    from .daily_recommend_feedback import FeedbackAction
    from ...models.schemas import DailyRecommendFeedbackResponse

    date_key = datetime.datetime.now().strftime("%Y-%m-%d")
    identity_key = body.identity_key
    identity_type = "title_hash"
    if identity_key.startswith("arxiv:"):
        identity_type, identity_key = "arxiv", identity_key[6:]
    elif identity_key.startswith("doi:"):
        identity_type, identity_key = "doi", identity_key[4:]
    elif identity_key.startswith("title_hash:"):
        identity_type, identity_key = "title_hash", identity_key[11:]

    ok = await run_in_threadpool(
        record_feedback,
        db_path,
        date_key=date_key,
        paper_identity_key=identity_key,
        identity_type=identity_type,
        title=body.title,
        action=FeedbackAction(body.action),
        source_list=body.source_list,
        score_at_recommend=body.score_at_recommend,
        keywords=body.keywords,
        category=body.category,
    )

    if str(body.action) == "skip":
        try:
            await run_in_threadpool(
                record_skip_negative_pref,
                db_path,
                identity_key=body.identity_key,
                title=str(body.title or ""),
                abstract=None,
                journal=body.journal,
                source=body.source,
                keywords=body.keywords,
                category=body.category,
                ttl_days=14,
            )
            await run_in_threadpool(
                maybe_promote_longterm_from_recent_skips,
                db_path,
                window_days=30,
                min_count=5,
                min_confidence=0.6,
                max_new_rules=2,
            )
        except Exception:
            pass

    return DailyRecommendFeedbackResponse(success=ok, message="反馈已记录" if ok else "记录失败")
