"""代码执行API"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from ...services.code_executor import get_executor
from ...agents.review_agent import get_review_agent
from ...services.data_store import data_store
from ...models.learning import CodeSubmission

router = APIRouter(prefix="/code", tags=["代码执行"])


class CodeRequest(BaseModel):
    """代码执行请求"""
    code: str
    language: str = "python"


class CodeResponse(BaseModel):
    """代码执行响应"""
    success: bool
    output: str
    error: str
    exit_code: int


class CodeSubmitRequest(BaseModel):
    """代码提交审查请求"""
    code: str
    language: str = "python"
    output: str = ""
    error: str = ""
    success: bool = True
    exit_code: int = 0
    user_id: str = "default"
    lesson_id: Optional[str] = None


class CodeSubmitResponse(BaseModel):
    """代码提交审查响应"""
    feedback: str
    submission_id: str
    created_at: str


@router.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest):
    """执行代码"""
    executor = get_executor()
    result = executor.execute(request.code, request.language)
    
    return CodeResponse(
        success=result["success"],
        output=result["output"],
        error=result["error"],
        exit_code=result["exit_code"],
    )


@router.post("/submit", response_model=CodeSubmitResponse)
async def submit_code(request: CodeSubmitRequest):
    """提交代码进行AI审查"""
    # 调用 ReviewAgent 进行练习反馈
    review_agent = get_review_agent()
    feedback = review_agent.review_exercise(request.code, context={
        "output": request.output,
        "error": request.error,
        "success": request.success,
        "exit_code": request.exit_code,
        "lesson_id": request.lesson_id,
    })
    
    # 构建提交记录
    submission_id = str(uuid.uuid4())
    created_at = datetime.now()
    submission = CodeSubmission(
        id=submission_id,
        user_id=request.user_id,
        code=request.code,
        language=request.language,
        output=request.output,
        error=request.error,
        success=request.success,
        exit_code=request.exit_code,
        lesson_id=request.lesson_id,
        feedback=feedback,
        created_at=created_at,
    )
    
    # 持久化
    data_store.save_submission(submission)
    
    return CodeSubmitResponse(
        feedback=feedback,
        submission_id=submission_id,
        created_at=created_at.isoformat(),
    )
