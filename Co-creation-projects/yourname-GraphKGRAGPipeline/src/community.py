from __future__ import annotations

import json
from typing import Dict, List

import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities

from .llm import LLMConfig


def detect_communities(g: nx.MultiDiGraph) -> List[List[str]]:
    undirected = nx.Graph()
    undirected.add_nodes_from(g.nodes(data=True))
    for u, v, data in g.edges(data=True):
        undirected.add_edge(u, v, weight=1.0)

    if undirected.number_of_nodes() == 0:
        return []

    communities = greedy_modularity_communities(undirected)
    return [sorted(list(c)) for c in communities]


def summarize_community_heuristic(g: nx.MultiDiGraph, node_ids: List[str]) -> str:
    names = [g.nodes[n].get("name", n) for n in node_ids]
    types = [g.nodes[n].get("type", "") for n in node_ids]

    head = "、".join(names[:8]) + ("..." if len(names) > 8 else "")
    type_stat: Dict[str, int] = {}
    for t in types:
        type_stat[t] = type_stat.get(t, 0) + 1

    top_types = sorted(type_stat.items(), key=lambda x: x[1], reverse=True)
    type_part = ", ".join([f"{t}:{c}" for t, c in top_types if t])
    return f"社区包含节点：{head}（类型分布：{type_part}）"


def build_hierarchy_summary(
    g: nx.MultiDiGraph,
    communities: List[List[str]],
    llm: LLMConfig,
) -> Dict[str, str]:
    summary: Dict[str, str] = {}

    for idx, nodes in enumerate(communities):
        key = str(idx)
        summary[key] = summarize_community_heuristic(g, nodes)

    # Top-level summary: simple stitching.
    top = [f"- 社区{idx}: {summary[str(idx)]}" for idx in range(len(communities))]
    summary["_top"] = "\n".join(top) if top else "(无社区)"
    return summary


def dump_communities(path: str, communities: List[List[str]], node_to_community: Dict[str, int]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"communities": communities, "node_to_community": node_to_community},
            f,
            ensure_ascii=False,
            indent=2,
        )
