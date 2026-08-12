from fastapi import APIRouter

from app.models.schemas import PlanRequest, PlanResponse
from app.services.plan_converter import PlanConverter


router = APIRouter(prefix="/api", tags=["plan"])


@router.post("/plan", response_model=PlanResponse)
def create_plan(payload: PlanRequest) -> PlanResponse:
    code = PlanConverter.to_mermaid(payload.text, payload.direction)
    return PlanResponse(mermaid_code=code)
