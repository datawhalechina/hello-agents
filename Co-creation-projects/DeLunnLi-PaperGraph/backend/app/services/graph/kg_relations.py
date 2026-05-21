
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from typing import Any

from ...utils.common import suppress_exceptions

from ..reader.paper_reader_context import extract_pdf_text_full_cached, extract_pdf_text_full, _cache_set
from ...utils import normalize_arxiv_id as _norm_arxiv_id

logger = logging.getLogger(__name__)

_kg_infer_lock = threading.Lock()

_kg_recent_fingerprints: dict[str, float] = {}
_kg_fingerprints_lock = threading.Lock()
_KG_DEDUP_WINDOW_SEC = 180.0

_kg_metrics: dict[str, int] = {
    "build_ok": 0,
    "build_skip_no_candidates": 0,
    "build_skip_dedup": 0,
    "relations_upserted": 0,
}
_kg_metrics_lock = threading.Lock()

def get_kg_metrics() -> dict[str, int]:
    with _kg_metrics_lock:
        return dict(_kg_metrics)

def _prune_recent_fingerprints(now: float) -> None:
    cutoff = now - _KG_DEDUP_WINDOW_SEC * 2
    with _kg_fingerprints_lock:
        dead = [k for k, t in _kg_recent_fingerprints.items() if t < cutoff]
        for k in dead:
            _kg_recent_fingerprints.pop(k, None)

from ...utils.common import exec_sql

