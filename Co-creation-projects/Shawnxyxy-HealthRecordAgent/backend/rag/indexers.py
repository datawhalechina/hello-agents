"""
将 SQLite 中的历史记录写入 Milvus 向量索引。
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from memory.store import (
    get_diet_reflect,
    get_diet_run,
    get_report_run,
    list_user_memory_chunks_sql,
)
from rag.embedding import embed_texts
from rag.milvus_store import upsert_chunks


def _chunk_id(source_type: str, source_id: str, text: str) -> str:
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"{source_type}:{source_id}:{h}"


def _to_chunk(
    user_id: str,
    source_type: str,
    source_id: str,
    text: str,
    created_at: str | None = None,
) -> Dict[str, Any]:
    return {
        "chunk_id": _chunk_id(source_type, source_id, text),
        "user_id": user_id,
        "source_type": source_type,
        "source_id": source_id,
        "text": text[:8000],
        "created_at": created_at or "",
    }


def _embed_and_upsert(chunks: List[Dict[str, Any]]) -> int:
    if not chunks:
        return 0
    vecs = embed_texts([c["text"] for c in chunks])
    for c, v in zip(chunks, vecs):
        c["vector"] = v
    return upsert_chunks(chunks)


def index_report_run(task_id: str) -> int:
    row = get_report_run(task_id)
    if not row:
        return 0
    txt = row.get("summary_text") or ""
    if not txt:
        report = row.get("report") or {}
        report_in = report.get("report") if isinstance(report, dict) else {}
        txt = (report_in or {}).get("summary") or ""
    if not txt:
        return 0
    chunk = _to_chunk(
        user_id=row["user_id"],
        source_type="report_summary",
        source_id=row["task_id"],
        text=txt,
        created_at=row.get("created_at"),
    )
    return _embed_and_upsert([chunk])


def index_diet_run(run_id: str) -> int:
    row = get_diet_run(run_id)
    if not row:
        return 0
    output = row.get("output") or {}
    mp = (output.get("meal_plan") or {}) if isinstance(output, dict) else {}
    hints = (output.get("habit_extras") or {}).get("execution_hints", [])
    items = mp.get("items") or []
    txt = "；".join(
        [f"{it.get('name')} {it.get('portion')} {it.get('why','')}" for it in items if isinstance(it, dict)]
    )
    if hints:
        txt += "\n执行提示：" + "；".join([str(x) for x in hints])
    if not txt:
        txt = str(output)[:2000]
    chunk = _to_chunk(
        user_id=row["user_id"],
        source_type="diet_plan",
        source_id=row["run_id"],
        text=txt,
        created_at=row.get("created_at"),
    )
    return _embed_and_upsert([chunk])


def index_reflect_event(reflect_id: int | str) -> int:
    row = get_diet_reflect(int(reflect_id))
    if not row:
        return 0
    txt = f"执行={row['followed']} 原因={row.get('reason_code') or '-'} 说明={row.get('reason_detail') or ''}"
    chunk = _to_chunk(
        user_id=row["user_id"],
        source_type="diet_reflect",
        source_id=str(row["id"]),
        text=txt,
        created_at=row.get("created_at"),
    )
    return _embed_and_upsert([chunk])


def reindex_user(user_id: str, limit: int = 200) -> int:
    rows = list_user_memory_chunks_sql(user_id=user_id, limit=limit)
    chunks = [
        _to_chunk(
            user_id=r["user_id"],
            source_type=r["source_type"],
            source_id=r["source_id"],
            text=r["text"],
            created_at=r.get("created_at"),
        )
        for r in rows
        if r.get("text")
    ]
    return _embed_and_upsert(chunks)
