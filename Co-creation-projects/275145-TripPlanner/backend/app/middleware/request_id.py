"""
请求ID中间件
为每个请求生成唯一的请求ID，用于日志追踪
"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.observability.logger import set_request_id, get_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    为每个请求生成唯一的请求ID，并添加到响应头中
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求，生成请求ID
        
        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理函数
        
        Returns:
            响应对象
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 设置到上下文
        set_request_id(request_id)
        
        # 处理请求
        response = await call_next(request)
        
        # 将请求ID添加到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response

