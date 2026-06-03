"""用户认证API路由 - 标准JWT(HttpOnly Cookie) + Redis持久化Refresh Token"""
from fastapi import APIRouter, HTTPException, Request, Response
from ...models.schemas import LoginRequest, RegisterRequest
from ...database import create_user, verify_user, get_user_by_id
from ...jwt_utils import (
    create_access_token, create_refresh_token,
    verify_access_token, verify_refresh_token,
)
from ...redis_service import store_refresh_token, validate_refresh_token, revoke_refresh_token
from ...config import get_settings
from ...rsa_service import get_public_key_pem, decrypt_data

router = APIRouter(prefix="/auth", tags=["用户认证"])

COOKIE_ACCESS_KEY = "access_token"
COOKIE_REFRESH_KEY = "refresh_token"
COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"
# 根据是否启用SSL自动设置Secure标志
COOKIE_SECURE = get_settings().ssl_enabled


def _set_auth_cookies(response: Response, access_token: str):
    """设置 Access Token HttpOnly Cookie"""
    response.set_cookie(
        key=COOKIE_ACCESS_KEY, value=access_token,
        httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
        max_age=1800, path=COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response):
    """清除认证Cookie"""
    response.delete_cookie(COOKIE_ACCESS_KEY, path=COOKIE_PATH)
    response.delete_cookie(COOKIE_REFRESH_KEY, path=COOKIE_PATH)


def require_auth(request: Request) -> dict:
    """从 Cookie 中读取 Access Token 验证"""
    token = request.cookies.get(COOKIE_ACCESS_KEY)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        return verify_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token已过期或无效，请重新登录")


@router.post("/register", summary="用户注册")
async def register(req: RegisterRequest, response: Response):
    """注册新用户（密码经RSA加密），设置Access Token Cookie + Refresh Token存入Redis"""
    if len(req.username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少2个字符")

    # RSA解密密码
    try:
        password = decrypt_data(req.encrypted_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"密码解密失败: {e}")

    if len(password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")
    try:
        user = create_user(req.username.strip(), password)
        _issue_tokens(response, user["id"])
        return {"success": True, "message": "注册成功", "username": user["username"]}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", summary="用户登录")
async def login(req: LoginRequest, response: Response):
    """登录（密码经RSA加密），设置Access Token Cookie + Refresh Token存入Redis"""
    # RSA解密密码
    try:
        password = decrypt_data(req.encrypted_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"密码解密失败: {e}")

    user = verify_user(req.username.strip(), password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    _issue_tokens(response, user["id"])
    return {"success": True, "message": "登录成功", "username": user["username"]}


@router.get("/public-key", summary="获取RSA公钥")
async def public_key():
    """获取RSA公钥（PEM格式），用于前端加密密码"""
    return {
        "success": True,
        "public_key": get_public_key_pem(),
    }


def _issue_tokens(response: Response, user_id: int):
    """签发双Token：Access→Cookie，Refresh→Redis"""
    # Access Token -> HttpOnly Cookie
    access_token = create_access_token(user_id)
    _set_auth_cookies(response, access_token)

    # Refresh Token -> JWT (存Redis)
    refresh_token, jti = create_refresh_token(user_id)
    store_refresh_token(user_id, jti)

    # Refresh Token 也设成 Cookie（仅用于携带到 /refresh 端点）
    response.set_cookie(
        key=COOKIE_REFRESH_KEY, value=refresh_token,
        httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
        max_age=604800, path=COOKIE_PATH,
    )


@router.post("/refresh", summary="刷新Token")
async def refresh(request: Request, response: Response):
    """用 Refresh Token（Cookie中）换取新的双Token"""
    refresh_token = request.cookies.get(COOKIE_REFRESH_KEY)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="未登录，缺少Refresh Token")

    # 1. JWT签名验证
    try:
        payload = verify_refresh_token(refresh_token)
    except Exception:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh Token已过期或无效")

    # 2. Redis验证：jti是否有效（未被吊销）
    uid = validate_refresh_token(payload["jti"])
    if uid is None or uid != payload["id"]:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh Token已被吊销")

    # 3. 吊销旧 Refresh Token（轮换）
    revoke_refresh_token(payload["jti"])

    # 4. 签发新双Token
    _issue_tokens(response, payload["id"])

    return {"success": True, "message": "Token刷新成功"}


@router.post("/logout", summary="用户登出")
async def logout(request: Request, response: Response):
    """登出：清除Cookie + 吊销Redis中的Refresh Token"""
    refresh_token = request.cookies.get(COOKIE_REFRESH_KEY)
    if refresh_token:
        try:
            payload = verify_refresh_token(refresh_token)
            revoke_refresh_token(payload["jti"])
        except Exception:
            pass

    _clear_auth_cookies(response)
    return {"success": True, "message": "已退出登录"}


@router.get("/profile", summary="获取用户信息")
async def profile(request: Request):
    """获取当前登录用户信息"""
    user = require_auth(request)
    user_info = get_user_by_id(user["id"])
    if not user_info:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True, "username": user_info["username"]}
