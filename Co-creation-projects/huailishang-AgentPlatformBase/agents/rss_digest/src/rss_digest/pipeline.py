from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
from time import perf_counter
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from rss_digest.config import build_config, load_sources
from rss_digest.db import (
    bootstrap_existing_digest_delivery,
    connect,
    get_articles_by_status,
    get_undelivered_ready_articles,
    init_db,
    mark_digest_delivered,
    update_article_paths,
    update_article_texts,
    upsert_article,
)
from rss_digest.digest import render_html
from rss_digest.extractor import fetch_and_extract, html_to_text, write_text
from rss_digest.feeds import fetch_feed_entries
from rss_digest.llm import (
    LLMClient,
    SUMMARY_SYSTEM_PROMPT,
    TRANSLATION_SYSTEM_PROMPT,
    build_summary_prompt,
    build_translation_prompt,
    parse_json_response,
)


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "article"


def _article_stem(article_id: int, title: str) -> str:
    slug = _slugify(title)[:64]
    return f"{article_id:06d}_{slug}"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def _string_list(value, limit: int = 5) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value[:limit]:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            output.append(text)
    return output


def _normalize_summary_payload(payload: dict) -> dict:
    score = payload.get("score", 0)
    try:
        score = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        score = 0

    return {
        "article_type": str(payload.get("article_type", "未分类")).strip() or "未分类",
        "score": score,
        "worth_reading": str(payload.get("worth_reading", "选择性阅读")).strip() or "选择性阅读",
        "one_line": str(payload.get("one_line", "暂无一句话结论")).strip() or "暂无一句话结论",
        "summary": str(payload.get("summary", "暂无摘要")).strip() or "暂无摘要",
        "key_points": _string_list(payload.get("key_points"), limit=4),
        "why_it_matters": str(payload.get("why_it_matters", "")).strip(),
        "engineering_takeaway": str(payload.get("engineering_takeaway", "")).strip(),
        "business_signal": str(payload.get("business_signal", "")).strip(),
        "limitations": str(payload.get("limitations", "")).strip(),
        "keywords": _string_list(payload.get("keywords"), limit=5),
        "recommended_action": str(payload.get("recommended_action", "")).strip(),
    }


def discover_articles(conn, cfg) -> int:
    discovered = 0
    sources = load_sources(cfg.sources_file)[: cfg.rss_source_limit]
    print(
        f"[1/4] Fetching feeds from {len(sources)} sources..."
        f" concurrency={cfg.rss_fetch_concurrency}"
        f" timeout={cfg.request_timeout_seconds}s"
    )

    def fetch_source(source: dict[str, str]) -> tuple[dict[str, str], list[Any]]:
        entries = fetch_feed_entries(source["feed_url"], cfg.request_timeout_seconds)
        return source, entries[: cfg.rss_entries_per_source]

    fetched_entries = 0
    with ThreadPoolExecutor(max_workers=cfg.rss_fetch_concurrency) as executor:
        futures = [executor.submit(fetch_source, source) for source in sources]
        for future in as_completed(futures):
            source, entries = future.result()
            fetched_entries += len(entries)
            for entry in entries:
                added = upsert_article(
                    conn,
                    source_name=source["name"],
                    category=source["category"],
                    title=entry.title,
                    link=entry.link,
                    published_at=entry.published_at,
                    feed_summary=entry.summary[:2000],
                )
                if added:
                    discovered += 1
    print(f"[1/4] Feed fetch complete: entries={fetched_entries} | new={discovered}")
    return discovered


def _select_article_rows(conn, cfg, statuses: list[str], limit: int) -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    counts: dict[str, int] = {}
    for status in statuses:
        status_rows = get_articles_by_status(conn, status, limit)
        counts[status] = len(status_rows)
        rows.extend(status_rows)

    deduped: list[dict] = []
    seen_ids: set[int] = set()
    for row in rows:
        if row["id"] in seen_ids:
            continue
        seen_ids.add(row["id"])
        deduped.append(row)
        if len(deduped) >= limit:
            break
    return deduped, counts


def extract_articles(conn, cfg) -> int:
    deduped_rows, counts = _select_article_rows(
        conn,
        cfg,
        statuses=["discovered", "fetch_failed"],
        limit=cfg.max_articles_per_run,
    )

    print(
        f"[2/4] Extracting article bodies: {len(deduped_rows)} item(s)"
        f" | new={counts.get('discovered', 0)}"
        f" | retry_failed={counts.get('fetch_failed', 0)}"
        f" | concurrency={cfg.rss_fetch_concurrency}"
    )

    def extract_row(row: dict) -> tuple[dict, str, str]:
        html_text, article_text = fetch_and_extract(row["link"], cfg.request_timeout_seconds)
        return row, html_text, article_text

    extracted = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=cfg.rss_fetch_concurrency) as executor:
        futures = [executor.submit(extract_row, row) for row in deduped_rows]
        for future in as_completed(futures):
            row, html_text, article_text = future.result()
            if not article_text:
                article_text = html_to_text(row.get("feed_summary") or "")
                html_text = row.get("feed_summary") or ""
                if not article_text:
                    update_article_paths(conn, row["id"], status="fetch_failed")
                    failed += 1
                    continue

            stem = _article_stem(row["id"], row["title"])
            html_path = cfg.raw_dir / f"{stem}_{_short_hash(row['link'])}.html"
            text_path = cfg.extracted_dir / f"{stem}.txt"
            write_text(html_path, html_text)
            write_text(text_path, article_text)
            update_article_paths(
                conn,
                row["id"],
                raw_html_path=str(html_path),
                extracted_text_path=str(text_path),
                status="extracted",
            )
            extracted += 1
    print(f"[2/4] Article extraction complete: extracted={extracted} | failed={failed}")
    return extracted


