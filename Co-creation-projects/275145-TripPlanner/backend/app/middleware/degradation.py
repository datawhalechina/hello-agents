"""
降级策略实现 - 简化版本
简单的异常捕获和默认值返回
"""
from typing import Callable, Any
from functools import wraps
from app.observability.logger import default_logger as logger


def fallback_response(default_value: Any = None):
    """
    降级装饰器
    当函数调用失败时，返回默认值
    
    Args:
        default_value: 降级时的默认返回值
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"函数 {func.__name__} 调用失败，使用降级方案: {e}"
                )
                return default_value
        return wrapper
    return decorator


def circuit_breaker_with_fallback(
    breaker_name: str,
    fallback_value: Any = None,
    failure_threshold: int = 5,
    timeout: float = 60.0
):
    """
    带降级的熔断器装饰器
    当熔断器打开或调用失败时，返回降级值
    
    Args:
        breaker_name: 熔断器名称
        fallback_value: 降级时的返回值
        failure_threshold: 失败次数阈值
        timeout: 熔断后等待时间（秒）
    
    Returns:
        装饰器函数
    """
    from .circuit_breaker import circuit_breaker_manager
    
    def decorator(func: Callable) -> Callable:
        breaker = circuit_breaker_manager.get_breaker(
            breaker_name,
            failure_threshold=failure_threshold,
            timeout=timeout
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"熔断器已打开或调用失败，使用降级方案 - 函数: {func.__name__}, 状态: {breaker.get_state()}"
                )
                return fallback_value
        return wrapper
    return decorator
