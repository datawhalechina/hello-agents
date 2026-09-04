"""
限流中间件 - 简化版本
使用简单的滑动窗口算法进行请求限流
"""
import time
from typing import Dict
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.observability.logger import default_logger as logger, get_request_id


class RateLimiter:
    """
    简化的限流器
    使用滑动窗口算法记录请求时间戳
    """
    
    def __init__(
        self,
        global_rate: int = 100,  # 全局每秒请求数
        per_ip_rate: int = 20,   # 每个IP每秒请求数
        enabled: bool = True
    ):
        """
        初始化限流器
        
        Args:
            global_rate: 全局每秒最大请求数
            per_ip_rate: 每个IP每秒最大请求数
            enabled: 是否启用限流
        """
        self.enabled = enabled
        self.global_rate = global_rate
        self.per_ip_rate = per_ip_rate
        
        # 记录请求时间戳
        self.global_requests: list[float] = []
        self.ip_requests: Dict[str, list[float]] = defaultdict(list)
        
        self.lock = Lock()
    
    def _clean_old_requests(self, requests: list[float]) -> list[float]:
        """清理超过1秒的旧请求"""
        now = time.time()
        return [t for t in requests if now - t < 1.0]
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def is_allowed(self, request: Request) -> tuple[bool, str]:
        """检查请求是否被允许"""
        if not self.enabled:
            return True, ""
        
        with self.lock:
            now = time.time()
            
            # 清理旧的全局请求
            self.global_requests = self._clean_old_requests(self.global_requests)
            
            # 检查全局限流
            if len(self.global_requests) >= self.global_rate:
                request_id = get_request_id()
                logger.warning(
                    f"全局限流触发 - RequestID: {request_id}",
                    extra={"request_id": request_id, "path": request.url.path}
                )
                return False, "请求过于频繁，请稍后再试"
            
            # 检查IP限流
            client_ip = self.get_client_ip(request)
            ip_request_list = self.ip_requests[client_ip]
            ip_request_list = self._clean_old_requests(ip_request_list)
            
            if len(ip_request_list) >= self.per_ip_rate:
                request_id = get_request_id()
                logger.warning(
                    f"IP限流触发 - IP: {client_ip}, RequestID: {request_id}",
                    extra={"request_id": request_id, "ip": client_ip, "path": request.url.path}
                )
                return False, "您的请求过于频繁，请稍后再试"
            
            # 记录此次请求
            self.global_requests.append(now)
            ip_request_list.append(now)
            self.ip_requests[client_ip] = ip_request_list
            
            return True, ""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 跳过健康检查端点的限流
        if request.url.path == "/health":
            return await call_next(request)
        
        # 检查限流
        allowed, error_message = self.rate_limiter.is_allowed(request)
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message
            )
        
        return await call_next(request)
