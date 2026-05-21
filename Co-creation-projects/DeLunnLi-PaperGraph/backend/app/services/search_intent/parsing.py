
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from app.core.search.paper_searcher import _sanitize_author_list_for_query


from .arxiv_normalization import sanitize_arxiv_categories, sanitize_arxiv_id_list
from ...utils.common import dedupe_strings_preserve_order
from .venue_phrases import sanitize_venue_tokens

if TYPE_CHECKING:
    from ...agents.support.search_models import SearchIntent

def _search_intent_cls():
    from ...agents.support.search_models import SearchIntent

    return SearchIntent

def strip_retrieval_meta_from_query(q: str) -> str:
    s = (q or "").strip()
    return " ".join(s.split()) if s else ""

def _fence_inner_after_first_fence(t: str) -> str | None:
    first = t.find("```")
    if first < 0:
        return None
    rest = t[first + 3 :]
    rl = rest.lstrip()
    if rl[:4].lower() == "json":
        rl = rl[4:].lstrip(" \t\r\n")
    end = rl.find("```")
    body = rl[:end].strip() if end >= 0 else rl.strip()
    return body or None

def extract_json_object(text: str) -> dict[str, Any | None]:
    t = (text or "").strip()
    if not t:
        return None
    if "```" in t and (boxed := _fence_inner_after_first_fence(t)):
        t = boxed
    start = t.find("{")
    end = t.rfind("}")
    if start < 0 or end <= start:
        return None
    raw = t[start : end + 1]
    raw = re.sub(r",\s*([\]}])", r"\1", raw)
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None

_SORT_ALLOWED = frozenset({"relevance", "date"})
_CONFIDENCE_ALLOWED = frozenset({"high", "medium", "low"})
_SEARCH_STRATEGY_ALLOWED = frozenset(
    {"keyword_matching", "semantic_search", "hybrid", "targeted_lookup"}
)

def _intent_str_list_field(source: Any, cap: int) -> list[str]:
    if not isinstance(source, list):
        return []
    return [str(x).strip() for x in source if str(x).strip()][:cap]

def _intent_str_or_list_field(source: Any, cap: int) -> list[str] | None:
    if isinstance(source, str) and source.strip():
        return [source.strip()][:cap]
    if isinstance(source, list):
        return [str(x).strip() for x in source if str(x).strip()][:cap]
    return None

def _intent_year_field(v: Any) -> int | None:
    if isinstance(v, (int, float)) and 1900 <= int(v) <= 2100:
        return int(v)
    return None

def _intent_bounded_int(v: Any, lo: int, hi: int) -> int | None:
    if isinstance(v, (int, float)):
        return max(lo, min(int(v), hi))
    return None

def _intent_flag_merge(flags: dict[str, Any], d: dict[str, Any], key: str) -> Any:
    return flags[key] if key in flags else d.get(key)

def _intent_use_tavily_raw(nested: bool, flags: dict[str, Any], d: dict[str, Any]) -> Any:
    if nested:
        return flags["use_tavily"] if "use_tavily" in flags else d.get("use_tavily")
    return d.get("use_tavily")

