"""Conservative project completion rules based on observed, verified records."""
import re

from ..schemas import WorkflowUpdateProposal


def update_project_status(proposal: WorkflowUpdateProposal) -> None:
    for project in proposal.projects:
        if project.analysis_mode == 'model':
            continue
        facts = sorted((f for f in proposal.facts if f.project_id == project.id and f.verified and f.review_status != "rejected"), key=lambda f: (f.occurred_at, f.id))
        markers = [f for f in facts if re.search(r"项目(?:已完成|验收通过|结项)|project (?:completed|closed)", f.summary, re.I) and not re.search(r"未|尚未|不|not\b", f.summary, re.I)]
        project.status = "active"
        if markers:
            terminal = markers[-1]
            later_work = any(f.occurred_at > terminal.occurred_at and f.status in {"planned", "pending", "in_progress", "blocked", "rework"} for f in facts)
            if not later_work:
                project.status = "completed"
