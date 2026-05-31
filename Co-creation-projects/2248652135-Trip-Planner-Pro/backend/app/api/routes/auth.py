"""用户认证API路由"""
from fastapi import APIRouter, HTTPException, Header
from ...models.schemas import LoginRequest, RegisterRequest, AuthResponse, UserProfile, ErrorResponse
from ...database import create_user, verify_user, create_token, get_user_by_token, delete_token

router = APIRouter(prefix="/auth", tags=["用户认证"])


def require_auth(authorization: str = Header(None)):
    """从请求头提取并验证token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="无效的认证格式")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user


@router.post(
    "/register",
    response_model=AuthResponse,
    summary="用户注册"
)
async def register(req: RegisterRequest):
    """注册新用户"""
    if len(req.username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")
    try:
        user = create_user(req.username.strip(), req.password)
        token = create_token(user["id"])
        return AuthResponse(success=True, message="注册成功", token=token, username=user["username"])
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="用户登录"
)
async def login(req: LoginRequest):
    """用户登录"""
    user = verify_user(req.username.strip(), req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user["id"])
    return AuthResponse(success=True, message="登录成功", token=token, username=user["username"])


@router.post(
    "/logout",
    response_model=AuthResponse,
    summary="用户登出"
)
async def logout(authorization: str = Header(None)):
    """登出（删除token）"""
    user = require_auth(authorization)
    scheme, _, token = authorization.partition(" ")
    delete_token(token)
    return AuthResponse(success=True, message="已退出登录")


@router.get(
    "/profile",
    response_model=UserProfile,
    summary="获取用户信息"
)
async def profile(authorization: str = Header(None)):
    """获取当前登录用户信息"""
    user = require_auth(authorization)
    return UserProfile(success=True, username=user["username"])
