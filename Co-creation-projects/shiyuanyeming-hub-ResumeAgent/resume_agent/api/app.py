"""FastAPI application factory for ResumeAgent."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from resume_agent.agents.mentor import DeterministicQuestionWriter
from resume_agent.agents.structured import AgentOutputError
from resume_agent.agents.unavailable import (
    AgentUnavailableError,
    UnavailableFactAuditAgent,
)
from resume_agent.api.schemas import (
    AnswerRequest,
    FactBaseCreateRequest,
    ExperienceCreateRequest,
    ProfileUpdateRequest,
    SessionCreateRequest,
    UnknownRequest,
    VersionCloneRequest,
    VersionCreateRequest,
    VersionRenameRequest,
    VersionStyleRequest,
)
from resume_agent.application.fact_base_service import FactBaseService
from resume_agent.application.interview_service import (
    InterviewService,
    InterviewTurn,
    MentorQuestion,
    UnknownOutcome,
)
from resume_agent.application.render_service import ResumeRenderService
from resume_agent.application.ports import (
    FactAuditAgent,
    QuestionWriterAgent,
    RevisionConflict,
)
from resume_agent.application.version_service import VersionService
from resume_agent.domain.models import (
    CareerFactBase,
    InterviewSession,
    ResumeVersion,
)
from resume_agent.domain.quality import QualityReport, evaluate_experience
from resume_agent.infrastructure.sqlite_repositories import (
    SQLiteFactBaseRepository,
    SQLiteSessionRepository,
    SQLiteStore,
    SQLiteVersionRepository,
)
from resume_agent.rendering.exporters import (
    RenderEngineUnavailable,
    RenderFormat,
    ResumeExporter,
)
from resume_agent.rendering.models import RenderedResume
from resume_agent.rendering.renderer import ResumeRenderer


@dataclass(frozen=True)
class ServiceContainer:
    store: SQLiteStore
    fact_base_repository: SQLiteFactBaseRepository
    session_repository: SQLiteSessionRepository
    version_repository: SQLiteVersionRepository
    fact_bases: FactBaseService
    interviews: InterviewService
    versions: VersionService
    rendering: ResumeRenderService


def create_app(
    database_path: Path,
    *,
    fact_audit_agent: Optional[FactAuditAgent] = None,
    question_writer: Optional[QuestionWriterAgent] = None,
    resume_exporter: Optional[ResumeExporter] = None,
    resume_renderer: Optional[ResumeRenderer] = None,
) -> FastAPI:
    store = SQLiteStore(Path(database_path))
    fact_base_repository = SQLiteFactBaseRepository(store)
    session_repository = SQLiteSessionRepository(store)
    version_repository = SQLiteVersionRepository(store)
    renderer = resume_renderer or ResumeRenderer()
    exporter = resume_exporter or ResumeExporter()
    container = ServiceContainer(
        store=store,
        fact_base_repository=fact_base_repository,
        session_repository=session_repository,
        version_repository=version_repository,
        fact_bases=FactBaseService(fact_base_repository),
        interviews=InterviewService(
            fact_base_repository,
            session_repository,
            fact_audit_agent or UnavailableFactAuditAgent(),
            question_writer or DeterministicQuestionWriter(),
        ),
        versions=VersionService(version_repository),
        rendering=ResumeRenderService(
            fact_base_repository,
            version_repository,
            renderer,
            exporter,
        ),
    )
    app = FastAPI(
        title="ResumeAgent API",
        version="0.1.0",
        description="Evidence-driven multi-agent resume mentoring service",
    )
    app.state.container = container

    @app.exception_handler(KeyError)
    def handle_not_found(request: Request, error: KeyError) -> JSONResponse:
        detail = error.args[0] if error.args else str(error)
        return JSONResponse(status_code=404, content={"detail": detail})

    @app.exception_handler(RevisionConflict)
    def handle_revision_conflict(
        request: Request,
        error: RevisionConflict,
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(AgentUnavailableError)
    def handle_agent_unavailable(
        request: Request,
        error: AgentUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.exception_handler(AgentOutputError)
    def handle_agent_output(
        request: Request,
        error: AgentOutputError,
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @app.exception_handler(RenderEngineUnavailable)
    def handle_render_engine_unavailable(
        request: Request,
        error: RenderEngineUnavailable,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.exception_handler(ValueError)
    def handle_invalid_state(request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    @app.post(
        "/fact-bases",
        response_model=CareerFactBase,
        status_code=status.HTTP_201_CREATED,
        tags=["fact-bases"],
    )
    def create_fact_base(request: FactBaseCreateRequest) -> CareerFactBase:
        return container.fact_bases.create(request.target)

    @app.get(
        "/fact-bases",
        response_model=list[CareerFactBase],
        tags=["fact-bases"],
    )
    def list_fact_bases() -> list[CareerFactBase]:
        return container.fact_bases.list()

    @app.get(
        "/fact-bases/{fact_base_id}",
        response_model=CareerFactBase,
        tags=["fact-bases"],
    )
    def get_fact_base(fact_base_id: UUID) -> CareerFactBase:
        return container.fact_bases.get(fact_base_id)

    @app.post(
        "/fact-bases/{fact_base_id}/experiences",
        response_model=CareerFactBase,
        status_code=status.HTTP_201_CREATED,
        tags=["fact-bases"],
    )
    def add_experience(
        fact_base_id: UUID,
        request: ExperienceCreateRequest,
    ) -> CareerFactBase:
        return container.fact_bases.add_experience(
            fact_base_id,
            request.organization,
            request.role,
        )

    @app.patch(
        "/fact-bases/{fact_base_id}/profile",
        response_model=CareerFactBase,
        tags=["fact-bases"],
    )
    def update_profile(
        fact_base_id: UUID,
        request: ProfileUpdateRequest,
    ) -> CareerFactBase:
        return container.fact_bases.update_profile(fact_base_id, request)

    @app.get(
        "/fact-bases/{fact_base_id}/experiences/{experience_id}/quality",
        response_model=QualityReport,
        tags=["fact-bases"],
    )
    def get_experience_quality(
        fact_base_id: UUID,
        experience_id: UUID,
    ) -> QualityReport:
        base = container.fact_bases.get(fact_base_id)
        return evaluate_experience(base.get_experience(experience_id))

    @app.post(
        "/sessions",
        response_model=InterviewSession,
        status_code=status.HTTP_201_CREATED,
        tags=["interviews"],
    )
    def create_session(request: SessionCreateRequest) -> InterviewSession:
        return container.interviews.create_session(
            request.fact_base_id,
            request.active_experience_id,
        )

    @app.get(
        "/sessions/{session_id}",
        response_model=InterviewSession,
        tags=["interviews"],
    )
    def get_session(session_id: UUID) -> InterviewSession:
        return container.interviews.get_session(session_id)

    @app.get(
        "/fact-bases/{fact_base_id}/sessions",
        response_model=list[InterviewSession],
        tags=["interviews"],
    )
    def list_sessions(
        fact_base_id: UUID,
        experience_id: Optional[UUID] = None,
    ) -> list[InterviewSession]:
        return container.interviews.list_sessions(fact_base_id, experience_id)

    @app.post(
        "/sessions/{session_id}/answers",
        response_model=InterviewTurn,
        tags=["interviews"],
    )
    def answer(session_id: UUID, request: AnswerRequest) -> InterviewTurn:
        return container.interviews.answer(session_id, request.message)

    @app.post(
        "/sessions/{session_id}/proposals/{proposal_id}/confirm",
        response_model=InterviewTurn,
        tags=["interviews"],
    )
    def confirm(session_id: UUID, proposal_id: UUID) -> InterviewTurn:
        return container.interviews.confirm(session_id, proposal_id)

    @app.post(
        "/sessions/{session_id}/proposals/{proposal_id}/reject",
        response_model=InterviewSession,
        tags=["interviews"],
    )
    def reject(session_id: UUID, proposal_id: UUID) -> InterviewSession:
        return container.interviews.reject(session_id, proposal_id)

    @app.post(
        "/sessions/{session_id}/unknown",
        response_model=UnknownOutcome,
        tags=["interviews"],
    )
    def record_unknown(
        session_id: UUID,
        request: UnknownRequest,
    ) -> UnknownOutcome:
        return container.interviews.record_unknown(
            session_id,
            request.dimension,
        )

    @app.get(
        "/sessions/{session_id}/next-question",
        response_model=Optional[MentorQuestion],
        tags=["interviews"],
    )
    def next_question(session_id: UUID) -> Optional[MentorQuestion]:
        return container.interviews.next_question(session_id)

    @app.get(
        "/sessions/{session_id}/current-question",
        response_model=Optional[MentorQuestion],
        tags=["interviews"],
    )
    def current_question(session_id: UUID) -> Optional[MentorQuestion]:
        return container.interviews.next_question(session_id)

    @app.post(
        "/fact-bases/{fact_base_id}/versions",
        response_model=ResumeVersion,
        status_code=status.HTTP_201_CREATED,
        tags=["versions"],
    )
    def create_version(
        fact_base_id: UUID,
        request: VersionCreateRequest,
    ) -> ResumeVersion:
        base = container.fact_bases.get(fact_base_id)
        return container.versions.create(
            base,
            request.name,
            selected_experience_ids=request.selected_experience_ids,
            target_role=request.target_role,
            company=request.company,
            raw_jd=request.raw_jd,
            locale=request.locale,
        )

    @app.get(
        "/fact-bases/{fact_base_id}/versions",
        response_model=list[ResumeVersion],
        tags=["versions"],
    )
    def list_versions(fact_base_id: UUID) -> list[ResumeVersion]:
        container.fact_bases.get(fact_base_id)
        return container.versions.list(fact_base_id)

    @app.post(
        "/fact-bases/{fact_base_id}/versions/refresh-staleness",
        response_model=list[ResumeVersion],
        tags=["versions"],
    )
    def refresh_staleness(fact_base_id: UUID) -> list[ResumeVersion]:
        base = container.fact_bases.get(fact_base_id)
        return container.versions.refresh_staleness(base)

    @app.get(
        "/versions/{version_id}",
        response_model=ResumeVersion,
        tags=["versions"],
    )
    def get_version(version_id: UUID) -> ResumeVersion:
        return container.versions.get(version_id)

    @app.get(
        "/versions/{version_id}/preview",
        response_model=RenderedResume,
        tags=["rendering"],
    )
    def preview_version(version_id: UUID) -> RenderedResume:
        return container.rendering.preview(version_id)

    @app.get(
        "/versions/{version_id}/export",
        tags=["rendering"],
    )
    def export_version(version_id: UUID, format: RenderFormat) -> Response:
        exported = container.rendering.export(version_id, format)
        ascii_filename = f"resume_{format.value}.{format.value}"
        encoded_filename = quote(exported.filename)
        disposition = (
            f'attachment; filename="{ascii_filename}"; '
            f"filename*=UTF-8''{encoded_filename}"
        )
        return Response(
            content=exported.content,
            media_type=exported.media_type,
            headers={"Content-Disposition": disposition},
        )

    @app.post(
        "/versions/{version_id}/clone",
        response_model=ResumeVersion,
        status_code=status.HTTP_201_CREATED,
        tags=["versions"],
    )
    def clone_version(
        version_id: UUID,
        request: VersionCloneRequest,
    ) -> ResumeVersion:
        return container.versions.clone(version_id, request.name)

    @app.patch(
        "/versions/{version_id}",
        response_model=ResumeVersion,
        tags=["versions"],
    )
    def rename_version(
        version_id: UUID,
        request: VersionRenameRequest,
    ) -> ResumeVersion:
        return container.versions.rename(version_id, request.name)

    @app.put(
        "/versions/{version_id}/style",
        response_model=ResumeVersion,
        tags=["versions"],
    )
    def set_version_style(
        version_id: UUID,
        request: VersionStyleRequest,
    ) -> ResumeVersion:
        return container.versions.set_style(version_id, request.style)

    @app.post(
        "/versions/{version_id}/activate",
        response_model=ResumeVersion,
        tags=["versions"],
    )
    def activate_version(version_id: UUID) -> ResumeVersion:
        return container.versions.activate(version_id)

    @app.delete(
        "/versions/{version_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["versions"],
    )
    def delete_version(version_id: UUID) -> Response:
        container.versions.delete(version_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
