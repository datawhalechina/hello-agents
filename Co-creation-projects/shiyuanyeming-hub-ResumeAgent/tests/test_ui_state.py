from uuid import UUID

from resume_agent.ui.state import Workspace, WorkspaceState


def test_state_serializes_only_identifiers_and_workspace():
    state = WorkspaceState(
        fact_base_id=UUID("00000000-0000-0000-0000-000000000001"),
        active_experience_id=UUID("00000000-0000-0000-0000-000000000002"),
        selected_version_id=UUID("00000000-0000-0000-0000-000000000003"),
        workspace=Workspace.VERSIONS,
    )

    serialized = state.to_query_params()

    assert serialized == {
        "fact_base": "00000000-0000-0000-0000-000000000001",
        "experience": "00000000-0000-0000-0000-000000000002",
        "version": "00000000-0000-0000-0000-000000000003",
        "workspace": "versions",
    }


def test_state_recovers_from_valid_query_params():
    state = WorkspaceState.from_query_params(
        {
            "fact_base": "00000000-0000-0000-0000-000000000001",
            "workspace": "evidence",
        }
    )

    assert str(state.fact_base_id).endswith("1")
    assert state.workspace is Workspace.EVIDENCE


def test_state_ignores_invalid_query_params():
    state = WorkspaceState.from_query_params(
        {"fact_base": "bad", "workspace": "unknown"}
    )

    assert state.fact_base_id is None
    assert state.workspace is Workspace.MENTOR
