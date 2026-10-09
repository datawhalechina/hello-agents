"""HTTP adapter for the logout workflow."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from fithealth_agent.workflows.logout_workflow import logout as run_logout


router = APIRouter()


@router.post("/logout")
def logout(payload: dict | None = None) -> JSONResponse:
    result = run_logout(payload)
    return JSONResponse(result.body, status_code=result.status_code)
