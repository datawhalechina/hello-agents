"""Search dispatch helpers."""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from config import Configuration
from search_tool import SearchTool
from utils import (
    deduplicate_and_format_sources,
    format_sources,
    get_config_value,
)

logger = logging.getLogger(__name__)

MAX_TOKENS_PER_SOURCE = 800
_GLOBAL_SEARCH_TOOL = SearchTool(backend="hybrid")

JOB_SEARCH_MIN_SCORE = 3
JOB_SEARCH_POSITIVE_TERMS = (
    "招聘",
    "实习",
    "实习生",
    "校招",
    "岗位",
    "职位",
    "jd",
    "职位描述",
    "岗位职责",
    "任职要求",
    "投递",
)
JOB_SEARCH_NEGATIVE_TERMS = (
    "面经",
    "面试",
    "教程",
    "学习",
    "学习资源",
    "开源项目",
    "面试题",
    "博客",
    "blog",
    "提示词",
    "prompt",
    "案例",
    "通关计划",
    "JavaGuide",
    "CSDN",
    "掘金",
    "SegmentFault",
    "YouTube",
)
JOB_SEARCH_INTERVIEW_TERMS = (
    "面经",
    "面试",
    "面试题",
    "通关计划",
)
JOB_SEARCH_TUTORIAL_TERMS = (
    "教程",
    "学习",
    "学习资源",
    "博客",
    "blog",
    "提示词",
    "prompt",
    "案例",
    "开源项目",
    "JavaGuide",
    "CSDN",
    "掘金",
    "SegmentFault",
    "YouTube",
)
JOB_SEARCH_POSITIVE_URLS = (
    "zhipin.com/job_detail",
    "shixiseng.com/intern",
    "yingjiesheng.com",
    "jobs.bytedance.com",
    "campus.alibaba.com",
    "campus.tencent.com",
    "campus.meituan.com",
    "join.qq.com",
    "talent.baidu.com",
    "nowcoder.com/jobs",
    "liepin.com",
    "zhaopin.com",
    "51job.com",
    "lagou.com",
    "shushuqiuzhi.com/position",
    "offer.gfjianli.com/position",
)
JOB_SEARCH_GENERIC_JOB_URL_PARTS = (
    "/job",
    "/jobs",
    "/career",
    "/careers",
    "/campus",
    "/recruit",
    "/position",
    "campus.",
    "career.",
    "careers.",
    "jobs.",
    "join.",
    "talent.",
)
JOB_SEARCH_REQUIRED_TERMS = (
    "招聘",
    "实习",
    "实习生",
    "校招",
    "岗位详情",
    "职位描述",
    "任职要求",
    "投递",
    "jd",
)