def search_intent_from_dict(d: dict[str, Any]) -> SearchIntent:
    nested = isinstance(d.get("search"), dict)
    if nested:
        s = dict(d["search"])
        flags = dict(d["flags"]) if isinstance(d.get("flags"), dict) else {}
        rank = dict(d["ranking"]) if isinstance(d.get("ranking"), dict) else {}
    else:
        s, flags, rank = dict(d), {}, {}

    Si = _search_intent_cls()
    intent = Si()

    intent.query = str(s.get("query") or "").strip()[:500]
    intent.keywords = _intent_str_list_field(s.get("keywords") or [], 16)
    intent.authors = _intent_str_list_field(s.get("authors") or d.get("authors") or [], 8)
    intent.venues = _intent_str_list_field(s.get("venues") or [], 8)

    tt_raw = s.get("target_titles") or s.get("paper_titles") or s.get("paper_title") or []
    if (tt_parsed := _intent_str_or_list_field(tt_raw, 6)) is not None:
        intent.target_titles = tt_parsed
    ta_raw = s.get("target_authors") or s.get("target_author") or []
    if (ta_parsed := _intent_str_or_list_field(ta_raw, 6)) is not None:
        intent.target_authors = ta_parsed

    if (yf := _intent_year_field(s.get("year_from"))) is not None:
        intent.year_from = yf
    if (yt := _intent_year_field(s.get("year_to"))) is not None:
        intent.year_to = yt

    sort = str(s.get("sort") or "relevance").lower()
    intent.sort = sort if sort in _SORT_ALLOWED else "relevance"

    if (mr := _intent_bounded_int(s.get("max_results", 10), 5, 30)) is not None:
        intent.max_results = mr

    intent.arxiv_categories = _intent_str_list_field(s.get("arxiv_categories") or [], 12)

    axl_raw = s.get("arxiv_id_list") or s.get("pinned_arxiv_ids") or d.get("arxiv_id_list")
    if (ax_parsed := _intent_str_or_list_field(axl_raw, 8)) is not None:
        intent.arxiv_id_list = ax_parsed

    intent.is_short_acronym = bool(_intent_flag_merge(flags, d, "is_short_acronym"))
    intent.wants_classic = bool(_intent_flag_merge(flags, d, "wants_classic"))
    intent.wants_recent = bool(_intent_flag_merge(flags, d, "wants_recent"))
    intent.main_conference_proceedings_only = bool(
        _intent_flag_merge(flags, d, "main_conference_proceedings_only")
    )
    ut = _intent_use_tavily_raw(nested, flags, d)
    intent.use_tavily = None if ut is None else bool(ut)

    conf = str(_intent_flag_merge(flags, d, "confidence_level") or "").strip().lower()
    if conf in _CONFIDENCE_ALLOWED:
        intent.confidence_level = conf

    strat = str(_intent_flag_merge(flags, d, "search_strategy") or "").strip().lower()
    if strat in _SEARCH_STRATEGY_ALLOWED:
        intent.search_strategy = strat

    llm_sources = flags.get("sources") or d.get("sources") or []
    if isinstance(llm_sources, list) and llm_sources:
        allowed = {"arxiv", "dblp", "openalex", "tavily"}
        intent.sources = [str(src).strip().lower() for src in llm_sources if str(src).strip().lower() in allowed]

    rk_strat = str(flags.get("ranking_strategy") or d.get("ranking_strategy") or "").strip().lower()
    if rk_strat in ("date", "relevance", "hybrid"):
        intent.ranking_strategy = rk_strat

    use_llm = rank.get("use_llm_rank", rank.get("use_two_stage_rerank", d.get("use_llm_rank", d.get("use_two_stage_rerank", True))))
    intent.use_llm_rank = bool(use_llm)
    rc_raw = rank.get("rerank_recall_max", rank.get("rerank_coarse_top_n", d.get("rerank_recall_max", d.get("rerank_coarse_top_n", 24))))
    if (rc := _intent_bounded_int(rc_raw, 8, 60)) is not None:
        intent.rerank_recall_max = rc

    rat = rank.get("rationale", d.get("ranking_rationale"))
    if rat is not None:
        intent.ranking_rationale = str(rat).strip()[:800]

    return intent

def finalize_llm_intent(intent: SearchIntent, profile: str) -> SearchIntent:
    intent.query = strip_retrieval_meta_from_query((intent.query or "")[:500])
    intent.keywords = dedupe_strings_preserve_order(list(intent.keywords or []), max_n=16)

    if not (intent.query or "").strip() and intent.keywords:
        intent.query = intent.keywords[0][:500]

    if not (intent.query or "").strip() and (intent.authors or []):
        intent.query = str((intent.authors or [])[0]).strip()[:500]

    from ...utils.author_query_match import normalize_author_names

    intent.authors = normalize_author_names(
        [str(x).strip() for x in (intent.authors or []) if str(x).strip()]
    )[:8]
    raw_venues = [str(x).strip() for x in (intent.venues or []) if str(x).strip()]
    intent.venues = sanitize_venue_tokens(raw_venues)[:8]
    intent.target_titles = [str(x).strip() for x in (intent.target_titles or []) if str(x).strip()][:6]
    from ..retrieval.method_acronym import is_method_acronym_token

    q_strip = (intent.query or "").strip()
    if intent.venues and is_method_acronym_token(q_strip):
        intent.keywords = [q_strip]
        intent.is_short_acronym = True
        intent.use_tavily = True
    intent.target_authors = [str(x).strip() for x in (intent.target_authors or []) if str(x).strip()][:6]
    intent.authors = _sanitize_author_list_for_query(intent.query or "", intent.authors)
    intent.max_results = max(5, min(int(intent.max_results or 10), 30))
    intent.rerank_recall_max = max(8, min(int(intent.rerank_recall_max or 24), 60))
    conf = str(intent.confidence_level or "").strip().lower()
    intent.confidence_level = conf if conf in ("high", "medium", "low") else "medium"
    strat = str(intent.search_strategy or "").strip().lower()
    intent.search_strategy = (
        strat
        if strat in ("keyword_matching", "semantic_search", "hybrid", "targeted_lookup")
        else "hybrid"
    )
    if profile == "novelty":
        intent.sort = "date"
    elif intent.sort not in ("relevance", "date"):
        intent.sort = "relevance"

    if bool(intent.wants_recent) and intent.sort != "date":
        intent.sort = "date"

    axl = [str(x).strip() for x in (intent.arxiv_id_list or []) if str(x).strip()][:8]
    intent.arxiv_id_list = axl

    if intent.year_from is not None and (intent.year_from < 1900 or intent.year_from > 2100):
        intent.year_from = None
    if intent.year_to is not None and (intent.year_to < 1900 or intent.year_to > 2100):
        intent.year_to = None
    _ensure_intent_year_window_ordered(intent)
    return intent

