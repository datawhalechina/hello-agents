"""Build a conservative temporal graph without inferring causation from order."""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from app.resolution.projects import canonical_name, resolve_projects, stable_id
from app.ordering import fact_order_key
from app.schemas import (
    EvidenceReference, Project, StandardMessage, WorkFact, WorkflowEdge,
    WorkflowNode, WorkflowUpdateProposal,
)
from app.workflow.verifier import fact_verification_errors, message_index, verify_references


RELATION_MARKERS: dict[str, tuple[str, ...]] = {
    "depends_on": ("依赖于", "依赖", "取决于", "依靠", "depends on", "requires"),
    "blocks": ("阻塞了", "阻塞", "阻挡", "blocks", "block", "blocking"),
    "resolves": ("解决了", "解决", "修复了", "修复", "resolves", "resolve", "fixes"),
    "produces": ("交付了", "交付", "产出了", "产出", "生成", "produces", "produce", "delivers"),
    "revises": ("返工", "重做", "修订", "修改", "调整", "revises", "revise", "rework"),
    "branches_to": ("分支到", "分支为", "分支", "分流到", "分流", "branches to", "branch to", "branches", "split"),
    "parallel_with": ("并行执行", "并行于", "并行", "同时开展", "parallel with", "parallel", "concurrent"),
}


def build_workflow(
    facts: list[WorkFact],
    messages: list[StandardMessage],
    existing_projects: list[Project] | None = None,
) -> WorkflowUpdateProposal:
    index = message_index(messages)
    warnings: list[str] = []
    unique: dict[str, WorkFact] = {}
    conflicting_ids: set[str] = set()
    for fact in facts:
        if fact.id in unique and unique[fact.id] != fact:
            conflicting_ids.add(fact.id)
        else:
            unique[fact.id] = fact
    checked: list[WorkFact] = []
    for original in unique.values():
        fact = original.model_copy(deep=True)
        errors = fact_verification_errors(fact, index)
        if fact.id in conflicting_ids:
            errors.append("conflicting duplicate fact ID")
        fact.verified = not errors
        if errors:
            warnings.append(f"Fact {fact.id}: {'; '.join(errors)}; excluded from graph")
        checked.append(fact)

    # Invalid evidence must not introduce a newly discovered project.
    valid, projects, resolution_warnings = resolve_projects(
        [fact for fact in checked if fact.verified], existing_projects
    )
    warnings.extend(resolution_warnings)
    invalid = [fact.model_copy(update={"project_id": None}) for fact in checked if not fact.verified]
    resolved = sorted([*valid, *invalid], key=_sort_fact)
    graph_facts = {fact.id: fact for fact in valid if fact.project_id is not None}
    nodes = [
        WorkflowNode(
            id=stable_id("node", fact.project_id or "", fact.id),
            project_id=fact.project_id or "", kind=fact.kind,
            label=fact.summary, status=fact.status, fact_ids=[fact.id],
            evidence=fact.evidence, occurred_at=fact.occurred_at, verified=True,
        )
        for fact in sorted(graph_facts.values(), key=_sort_fact)
    ]
    by_fact = {node.fact_ids[0]: node for node in nodes}
    edges: dict[tuple[str, str, str], WorkflowEdge] = {}
    grouped: dict[str, list[WorkFact]] = defaultdict(list)
    for fact in graph_facts.values():
        grouped[fact.project_id or ""].append(fact)

    for edge in build_chronological_edges(list(graph_facts.values()), nodes):
        edges[(edge.source, edge.target, edge.relation)] = edge

    for project_facts in grouped.values():
        project_facts.sort(key=_sort_fact)
        entities: dict[str, list[WorkFact]] = defaultdict(list)
        for fact in project_facts:
            if fact.entity_key:
                entities[canonical_name(fact.entity_key)].append(fact)
        for fact in project_facts:
            relations = fact.attributes.get("relations", [])
            if not isinstance(relations, list):
                warnings.append(f"Fact {fact.id}: malformed relations ignored")
                continue
            for specification in relations:
                edge, error = _explicit_edge(fact, specification, graph_facts, entities, by_fact, index)
                if error:
                    warnings.append(error)
                elif edge:
                    edges[(edge.source, edge.target, edge.relation)] = edge

    ordered_edges = sorted(edges.values(), key=lambda edge: (edge.project_id, edge.source, edge.target, edge.relation))
    if _has_dependency_cycle(ordered_edges):
        warnings.append("Explicit dependency cycle detected; retained as a source-supported cycle requiring human review")
    return WorkflowUpdateProposal(projects=projects, facts=resolved, nodes=nodes, edges=ordered_edges, warnings=warnings)


def _sort_fact(fact: WorkFact) -> tuple[float, str, str, int, str]:
    return fact_order_key(fact)


def build_chronological_edges(facts: list[WorkFact], nodes: list[WorkflowNode]) -> list[WorkflowEdge]:
    """Re-link retained observations without re-resolving projects or claims."""
    by_fact = {key: node for node in nodes for key in node.fact_ids}
    grouped: dict[str, list[WorkFact]] = defaultdict(list)
    for fact in facts:
        if fact.id in by_fact and fact.project_id:
            grouped[fact.project_id].append(fact)
    edges = []
    for project_facts in grouped.values():
        previous: WorkFact | None = None
        for fact in sorted(project_facts, key=_sort_fact):
            if previous and previous.occurred_at < fact.occurred_at and by_fact[previous.id].id != by_fact[fact.id].id:
                edges.append(_make_edge(previous, fact, "precedes", by_fact, _combine_evidence(previous.evidence, fact.evidence),
                                        "Observed source chronology only; no causal dependency implied.", 1.0))
            previous = fact
    return edges


