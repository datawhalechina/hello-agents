"""
用户认证API路由
轻量级用户管理：无密码，仅用户名 + 重名检测
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ...services.data_store import data_store

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """登录请求"""
    username: str


class LoginResponse(BaseModel):
    """登录响应"""
    username: str
    is_new_user: bool
    has_existing_data: bool
    message: str


@router.post("/check")
async def check_username(request: LoginRequest):
    """检查用户名是否已存在"""
    progress = data_store.get_user_progress(request.username)
    assessments = data_store.get_user_assessments(request.username)
    
    exists = progress is not None
    has_data = exists and (
        len(assessments) > 0
        or len(progress.completed_lessons) > 0
        or progress.current_path is not None
    )
    
    return {
        "username": request.username,
        "exists": exists,
        "has_data": has_data,
    }


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """登录/注册"""
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    
    progress = data_store.get_user_progress(username)
    assessments = data_store.get_user_assessments(username)
    
    is_new_user = progress is None
    has_existing_data = False
    
    if is_new_user:
        # 新用户：自动创建进度记录
        from datetime import datetime
        from ...models.learning import UserProgress
        progress = UserProgress(
            user_id=username,
            started_at=datetime.now(),
            last_activity_at=datetime.now(),
        )
        data_store.save_user_progress(progress)
        message = f"欢迎新用户 {username}！"
    else:
        # 老用户：检查是否有学习数据
        has_existing_data = (
            len(assessments) > 0
            or len(progress.completed_lessons) > 0
            or progress.current_path is not None
        )
        if has_existing_data:
            message = f"欢迎回来，{username}！将继续你的学习进度。"
        else:
            message = f"欢迎回来，{username}！"
    
    return LoginResponse(
        username=username,
        is_new_user=is_new_user,
        has_existing_data=has_existing_data,
        message=message,
    )