def _rows_for_resummarize(conn, cfg) -> list[dict]:
    if not cfg.resummarize_existing:
        return []

    candidates = []
    for row in get_undelivered_ready_articles(conn, "__resummarize__", limit=max(cfg.max_articles_per_run * 3, 36)):
        if row.get("summary_data") and row.get("article_type") and row.get("article_score") is not None:
            continue
        candidates.append(row)
        if len(candidates) >= cfg.max_articles_per_run:
            break
    return candidates


def summarize_articles(conn, cfg, llm_client: LLMClient, translation_client: LLMClient) -> list[int]:
    summary_limit = min(cfg.max_articles_per_run, cfg.rss_max_summary_articles_per_run)
    extracted_rows = get_articles_by_status(conn, "extracted", summary_limit)
    retry_rows = get_articles_by_status(conn, "summary_failed", summary_limit)
    resummarize_rows = _rows_for_resummarize(conn, cfg)
    rows = extracted_rows + retry_rows + resummarize_rows

    deduped: list[dict] = []
    seen_ids: set[int] = set()
    for row in rows:
        if row["id"] in seen_ids:
            continue
        seen_ids.add(row["id"])
        deduped.append(row)
        if len(deduped) >= summary_limit:
            break

    print(
        f"[3/4] Summarizing articles: {len(deduped)} item(s)"
        f" | new={len(extracted_rows)}"
        f" | retry_failed={len(retry_rows)}"
        f" | resummarize={len(resummarize_rows)}"
        f" | batch_size={cfg.rss_ai_batch_size}"
        f" | ai_concurrency={cfg.rss_ai_max_concurrency}"
    )

    def summarize_row(row: dict) -> tuple[dict, dict | None, str | None, str | None, str | None]:
        text_path_value = row.get("extracted_text_path")
        if not text_path_value:
            return row, None, None, None, "extract_missing"

        text_path = Path(text_path_value)
        if not text_path.exists():
            return row, None, None, None, "extract_missing"

        article_text = text_path.read_text(encoding="utf-8")
        if not article_text.strip():
            return row, None, None, None, "empty_text"

        try:
            summary_payload = parse_json_response(
                llm_client.chat(
                    SUMMARY_SYSTEM_PROMPT,
                    build_summary_prompt(
                        title=row["title"],
                        source_name=row["source_name"],
                        category=row["category"],
                        article_text=article_text,
                    ),
                )
            )
            normalized = _normalize_summary_payload(summary_payload)
        except Exception as exc:
            return row, {"summary": f"摘要生成失败: {exc}"}, None, None, "summary_failed"

        translation_cn = None
        translated_path = None
        if cfg.fetch_full_translation and normalized["score"] >= 85:
            try:
                translation_payload = parse_json_response(
                    translation_client.chat(
                        TRANSLATION_SYSTEM_PROMPT,
                        build_translation_prompt(row["title"], article_text),
                    )
                )
                translation_cn = str(translation_payload.get("translation", "")).strip()
                if translation_cn:
                    translated_path_obj = cfg.translated_dir / f"{_article_stem(row['id'], row['title'])}.md"
                    write_text(translated_path_obj, translation_cn)
                    translated_path = str(translated_path_obj)
            except Exception as exc:
                translation_cn = f"全文翻译失败: {exc}"

        return row, normalized, translation_cn, translated_path, None

    completed_ids: list[int] = []
    failed_count = 0
    for batch_start in range(0, len(deduped), cfg.rss_ai_batch_size):
        batch = deduped[batch_start : batch_start + cfg.rss_ai_batch_size]
        with ThreadPoolExecutor(max_workers=cfg.rss_ai_max_concurrency) as executor:
            futures = [executor.submit(summarize_row, row) for row in batch]
            for future in as_completed(futures):
                row, normalized, translation_cn, translated_path, error_status = future.result()
                if error_status:
                    update_article_texts(
                        conn,
                        row["id"],
                        summary_cn=(normalized or {}).get("summary"),
                        status=error_status,
                    )
                    failed_count += 1
                    continue

                if not normalized:
                    update_article_texts(conn, row["id"], status="summary_failed")
                    failed_count += 1
                    continue

                update_article_texts(
                    conn,
                    row["id"],
                    summary_cn=normalized["summary"],
                    translation_cn=translation_cn,
                    translated_text_path=translated_path,
                    article_type=normalized["article_type"],
                    article_score=normalized["score"],
                    worth_reading=normalized["worth_reading"],
                    one_line=normalized["one_line"],
                    summary_data=normalized,
                    status="ready",
                )
                completed_ids.append(int(row["id"]))
    print(f"[3/4] Article summarization complete: summarized={len(completed_ids)} | failed={failed_count}")
    return completed_ids