def dispatch_search(
    query: str,
    config: Configuration,
    loop_count: int,
) -> Tuple[dict[str, Any] | None, list[str], Optional[str], str]:
    """Execute configured search backend and normalise response payload."""

    search_api = get_config_value(config.search_api)

    try:
        raw_response = _GLOBAL_SEARCH_TOOL.run(
            {
                "input": query,
                "backend": search_api,
                "mode": "structured",
                "fetch_full_page": config.fetch_full_page,
                "max_results": 5,
                "max_tokens_per_source": MAX_TOKENS_PER_SOURCE,
                "loop_count": loop_count,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Search backend %s failed: %s", search_api, exc)
        raise

    if isinstance(raw_response, str):
        notices = [raw_response]
        logger.warning("Search backend %s returned text notice: %s", search_api, raw_response)
        payload: dict[str, Any] = {
            "results": [],
            "backend": search_api,
            "answer": None,
            "notices": notices,
        }
    else:
        payload = raw_response
        notices = list(payload.get("notices") or [])

    backend_label = str(payload.get("backend") or search_api)
    answer_text = payload.get("answer")
    results = payload.get("results", [])

    if notices:
        for notice in notices:
            logger.info("Search notice (%s): %s", backend_label, notice)

    logger.info(
        "Search backend=%s resolved_backend=%s answer=%s results=%s",
        search_api,
        backend_label,
        bool(answer_text),
        len(results),
    )

    return payload, notices, answer_text, backend_label


def prepare_research_context(
    search_result: dict[str, Any] | None,
    answer_text: Optional[str],
    config: Configuration,
) -> tuple[str, str]:
    """Build structured context and source summary for downstream agents."""

    sources_summary = format_sources(search_result)
    context = deduplicate_and_format_sources(
        search_result or {"results": []},
        max_tokens_per_source=MAX_TOKENS_PER_SOURCE,
        fetch_full_page=config.fetch_full_page,
    )

    if answer_text:
        context = f"AI直接答案：\n{answer_text}\n\n{context}"

    return sources_summary, context


def build_strict_job_query(query: str) -> str:
    """Make a job-search query prefer JD and application pages over interview posts."""

    additions = (
        "实习生招聘 JD 岗位详情 职位描述 任职要求 投递入口 "
        "校招官网 招聘官网 BOSS直聘 实习僧 牛客招聘 应届生 "
        "-面经 -面试 -教程 -博客 -学习资源 -开源项目 -提示词"
    )
    return f"{query} {additions}".strip()


def build_platform_job_query(query: str) -> str:
    """Make a second-pass query strongly target job boards and career sites."""

    additions = (
        "BOSS直聘 实习僧 牛客招聘 应届生 校招官网 招聘官网 "
        "岗位详情 JD 投递入口 实习生招聘 职位描述 任职要求 "
        "site:zhipin.com/job_detail site:shixiseng.com/intern site:jobs.bytedance.com "
        "-面经 -面试 -教程 -博客 -学习资源 -开源项目 -提示词"
    )
    return f"{query} {additions}".strip()


def prioritize_job_search_results(search_result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Prefer internship JD/application pages and drop obvious interview/tutorial noise."""

    if not search_result:
        return search_result

    results = search_result.get("results")
    if not isinstance(results, list):
        return search_result

    scored_results = [
        (score, item)
        for item in results
        if isinstance(item, dict)
        for score in [_score_job_result(item)]
        if score >= JOB_SEARCH_MIN_SCORE and is_reliable_job_source(item)
    ]

    if not scored_results:
        payload = dict(search_result)
        payload["results"] = []
        return payload

    payload = dict(search_result)
    payload["results"] = [item for _, item in sorted(scored_results, key=lambda pair: pair[0], reverse=True)]
    return payload


def merge_search_results(
    first: dict[str, Any] | None,
    second: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge search results while preserving unique URLs."""

    if not first:
        return second
    if not second:
        return first

    merged = dict(first)
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    for payload in (first, second):
        for item in payload.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            results.append(item)

    merged["results"] = results
    merged["notices"] = list(first.get("notices") or []) + list(second.get("notices") or [])
    return merged


def is_reliable_job_source(item: dict[str, Any]) -> bool:
    """Return True for sources likely to be real job/JD/application pages."""

    return classify_job_source(item) == "reliable"


def classify_job_source(item: dict[str, Any]) -> str:
    """Classify a search result as reliable or return the main rejection reason."""

    text = _job_result_text(item)
    text_lower = text.lower()
    url_lower = str(item.get("url") or "").lower()

    if not text.strip():
        return "empty_result"

    has_trusted_job_url = any(part in url_lower for part in JOB_SEARCH_POSITIVE_URLS)
    has_generic_job_url = any(part in url_lower for part in JOB_SEARCH_GENERIC_JOB_URL_PARTS)
    has_required_term = any(term.lower() in text_lower for term in JOB_SEARCH_REQUIRED_TERMS)

    if has_trusted_job_url:
        return "reliable"

    if any(term.lower() in text_lower for term in JOB_SEARCH_INTERVIEW_TERMS):
        return "interview_noise"

    if any(term.lower() in text_lower for term in JOB_SEARCH_TUTORIAL_TERMS):
        return "tutorial_or_blog"

    if has_generic_job_url and has_required_term:
        return "reliable"

    if not has_generic_job_url:
        return "not_job_url"

    return "missing_jd_terms"


def build_search_diagnostics(
    *,
    task_id: int,
    task_title: str,
    backend: str,
    query: str,
    final_query: str,
    retry_query: str | None,
    raw_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact diagnostic payload for job search quality."""

    reject_reasons: dict[str, int] = {}
    rejected_samples: list[dict[str, str]] = []
    reliable_count = 0

    for item in raw_results:
        reason = classify_job_source(item)
        if reason == "reliable":
            reliable_count += 1
            continue

        reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
        if len(rejected_samples) < 5:
            rejected_samples.append(
                {
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("url") or ""),
                    "reason": reason,
                }
            )

    raw_count = len(raw_results)
    filtered_count = max(0, raw_count - reliable_count)
    return {
        "task_id": task_id,
        "task_title": task_title,
        "backend": backend,
        "query": query,
        "final_query": final_query,
        "retry_query": retry_query,
        "counts": {
            "raw": raw_count,
            "reliable": reliable_count,
            "filtered": filtered_count,
        },
        "reject_reasons": reject_reasons,
        "rejected_samples": rejected_samples,
        "suggestion": _diagnostic_suggestion(
            raw_count=raw_count,
            reliable_count=reliable_count,
            reject_reasons=reject_reasons,
        ),
    }


def _score_job_result(item: dict[str, Any]) -> int:
    text = _job_result_text(item)
    text_lower = text.lower()
    url_lower = str(item.get("url") or "").lower()

    score = 0
    for term in JOB_SEARCH_POSITIVE_TERMS:
        if term.lower() in text_lower:
            score += 2
    for url_part in JOB_SEARCH_POSITIVE_URLS:
        if url_part in url_lower:
            score += 6
    for term in JOB_SEARCH_NEGATIVE_TERMS:
        if term.lower() in text_lower:
            score -= 5

    return score


def _diagnostic_suggestion(
    *,
    raw_count: int,
    reliable_count: int,
    reject_reasons: dict[str, int],
) -> str:
    if raw_count == 0:
        return "当前搜索没有返回结果，可切换搜索引擎，或补充岗位方向、城市、公司类型。"

    if reliable_count > 0:
        return "已找到可靠岗位/JD来源，请点开来源核验招聘状态、城市和投递入口。"

    tutorial_count = reject_reasons.get("tutorial_or_blog", 0)
    interview_count = reject_reasons.get("interview_noise", 0)

    if tutorial_count > 0 and tutorial_count >= interview_count:
        return "当前结果多为教程、博客或学习资源，也可能误命中 JD 中的经验词；建议补充公司/城市/岗位关键词，或切换 Tavily 后重试。"

    if interview_count:
        return "当前结果偏面经或面试资料，建议加入“岗位详情、投递入口、招聘官网”等关键词后重试。"

    return "未发现可靠岗位/JD链接，建议切换搜索引擎，或使用 BOSS直聘、实习僧、校招官网等平台关键词。"


def _job_result_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "url", "content", "raw_content", "snippet")
    )
