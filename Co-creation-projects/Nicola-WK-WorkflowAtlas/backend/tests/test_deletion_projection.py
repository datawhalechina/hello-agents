from app.schemas import Project, WorkflowUpdateProposal
from app.services.deletion import redact_source


def test_legacy_empty_project_cleanup_marks_snapshot_as_changed():
    legacy = WorkflowUpdateProposal(projects=[Project(id="legacy-empty", name="虚构旧候选")])
    retained, removed, changed = redact_source(legacy, "synthetic-source")
    assert retained.projects == [] and removed == set() and changed
