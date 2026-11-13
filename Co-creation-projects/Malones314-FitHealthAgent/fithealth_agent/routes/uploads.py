"""HTTP adapters for upload workflows."""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from fithealth_agent.workflows.upload_workflow import (
    analyze_food as run_analyze_food,
    upload_activity_from_health_zip as run_upload_activity,
    upload_fit as run_upload_fit,
    upload_health as run_upload_health,
    upload_plan as run_upload_plan,
)


food_router = APIRouter()
router = APIRouter()
activity_router = APIRouter()


@food_router.post("/analyze_food")
async def analyze_food(
    file: UploadFile = File(...), context: str = Form("")
) -> JSONResponse:
    result = await run_analyze_food(file, context)
    return JSONResponse(result.body, status_code=result.status_code)


@router.post("/upload_fit")
async def upload_fit(
    file: UploadFile = File(...), overwrite_pending: bool = Form(False)
) -> JSONResponse:
    result = await run_upload_fit(file, overwrite_pending)
    return JSONResponse(result.body, status_code=result.status_code)


@router.post("/upload_plan")
async def upload_plan(
    file: UploadFile = File(...), confirm_large: bool = Form(False)
) -> JSONResponse:
    result = await run_upload_plan(file, confirm_large)
    return JSONResponse(result.body, status_code=result.status_code)


@router.post("/upload_health")
async def upload_health(files: list[UploadFile] = File(...)) -> JSONResponse:
    result = await run_upload_health(files)
    return JSONResponse(result.body, status_code=result.status_code)


@activity_router.post("/upload_health/activity")
async def upload_activity_from_health_zip(
    file: UploadFile = File(...),
    activity_name: str = Form(...),
    overwrite_pending: bool = Form(False),
) -> JSONResponse:
    result = await run_upload_activity(file, activity_name, overwrite_pending)
    return JSONResponse(result.body, status_code=result.status_code)
