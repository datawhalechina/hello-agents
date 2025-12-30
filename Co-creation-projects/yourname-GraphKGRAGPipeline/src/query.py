from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .graph_store import GraphStore


@dataclass
class QueryEngine:
    store: GraphStore

    def find_by_name(self, name_substr: str) -> List[str]:
        q = name_substr.strip()
        if not q:
            return []
        out = []
        for nid, data in self.store.g.nodes(data=True):
            name = str(data.get("name", ""))
            if q in name:
                out.append(nid)
        return out

    def neighborhood(self, node_id: str, hops: int = 1) -> Dict[str, List[Tuple[str, str]]]:
        g = self.store.g
        if node_id not in g:
            return {"nodes": [], "edges": []}

        nodes = {node_id}
        frontier = {node_id}
        for _ in range(max(1, hops)):
            nxt = set()
            for n in frontier:
                nxt.update(v for _, v in g.out_edges(n))
                nxt.update(u for u, _ in g.in_edges(n))
            nxt -= nodes
            nodes |= nxt
            frontier = nxt

        edges: List[Tuple[str, str, str]] = []
        for u, v, key, data in g.edges(keys=True, data=True):
            if u in nodes and v in nodes:
                edges.append((u, v, str(data.get("type", key))))

        return {
            "nodes": [(n, g.nodes[n].get("name", n)) for n in sorted(nodes)],
            "edges": edges,
        }

    def semantic_search_nodes(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        q = query.strip()
        if not q:
            return []

        texts: List[str] = []
        node_ids: List[str] = []
        for nid, txt in self.store.iter_entity_texts():
            node_ids.append(nid)
            texts.append(txt)

        vec = TfidfVectorizer().fit(texts + [q])
        X = vec.transform(texts)
        qv = vec.transform([q])
        sims = cosine_similarity(qv, X)[0]

        pairs = sorted(zip(node_ids, sims), key=lambda x: x[1], reverse=True)
        return [(nid, float(score)) for nid, score in pairs[:top_k]]