def _ensure_intent_year_window_ordered(intent: SearchIntent) -> None:
    yf = getattr(intent, "year_from", None)
    yt = getattr(intent, "year_to", None)
    if isinstance(yf, int) and isinstance(yt, int) and yf > yt:
        intent.year_from, intent.year_to = yt, yf

def infer_target_edition_year_for_recent(*, is_latest: bool = True, settings: Any | None = None) -> int:
    """Prompt hint for the latest likely conference edition year."""
    _ = is_latest, settings
    y_now = int(datetime.now().year)
    return max(1990, y_now - 1)


def format_intent_llm_prompt(
    template: str,
    user_text: str,
    profile: str,
    *,
    correction_hint: str | None = None,
) -> str:
    now = datetime.now()
    edition_year = infer_target_edition_year_for_recent(is_latest=True)
    base = template.format(
        user_text=(user_text or "").strip()[:3500],
        profile=profile,
        current_date_iso=now.strftime("%Y-%m-%d"),
        current_year=now.year,
        suggested_edition_year=edition_year,
    )
    hint = (correction_hint or "").strip()
    if not hint:
        return base
    return (
        f"{base}\n\n"
        "## 修正要求（上次输出无效，请重新生成完整 JSON）\n"
        f"{hint}\n\n"
        "只输出一个 JSON 对象，不要 markdown 代码块或解释文字。"
    )


def build_intent_retry_correction_hint(
    exc: BaseException,
    *,
    user_message: str,
    last_output: str | None = None,
) -> str:
    em = str(exc or "").strip()
    em_l = em.lower()
    msg = (user_message or "").strip()[:400]
    parts: list[str] = [f"用户查询：「{msg}」。"]
    if "empty_query" in em_l or "intent_parse_empty" in em_l:
        parts.append(
            "上次 JSON 缺少有效检索锚点：query、venues、authors、target_titles、arxiv_id_list 至少应有一项非空；"
            "若用户只提会议/最新，请把会议写入 venues，并按上文日期规则填写 year_from/year_to。"
        )
    elif "json" in em_l or "未返回有效" in em:
        parts.append("上次未返回可解析的 JSON 对象。")
    else:
        parts.append(f"上次解析失败：{em[:400]}。")
    out_snip = (last_output or "").strip()
    if out_snip:
        parts.append(f"上次模型输出片段（供对照，勿照抄错误）：{out_snip[:600]}")
    return " ".join(parts)


def apply_llm_intent_hygiene(intent: SearchIntent, _raw_user_text: str | None = None) -> None:
    """Clean parsed fields without changing venue/year semantics."""
    _ = _raw_user_text
    if intent is None:
        return
    intent.venues = sanitize_venue_tokens(list(intent.venues or []))[:8]
    intent.keywords = dedupe_strings_preserve_order(list(intent.keywords or []), max_n=16)
    intent.arxiv_categories = sanitize_arxiv_categories(list(intent.arxiv_categories or []))
    intent.arxiv_id_list = sanitize_arxiv_id_list(list(intent.arxiv_id_list or []))


__all__ = [
    "extract_json_object",
    "search_intent_from_dict",
    "finalize_llm_intent",
    "apply_llm_intent_hygiene",
    "build_intent_retry_correction_hint",
    "format_intent_llm_prompt",
    "infer_target_edition_year_for_recent",
    "_ensure_intent_year_window_ordered",
]
