
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class RelationRepository:
    db_path: str

    def fetch_relation_rows(
        self, *, focus_id: int | None, paper_ids: set[int | None], limit: int,
    ) -> list[tuple[int, int, str, float, str]]:
        import sqlite3
        if int(limit) <= 0:
            return []
        rows: list[tuple[int, int, str, float, str]] = []
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            if focus_id is not None:
                cur.execute(
                    """SELECT source_paper_id, target_paper_id, relation, score, evidence
                    FROM paper_relations
                    WHERE source_paper_id = ? OR target_paper_id = ?
                    ORDER BY score DESC, updated_at DESC LIMIT ?""",
                    (int(focus_id), int(focus_id), int(limit)),
                )
            else:
                ids = sorted(int(x) for x in (paper_ids or set()) if int(x) > 0)
                if not ids:
                    return []
                cur.execute("CREATE TEMP TABLE IF NOT EXISTS _kg_pid (id INTEGER PRIMARY KEY)")
                cur.execute("DELETE FROM _kg_pid")
                cur.executemany("INSERT OR IGNORE INTO _kg_pid(id) VALUES (?)", [(i,) for i in ids])
                cur.execute(
                    """SELECT pr.source_paper_id, pr.target_paper_id, pr.relation, pr.score, pr.evidence
                    FROM paper_relations pr
                    INNER JOIN _kg_pid a ON a.id = pr.source_paper_id
                    INNER JOIN _kg_pid b ON b.id = pr.target_paper_id
                    ORDER BY pr.score DESC, pr.updated_at DESC LIMIT ?""",
                    (int(limit),),
                )
            for sid, tid, rel, score, evidence in cur.fetchall():
                rows.append((int(sid), int(tid), str(rel or ""), float(score or 0.0), str(evidence or "")))
        return rows

    def papers_minimal_by_ids(self, paper_ids: set[int]) -> dict[int, tuple[str, int | None, str | None]]:
        import sqlite3
        ids = sorted(int(x) for x in paper_ids if int(x) > 0)
        if not ids:
            return {}
        out: dict[int, tuple[str, int | None, str | None]] = {}
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("CREATE TEMP TABLE IF NOT EXISTS _kg_meta (id INTEGER PRIMARY KEY)")
            cur.execute("DELETE FROM _kg_meta")
            cur.executemany("INSERT OR IGNORE INTO _kg_meta(id) VALUES (?)", [(i,) for i in ids])
            cur.execute(
                """SELECT p.id, p.title, p.year, p.category
                FROM papers p INNER JOIN _kg_meta t ON t.id = p.id"""
            )
            for rid, title, year, cat in cur.fetchall():
                out[int(rid)] = (str(title or ""), int(year) if year is not None else None, str(cat) if cat else None)
        return out
