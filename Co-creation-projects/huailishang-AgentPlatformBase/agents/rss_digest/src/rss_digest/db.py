from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass
class JsonDB:
    db_path: Path
    payload: dict[str, Any]

    def save(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.write_text(
            json.dumps(self.payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_article() -> dict[str, Any]:
    return {
        "id": 0,
        "source_name": "",
        "category": "",
        "title": "",
        "link": "",
        "published_at": "",
        "feed_summary": "",
        "raw_html_path": None,
        "extracted_text_path": None,
        "translated_text_path": None,
        "summary_cn": None,
        "translation_cn": None,
        "article_type": None,
        "article_score": None,
        "worth_reading": None,
        "one_line": None,
        "summary_data": None,
        "status": "discovered",
    }


def _default_payload() -> dict[str, Any]:
    return {
        "next_id": 1,
        "articles": [],
        "digest_history": {},
    }


def connect(db_path: Path) -> JsonDB:
    if db_path.exists():
        try:
            payload = json.loads(db_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = _default_payload()
    else:
        payload = _default_payload()
    return JsonDB(db_path=db_path, payload=payload)


def init_db(conn: JsonDB) -> None:
    conn.payload.setdefault("next_id", 1)
    conn.payload.setdefault("articles", [])
    conn.payload.setdefault("digest_history", {})

    changed = False
    for article in conn.payload["articles"]:
        defaults = _default_article()
        for key, value in defaults.items():
            if key not in article:
                article[key] = value
                changed = True

    if changed or not conn.db_path.exists():
        conn.save()


def _find_article(conn: JsonDB, article_id: int) -> dict[str, Any] | None:
    for article in conn.payload["articles"]:
        if article["id"] == article_id:
            return article
    return None


def upsert_article(
    conn: JsonDB,
    *,
    source_name: str,
    category: str,
    title: str,
    link: str,
    published_at: str,
    feed_summary: str,
) -> bool:
    for article in conn.payload["articles"]:
        if article["link"] == link:
            return False

    article = _default_article()
    article.update(
        {
            "id": conn.payload["next_id"],
            "source_name": source_name,
            "category": category,
            "title": title,
            "link": link,
            "published_at": published_at,
            "feed_summary": feed_summary,
            "status": "discovered",
        }
    )
    conn.payload["articles"].append(article)
    conn.payload["next_id"] += 1
    conn.save()
    return True


def get_articles_by_status(conn: JsonDB, status: str, limit: int) -> list[dict[str, Any]]:
    rows = [article for article in conn.payload["articles"] if article["status"] == status]
    rows.sort(key=lambda item: (item.get("published_at") or "", item["id"]), reverse=True)
    return rows[:limit]


def update_article_paths(
    conn: JsonDB,
    article_id: int,
    *,
    raw_html_path: str | None = None,
    extracted_text_path: str | None = None,
    translated_text_path: str | None = None,
    status: str | None = None,
) -> None:
    article = _find_article(conn, article_id)
    if article is None:
        return

    if raw_html_path is not None:
        article["raw_html_path"] = raw_html_path
    if extracted_text_path is not None:
        article["extracted_text_path"] = extracted_text_path
    if translated_text_path is not None:
        article["translated_text_path"] = translated_text_path
    if status is not None:
        article["status"] = status
    conn.save()


def update_article_texts(
    conn: JsonDB,
    article_id: int,
    *,
    summary_cn: str | None = None,
    translation_cn: str | None = None,
    translated_text_path: str | None = None,
    article_type: str | None = None,
    article_score: int | None = None,
    worth_reading: str | None = None,
    one_line: str | None = None,
    summary_data: dict[str, Any] | None = None,
    status: str | None = None,
) -> None:
    article = _find_article(conn, article_id)
    if article is None:
        return

    if summary_cn is not None:
        article["summary_cn"] = summary_cn
    if translation_cn is not None:
        article["translation_cn"] = translation_cn
    if translated_text_path is not None:
        article["translated_text_path"] = translated_text_path
    if article_type is not None:
        article["article_type"] = article_type
    if article_score is not None:
        article["article_score"] = article_score
    if worth_reading is not None:
        article["worth_reading"] = worth_reading
    if one_line is not None:
        article["one_line"] = one_line
    if summary_data is not None:
        article["summary_data"] = summary_data
    if status is not None:
        article["status"] = status
    conn.save()


def get_recent_articles(conn: JsonDB, limit: int = 30) -> list[dict[str, Any]]:
    rows = [article for article in conn.payload["articles"] if article.get("summary_cn")]
    rows.sort(
        key=lambda item: (
            item.get("published_at") or "",
            item["id"],
            item.get("article_score") or 0,
        ),
        reverse=True,
    )
    return rows[:limit]


def get_undelivered_ready_articles(
    conn: JsonDB,
    digest_key: str,
    limit: int = 30,
    *,
    exclude_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    delivered_ids = set(conn.payload.get("digest_history", {}).get(digest_key, []))
    if exclude_ids:
        delivered_ids |= exclude_ids

    rows = [
        article
        for article in conn.payload["articles"]
        if article.get("summary_cn") and article.get("id") not in delivered_ids
    ]
    rows.sort(
        key=lambda item: (
            item.get("published_at") or "",
            item["id"],
            item.get("article_score") or 0,
        ),
        reverse=True,
    )
    return rows[:limit]


def mark_digest_delivered(conn: JsonDB, digest_key: str, article_ids: list[int]) -> None:
    if not article_ids:
        return

    history = conn.payload.setdefault("digest_history", {})
    delivered = set(history.get(digest_key, []))
    delivered.update(int(article_id) for article_id in article_ids)
    history[digest_key] = sorted(delivered)
    conn.save()


def bootstrap_existing_digest_delivery(
    conn: JsonDB,
    digest_key: str,
    *,
    exclude_ids: set[int] | None = None,
) -> int:
    history = conn.payload.setdefault("digest_history", {})
    if digest_key in history:
        return 0

    exclude_ids = exclude_ids or set()
    article_ids = [
        int(article["id"])
        for article in conn.payload["articles"]
        if article.get("summary_cn") and article.get("id") not in exclude_ids
    ]
    history[digest_key] = sorted(set(article_ids))
    conn.save()
    return len(article_ids)