def ensure_tables(db_path: str) -> None:
    exec_sql(db_path,
        """CREATE TABLE IF NOT EXISTS paper_relations (
          source_paper_id INTEGER NOT NULL,
          target_paper_id INTEGER NOT NULL,
          relation TEXT NOT NULL,
          score REAL DEFAULT 0.0,
          evidence TEXT,
          created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL,
          PRIMARY KEY (source_paper_id, target_paper_id, relation)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_paper_relations_source ON paper_relations(source_paper_id)",
        "CREATE INDEX IF NOT EXISTS idx_paper_relations_target ON paper_relations(target_paper_id)",
    )

@suppress_exceptions(default_return=[])
def _loads_json_list(x: str | None) -> list[Any]:
    r = json.loads(x or "[]")
    return r if isinstance(r, list) else []

def _row_to_paper_meta(row: sqlite3.Row) -> dict[str, Any]:
    keys = row.keys()

    def _col(name: str) -> Any:
        return row[name] if name in keys else None

    return {
        "id": row["id"],
        "title": row["title"],
        "abstract": row["abstract"],
        "keywords": _loads_json_list(_col("keywords")),
        "tags": _loads_json_list(_col("tags")),
        "journal": row["journal"],
        "venue_type": row["venue_type"] if "venue_type" in keys else None,
        "year": row["year"],
        "category": row["category"],
        "local_pdf_path": _col("local_pdf_path"),
        "doi": (_col("doi") or None),
        "arxiv_id": (_col("arxiv_id") or None),
        "references": _loads_json_list(_col("references")),
    }

def _pdf_abspath_from_row(db_path: str, local_pdf_path: str | None) -> str | None:
    import os

    if not local_pdf_path or not str(local_pdf_path).strip():
        return None
    data_root = os.path.dirname(os.path.abspath(db_path))
    abspath = os.path.normpath(os.path.join(data_root, str(local_pdf_path).strip()))
    if os.path.isfile(abspath):
        return abspath
    return None

def _extract_related_work_excerpt(text: str, max_chars: int = 1600) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    patterns = [
        r"(?i)\brelated\s+work\b",
        r"(?i)\brelated\s+works\b",
        r"相关工作",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            return t[m.start() : m.start() + max_chars].strip()
    return t[: max_chars // 2].strip()

_TOKEN_RE = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)

_LEX_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "by",
    "we", "our", "is", "are", "be", "this", "that", "from", "as", "at", "it",
})

def _lexical_token_set(meta: dict[str, Any]) -> set[str]:
    parts = [
        str(meta.get("title") or ""),
        str(meta.get("abstract") or ""),
        *(str(k) for k in meta.get("keywords") or []),
        *(str(t) for t in meta.get("tags") or []),
    ]
    text = " ".join(parts).lower()
    text = _TOKEN_RE.sub(" ", text)
    return {s for s in text.split() if len(s) >= 2 and s not in _LEX_STOP}

def _reference_signatures(refs: list[Any]) -> set[str]:
    sigs: set[str] = set()
    for r in refs or []:
        s = str(r).strip().lower()
        if not s:
            continue
        sigs.add(s)
        m = re.search(r"(10\.\d{4,9}/[^\s,;\"'<>]+)", s)
        if m:
            sigs.add(m.group(1).rstrip(").,]}"))
        m = re.search(r"arxiv[:/\s]*(\d{4}\.\d{4,5})(?:v\d+)?", s)
        if m:
            sigs.add(_norm_arxiv_id(m.group(1)) or m.group(1))
    return sigs

def _ref_overlap_bonus(new_sigs: set[str], cand: dict[str, Any]) -> float:
    if not new_sigs:
        return 0.0
    doi = (cand.get("doi") or "").strip().lower()
    if doi and doi in new_sigs:
        return 1.0
    ax = _norm_arxiv_id(cand.get("arxiv_id"))
    if ax and ax in new_sigs:
        return 1.0
    if doi:
        for sig in new_sigs:
            if len(sig) > 8 and sig in doi:
                return 0.85
    return 0.0

def fetch_new_and_candidates(
    db_path: str,
    new_paper_id: int,
    k: int = 32,
    *,
    sql_limit: int = 22,
    lexical_pool: int = 480,
) -> tuple[dict[str, Any | None], list[dict[str, Any]]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM papers WHERE id=?", (int(new_paper_id),))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None, []
    new_meta = _row_to_paper_meta(row)

    cat = (new_meta.get("category") or "").strip()
    year = new_meta.get("year")
    params: list[Any] = []
    where = ["id != ?"]
    params.append(int(new_paper_id))

    if cat:
        where.append("(category = ? OR category LIKE ?)")
        params.extend([cat, f"{cat.split('/')[0]}%"])

    if year:
        try:
            y = int(year)
            where.append("(year IS NULL OR year >= ?)")
            params.append(max(1900, y - 8))
        except Exception:
            pass

    wsql = " AND ".join(where)
    cur.execute(
        f"SELECT * FROM papers WHERE {wsql} ORDER BY created_at DESC LIMIT ?",
        (*params, int(sql_limit)),
    )
    sql_metas = [_row_to_paper_meta(r) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT * FROM papers
        WHERE id != ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (int(new_paper_id), int(lexical_pool)),
    )
    pool_rows = cur.fetchall()
    conn.close()

    new_lex = _lexical_token_set(new_meta)
    new_ref_sigs = _reference_signatures(new_meta.get("references") or [])

    scored: list[tuple[float, dict[str, Any]]] = []
    for r in pool_rows:
        meta = _row_to_paper_meta(r)
        cand_tokens = _lexical_token_set(meta)
        j = len(new_lex & cand_tokens) / max(1, len(new_lex | cand_tokens))
        ro = _ref_overlap_bonus(new_ref_sigs, meta)
        comb = j + ro * 0.45
        scored.append((comb, meta))

    scored.sort(key=lambda x: -x[0])

    seen: set[int] = set()
    out: list[dict[str, Any]] = []

    for m in sql_metas:
        pid = int(m["id"])
        if pid not in seen:
            seen.add(pid)
            out.append(m)

    min_lex = 0.055
    for comb, m in scored:
        if len(out) >= int(k):
            break
        pid = int(m["id"])
        if pid in seen:
            continue
        ro = _ref_overlap_bonus(new_ref_sigs, m)
        if comb < min_lex and ro <= 0:
            continue
        seen.add(pid)
        out.append(m)

    return new_meta, out[: int(k)]

def upsert_relations(db_path: str, source_paper_id: int, edges: list[dict[str, Any]]) -> int:
    ensure_tables(db_path)
    now = int(time.time())
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    n = 0
    for e in edges:
        try:
            tid = int(e.get("target_paper_id"))
        except Exception:
            continue
        rel = str(e.get("relation") or "").strip()[:32]
        if len(rel) < 2 or len(rel) > 32:
            continue
        try:
            score = float(e.get("score") or 0.0)
        except Exception:
            score = 0.0
        ev = str(e.get("evidence") or "").strip()[:240]
        if tid <= 0 or tid == int(source_paper_id):
            continue
        cur.execute(
            """
            INSERT INTO paper_relations(source_paper_id, target_paper_id, relation, score, evidence, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_paper_id, target_paper_id, relation) DO UPDATE SET
              score=excluded.score,
              evidence=excluded.evidence,
              updated_at=excluded.updated_at
            """,
            (int(source_paper_id), int(tid), rel, float(score), ev, now, now),
        )
        n += 1
    conn.commit()
    conn.close()
    return n

def build_relations_for_new_paper(db_path: str, new_paper_id: int) -> int:
    from ...agents import get_knowledge_graph_agent

    ensure_tables(db_path)
    new_meta, cands = fetch_new_and_candidates(db_path, int(new_paper_id), k=32)
    if not new_meta:
        return 0
    if not cands:
        with _kg_metrics_lock:
            _kg_metrics["build_skip_no_candidates"] = _kg_metrics.get("build_skip_no_candidates", 0) + 1
        logger.info(
            "kg_build_skip_no_candidates",
            extra={"paper_id": int(new_paper_id)},
        )
        return 0

    now = time.time()
    _prune_recent_fingerprints(now)

    _ax = _norm_arxiv_id(new_meta.get("arxiv_id"))
    if _ax:
        fp = f"arxiv:{_ax}"
    else:
        _doi = (new_meta.get("doi") or "").strip().lower()
        if _doi:
            fp = f"doi:{_doi}"
        else:
            _t = (new_meta.get("title") or "").strip().lower()[:160]
            fp = f"title:{_t}"

    with _kg_fingerprints_lock:
        last = _kg_recent_fingerprints.get(fp)
        if last is not None and (now - last) < _KG_DEDUP_WINDOW_SEC:
            with _kg_metrics_lock:
                _kg_metrics["build_skip_dedup"] = _kg_metrics.get("build_skip_dedup", 0) + 1
            logger.info(
                "kg_build_skip_dedup",
                extra={"paper_id": int(new_paper_id), "fingerprint": fp},
            )
            return 0
        _kg_recent_fingerprints[fp] = now

    try:
        pdf_abspath = _pdf_abspath_from_row(db_path, new_meta.get("local_pdf_path"))
        if pdf_abspath:
            excerpt, _hit = extract_pdf_text_full_cached(
                db_path, int(new_paper_id), pdf_abspath, max_chars=9000
            )
            if not excerpt.strip():
                excerpt = extract_pdf_text_full(pdf_abspath, max_chars=9000)
                if excerpt.strip():
                    _cache_set(db_path, int(new_paper_id), pdf_abspath, excerpt)
            if excerpt.strip():
                new_meta["pdf_excerpt"] = excerpt[:9000]
                new_meta["related_work_excerpt"] = _extract_related_work_excerpt(excerpt, max_chars=1600)
    except Exception as exc:
        logger.warning(
            "kg_pdf_excerpt_failed",
            extra={"paper_id": int(new_paper_id)},
            exc_info=exc,
        )

    edges: list[dict[str, Any]] = []
    with _kg_infer_lock:
        agent = get_knowledge_graph_agent()
        edges, _ = agent.infer_edges(new_paper=new_meta, candidates=cands)

    n = upsert_relations(db_path, int(new_paper_id), edges)
    if n:
        with _kg_metrics_lock:
            _kg_metrics["relations_upserted"] = _kg_metrics.get("relations_upserted", 0) + n
    with _kg_metrics_lock:
        _kg_metrics["build_ok"] = _kg_metrics.get("build_ok", 0) + 1
    return n
