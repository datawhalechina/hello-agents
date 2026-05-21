
from __future__ import annotations

import json
import logging
from typing import Any

from hello_agents import SimpleAgent

from ..utils import parse_llm_json
from ..services.llm.agent_config import papergraph_agent_config
from .base import BaseAgent
from .prompts.knowledge_graph import REL_PROMPT

logger = logging.getLogger(__name__)

class KnowledgeGraphAgent(BaseAgent):
    def __init__(
        self,
        *,
        agent: SimpleAgent | None = None,
        min_score: float = 0.55,
        max_edges: int = 12,
        chunk_size: int = 20,
    ) -> None:
        super().__init__()
        self.min_score = min_score
        self.max_edges = max_edges
        self.chunk_size = chunk_size
        self._agent = agent or SimpleAgent(
            name="papergraph_kg_rel",
            llm=self.llm,
            system_prompt=REL_PROMPT,
            config=papergraph_agent_config(),
        )

    def _candidate_id(self, paper: dict[str, Any]) -> int | None:
        for key in ("paper_id", "id", "target_paper_id"):
            try:
                value = int(paper.get(key))
                if value > 0:
                    return value
            except (TypeError, ValueError):
                continue
        return None

    def _compact_paper(self, paper: dict[str, Any]) -> dict[str, Any]:
        out = {
            "paper_id": self._candidate_id(paper),
            "title": self._clip(paper.get("title"), 300),
            "abstract": self._clip(paper.get("abstract"), 2000),
            "keywords": list((paper.get("keywords") or [])[:12]),
            "source": paper.get("source"),
            "year": paper.get("year"),
            "category": paper.get("category"),
            "pdf_excerpt": self._clip(paper.get("pdf_excerpt"), 1200),
            "related_work_excerpt": self._clip(paper.get("related_work_excerpt"), 1200),
        }
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}

    def _validate_edges(self, edges: Any, allowed_ids: set[int]) -> list[dict[str, Any]]:
        if not isinstance(edges, list):
            raise ValueError("edges is not a list")
        best: dict[int, dict[str, Any]] = {}
        for e in edges:
            if not isinstance(e, dict):
                continue
            try:
                tid = int(e.get("target_paper_id"))
                score = float(e.get("score") or 0.0)
            except Exception:
                continue
            if tid not in allowed_ids or score < self.min_score:
                continue
            relation = str(e.get("relation") or "").strip()
            if not relation:
                continue
            edge = {"target_paper_id": tid, "relation": relation,
                    "score": max(0.0, min(1.0, score)),
                    "evidence": str(e.get("evidence") or "").strip()[:80]}
            if tid not in best or score > best[tid]["score"]:
                best[tid] = edge
        return sorted(best.values(), key=lambda x: x["score"], reverse=True)

    def _chunks(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        return [items[i : i + self.chunk_size] for i in range(0, len(items), self.chunk_size)]

    def infer_edges(
        self, *, new_paper: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        compact_new = self._compact_paper(new_paper)

        compact_candidates: list[dict[str, Any]] = []
        for c in candidates:
            tid = self._candidate_id(c)
            if tid is None:
                continue
            item = self._compact_paper(c)
            item["paper_id"] = tid
            compact_candidates.append(item)

        if not compact_candidates:
            return [], None

        merged: dict[int, dict[str, Any]] = {}

        for chunk in self._chunks(compact_candidates):
            payload = {"new_paper": compact_new, "candidates": chunk}
            try:
                raw = self._agent.run(json.dumps(payload, ensure_ascii=False))
            except Exception as exc:
                logger.exception("kg_llm_run_failed")
                raise RuntimeError("kg_llm_run_failed") from exc

            data = parse_llm_json(raw)
            if data is None:
                raise ValueError("kg_llm_parse_failed")

            try:
                valid_edges = self._validate_edges(
                    data.get("edges"),
                    allowed_ids={int(x["paper_id"]) for x in chunk},
                )
            except Exception as exc:
                raise ValueError("kg_edge_validation_failed") from exc

            for edge in valid_edges:
                tid = edge["target_paper_id"]
                if tid not in merged or edge["score"] > merged[tid]["score"]:
                    merged[tid] = edge

        edges = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[: self.max_edges]

        try:
            from ..services.memory.agent_memory import get_agent_memory

            am = get_agent_memory()
            title = str(new_paper.get("title") or "")[:120]
            am.add(agent_name="knowledge_graph", content=f"关系抽取：{title}", memory_type="working", importance=0.45, shared=False)
            if edges:
                am.add(
                    agent_name="knowledge_graph",
                    content=f"关系抽取要点：top_relation={edges[0].get('relation')} score={edges[0].get('score')}",
                    memory_type="working",
                    importance=0.5,
                    shared=True,
                )
        except Exception:
            logger.debug("kg_memory_write_failed", exc_info=True)
        return edges, None
