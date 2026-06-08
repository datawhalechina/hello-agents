"""
请求级用户上下文 — Python contextvars 实现（等价于 Java ThreadLocal）

中间件在每个请求开始时解析 JWT Cookie，将用户信息存入 ContextVar，
后续任何位置（路由、服务、工具函数）通过 get_current_user() 即可获取，
无需显式传参或重复解码 JWT。
"""
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .jwt_utils import verify_access_token
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


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 中间件 — 自动解析 access_token Cookie，注入当前用户到上下文。
    注册在路由层之上，每个请求执行一次。
    """

    async def dispatch(self, request: Request, call_next):
        user = None
        token = request.cookies.get("access_token")

        if token:
            try:
                payload = verify_access_token(token)
                user_info = get_user_by_id(payload["id"])
                if user_info:
                    user = {"id": user_info["id"], "username": user_info["username"]}
            except Exception:
                pass  # token 无效 → user 为 None，后续路由自行处理 401

        # 把当前用户 "set" 进上下文，类似 ThreadLocal.set()
        ctx_token = _current_user_var.set(user)
        try:
            response = await call_next(request)
            return response
        finally:
            # 请求结束必须 reset，防止上下文泄漏到下一个请求
            _current_user_var.reset(ctx_token)
