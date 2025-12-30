from __future__ import annotations

from typing import List

import networkx as nx


def apply_gleaning(g: nx.MultiDiGraph) -> List[str]:
    """Rule-based gleaning: infer extra edges from existing patterns.

    Returns a list of human-readable logs.
    """

    logs: List[str] = []

    # If a GROUP hosted an EVENT and EVENT held_at a LOCATION, infer GROUP active_in LOCATION.
    for group_id, event_id, key, data in g.edges(keys=True, data=True):
        if data.get("type") != "hosted":
            continue
        for _, loc_id, k2, d2 in g.out_edges(event_id, keys=True, data=True):
            if d2.get("type") != "held_at":
                continue
            if not g.has_edge(group_id, loc_id, key="active_in"):
                g.add_edge(group_id, loc_id, key="active_in", type="active_in", inferred=True)
                logs.append(f"inferred active_in: {group_id} -> {loc_id}")

    # If PERSON attended EVENT and EVENT held_at LOCATION, infer PERSON visited LOCATION.
    for person_id, event_id, key, data in g.edges(keys=True, data=True):
        if data.get("type") != "attended":
            continue
        for _, loc_id, k2, d2 in g.out_edges(event_id, keys=True, data=True):
            if d2.get("type") != "held_at":
                continue
            if not g.has_edge(person_id, loc_id, key="visited"):
                g.add_edge(person_id, loc_id, key="visited", type="visited", inferred=True)
                logs.append(f"inferred visited: {person_id} -> {loc_id}")

    return logs
