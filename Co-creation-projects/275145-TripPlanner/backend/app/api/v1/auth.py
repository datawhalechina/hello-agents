"""
用户认证API接口
提供登录、注册等功能
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends, UploadFile, File
from pydantic import BaseModel, validator
from typing import Optional
import os
import uuid
from pathlib import Path
from app.middleware.auth import AuthMiddleware, get_current_user, get_user_id
from app.observability.logger import default_logger as logger
from app.config import settings
from app.services.redis_service import redis_service

router = APIRouter()

# 头像上传目录
UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 用户模型
class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str
    password: str

class UserUpdate(BaseModel):
    """用户信息更新请求"""
    username: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    bio: Optional[str] = None
    travel_preferences: Optional[list] = None
    avatar_url: Optional[str] = None

    @validator('gender')
    def validate_gender(cls, v):
        if v is not None and v not in ['male', 'female', 'other']:
            raise ValueError('性别必须是 male、female 或 other')
        return v

class ChangePassword(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str

class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    user_type: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    bio: Optional[str] = None
    travel_preferences: Optional[list] = None
    avatar_url: Optional[str] = None

class AuthToken(BaseModel):
    """认证令牌响应"""
    access_token: str
    token_type: str
    user: UserResponse

@router.post("/login", response_model=AuthToken)
def login(request: Request, login_data: UserLogin):
    """
    用户登录
    
    Args:
        request: FastAPI请求对象
        login_data: 登录数据
        
    Returns:
        JWT令牌和用户信息
    """
    logger.info(f"用户登录尝试 - 账号: {login_data.username}")
    
    # 使用Redis验证用户
    user = redis_service.verify_user(login_data.username, login_data.password)
    
    if not user:
        logger.warning(f"登录失败 - 账号: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误"
        )
    
    # 生成JWT令牌
    access_token = AuthMiddleware.generate_jwt_token(
        user_id=user["user_id"],
        username=user["username"]
    )
    
    logger.info(f"用户登录成功 - UserID: {user['user_id']}")
    
    return AuthToken(
        access_token=access_token,
        token_type="Bearer",
        user=UserResponse(
            user_id=user["user_id"],
            username=user["username"],
            user_type="registered",
            phone=user.get("phone"),
            gender=user.get("gender"),
            birthday=user.get("birthday"),
            bio=user.get("bio"),
            travel_preferences=user.get("travel_preferences"),
            avatar_url=user.get("avatar_url")
        )
    )

@router.post("/register", response_model=AuthToken)
def register(request: Request, register_data: UserRegister):
    """
    用户注册
    
    Args:
        request: FastAPI请求对象
        register_data: 注册数据
        
    Returns:
        JWT令牌和用户信息
    """
    logger.info(f"用户注册尝试 - 账号: {register_data.username}")
    
    # 使用Redis创建用户
    try:
        user_id = str(uuid.uuid4())
        user = redis_service.create_user(
            user_id=user_id,
            username=register_data.username,
            password=register_data.password,
            phone=None,
            gender="other",
            birthday=None,
            bio=None,
            travel_preferences=[],
            avatar_url=None
        )
    except ValueError as e:
        # 用户已存在
        logger.warning(f"注册失败 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except RuntimeError as e:
        # 其他错误
        logger.error(f"注册失败 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )
    
    # 生成JWT令牌
    access_token = AuthMiddleware.generate_jwt_token(
        user_id=user_id,
        username=register_data.username
    )
    
    logger.info(f"用户注册成功 - UserID: {user_id}")
    
    return AuthToken(
        access_token=access_token,
        token_type="Bearer",
        user=UserResponse(
            user_id=user_id,
            username=register_data.username,
            user_type="registered"
        )
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_info(request: Request, current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息
    
    Args:
        request: FastAPI请求对象
        current_user: 当前认证用户信息
        
    Returns:
        用户信息
    """
    user_username = current_user.get("username", "")
    
    # 从Redis获取用户完整信息
    user = redis_service.get_user_by_username(user_username)
    
    if not user:
        # 如果找不到用户，返回基本信息
        return UserResponse(
            user_id=current_user["user_id"],
            username=current_user.get("username", ""),
            user_type="registered"
        )
    
    return UserResponse(
        user_id=current_user["user_id"],
        username=current_user.get("username", ""),
        user_type=current_user.get("user_type", "registered"),
        phone=user.get("phone"),
        gender=user.get("gender"),
        birthday=user.get("birthday"),
        bio=user.get("bio"),
        travel_preferences=user.get("travel_preferences", []),
        avatar_url=user.get("avatar_url")
    )

