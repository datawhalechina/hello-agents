"""
水平检测API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ...models.learning import (
    AssessmentStartRequest, AssessmentAnswerRequest,
    AssessmentCompleteRequest, AssessmentStartResponse,
    AssessmentAnswerResponse, AssessmentResult
)
from ...services.assessment_service import (
    start_assessment, submit_answer, complete_assessment
)
from ...services.data_store import data_store

router = APIRouter(prefix="/assessment", tags=["assessment"])


@router.get("/check/{path_type}")
async def check_assessment(path_type: str, user_id: str = "default"):
    """检查用户是否已测试过指定路径"""
    has_test = data_store.has_assessment(user_id, path_type)
    current = data_store.get_current_assessment(user_id, path_type)

    return {
        "has_assessment": has_test,
        "current_result": current,
    }


@router.get("/result/{path_type}")
async def get_assessment_result(path_type: str, user_id: str = "default"):
    """获取用户测试结果"""
    result = data_store.get_current_assessment(user_id, path_type)
    if not result:
        raise HTTPException(status_code=404, detail="未找到测试结果")
    return result


@router.get("/history/{path_type}")
async def get_assessment_history(path_type: str, user_id: str = "default"):
    """获取用户测试历史"""
    assessments = data_store.get_user_assessments(user_id, path_type)
    return {"assessments": assessments}


@router.post("/start")
async def api_start_assessment(request: AssessmentStartRequest):
    """开始测试"""
    result = start_assessment(request.path_type, user_id=request.user_id)
    return result


@router.post("/answer")
async def api_submit_answer(request: AssessmentAnswerRequest):
    """提交答案"""
    result = submit_answer(
        request.session_id,
        request.question_id,
        request.answer,
        user_id=request.user_id,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/complete")
async def api_complete_assessment(request: AssessmentCompleteRequest):
    """完成测试"""
    result = complete_assessment(request.session_id, user_id=request.user_id)
    if not result:
        raise HTTPException(status_code=400, detail="会话不存在或已过期")
    return result


@router.post("/save-result")
async def save_assessment_result(result: AssessmentResult, user_id: str = "default"):
    """保存测试结果"""
    result.user_id = user_id
    data_store.save_assessment(result)
    return {"message": "保存成功", "result": result}