def _explicit_edge(
    fact: WorkFact,
    specification: Any,
    graph_facts: dict[str, WorkFact],
    entities: dict[str, list[WorkFact]],
    by_fact: dict[str, WorkflowNode],
    index: dict[tuple[str, str], StandardMessage],
) -> tuple[WorkflowEdge | None, str | None]:
    prefix = f"Fact {fact.id}: "
    if not isinstance(specification, dict):
        return None, prefix + "non-object relation ignored"
    relation = specification.get("relation")
    if not isinstance(relation, str) or relation not in RELATION_MARKERS:
        return None, prefix + f"unsupported explicit relation {relation!r}"
    target_id = specification.get("target_fact_id")
    target_key = specification.get("target_entity_key")
    target = graph_facts.get(target_id) if isinstance(target_id, str) else None
    if target_id and target is None:
        return None, prefix + "dangling relation target ignored"
    if target is None and isinstance(target_key, str):
        candidates = [item for item in entities.get(canonical_name(target_key), []) if item.id != fact.id]
        prior = [item for item in candidates if item.occurred_at <= fact.occurred_at]
        candidates = sorted(prior or candidates, key=_sort_fact, reverse=bool(prior))
        if candidates:
            if len(candidates) > 1 and candidates[0].occurred_at == candidates[1].occurred_at:
                return None, prefix + "ambiguous target entity occurrences; relation ignored"
            target = candidates[0]
    if target is None:
        return None, prefix + "unresolved relation target ignored"
    if target.project_id != fact.project_id:
        return None, prefix + "cross-project relation ignored"
    if target.id == fact.id:
        return None, prefix + "self relation ignored"
    quote = specification.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        return None, prefix + "relation lacks literal supporting quote"
    references = [
        EvidenceReference(message_id=item.message_id, source_id=item.source_id, quote=quote)
        for item in fact.evidence if quote in item.quote
    ]
    if isinstance(target_key, str) and target.entity_key and canonical_name(target_key) != canonical_name(target.entity_key):
        return None, prefix + "relation target key conflicts with target fact identity"
    target_mentions = [value for value in [target.entity_key, target.summary] if isinstance(value, str) and value]
    normalized_quote = canonical_name(quote)
    if not references or not verify_references(references, index):
        return None, prefix + "relation quote is absent from the source fact evidence"
    if not any(marker in normalized_quote for marker in RELATION_MARKERS[relation]):
        return None, prefix + "relation quote has no explicit relation marker"
    if not any(canonical_name(value) in normalized_quote for value in target_mentions):
        return None, prefix + "relation quote does not identify its target"
    if not _supports_relation(normalized_quote, relation, target_mentions):
        return None, prefix + "relation phrase is negated or does not directly name the target"
    # A report of fixing or reworking something cannot precede the observed
    # target occurrence. Dependencies/branches/deliveries may name future work.
    if relation in {"resolves", "revises"} and fact.occurred_at < target.occurred_at:
        return None, prefix + "relation has inconsistent occurrence order"
    edge = _make_edge(fact, target, relation, by_fact, _combine_evidence(references, target.evidence),
                      "Explicit relation phrase and target identity in source evidence; semantic review remains pending.",
                      min(fact.confidence, target.confidence))
    return edge, None


def _combine_evidence(*groups: list[EvidenceReference]) -> list[EvidenceReference]:
    references: dict[tuple[str, str, str], EvidenceReference] = {}
    for group in groups:
        for item in group:
            references[(item.source_id, item.message_id, item.quote)] = item
    return [references[key] for key in sorted(references)]


def _make_edge(
    source: WorkFact, target: WorkFact, relation: str,
    by_fact: dict[str, WorkflowNode], evidence: list[EvidenceReference],
    rationale: str, confidence: float,
) -> WorkflowEdge:
    source_node, target_node = by_fact[source.id], by_fact[target.id]
    return WorkflowEdge(
        id=stable_id("edge", source_node.id, target_node.id, relation),
        project_id=source.project_id or "", source=source_node.id,
        target=target_node.id, relation=relation, evidence=evidence,
        confidence=confidence, verified=True, rationale=rationale,
    )


def _has_dependency_cycle(edges: list[WorkflowEdge]) -> bool:
    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = defaultdict(int)
    for edge in edges:
        if edge.relation == "depends_on":
            adjacency[edge.source].append(edge.target)
            indegree.setdefault(edge.source, 0)
            indegree[edge.target] += 1
    ready = [node for node, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for target in adjacency.get(node, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return visited != len(indegree)


def _supports_relation(quote: str, relation: str, target_mentions: list[str]) -> bool:
    """Require an enumerated phrase followed by target, ignoring punctuation.

    Full markers include bounded grammatical forms such as 分支到 and 解决了,
    matching the extractor's explicit-relation protocol. Arbitrary text between
    a phrase and its target remains unsupported. Negated statements are not
    positive relation evidence and remain facts for human inspection.
    """
    for marker in RELATION_MARKERS[relation]:
        for match in re.finditer(re.escape(marker), quote):
            prefix = quote[max(0, match.start() - 14):match.start()]
            if re.search(r"(?:不|不再|不必|不要|不能|不会|不需要|无需|无须|无法|未|未曾|未能|尚未|并非|没有|not\s+|never\s+)\s*$", prefix):
                continue
            suffix = quote[match.end():].lstrip(" \t:：、,，「」『』\"'“”[]【】")
            if any(suffix.startswith(canonical_name(target)) for target in target_mentions):
                return True
    return False
