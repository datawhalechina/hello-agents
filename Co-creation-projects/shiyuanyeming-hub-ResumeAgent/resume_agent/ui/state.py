"""Serializable browser-session selection state."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional
from uuid import UUID


class Workspace(str, Enum):
    MENTOR = "mentor"
    EVIDENCE = "evidence"
    VERSIONS = "versions"
    PREVIEW = "preview"


def _uuid(value: object) -> Optional[UUID]:
    try:
        return UUID(str(value)) if value else None
    except (TypeError, ValueError):
        return None


@dataclass
class WorkspaceState:
    fact_base_id: Optional[UUID] = None
    active_experience_id: Optional[UUID] = None
    selected_version_id: Optional[UUID] = None
    session_ids_by_experience: dict[UUID, UUID] = field(default_factory=dict)
    workspace: Workspace = Workspace.MENTOR

    def to_query_params(self) -> dict[str, str]:
        result = {"workspace": self.workspace.value}
        if self.fact_base_id:
            result["fact_base"] = str(self.fact_base_id)
        if self.active_experience_id:
            result["experience"] = str(self.active_experience_id)
        if self.selected_version_id:
            result["version"] = str(self.selected_version_id)
        return result

    @classmethod
    def from_query_params(cls, params: Mapping[str, object]) -> "WorkspaceState":
        try:
            workspace = Workspace(str(params.get("workspace", "mentor")))
        except ValueError:
            workspace = Workspace.MENTOR
        return cls(
            fact_base_id=_uuid(params.get("fact_base")),
            active_experience_id=_uuid(params.get("experience")),
            selected_version_id=_uuid(params.get("version")),
            workspace=workspace,
        )
