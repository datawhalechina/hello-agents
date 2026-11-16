"""Local source removal projections; no model, filesystem or enterprise writes."""
from ..schemas import WorkFact, WorkflowUpdateProposal


def _has_reference(value, source_id: str) -> bool:
    if isinstance(value, dict):
        if value.get("source_id") == source_id and "message_id" in value:
            return True
        return any(_has_reference(item, source_id) for item in value.values())
    if isinstance(value, list):
        return any(_has_reference(item, source_id) for item in value)
    return False


def fact_uses_source(fact: WorkFact, source_id: str) -> bool:
    return any(ref.source_id == source_id for ref in fact.evidence) or _has_reference(fact.attributes, source_id)


def redact_source(graph: WorkflowUpdateProposal, source_id: str) -> tuple[WorkflowUpdateProposal, set[str], bool]:
    """Remove whole dependent facts; never detach a claim from its provenance."""
    removed = {fact.id for fact in graph.facts if fact_uses_source(fact, source_id)}
    facts = [fact for fact in graph.facts if fact.id not in removed]
    fact_ids = {fact.id for fact in facts}
    nodes = [node for node in graph.nodes if node.fact_ids and all(key in fact_ids for key in node.fact_ids) and not any(ref.source_id == source_id for ref in node.evidence)]
    node_ids = {node.id for node in nodes}
    edges = [edge for edge in graph.edges if edge.source in node_ids and edge.target in node_ids and not any(ref.source_id == source_id for ref in edge.evidence)]
    referenced_projects = {fact.project_id for fact in facts if fact.project_id and fact.verified}
    projects = [project for project in graph.projects if project.id in referenced_projects or (project.analysis_mode == 'model' and project.source_id != source_id)]
    changed = bool(removed) or len(nodes) != len(graph.nodes) or len(edges) != len(graph.edges) or len(projects) != len(graph.projects)
    return WorkflowUpdateProposal(
        facts=facts, nodes=nodes, edges=edges,
        projects=projects,
        warnings=[] if changed else graph.warnings,
    ), removed, changed
