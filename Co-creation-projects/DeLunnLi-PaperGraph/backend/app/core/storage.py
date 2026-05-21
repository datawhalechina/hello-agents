
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from collections import defaultdict
from contextlib import contextmanager, suppress
from typing import Any

from .author import Author
from .paper import Paper
from .paper_paths import LIBRARY_PDF_ROOT_DIR, category_slug_for_pdf_dir
from ..settings import get_settings

logger = logging.getLogger(__name__)

class PaperDatabase:

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_path = os.path.join(os.path.abspath(get_settings().data_dir), "papers.db")

        self.db_path = db_path
        self._library_fts_ready = False
        self._ensure_directory()
        self._init_database()
        self._library_fts_ready = self._detect_fts_table()

    def _data_root(self) -> str:
        return os.path.dirname(os.path.abspath(self.db_path))

    def _abs_local_pdf(self, relpath: str | None) -> str | None:
        if not relpath or not str(relpath).strip():
            return None
        return os.path.normpath(os.path.join(self._data_root(), str(relpath).strip()))

    def _ensure_directory(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _detect_fts_table(self) -> bool:
        try:
            return self._query(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='papers_fts' LIMIT 1",
                fetch='one'
            ) is not None
        except Exception:
            return False

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Database transaction failed: %s", e)
            raise
        finally:
            conn.close()

    def _query(self, sql, params=(), fetch='all'):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            if fetch == 'one':
                return cur.fetchone()
            if fetch == 'all':
                return cur.fetchall()
            return None

    def _ensure_column(self, conn: sqlite3.Connection, col_name: str, col_type: str = "TEXT") -> None:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(papers)")
        cols = [r[1] for r in cur.fetchall()]
        if col_name not in cols:
            cur.execute(f"ALTER TABLE papers ADD COLUMN {col_name} {col_type}")

    def _init_database(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version")
            db_version = int(cursor.fetchone()[0])

            if db_version < 1:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS papers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        abstract TEXT,
                        doi TEXT UNIQUE,
                        pmid TEXT UNIQUE,
                        arxiv_id TEXT UNIQUE,
                        pmc_id TEXT UNIQUE,
                        journal TEXT,
                        year INTEGER,
                        volume TEXT,
                        issue TEXT,
                        pages TEXT,
                        publisher TEXT,
                        pdf_url TEXT,
                        source_url TEXT,
                        local_pdf_path TEXT,
                        keywords TEXT,
                        mesh_terms TEXT,
                        "references" TEXT,
                        citations INTEGER DEFAULT 0,
                        source TEXT DEFAULT 'unknown',
                        notes TEXT,
                        tags TEXT,
                        category TEXT,
                        rating INTEGER,
                        read_status TEXT DEFAULT 'unread',
                        importance TEXT DEFAULT 'normal',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                self._ensure_column(conn, "local_pdf_path")
                self._ensure_column(conn, "category")
                self._ensure_column(conn, "venue_type")

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS authors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        affiliation TEXT,
                        email TEXT,
                        orcid TEXT UNIQUE
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS paper_authors (
                        paper_id INTEGER NOT NULL,
                        author_id INTEGER NOT NULL,
                        author_order INTEGER DEFAULT 0,
                        PRIMARY KEY (paper_id, author_id),
                        FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                        FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute("PRAGMA user_version = 1")
                db_version = 1

            if db_version < 2:
                cursor.executescript(
                    """
                    CREATE INDEX IF NOT EXISTS idx_papers_category ON papers(category);
                    CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
                    CREATE INDEX IF NOT EXISTS idx_papers_read_status ON papers(read_status);
                    CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers(created_at);
                    CREATE INDEX IF NOT EXISTS idx_category_year ON papers(category, year);
                    """
                )
                try:
                    cursor.executescript(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                            title, abstract,
                            content='papers', content_rowid='id'
                        );

                        CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
                            INSERT INTO papers_fts(rowid, title, abstract)
                            VALUES (new.id, new.title, new.abstract);
                        END;

                        CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
                            INSERT INTO papers_fts(papers_fts, rowid, title, abstract)
                            VALUES ('delete', old.id, old.title, old.abstract);
                        END;

                        CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
                            INSERT INTO papers_fts(papers_fts, rowid, title, abstract)
                            VALUES ('delete', old.id, old.title, old.abstract);
                            INSERT INTO papers_fts(rowid, title, abstract)
                            VALUES (new.id, new.title, new.abstract);
                        END;
                        """
                    )
                    cursor.execute("INSERT INTO papers_fts(papers_fts) VALUES('rebuild')")
                except sqlite3.OperationalError as e:
                    logger.warning("FTS5 不可用或未启用，跳过全文索引: %s", e)
                cursor.execute("PRAGMA user_version = 2")

    @staticmethod
    def _norm_id_field(val: str | None) -> str | None:
        s = (val or "").strip()
        return s if s else None

    def _sync_saved_meta(self, cursor: sqlite3.Cursor, paper_id: int, paper: Paper) -> None:
        cat = getattr(paper, "category", None)
        doi = self._norm_id_field(paper.doi)
        arxiv_id = self._norm_id_field(paper.arxiv_id)
        abs_new = (paper.abstract or "").strip() or None
        title_new = (paper.title or "").strip() or None
        cursor.execute(
            """UPDATE papers SET category = ?, tags = ?, pdf_url = ?, source_url = ?,
               doi = COALESCE(?, doi),
               arxiv_id = COALESCE(?, arxiv_id),
               abstract = COALESCE(?, abstract),
               title = COALESCE(?, title),
               venue_type = COALESCE(?, venue_type),
               updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (
                cat,
                json.dumps(paper.tags or [], ensure_ascii=False),
                paper.pdf_url,
                paper.source_url,
                doi,
                arxiv_id,
                abs_new,
                title_new,
                getattr(paper, "venue_type", None),
                paper_id,
            ),
        )

    def _add_paper_internal(self, conn: sqlite3.Connection, paper: Paper) -> tuple[int, bool]:
        cursor = conn.cursor()
        doi = self._norm_id_field(paper.doi)
        arxiv_id = self._norm_id_field(paper.arxiv_id)
        pmid = self._norm_id_field(paper.pmid)
        pmc_id = self._norm_id_field(paper.pmc_id)

        for field, val in (("doi", doi), ("arxiv_id", arxiv_id), ("pmid", pmid), ("pmc_id", pmc_id)):
            if val:
                cursor.execute(f"SELECT id FROM papers WHERE {field} = ?", (val,))
                existing = cursor.fetchone()
                if existing:
                    eid = int(existing[0])
                    self._sync_saved_meta(cursor, eid, paper)
                    return eid, False

        cursor.execute(
            """
            INSERT INTO papers (
                title, abstract, doi, pmid, arxiv_id, pmc_id,
                journal, year, volume, issue, pages, publisher,
                pdf_url, source_url, local_pdf_path, keywords, mesh_terms, "references",
                citations, source, notes, tags, category, venue_type, rating, read_status, importance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper.title,
                paper.abstract,
                doi,
                pmid,
                arxiv_id,
                pmc_id,
                paper.journal,
                paper.year,
                paper.volume,
                paper.issue,
                paper.pages,
                paper.publisher,
                paper.pdf_url,
                paper.source_url,
                getattr(paper, "local_pdf_path", None),
                json.dumps(paper.keywords, ensure_ascii=False),
                json.dumps(paper.mesh_terms, ensure_ascii=False),
                json.dumps(paper.references, ensure_ascii=False),
                paper.citations,
                paper.source,
                paper.notes,
                json.dumps(paper.tags, ensure_ascii=False),
                getattr(paper, "category", None),
                getattr(paper, "venue_type", None),
                paper.rating,
                paper.read_status,
                paper.importance,
            ),
        )

        paper_id = cursor.lastrowid
        self._add_authors(conn, paper_id, paper.authors)
        return int(paper_id), True

    def add_paper(self, paper: Paper) -> tuple[int, bool]:
        with self._get_connection() as conn:
            return self._add_paper_internal(conn, paper)

    def add_papers(self, papers: list[Paper]) -> tuple[list[int], int, int]:
        ids: list[int] = []
        added = 0
        updated = 0
        with self._get_connection() as conn:
            for paper in papers:
                try:
                    paper_id, is_new = self._add_paper_internal(conn, paper)
                    ids.append(int(paper_id))
                    if is_new:
                        added += 1
                    else:
                        updated += 1
                except Exception as e:
                    logger.error("批量添加文献时出错 '%s': %s", getattr(paper, "title", ""), e)
                    ids.append(-1)
        return ids, added, updated

    def _add_authors(self, conn: sqlite3.Connection, paper_id: int, authors: list[Author]) -> None:
        cursor = conn.cursor()
        for order, author in enumerate(authors):
            if author.orcid:
                cursor.execute("SELECT id FROM authors WHERE orcid = ?", (author.orcid,))
            else:
                cursor.execute("SELECT id FROM authors WHERE name = ?", (author.name,))

            result = cursor.fetchone()
            if result:
                author_id = result[0]
            else:
                cursor.execute(
                    "INSERT INTO authors (name, affiliation, email, orcid) VALUES (?, ?, ?, ?)",
                    (author.name, author.affiliation, author.email, author.orcid),
                )
                author_id = cursor.lastrowid

            with suppress(sqlite3.IntegrityError):
                cursor.execute(
                    "INSERT INTO paper_authors (paper_id, author_id, author_order) VALUES (?, ?, ?)",
                    (paper_id, author_id, order),
                )

    def _fetch_authors_for_papers(
        self, conn: sqlite3.Connection, paper_ids: list[int]
    ) -> dict[int, list[Author]]:
        if not paper_ids:
            return {}
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(paper_ids))
        cursor.execute(
            f"""
            SELECT pa.paper_id, a.* FROM authors a
            JOIN paper_authors pa ON a.id = pa.author_id
            WHERE pa.paper_id IN ({placeholders})
            ORDER BY pa.paper_id, pa.author_order
            """,
            paper_ids,
        )
        authors_by_paper: dict[int, list[Author]] = defaultdict(list)
        for row in cursor.fetchall():
            authors_by_paper[int(row["paper_id"])].append(
                Author(
                    name=row["name"],
                    affiliation=row["affiliation"],
                    email=row["email"],
                    orcid=row["orcid"],
                    db_id=int(row["id"]) if row["id"] is not None else None,
                )
            )
        return dict(authors_by_paper)

    def _row_to_paper_fast(self, row: sqlite3.Row, authors: list[Author]) -> Paper:
        keys = row.keys()
        return Paper(
            id=row["id"],
            title=row["title"],
            authors=authors,
            abstract=row["abstract"],
            doi=row["doi"],
            pmid=row["pmid"],
            arxiv_id=row["arxiv_id"],
            pmc_id=row["pmc_id"],
            journal=row["journal"],
            year=row["year"],
            volume=row["volume"],
            issue=row["issue"],
            pages=row["pages"],
            publisher=row["publisher"],
            pdf_url=row["pdf_url"],
            source_url=row["source_url"],
            local_pdf_path=row["local_pdf_path"] if "local_pdf_path" in keys else None,
            keywords=json.loads(row["keywords"] or "[]"),
            mesh_terms=json.loads(row["mesh_terms"] or "[]"),
            references=json.loads(row["references"] or "[]"),
            citations=row["citations"] or 0,
            source=row["source"] or "unknown",
            notes=row["notes"],
            tags=json.loads(row["tags"] or "[]"),
            category=row["category"] if "category" in keys else None,
            venue_type=row["venue_type"] if "venue_type" in keys else None,
            rating=row["rating"],
            read_status=row["read_status"] or "unread",
            importance=row["importance"] or "normal",
        )

    def count_papers(self) -> int:
        return self._query("SELECT COUNT(*) FROM papers", fetch='one')[0]

    def get_all_papers(self, limit: int | None = None, offset: int = 0, order_by: str = "created_at DESC") -> list[Paper]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT * FROM papers ORDER BY {order_by}"
            if limit:
                query += f" LIMIT {int(limit)}"
            if offset:
                query += f" OFFSET {int(offset)}"
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return []
            paper_ids = [int(r["id"]) for r in rows]
            authors_map = self._fetch_authors_for_papers(conn, paper_ids)
            return [
                self._row_to_paper_fast(row, authors_map.get(int(row["id"]), []))
                for row in rows
            ]

    def get_paper_by_id(self, paper_id: int) -> Paper | None:
        row = self._query("SELECT * FROM papers WHERE id = ?", (paper_id,), fetch='one')
        if not row:
            return None
        with self._get_connection() as conn:
            authors_map = self._fetch_authors_for_papers(conn, [paper_id])
        return self._row_to_paper_fast(row, authors_map.get(paper_id, []))

    def search_library(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        read_status: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Paper]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            clauses: list[str] = ["1=1"]
            params: list[Any] = []
            use_fts = False
            match_expr = ""
            clean_query = ""

            if query and str(query).strip():
                clean_query = re.sub(r'["\'*^]', " ", str(query)).strip()
                if clean_query and self._library_fts_ready:
                    parts = [w for w in clean_query.split() if w.strip()]
                    if parts:
                        match_expr = " AND ".join(f'"{w}"' for w in parts)
                        use_fts = True

            if use_fts:
                base_from = "papers p"
                clauses.append(
                    "(p.id IN (SELECT rowid FROM papers_fts WHERE papers_fts MATCH ?)"
                    " OR p.id IN (SELECT pa.paper_id FROM paper_authors pa JOIN authors a ON pa.author_id = a.id WHERE a.name LIKE ?))"
                )
                params.append(match_expr)
                like_author = f"%{clean_query}%"
                params.append(like_author)
            elif query and str(query).strip():
                clauses.append("(p.title LIKE ? OR p.abstract LIKE ? OR p.id IN (SELECT pa.paper_id FROM paper_authors pa JOIN authors a ON pa.author_id = a.id WHERE a.name LIKE ?))")
                like = f"%{str(query).strip()}%"
                params.extend([like, like, like])
                base_from = "papers p"
            else:
                base_from = "papers p"

            if category:
                cat = category.strip()
                if cat.endswith("/*"):
                    prefix = cat[:-2].strip()
                    if prefix == "未分类":
                        clauses.append(
                            "(p.category IS NULL OR TRIM(COALESCE(p.category, '')) IN ('', '未分类') "
                            "OR TRIM(COALESCE(p.category, '')) LIKE '未分类/%')"
                        )
                    elif prefix:
                        clauses.append(
                            "(TRIM(COALESCE(p.category, '')) = ? OR TRIM(COALESCE(p.category, '')) LIKE ?)"
                        )
                        params.extend([prefix, prefix + "/%"])
                elif cat == "未分类":
                    clauses.append(
                        "(p.category IS NULL OR TRIM(COALESCE(p.category, '')) IN ('', '未分类'))"
                    )
                else:
                    clauses.append("TRIM(COALESCE(p.category, '')) = ?")
                    params.append(cat)

            if year_from is not None:
                clauses.append("(p.year IS NOT NULL AND p.year >= ?)")
                params.append(year_from)
            if year_to is not None:
                clauses.append("(p.year IS NOT NULL AND p.year <= ?)")
                params.append(year_to)
            if read_status:
                clauses.append("p.read_status = ?")
                params.append(read_status)

            order_clause = "ORDER BY p.created_at DESC"

            sql = f"SELECT p.* FROM {base_from} WHERE {' AND '.join(clauses)} {order_clause} LIMIT ?"
            params.append(int(limit))
            if offset:
                sql += " OFFSET ?"
                params.append(int(offset))
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            if not rows:
                return []
            paper_ids = [int(r["id"]) for r in rows]
            authors_map = self._fetch_authors_for_papers(conn, paper_ids)
            papers = [self._row_to_paper_fast(row, authors_map.get(int(row["id"]), [])) for row in rows]
            if tags:
                tag_set = set(tags)
                papers = [p for p in papers if tag_set.intersection(set(p.tags))]
            return papers

    def update_paper(self, paper_id: int, **fields) -> bool:
        allowed = {"notes", "tags", "rating", "read_status", "importance", "category", "abstract"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)
        set_parts = [f"{k} = ?" for k in updates]
        values = list(updates.values()) + [paper_id]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE papers SET {', '.join(set_parts)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values,
            )
            return cursor.rowcount > 0

    def set_local_pdf_path(self, paper_id: int, relative_path: str | None) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE papers SET local_pdf_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (relative_path, paper_id),
            )
            return cursor.rowcount > 0

    def delete_paper(self, paper_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT local_pdf_path FROM papers WHERE id = ?", (paper_id,))
            row = cursor.fetchone()
            if row and row[0]:
                abspath = self._abs_local_pdf(row[0])
                if abspath and os.path.isfile(abspath):
                    with suppress(OSError):
                        os.remove(abspath)
            cursor.execute("DELETE FROM paper_authors WHERE paper_id = ?", (paper_id,))
            cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
            return cursor.rowcount > 0

    def repair_library_local_pdf_paths_batch(self, paper_ids: list[int]) -> dict[int, str]:
        want = {int(x) for x in paper_ids if x is not None and int(x) >= 0}
        if not want:
            return {}
        data_root = self._data_root()
        lib_root = os.path.join(data_root, LIBRARY_PDF_ROOT_DIR)
        if not os.path.isdir(lib_root):
            return {}
        candidates: dict[int, list[tuple[float, str]]] = {k: [] for k in want}
        name_pat = re.compile(r"^(\d+)\.pdf$")
        for dirpath, _, filenames in os.walk(lib_root):
            for fn in filenames:
                m = name_pat.match(fn)
                if not m:
                    continue
                pid = int(m.group(1))
                if pid not in want:
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    mt = os.path.getmtime(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, data_root).replace("\\", "/")
                if rel.startswith(".."):
                    continue
                candidates[pid].append((mt, rel))
        out: dict[int, str] = {}
        for pid, rows in candidates.items():
            if not rows:
                continue
            rows.sort(key=lambda x: -x[0])
            best_rel = rows[0][1]
            if self.set_local_pdf_path(pid, best_rel):
                out[pid] = best_rel
        return out

    def get_library_pdf_abspath(self, paper_id: int) -> str | None:
        p = self.get_paper_by_id(paper_id)
        if not p or not (getattr(p, "local_pdf_path", None) or "").strip():
            return None
        rel = (p.local_pdf_path or "").strip()
        candidates = [self._abs_local_pdf(rel)]
        if rel.startswith(f"{LIBRARY_PDF_ROOT_DIR}/"):
            candidates.append(
                self._abs_local_pdf("pdfs/" + rel[len(LIBRARY_PDF_ROOT_DIR) + 1 :])
            )
        elif rel.startswith("pdfs/"):
            candidates.append(
                self._abs_local_pdf(f"{LIBRARY_PDF_ROOT_DIR}/" + rel[len("pdfs/") :])
            )
        root = os.path.realpath(self._data_root())
        for abspath in candidates:
            if not abspath or not os.path.isfile(abspath):
                continue
            real_f = os.path.realpath(abspath)
            if real_f != root and not real_f.startswith(root + os.sep):
                continue
            return real_f
        return None

    def list_library_category_folders(self) -> list[dict[str, Any]]:
        rows = self._query(
            """
            SELECT COALESCE(NULLIF(TRIM(category), ''), '未分类') AS c, COUNT(*) AS n
            FROM papers
            GROUP BY c
            ORDER BY n DESC, c ASC
            """
        )

        standalone: dict[str, int] = {}
        by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            c = row["c"] or "未分类"
            n = int(row["n"])
            if "/" not in c:
                standalone[c] = standalone.get(c, 0) + n
                continue
            parts = [p.strip() for p in c.split("/") if p.strip()]
            if len(parts) < 2:
                standalone[c] = standalone.get(c, 0) + n
                continue
            parent = parts[0]
            label = "/".join(parts[1:])
            by_parent[parent].append(
                {
                    "category": c,
                    "label": label,
                    "folder": category_slug_for_pdf_dir(c),
                    "count": n,
                }
            )

        consumed_standalone: set[str] = set()
        out: list[dict[str, Any]] = []

        for parent in sorted(
            by_parent.keys(),
            key=lambda p: (-sum(x["count"] for x in by_parent[p]), p),
        ):
            ch = sorted(by_parent[parent], key=lambda x: (-x["count"], x["label"]))
            extra = standalone.get(parent, 0)
            total = sum(x["count"] for x in ch) + extra
            children: list[dict[str, Any]] = []
            if extra > 0:
                children.append(
                    {
                        "category": parent,
                        "label": "未分子类",
                        "folder": category_slug_for_pdf_dir(parent),
                        "count": extra,
                    }
                )
                consumed_standalone.add(parent)
            children.extend(ch)
            out.append(
                {
                    "category": parent,
                    "folder": category_slug_for_pdf_dir(parent),
                    "count": total,
                    "children": children,
                }
            )

        for cat, n in standalone.items():
            if cat in consumed_standalone:
                continue
            out.append(
                {
                    "category": cat,
                    "folder": category_slug_for_pdf_dir(cat),
                    "count": n,
                    "children": [],
                }
            )

        out.sort(key=lambda x: (-x["count"], x["category"]))
        return out

    def list_library_categories_by_count(self, limit: int = 80) -> list[str]:
        limit = int(limit or 0)
        if limit <= 0:
            limit = 80
        rows = self._query(
            """
            SELECT COALESCE(NULLIF(TRIM(category), ''), '未分类') AS c, COUNT(*) AS n
            FROM papers
            GROUP BY c
            ORDER BY n DESC, c ASC
            LIMIT ?
            """,
            (limit,),
        )
        out: list[str] = []
        for r in rows:
            c = (r["c"] or "").strip() or "未分类"
            if c not in out:
                out.append(c)
        return out
