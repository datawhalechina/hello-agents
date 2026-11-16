"""Mechanical storage projection of model-authored conclusions; no inference."""
import hashlib

from ..schemas import ModelWorkflowReport, Project, WorkFact, WorkflowEdge, WorkflowNode, WorkflowUpdateProposal


def report_proposal(report: ModelWorkflowReport, messages, source_id: str) -> WorkflowUpdateProposal:
    originals = {m.id: m for m in messages}

    def identity(kind, value):
        return kind + '_' + hashlib.sha256((source_id + '\0' + value).encode()).hexdigest()[:24]

    def evidence_time(evidence):
        return max(originals[e.message_id].timestamp for e in evidence)

    projects = [Project(id=identity('model_project', w.id), name=w.name, description=w.summary,
                        status=w.status, source_id=source_id, analysis_mode='model',
                        created_at=evidence_time(w.evidence)) for w in report.workstreams]
    by_id = {w.id: p for w, p in zip(report.workstreams, projects)}
    facts, nodes, edges = [], [], []
    for step in report.steps:
        project = by_id.get(step.workstream_id)
        stamp = step.occurred_at or evidence_time(step.evidence)
        fact = WorkFact(id=identity('model_fact', step.id), kind=step.kind, summary=step.title,
                        project_id=project.id if project else None, project_hint=project.name if project else None,
                        actor=step.actor, status=step.status, occurred_at=stamp, evidence=step.evidence,
                        verified=True, attributes={'analysis_mode': 'model', 'model_step_id': step.id,
                        'assigned_actor_names': [step.actor] if step.actor else [], 'time_is_evidence_time': step.occurred_at is None})
        facts.append(fact)
        if project:
            nodes.append(WorkflowNode(id=identity('model_node', step.id), project_id=project.id,
                         kind=step.kind, label=step.title, status=step.status, fact_ids=[fact.id],
                         evidence=step.evidence, occurred_at=stamp, verified=True))
    steps = {s.id: s for s in report.steps}
    for index, relation in enumerate(report.relations):
        project = by_id[steps[relation.source_step_id].workstream_id]
        edges.append(WorkflowEdge(id=identity('model_edge', str(index)), project_id=project.id,
                     source=identity('model_node', relation.source_step_id), target=identity('model_node', relation.target_step_id),
                     relation=relation.relation, evidence=relation.evidence, rationale=relation.rationale, verified=True))
    return WorkflowUpdateProposal(projects=projects, facts=facts, nodes=nodes, edges=edges,
                                  warnings=report.uncertainties + report.limitations)
