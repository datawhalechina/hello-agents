"""Source-scoped read projections; filters are navigation, not tenant authorization."""
from collections import Counter

from ..schemas import SourceAnalysis, StandardMessage, WorkFact, WorkflowUpdateProposal


def facts_in_source(facts: list[WorkFact], source_id: str | None) -> list[WorkFact]:
    if source_id is None:
        return facts
    return [fact for fact in facts if any(e.source_id == source_id for e in fact.evidence)]


def scoped_graph(graph: WorkflowUpdateProposal, source_id: str | None) -> WorkflowUpdateProposal:
    if source_id is None:
        return graph
    facts = facts_in_source(graph.facts, source_id)
    fact_ids = {fact.id for fact in facts}
    project_ids = {fact.project_id for fact in facts if fact.project_id}
    nodes = [node for node in graph.nodes if any(key in fact_ids for key in node.fact_ids)]
    node_ids = {node.id for node in nodes}
    return WorkflowUpdateProposal(
        projects=[project for project in graph.projects if project.id in project_ids or project.source_id == source_id], facts=facts,
        nodes=nodes, edges=[edge for edge in graph.edges if edge.source in node_ids and edge.target in node_ids],
        warnings=[warning for warning in graph.warnings if not warning.startswith("Fact ") or any(key in warning for key in fact_ids)],
    )


def project_context(graph: WorkflowUpdateProposal, project_id: str):
    own_nodes = {node.id for node in graph.nodes if node.project_id == project_id}
    edges = [edge for edge in graph.edges if (edge.source in own_nodes) != (edge.target in own_nodes)]
    related_ids = {endpoint for edge in edges for endpoint in (edge.source, edge.target)} - own_nodes
    nodes = [node for node in graph.nodes if node.id in related_ids]
    fact_ids = {key for node in nodes for key in node.fact_ids}
    facts = [fact for fact in graph.facts if fact.id in fact_ids]
    return nodes, edges, facts


def source_analysis(source_id: str, messages: list[StandardMessage], graph: WorkflowUpdateProposal) -> SourceAnalysis:
    selected = [m for m in messages if m.source_id == source_id]
    scoped = scoped_graph(graph, source_id)
    types = Counter(_message_kind(message) for message in selected)
    textual = sum(types.get(kind, 0) for kind in ("text", "post", "link", "system"))
    # Additional header/reply evidence supports attribution; it is not another
    # independently extracted observation from that supporting message.
    extracted = {fact.evidence[0].message_id for fact in scoped.facts if fact.evidence[0].source_id == source_id}
    methods: Counter[str] = Counter()
    for fact in scoped.facts:
        attribution = fact.attributes.get("project_attribution")
        method = attribution.get("method") if isinstance(attribution, dict) else None
        methods[str(method or ('model_context' if fact.attributes.get('analysis_mode') == 'model' else "explicit_tag" if fact.project_hint else "unassigned"))] += 1
    return SourceAnalysis(
        source_id=source_id, messages=len(selected), message_types=dict(types), textual_messages=textual,
        attachment_messages=len(selected) - textual,
        reply_messages=sum(bool(m.thread_id or _raw_message(m).get("parent_id") or _raw_message(m).get("root_id")) for m in selected),
        extracted_messages=len(extracted), facts=len(scoped.facts),
        assigned_facts=sum(f.project_id is not None for f in scoped.facts),
        unassigned_facts=sum(f.project_id is None for f in scoped.facts),
        verified_facts=sum(f.verified for f in scoped.facts), pending_review=sum(f.review_status == "pending" for f in scoped.facts),
        projects=len(scoped.projects), nodes=len(scoped.nodes), explicit_edges=sum(e.relation != "precedes" for e in scoped.edges),
        attribution_methods=dict(methods),
        notes=["统计表示提取覆盖和归属情况，不代表语义准确率。", "图片、音视频和附件只保留原始元数据；未读取附件内容。", "未归属事实可在事实审核中查看；项目归属依据保留在事实属性中。", "工作线及归属由接入模型根据上下文判断，仍需人工核对。" if any(p.analysis_mode == 'model' for p in scoped.projects) else "项目候选来自原文字面名称；名称变体未自动认定为同一项目。"],
    )


def _raw_message(message: StandardMessage) -> dict:
    raw = message.metadata.get('raw', {})
    return raw if isinstance(raw, dict) else {}


def _message_kind(message: StandardMessage) -> str:
    imported = message.metadata.get('import', {})
    if isinstance(imported, dict) and isinstance(imported.get('message_kind'), str):
        return imported['message_kind']
    return str(_raw_message(message).get('msg_type', 'text'))
