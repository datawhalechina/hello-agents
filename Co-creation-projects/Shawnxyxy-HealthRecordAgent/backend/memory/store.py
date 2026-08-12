"""
SQLite 持久化：用户表 + 体检分析履历（report_runs）。
同步 API，在 async 路由中通过 asyncio.to_thread 调用。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# backend/memory/store.py -> 项目根目录（HealthRecordAgent）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "data"
_DEFAULT_DB_PATH = _DEFAULT_DATA_DIR / "health_memory.db"


def get_db_path() -> Path:
    override = os.getenv("HEALTH_MEMORY_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_legacy_columns(conn: sqlite3.Connection) -> None:
    """旧库补列（阶段 3：体检 trace、饮食 replay 溯源）。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(report_runs)").fetchall()}
    if "agent_trace_json" not in cols:
        conn.execute("ALTER TABLE report_runs ADD COLUMN agent_trace_json TEXT")
    cols_d = {r[1] for r in conn.execute("PRAGMA table_info(diet_runs)").fetchall()}
    if "replayed_from_run_id" not in cols_d:
        conn.execute("ALTER TABLE diet_runs ADD COLUMN replayed_from_run_id TEXT")


def init_db() -> None:
    """创建表与索引（幂等）。"""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS report_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                summary_text TEXT,
                report_json TEXT NOT NULL,
                agent_trace_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_report_runs_user_created
            ON report_runs (user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );

            CREATE TABLE IF NOT EXISTS diet_runs (
                run_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                input_json TEXT NOT NULL,
                steps_trace_json TEXT NOT NULL,
                output_json TEXT NOT NULL,
                replayed_from_run_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );

            CREATE TABLE IF NOT EXISTS diet_reflect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                diet_run_id TEXT NOT NULL,
                followed INTEGER NOT NULL DEFAULT 0,
                reason_code TEXT,
                reason_detail TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_diet_runs_user_created
            ON diet_runs (user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_diet_reflect_user_created
            ON diet_reflect (user_id, created_at DESC);
            """
        )
        _ensure_legacy_columns(conn)
        conn.commit()
    logger.info("SQLite 记忆库已就绪: %s", get_db_path())


def ensure_user(user_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
            (user_id, now),
        )
        conn.commit()


def save_completed_report_run(
    user_id: str,
    task_id: str,
    final_report: Dict[str, Any],
    agent_trace: Optional[Dict[str, Any]] = None,
) -> None:
    """
    分析成功完成后写入一条履历；失败时由调用方捕获日志，不影响主流程。
    agent_trace: 各 Agent 的 trace 列表（阶段 3 可观测性）。
    """
    ensure_user(user_id)
    summary = ""
    report_inner = final_report.get("report") if isinstance(final_report, dict) else None
    if isinstance(report_inner, dict):
        s = report_inner.get("summary")
        if isinstance(s, str):
            summary = s[:8000]
        elif s is not None:
            summary = str(s)[:8000]

    payload = json.dumps(final_report, ensure_ascii=False)
    trace_payload = json.dumps(agent_trace, ensure_ascii=False) if agent_trace else None
    now = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO report_runs (task_id, user_id, created_at, summary_text, report_json, agent_trace_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, user_id, now, summary or None, payload, trace_payload),
        )
        conn.commit()


def list_report_runs_for_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT task_id, user_id, created_at, summary_text
            FROM report_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_report_run(task_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT task_id, user_id, created_at, summary_text, report_json, agent_trace_json
            FROM report_runs
            WHERE task_id = ?
            """,
            (task_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("report_json"):
        try:
            d["report"] = json.loads(d["report_json"])
        except json.JSONDecodeError:
            d["report"] = None
        del d["report_json"]
    raw_trace = d.pop("agent_trace_json", None)
    if raw_trace:
        try:
            d["agent_trace"] = json.loads(raw_trace)
        except json.JSONDecodeError:
            d["agent_trace"] = None
    else:
        d["agent_trace"] = None
    return d


def save_diet_run(
    user_id: str,
    run_id: str,
    input_payload: Dict[str, Any],
    steps_trace: List[Dict[str, Any]],
    output_payload: Dict[str, Any],
    replayed_from_run_id: Optional[str] = None,
) -> None:
    ensure_user(user_id)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO diet_runs (run_id, user_id, created_at, input_json, steps_trace_json, output_json, replayed_from_run_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                now,
                json.dumps(input_payload, ensure_ascii=False),
                json.dumps(steps_trace, ensure_ascii=False),
                json.dumps(output_payload, ensure_ascii=False),
                replayed_from_run_id,
            ),
        )
        conn.commit()


def insert_diet_reflect(
    user_id: str,
    diet_run_id: str,
    followed: bool,
    reason_code: str | None,
    reason_detail: str | None,
) -> int:
    ensure_user(user_id)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO diet_reflect (user_id, diet_run_id, followed, reason_code, reason_detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                diet_run_id,
                1 if followed else 0,
                reason_code,
                (reason_detail or "")[:2000] or None,
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_recent_diet_reflect(user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 50))
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, diet_run_id, followed, reason_code, reason_detail, created_at
            FROM diet_reflect
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["followed"] = bool(d["followed"])
        out.append(d)
    return out


def format_reflect_memory_for_prompt(user_id: str, limit: int = 5) -> str:
    rows = list_recent_diet_reflect(user_id, limit=limit)
    if not rows:
        return "（暂无历史执行反馈）"
    lines = []
    for r in rows:
        fl = "已执行" if r["followed"] else "未执行"
        rc = r.get("reason_code") or "-"
        rd = (r.get("reason_detail") or "").strip()
        lines.append(
            f"- {r['created_at'][:19]} | run={r['diet_run_id'][:8]}… | {fl} | 原因码={rc}"
            + (f" | 说明={rd}" if rd else "")
        )
    return "\n".join(lines)


def get_diet_run(run_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT run_id, user_id, created_at, input_json, steps_trace_json, output_json, replayed_from_run_id
            FROM diet_runs
            WHERE run_id = ?
            """,
            (run_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    mapping = {
        "input_json": "input",
        "steps_trace_json": "steps_trace",
        "output_json": "output",
    }
    for raw_key, out_key in mapping.items():
        raw = d.pop(raw_key, None)
        if raw:
            try:
                d[out_key] = json.loads(raw)
            except json.JSONDecodeError:
                d[out_key] = None
        else:
            d[out_key] = None
    return d


def list_diet_runs_for_user(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 100))
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT run_id, user_id, created_at,
                   json_extract(output_json, '$.meal_plan.total_est_protein_g') AS total_protein
            FROM diet_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_diet_reflect(reflect_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, user_id, diet_run_id, followed, reason_code, reason_detail, created_at
            FROM diet_reflect
            WHERE id = ?
            """,
            (reflect_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["followed"] = bool(d["followed"])
    return d


def list_all_user_ids(limit: int = 5000) -> List[str]:
    limit = max(1, min(limit, 20000))
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT user_id
            FROM users
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return [r["user_id"] for r in rows]


def list_user_memory_chunks_sql(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    SQL 回退检索：按时间抓取用户近期文本记忆。
    """
    limit = max(1, min(limit, 500))
    out: List[Dict[str, Any]] = []
    with _connect() as conn:
        r1 = conn.execute(
            """
            SELECT task_id, created_at, summary_text
            FROM report_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        for r in r1:
            txt = (r["summary_text"] or "").strip()
            if not txt:
                continue
            out.append(
                {
                    "chunk_id": f"report:{r['task_id']}",
                    "user_id": user_id,
                    "source_type": "report_summary",
                    "source_id": r["task_id"],
                    "created_at": r["created_at"],
                    "text": txt[:8000],
                }
            )

        r2 = conn.execute(
            """
            SELECT run_id, created_at, output_json
            FROM diet_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        for r in r2:
            txt = ""
            try:
                obj = json.loads(r["output_json"] or "{}")
                mp = obj.get("meal_plan") or {}
                items = mp.get("items") or []
                hints = (obj.get("habit_extras") or {}).get("execution_hints", [])
                txt = "；".join(
                    [f"{it.get('name')} {it.get('portion')} {it.get('why','')}" for it in items if isinstance(it, dict)]
                )
                if hints:
                    txt += "\n执行提示：" + "；".join([str(h) for h in hints])
            except Exception:
                txt = str(r["output_json"] or "")
            txt = txt.strip()
            if not txt:
                continue
            out.append(
                {
                    "chunk_id": f"diet:{r['run_id']}",
                    "user_id": user_id,
                    "source_type": "diet_plan",
                    "source_id": r["run_id"],
                    "created_at": r["created_at"],
                    "text": txt[:8000],
                }
            )

        r3 = conn.execute(
            """
            SELECT id, created_at, followed, reason_code, reason_detail
            FROM diet_reflect
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        for r in r3:
            txt = f"执行={bool(r['followed'])} 原因={r['reason_code'] or '-'} 说明={r['reason_detail'] or ''}".strip()
            out.append(
                {
                    "chunk_id": f"reflect:{r['id']}",
                    "user_id": user_id,
                    "source_type": "diet_reflect",
                    "source_id": str(r["id"]),
                    "created_at": r["created_at"],
                    "text": txt[:8000],
                }
            )
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out[:limit]
