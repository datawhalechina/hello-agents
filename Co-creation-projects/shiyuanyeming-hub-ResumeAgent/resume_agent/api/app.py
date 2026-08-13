"""FastAPI application factory for ResumeAgent."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from resume_agent.api.schemas import FactBaseCreateRequest, ExperienceCreateRequest
from resume_agent.application.fact_base_service import FactBaseService
from resume_agent.domain.models import CareerFactBase
from resume_agent.infrastructure.sqlite_repositories import (
    SQLiteFactBaseRepository,
    SQLiteSessionRepository,
    SQLiteStore,
    SQLiteVersionRepository,
)


@dataclass(frozen=True)
class ServiceContainer:
    store: SQLiteStore
    fact_base_repository: SQLiteFactBaseRepository
    session_repository: SQLiteSessionRepository
    version_repository: SQLiteVersionRepository
    fact_bases: FactBaseService


def create_app(database_path: Path) -> FastAPI:
    store = SQLiteStore(Path(database_path))
    fact_base_repository = SQLiteFactBaseRepository(store)
    container = ServiceContainer(
        store=store,
        fact_base_repository=fact_base_repository,
        session_repository=SQLiteSessionRepository(store),
        version_repository=SQLiteVersionRepository(store),
        fact_bases=FactBaseService(fact_base_repository),
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

    return app
