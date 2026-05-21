
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ..llm.agent_runtime import run_json_task
from ..llm.llm_service import get_llm
from ...utils.common import exec_sql

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        """CREATE TABLE IF NOT EXISTS negative_pref_memory (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at INTEGER NOT NULL,
          expires_at INTEGER NOT NULL,
          identity_key TEXT,
          title TEXT,
          payload_json TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_negpref_exp ON negative_pref_memory(expires_at)",
        """CREATE TABLE IF NOT EXISTS negative_pref_longterm (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL,
          value TEXT NOT NULL,
          weight REAL DEFAULT -0.2,
          created_at INTEGER NOT NULL,
          last_triggered_at INTEGER NOT NULL,
          trigger_count INTEGER DEFAULT 0,
          disabled INTEGER DEFAULT 0,
          evidence_json TEXT
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_negpref_longterm_kind_val ON negative_pref_longterm(kind, value)",
        "CREATE INDEX IF NOT EXISTS idx_negpref_longterm_disabled ON negative_pref_longterm(disabled, last_triggered_at)",
    )

def _extract_pref_dims(payload: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "topic": [str(x).strip().lower() for x in (payload.get("topics_to_downrank") or []) if str(x).strip()],
        "subdomain": [str(x).strip().lower() for x in (payload.get("subdomains_to_downrank") or []) if str(x).strip()],
        "style": [str(x).strip().lower() for x in (payload.get("styles_to_downrank") or []) if str(x).strip()],
        "venue": [str(x).strip().lower() for x in (payload.get("venues_to_downrank") or []) if str(x).strip()],
        "source": [str(x).strip().lower() for x in (payload.get("sources_to_downrank") or []) if str(x).strip()],
    }

def maybe_promote_longterm_from_recent_skips(
    db_path: str,
    *,
    window_days: int = 30,
    min_count: int = 5,
    min_confidence: float = 0.6,
    max_new_rules: int = 2,
) -> list[tuple[str, str]]:
    ensure_tables(db_path)
    now = int(time.time())
    win = max(7, min(90, int(window_days))) * 86400
    since = now - win

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT created_at, title, payload_json
            FROM negative_pref_memory
            WHERE created_at >= ? ORDER BY created_at DESC LIMIT 1000""",
            (since,),
        )
        counts: dict[tuple[str, str], int] = {}
        evidences: dict[tuple[str, str], dict[str, Any]] = {}

        for created_at, title, payload_json in cur.fetchall():
            try:
                payload = json.loads(payload_json or "{}")
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            conf = float(payload.get("confidence") or 0.0)
            if conf < float(min_confidence):
                continue
            dims = _extract_pref_dims(payload)
            for kind, vals in dims.items():
                for v in vals[:8]:
                    vv = (v or "").strip().lower()[:64]
                    if len(vv) < 2:
                        continue
                    key = (kind, vv)
                    counts[key] = counts.get(key, 0) + 1
                    if key not in evidences:
                        evidences[key] = {
                            "window_days": int(window_days),
                            "min_confidence": float(min_confidence),
                            "example_titles": [],
                            "last_seen_at": int(created_at or 0),
                        }
                    if title and len(evidences[key]["example_titles"]) < 3:
                        evidences[key]["example_titles"].append(str(title)[:160])
                    evidences[key]["last_seen_at"] = max(int(evidences[key]["last_seen_at"]), int(created_at or 0))

        promoted: list[tuple[str, str]] = []
        items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        for (kind, value), cnt in items:
            if cnt < int(min_count):
                break
            if len(promoted) >= int(max_new_rules):
                break
            weight = -0.2
            ev = evidences.get((kind, value), {})
            ev["count"] = int(cnt)
            cur.execute(
                """INSERT INTO negative_pref_longterm(kind, value, weight, created_at, last_triggered_at, trigger_count, disabled, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(kind, value) DO UPDATE SET
                  last_triggered_at = excluded.last_triggered_at,
                  trigger_count = COALESCE(negative_pref_longterm.trigger_count, 0) + 1,
                  evidence_json = excluded.evidence_json""",
                (kind, value, float(weight), now, int(ev.get("last_seen_at") or now), 1, json.dumps(ev, ensure_ascii=False)),
            )
            promoted.append((kind, value))
        conn.commit()
        return promoted
    finally:
        conn.close()

def record_skip_negative_pref(
    db_path: str,
    *,
    identity_key: str,
    title: str,
    abstract: str | None = None,
    journal: str | None = None,
    source: str | None = None,
    keywords: list[str | None] = None,
    category: str | None = None,
    ttl_days: int = 14,
) -> bool:
    ensure_tables(db_path)
    ttl = max(1, min(60, int(ttl_days or 14)))
    now = int(time.time())
    exp = now + ttl * 86400

    system_prompt = (
        "你是推荐系统的反馈分析器。用户点了「不感兴趣(skip)」。"
        "请把这一次 skip 总结成短期负偏好，用于未来 7-14 天轻微降权（不是硬过滤）。"
        "输出必须是 JSON，字段如下：\n"
        "- topics_to_downrank: string[]（主题关键词，2-8 个）\n"
        "- subdomains_to_downrank: string[]（子领域标签，0-5 个）\n"
        "- venues_to_downrank: string[]（会议/期刊关键词，0-3 个）\n"
        "- sources_to_downrank: string[]（arxiv/openalex/dblp，0-2 个）\n"
        "- styles_to_downrank: string[]（survey/tutorial/benchmark/...，0-3 个）\n"
        "- confidence: number（0-1）\n"
        "规则：宁可少写，避免误伤；不要输出解释文字，只输出 JSON。"
    )
    prompt = json.dumps({
        "title": title, "abstract": (abstract or "")[:1200],
        "journal": journal or "", "source": source or "",
        "keywords": (keywords or [])[:20], "category": category or "",
    }, ensure_ascii=False)
    payload = run_json_task(
        task_name="negative_pref_summarizer", agent_name="neg_pref_summarizer",
        llm=get_llm(), system_prompt=system_prompt, user_prompt=prompt,
        timeout_sec=10.0, retries=1, default={},
    )
    payload_json = json.dumps(payload or {}, ensure_ascii=False)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO negative_pref_memory(created_at, expires_at, identity_key, title, payload_json)
            VALUES (?, ?, ?, ?, ?)""",
            (now, exp, (identity_key or "")[:160], (title or "")[:400], payload_json),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