@router.put("/me", response_model=UserResponse)
def update_user_profile(
    request: Request,
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新用户资料
    
    Args:
        request: FastAPI请求对象
        update_data: 更新数据
        current_user: 当前认证用户信息
        
    Returns:
        更新后的用户信息
    """
    user_username = current_user.get("username", "")
    
    # 使用Redis更新用户信息
    try:
        user = redis_service.update_user(
            username=user_username,
            phone=update_data.phone,
            gender=update_data.gender,
            birthday=update_data.birthday,
            bio=update_data.bio,
            travel_preferences=update_data.travel_preferences,
            avatar_url=update_data.avatar_url
        )
    except ValueError as e:
        logger.warning(f"更新用户资料失败 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"更新用户资料失败 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败，请稍后重试"
        )
    
    logger.info(f"用户资料更新成功 - UserID: {user['user_id']}")
    
    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        user_type="registered",
        phone=user.get("phone"),
        gender=user.get("gender"),
        birthday=user.get("birthday"),
        bio=user.get("bio"),
        travel_preferences=user.get("travel_preferences", []),
        avatar_url=user.get("avatar_url")
    )

@router.post("/change-password")
def change_password(
    request: Request,
    password_data: ChangePassword,
    current_user: dict = Depends(get_current_user)
):
    """
    修改密码
    
    Args:
        request: FastAPI请求对象
        password_data: 密码数据
        current_user: 当前认证用户信息
        
    Returns:
        操作结果
    """
    user_username = current_user.get("username", "")
    
    # 使用Redis更新密码
    try:
        redis_service.update_password(
            username=user_username,
            old_password=password_data.old_password,
            new_password=password_data.new_password
        )
    except ValueError as e:
        logger.warning(f"密码修改失败 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"密码修改失败 - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败，请稍后重试"
        )
    
    logger.info(f"用户密码修改成功 - Username: {user_username}")
    
    return {"message": "密码修改成功"}

@router.post("/logout")
def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """
    退出登录
    
    Args:
        request: FastAPI请求对象
        current_user: 当前认证用户信息
        
    Returns:
        操作结果
    """
    user_id = current_user.get("user_id", "unknown")
    user_type = current_user.get("user_type", "unknown")
    
    logger.info(f"用户退出登录 - UserID: {user_id}, UserType: {user_type}")
    
    # 生产环境可能需要：
    # 1. 将JWT令牌加入黑名单
    # 2. 清除会话数据
    # 3. 记录退出时间等
    
    return {"message": "退出登录成功"}

@router.post("/upload-avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    上传用户头像
    
    Args:
        request: FastAPI请求对象
        file: 上传的头像文件
        current_user: 当前认证用户信息
        
    Returns:
        头像URL
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能上传图片文件"
        )
    
    # 生成唯一文件名
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    unique_filename = f"{current_user['user_id']}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        # 保存文件
        contents = await file.read()
        # 验证文件大小（2MB限制）
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件大小不能超过2MB"
            )
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # 生成文件URL
        file_url = f"/uploads/avatars/{unique_filename}"
        
        logger.info(f"头像上传成功 - UserID: {current_user['user_id']}, URL: {file_url}")
        
        return {"url": file_url}
        
    except Exception as e:
        logger.error(f"头像上传失败 - UserID: {current_user['user_id']}, Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="头像上传失败"
        )