# -*- coding: utf-8 -*-
"""Neo4j knowledge-graph store for PubMed literature.

Problem Solved:
    Vector search answers "which papers are semantically similar", but
    researchers also want structural questions: who are the authors, which
    journal published related work, and which papers share authors/journals
    with a paper of interest. A property graph (Neo4j Aura) models these
    relationships natively.

Graph Model:
    (:Paper {pmid, title, abstract, journal, year, doi})
    (:Author {name})
    (:Journal {name})
    (a:Author)-[:AUTHORED]->(p:Paper)
    (p:Paper)-[:PUBLISHED_IN]->(j:Journal)

Design Notes:
    - The neo4j driver is imported lazily so the rest of the app keeps
      working (with graceful degradation) when the package is not installed.
    - All writes use MERGE so re-indexing the same article is idempotent.

Usage:
    store = Neo4jGraphStore(uri, user, password, database="neo4j")
    store.upsert_articles(articles)          # list[PubMedArticle] or dicts
    related = store.related_papers(pmid, limit=10)
    stats = store.stats()
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase  # noqa: F401
    _NEO4J_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when package is absent
    GraphDatabase = None  # type: ignore[assignment]
    _NEO4J_AVAILABLE = False


class Neo4jStoreError(Exception):
    """Raised when the Neo4j store is unavailable or a query fails."""


def _extract_year(publish_date: str) -> str:
    """Best-effort year extraction from a PubMed publish date string."""
    match = re.search(r"\b(19|20)\d{2}\b", publish_date or "")
    return match.group(0) if match else ""


class Neo4jGraphStore:
    """Neo4j-backed knowledge graph for PubMed articles.

    Parameters
    ----------
    uri : str
        Neo4j connection URI (e.g. neo4j+s://xxxx.databases.neo4j.io).
    username : str
        Neo4j username.
    password : str
        Neo4j password.
    database : str
        Database name (default "neo4j").
    """

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver: Any = None
        logger.info(
            "Neo4jGraphStore configured (uri=%s, database=%s)",
            uri,
            database,
        )

    # ------------------------------------------------------------------
    # Driver access (lazy)
    # ------------------------------------------------------------------

    @property
    def driver(self) -> Any:
        """Lazily create the Neo4j driver."""
        if self._driver is None:
            if not _NEO4J_AVAILABLE:
                raise Neo4jStoreError(
                    "neo4j driver is not installed. Run: pip install 'neo4j>=5.20.0'"
                )
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
            )
            logger.info("Neo4j driver created: %s", self.uri)
        return self._driver

    def close(self) -> None:
        """Close the driver if it was created."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    # ------------------------------------------------------------------
    # Health / stats
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True when the Neo4j server is reachable."""
        ready, _ = self.diagnose()
        return ready

    def diagnose(self) -> tuple[bool, str]:
        """Return (reachable, error_message) for the Neo4j connection.

        The error message distinguishes missing-driver from real connection
        failures so operators can act on the root cause.
        """
        try:
            self.driver.verify_connectivity()
            return True, ""
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            logger.warning("Neo4j connectivity check failed: %s", msg)
            return False, msg

    def stats(self) -> dict[str, int]:
        """Return node counts for papers, authors, and journals."""
        counts = {"papers": 0, "authors": 0, "journals": 0}
        statements = {
            "papers": "MATCH (p:Paper) RETURN count(p) AS n",
            "authors": "MATCH (a:Author) RETURN count(a) AS n",
            "journals": "MATCH (j:Journal) RETURN count(j) AS n",
        }
        try:
            with self.driver.session(database=self.database) as session:
                for key, cypher in statements.items():
                    record = session.run(cypher).single()
                    if record is not None:
                        counts[key] = int(record["n"])
            return counts
        except Exception as exc:
            logger.warning("Neo4j stats failed: %s", exc)
            return counts

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def upsert_articles(self, articles: list[Any]) -> int:
        """Index articles into the graph (papers, authors, journals).

        Accepts PubMedArticle objects or plain dicts. Returns the number of
        paper nodes written. Idempotent thanks to MERGE.
        """
        if not articles:
            return 0
        try:
            with self.driver.session(database=self.database) as session:
                for article in articles:
                    payload = self._payload(article)
                    session.execute_write(
                        self._upsert_paper_tx,
                        payload=payload,
                    )
            logger.info("Neo4j indexed %d articles", len(articles))
            return len(articles)
        except Exception as exc:
            logger.error("Neo4j upsert failed: %s", exc)
            raise Neo4jStoreError(f"Neo4j upsert failed: {exc}") from exc

    @staticmethod
    def _upsert_paper_tx(tx: Any, payload: dict[str, Any]) -> None:
        """Transactional Cypher: MERGE paper + authors + journal."""
        authors = payload.get("authors", []) or []
        author_names = [a.get("name") or a.get("last_name") for a in authors]
        author_names = [n for n in author_names if n]

        tx.run(
            """
            MERGE (p:Paper {pmid: $pmid})
            SET p.title = $title,
                p.abstract = $abstract,
                p.journal = $journal,
                p.year = $year,
                p.doi = $doi
            """,
            pmid=payload["pmid"],
            title=payload.get("title", "") or "",
            abstract=payload.get("abstract", "") or "",
            journal=payload.get("journal", "") or "",
            year=payload.get("year", ""),
            doi=payload.get("doi", "") or "",
        )

        if author_names:
            tx.run(
                """
                UNWIND $names AS name
                MERGE (a:Author {name: name})
                WITH a, $pmid AS pmid
                MATCH (p:Paper {pmid: pmid})
                MERGE (a)-[:AUTHORED]->(p)
                """,
                names=author_names,
                pmid=payload["pmid"],
            )

        journal = payload.get("journal", "") or ""
        if journal:
            tx.run(
                """
                MERGE (j:Journal {name: $journal})
                WITH j, $pmid AS pmid
                MATCH (p:Paper {pmid: pmid})
                MERGE (p)-[:PUBLISHED_IN]->(j)
                """,
                journal=journal,
                pmid=payload["pmid"],
            )

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def related_papers(self, pmid: str, limit: int = 10) -> list[dict]:
        """Return papers sharing authors or journals with the given PMID.

        Ranked by the number of shared nodes (overlap count).
        """
        if not pmid:
            return []
        cypher = """
            MATCH (p:Paper {pmid: $pmid})-[:AUTHORED|PUBLISHED_IN]-(shared)
                  -[:AUTHORED|PUBLISHED_IN]-(other:Paper)
            WHERE other.pmid <> $pmid
            WITH other, count(*) AS overlap
            RETURN other.pmid AS pmid,
                   other.title AS title,
                   overlap
            ORDER BY overlap DESC, other.pmid
            LIMIT $limit
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, pmid=pmid, limit=int(limit))
                rows = [
                    {
                        "pmid": record["pmid"],
                        "title": record["title"] or "",
                        "overlap": int(record["overlap"]),
                    }
                    for record in result
                ]
            return rows
        except Exception as exc:
            logger.warning("Neo4j related_papers failed: %s", exc)
            raise Neo4jStoreError(f"Neo4j related_papers failed: {exc}") from exc

    def subgraph(self, pmid: str, limit: int = 10) -> dict:
        """Return nodes + links centered on a paper for graph visualization.

        Builds a 1-hop subgraph: the center paper, its authors and journal,
        related papers (sharing authors/journals), and the shared nodes that
        connect them. Returns ``{"pmid", "nodes", "links"}`` where node ids
        are ``paper:<pmid>`` / ``author:<name>`` / ``journal:<name>``.
        """
        related = self.related_papers(pmid, limit)
        nodes: dict[str, dict] = {}
        links: list[dict] = []

        def add_node(node_id: str, node_type: str, label: str, paper_pmid: str = "") -> None:
            if node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "type": node_type,
                    "label": label or "",
                    "pmid": paper_pmid,
                }

        def add_link(source: str, target: str, link_type: str) -> None:
            links.append({"source": source, "target": target, "type": link_type})

        try:
            with self.driver.session(database=self.database) as session:
                center = session.run(
                    """
                    MATCH (p:Paper {pmid: $pmid})
                    OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
                    OPTIONAL MATCH (p)-[:PUBLISHED_IN]->(j:Journal)
                    RETURN p.title AS title,
                           collect(DISTINCT a.name) AS authors,
                           collect(DISTINCT j.name) AS journals
                    """,
                    pmid=pmid,
                ).single()
                title = ""
                authors: list[str] = []
                journals: list[str] = []
                if center is not None:
                    title = center["title"] or ""
                    authors = [n for n in (center["authors"] or []) if n]
                    journals = [n for n in (center["journals"] or []) if n]
                add_node(f"paper:{pmid}", "paper", title or pmid, pmid)
                for name in authors:
                    add_node(f"author:{name}", "author", name)
                    add_link(f"paper:{pmid}", f"author:{name}", "AUTHORED")
                for name in journals:
                    add_node(f"journal:{name}", "journal", name)
                    add_link(f"paper:{pmid}", f"journal:{name}", "PUBLISHED_IN")

                for row in related:
                    other_pmid = row["pmid"]
                    add_node(
                        f"paper:{other_pmid}",
                        "paper",
                        row.get("title") or other_pmid,
                        other_pmid,
                    )
                    add_link(f"paper:{pmid}", f"paper:{other_pmid}", "RELATED")
                    shared = session.run(
                        """
                        MATCH (p:Paper {pmid: $pmid})-[:AUTHORED|PUBLISHED_IN]-(shared)
                              -[:AUTHORED|PUBLISHED_IN]-(other:Paper {pmid: $other})
                        RETURN labels(shared)[0] AS stype, shared.name AS sname
                        """,
                        pmid=pmid,
                        other=other_pmid,
                    )
                    for row_shared in shared:
                        stype = row_shared["stype"]
                        sname = row_shared["sname"]
                        shared_id = f"{str(stype).lower()}:{sname}"
                        if shared_id in nodes:
                            link_type = "AUTHORED" if stype == "Author" else "PUBLISHED_IN"
                            add_link(shared_id, f"paper:{other_pmid}", link_type)
        except Exception as exc:
            logger.warning("Neo4j subgraph failed: %s", exc)
            raise Neo4jStoreError(f"Neo4j subgraph failed: {exc}") from exc

        return {"pmid": pmid, "nodes": list(nodes.values()), "links": links}

    # ------------------------------------------------------------------
    # Article helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _payload(article: Any) -> dict[str, Any]:
        """Normalize an article (PubMedArticle or dict) to a graph payload."""
        if isinstance(article, dict):
            data = dict(article)
        elif hasattr(article, "to_dict"):
            data = article.to_dict()
        else:
            data = {}

        payload = {
            "pmid": str(data.get("pmid", "")),
            "title": data.get("title", "") or "",
            "abstract": data.get("abstract", "") or "",
            "journal": data.get("journal", "") or "",
            "doi": data.get("doi", "") or "",
        }
        payload["year"] = _extract_year(str(data.get("publish_date", "")))
        payload["authors"] = list(data.get("authors", []) or [])
        return payload

