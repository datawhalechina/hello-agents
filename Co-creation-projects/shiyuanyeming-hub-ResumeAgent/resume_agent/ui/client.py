"""Typed, non-retrying HTTP client for the ResumeAgent API."""

from typing import Optional, Sequence, Type, TypeVar, Union
from uuid import UUID

import httpx
from pydantic import BaseModel

from resume_agent.application.interview_service import (
    InterviewTurn,
    MentorQuestion,
    UnknownOutcome,
)
from resume_agent.domain.models import (
    CandidateProfile,
    CareerFactBase,
    CareerTarget,
    InterviewSession,
    QualityDimension,
    ResumeVersion,
)
from resume_agent.domain.quality import QualityReport
from resume_agent.rendering.exporters import RenderFormat
from resume_agent.rendering.models import RenderedResume


class ResumeApiError(RuntimeError):
    def __init__(
        self,
        detail: str,
        *,
        status_code: Optional[int] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.retryable = retryable


class ApiNotFound(ResumeApiError): ...
class ApiConflict(ResumeApiError): ...
class ApiValidationError(ResumeApiError): ...
class InvalidAgentOutput(ResumeApiError): ...
class AgentUnavailable(ResumeApiError): ...
class ApiTransportError(ResumeApiError): ...


ERROR_TYPES = {
    404: ApiNotFound,
    409: ApiConflict,
    422: ApiValidationError,
    502: InvalidAgentOutput,
    503: AgentUnavailable,
}

ModelT = TypeVar("ModelT", bound=BaseModel)
Identifier = Union[str, UUID]


class HttpResumeAgentClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise ApiTransportError(str(error), retryable=True) from error
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            if isinstance(detail, list):
                detail = "; ".join(str(item) for item in detail)
            error_type = ERROR_TYPES.get(response.status_code, ResumeApiError)
            raise error_type(str(detail), status_code=response.status_code)
        if response.status_code == 204:
            return None
        return response.json()

    def _model(self, model: Type[ModelT], method: str, path: str, **kwargs) -> ModelT:
        return model.model_validate(self._request(method, path, **kwargs))

    def health(self) -> bool:
        return self._request("GET", "/health").get("status") == "ok"

    def list_fact_bases(self) -> list[CareerFactBase]:
        return [CareerFactBase.model_validate(item) for item in self._request("GET", "/fact-bases")]

    def create_fact_base(self, target: Optional[CareerTarget] = None) -> CareerFactBase:
        payload = {"target": (target or CareerTarget()).model_dump(mode="json")}
        return self._model(CareerFactBase, "POST", "/fact-bases", json=payload)

    def get_fact_base(self, fact_base_id: Identifier) -> CareerFactBase:
        return self._model(CareerFactBase, "GET", f"/fact-bases/{fact_base_id}")

    def add_experience(self, fact_base_id: Identifier, *, organization: str, role: str) -> CareerFactBase:
        return self._model(
            CareerFactBase, "POST", f"/fact-bases/{fact_base_id}/experiences",
            json={"organization": organization, "role": role},
        )

    def update_profile(
        self,
        fact_base_id: Identifier,
        profile: CandidateProfile,
    ) -> CareerFactBase:
        return self._model(
            CareerFactBase,
            "PATCH",
            f"/fact-bases/{fact_base_id}/profile",
            json=profile.model_dump(mode="json"),
        )

    def get_experience_quality(self, fact_base_id: Identifier, experience_id: Identifier) -> QualityReport:
        return self._model(QualityReport, "GET", f"/fact-bases/{fact_base_id}/experiences/{experience_id}/quality")

    def create_session(self, fact_base_id: Identifier, experience_id: Identifier) -> InterviewSession:
        return self._model(InterviewSession, "POST", "/sessions", json={"fact_base_id": str(fact_base_id), "active_experience_id": str(experience_id)})

    def list_sessions(self, fact_base_id: Identifier, experience_id: Optional[Identifier] = None) -> list[InterviewSession]:
        params = {"experience_id": str(experience_id)} if experience_id else None
        payload = self._request("GET", f"/fact-bases/{fact_base_id}/sessions", params=params)
        return [InterviewSession.model_validate(item) for item in payload]

    def get_session(self, session_id: Identifier) -> InterviewSession:
        return self._model(InterviewSession, "GET", f"/sessions/{session_id}")

    def current_question(self, session_id: Identifier) -> Optional[MentorQuestion]:
        payload = self._request("GET", f"/sessions/{session_id}/current-question")
        return MentorQuestion.model_validate(payload) if payload else None

    def answer(self, session_id: Identifier, message: str) -> InterviewTurn:
        return self._model(InterviewTurn, "POST", f"/sessions/{session_id}/answers", json={"message": message})

    def confirm_proposal(self, session_id: Identifier, proposal_id: Identifier) -> InterviewTurn:
        return self._model(InterviewTurn, "POST", f"/sessions/{session_id}/proposals/{proposal_id}/confirm")

    def reject_proposal(self, session_id: Identifier, proposal_id: Identifier) -> InterviewSession:
        return self._model(InterviewSession, "POST", f"/sessions/{session_id}/proposals/{proposal_id}/reject")

    def record_unknown(self, session_id: Identifier, dimension: QualityDimension) -> UnknownOutcome:
        return self._model(UnknownOutcome, "POST", f"/sessions/{session_id}/unknown", json={"dimension": dimension.value})

    def list_versions(self, fact_base_id: Identifier) -> list[ResumeVersion]:
        return [ResumeVersion.model_validate(item) for item in self._request("GET", f"/fact-bases/{fact_base_id}/versions")]

    def create_version(self, fact_base_id: Identifier, *, name: str, target_role: str = "", company: str = "", raw_jd: str = "", locale: str = "zh", selected_experience_ids: Sequence[Identifier] = ()) -> ResumeVersion:
        return self._model(ResumeVersion, "POST", f"/fact-bases/{fact_base_id}/versions", json={"name": name, "target_role": target_role, "company": company, "raw_jd": raw_jd, "locale": locale, "selected_experience_ids": [str(item) for item in selected_experience_ids]})

    def get_version(self, version_id: Identifier) -> ResumeVersion:
        return self._model(ResumeVersion, "GET", f"/versions/{version_id}")

    def clone_version(self, version_id: Identifier, name: str) -> ResumeVersion:
        return self._model(ResumeVersion, "POST", f"/versions/{version_id}/clone", json={"name": name})

    def rename_version(self, version_id: Identifier, name: str) -> ResumeVersion:
        return self._model(ResumeVersion, "PATCH", f"/versions/{version_id}", json={"name": name})

    def set_version_style(
        self,
        version_id: Identifier,
        style: str,
    ) -> ResumeVersion:
        return self._model(
            ResumeVersion,
            "PUT",
            f"/versions/{version_id}/style",
            json={"style": style},
        )

    def preview_version(self, version_id: Identifier) -> RenderedResume:
        return self._model(
            RenderedResume,
            "GET",
            f"/versions/{version_id}/preview",
        )

    def version_export_url(
        self,
        version_id: Identifier,
        format_name: str,
    ) -> str:
        format = RenderFormat(format_name)
        return (
            f"{self.base_url}/versions/{version_id}/export?format={format.value}"
        )

    def activate_version(self, version_id: Identifier) -> ResumeVersion:
        return self._model(ResumeVersion, "POST", f"/versions/{version_id}/activate")

    def refresh_version_staleness(self, fact_base_id: Identifier) -> list[ResumeVersion]:
        payload = self._request("POST", f"/fact-bases/{fact_base_id}/versions/refresh-staleness")
        return [ResumeVersion.model_validate(item) for item in payload]

    def delete_version(self, version_id: Identifier) -> None:
        self._request("DELETE", f"/versions/{version_id}")
