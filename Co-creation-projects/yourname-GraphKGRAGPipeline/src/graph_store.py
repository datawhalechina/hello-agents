from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

import networkx as nx

from .schema import Entity, ExtractedGraph, Relation


@dataclass
class GraphStore:
    g: nx.MultiDiGraph

    @staticmethod
    def from_extracted(extracted: ExtractedGraph) -> "GraphStore":
        g = nx.MultiDiGraph()
        for e in extracted.entities:
            g.add_node(e.id, type=e.type.value, name=e.name, **(e.props or {}))
        for r in extracted.relations:
            g.add_edge(r.source, r.target, key=r.type, type=r.type, **(r.props or {}))
        return GraphStore(g=g)

    def to_lpg_json(self) -> Dict[str, Any]:
        nodes = []
        for node_id, data in self.g.nodes(data=True):
            nodes.append({"id": node_id, **data})

        edges = []
        for u, v, key, data in self.g.edges(keys=True, data=True):
            edges.append({"source": u, "target": v, "key": key, **data})

        return {"nodes": nodes, "edges": edges}

    def dump_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_lpg_json(), f, ensure_ascii=False, indent=2)

    def iter_entity_texts(self) -> Iterable[Tuple[str, str]]:
        for node_id, data in self.g.nodes(data=True):
            parts: List[str] = []
            parts.append(str(data.get("name", "")))
            parts.append(str(data.get("type", "")))
            for k, v in data.items():
                if k in {"name", "type"}:
                    continue
                parts.append(f"{k}:{v}")
            yield node_id, " ".join(p for p in parts if p)
