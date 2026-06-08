"""
请求级用户上下文 — Python contextvars 实现（等价于 Java ThreadLocal）

中间件在每个请求开始时解析 JWT（Cookie 或 Authorization Header），
将用户信息存入 ContextVar，后续任何位置通过 get_current_user() 即可获取，
无需显式传参或重复解码 JWT。

支持两种认证方式 + 自动续期：
1. Cookie:   access_token（浏览器，HttpOnly 自动携带）
2. Header:   Authorization: Bearer <token> + X-Refresh-Token（非浏览器设备）
3. 自动续期：非浏览器设备 access_token 过期时，中间件自动用 refresh_token 换新
"""
from contextvars import ContextVar
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .jwt_utils import (
    verify_access_token, verify_refresh_token,
    create_access_token, create_refresh_token,
)
from .redis_service import (
    validate_refresh_token, revoke_refresh_token, store_refresh_token,
)
from .database import get_user_by_id

# 核心：ContextVar 像 ThreadLocal，但兼容 asyncio
# 每个请求只能看见自己的那份，请求之间完全隔离
_current_user_var: ContextVar[dict | None] = ContextVar("current_user", default=None)


def get_current_user() -> dict | None:
    """
    获取当前登录用户。
    返回值: {"id": int, "username": str} 或 None（未登录时）
    无需 Request 参数，像全局变量一样调用。
    """
    return _current_user_var.get()


def _extract_token(request: Request) -> str:
    """
    从请求中提取 JWT Token，优先级：
    1. Authorization: Bearer <token>（非浏览器设备）
    2. Cookie: access_token（浏览器）
    """
    # 1. 检查 Authorization Header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 2. 回退到 Cookie
    return request.cookies.get("access_token", "")


def _try_auto_refresh(request: Request) -> tuple:
    """
    当 access_token 过期时，尝试用 X-Refresh-Token 自动续期。
    返回: (user_dict, new_access_token, new_refresh_token) 或 (None, None, None)
    """
    refresh_token = request.headers.get("X-Refresh-Token", "")
    if not refresh_token:
        return None, None, None

    try:
        payload = verify_refresh_token(refresh_token)
        stored = validate_refresh_token(payload["jti"])
        if stored is None or stored["user_id"] != payload["id"]:
            return None, None, None

        # 设备校验（非浏览器设备可能无 User-Agent，不阻塞）
        current_ua = request.headers.get("User-Agent", "")
        if stored.get("user_agent") and current_ua and stored["user_agent"] != current_ua:
            return None, None, None

        # 吊销旧 Token，签发新 Token
        revoke_refresh_token(payload["jti"])
        new_access = create_access_token(payload["id"])
        new_refresh, new_jti = create_refresh_token(payload["id"])
        store_refresh_token(payload["id"], new_jti, user_agent=current_ua)

        # 查用户信息
        user_info = get_user_by_id(payload["id"])
        if user_info:
            return {"id": user_info["id"], "username": user_info["username"]}, new_access, new_refresh
    except Exception:
        pass

    return None, None, None


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 中间件 — 自动解析 access_token（Cookie 或 Header），
    注入当前用户到上下文。access_token 过期时自动续期（非浏览器设备）。
    """

    async def dispatch(self, request: Request, call_next):
        user = None
        new_access_token = None
        new_refresh_token = None
        token = _extract_token(request)

        if token:
            try:
                payload = verify_access_token(token)
                user_info = get_user_by_id(payload["id"])
                if user_info:
                    user = {"id": user_info["id"], "username": user_info["username"]}
            except jwt.ExpiredSignatureError:
                # 过期 → 用 X-Refresh-Token 自动续期（对客户端透明）
                user, new_access_token, new_refresh_token = _try_auto_refresh(request)
            except Exception:
                pass  # token 无效 → user 为 None，后续路由自行处理 401

        # 把当前用户 "set" 进上下文，类似 ThreadLocal.set()
        ctx_token = _current_user_var.set(user)
        try:
            response = await call_next(request)

            # 自动续期成功 → 通过响应头把新 Token 带回客户端
            if new_access_token:
                response.headers["X-Access-Token"] = new_access_token
            if new_refresh_token:
                response.headers["X-Refresh-Token"] = new_refresh_token

            return response
        finally:
            # 请求结束必须 reset，防止上下文泄漏到下一个请求
            _current_user_var.reset(ctx_token)