def build_daily_digest(conn, cfg, newly_ready_ids: list[int]) -> tuple[Path, int, bool, int]:
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = cfg.digests_dir / f"digest_{today}.html"

    if output_path.exists():
        bootstrapped = bootstrap_existing_digest_delivery(
            conn,
            today,
            exclude_ids=set(newly_ready_ids),
        )
        if bootstrapped:
            print(f"[4/4] Bootstrapped delivered history for {bootstrapped} already-rendered article(s)")
    else:
        bootstrapped = 0

    recent_rows = get_undelivered_ready_articles(
        conn,
        today,
        limit=max(cfg.max_articles_per_run * 5, cfg.rss_max_digest_articles * 10, 200),
    )
    before_filter_count = len(recent_rows)
    recent_rows = [
        row
        for row in recent_rows
        if int(row.get("article_score") or 0) >= cfg.rss_relevance_threshold
    ]
    recent_rows.sort(
        key=lambda row: (
            int(row.get("article_score") or 0),
            row.get("published_at") or "",
            int(row.get("id") or 0),
        ),
        reverse=True,
    )
    recent_rows = recent_rows[: cfg.rss_max_digest_articles]
    no_new_articles = not recent_rows
    print(
        f"[4/4] Rendering digest with {len(recent_rows)} new article card(s)"
        f" | candidates={before_filter_count}"
        f" | threshold={cfg.rss_relevance_threshold}"
        f" | max_digest={cfg.rss_max_digest_articles}"
    )
    render_html(recent_rows, output_path)
    mark_digest_delivered(conn, today, [int(row["id"]) for row in recent_rows])
    return output_path, len(recent_rows), no_new_articles, bootstrapped


def run_pipeline(root_dir: Path, data_root: Path | None = None) -> dict[str, Any]:
    total_started = perf_counter()
    cfg = build_config(root_dir, data_root)
    conn = connect(cfg.db_path)
    init_db(conn)

    llm_client = LLMClient(
        model_name=cfg.model_name,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout_seconds=cfg.llm_timeout_seconds,
    )
    translation_client = LLMClient(
        model_name=cfg.translation_model_name or cfg.model_name,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout_seconds=cfg.llm_timeout_seconds,
    )

    timings: dict[str, float] = {}

    started = perf_counter()
    discovered = discover_articles(conn, cfg)
    timings["discover_seconds"] = round(perf_counter() - started, 3)

    started = perf_counter()
    extracted = extract_articles(conn, cfg)
    timings["extract_seconds"] = round(perf_counter() - started, 3)

    summarized_ids: list[int] = []
    llm_enabled = llm_client.is_enabled()
    if llm_enabled:
        started = perf_counter()
        summarized_ids = summarize_articles(conn, cfg, llm_client, translation_client)
        timings["summarize_seconds"] = round(perf_counter() - started, 3)
    else:
        print("[3/4] Summarizing articles skipped: LLM client is not configured.")
        timings["summarize_seconds"] = 0.0

    started = perf_counter()
    digest_path, digest_article_count, no_new_articles, bootstrapped_delivered = build_daily_digest(
        conn,
        cfg,
        summarized_ids,
    )
    timings["digest_seconds"] = round(perf_counter() - started, 3)
    timings["total_seconds"] = round(perf_counter() - total_started, 3)

    print(
        "[rss_digest] Pipeline summary: "
        f"discovered={discovered} | extracted={extracted} | summarized={len(summarized_ids)} | "
        f"digest_articles={digest_article_count} | digest={digest_path} | timings={timings}"
    )

    return {
        "discovered": discovered,
        "extracted": extracted,
        "summarized": len(summarized_ids),
        "summarized_ids": summarized_ids,
        "digest_article_count": digest_article_count,
        "no_new_articles": no_new_articles,
        "bootstrapped_delivered": bootstrapped_delivered,
        "llm_enabled": llm_enabled,
        "digest_path": str(digest_path),
        "max_articles_per_run": cfg.max_articles_per_run,
        "rss_fetch_concurrency": cfg.rss_fetch_concurrency,
        "rss_source_limit": cfg.rss_source_limit,
        "rss_entries_per_source": cfg.rss_entries_per_source,
        "rss_ai_batch_size": cfg.rss_ai_batch_size,
        "rss_ai_max_concurrency": cfg.rss_ai_max_concurrency,
        "rss_relevance_threshold": cfg.rss_relevance_threshold,
        "rss_max_summary_articles_per_run": cfg.rss_max_summary_articles_per_run,
        "rss_max_digest_articles": cfg.rss_max_digest_articles,
        "timings": timings,
    }
