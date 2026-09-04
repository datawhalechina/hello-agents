"""
熔断器实现 - 简化版本
简单的失败计数和快速失败机制
"""
import time
from typing import Callable, Any
from threading import Lock
from app.observability.logger import default_logger as logger


class CircuitBreaker:
    """
    简化的熔断器
    失败达到阈值后熔断，一段时间后自动恢复
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,  # 失败次数阈值
        timeout: float = 60.0  # 熔断后等待时间（秒）
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败次数阈值
            timeout: 熔断后等待时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False
        self.lock = Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            函数返回值
        
        Raises:
            Exception: 当熔断器打开时抛出异常
        """
        with self.lock:
            # 检查是否应该从熔断状态恢复
            if self.is_open:
                if time.time() - self.last_failure_time >= self.timeout:
                    # 超过等待时间，尝试恢复
                    self.is_open = False
                    self.failure_count = 0
                    logger.info("熔断器已恢复，允许请求通过")
                else:
                    raise Exception("熔断器已打开，服务暂时不可用")
        
        # 执行函数
        try:
            result = func(*args, **kwargs)
            
            # 成功后重置计数
            with self.lock:
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            # 失败时计数
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # 达到阈值，打开熔断器
                if self.failure_count >= self.failure_threshold and not self.is_open:
                    self.is_open = True
                    logger.error(
                        f"失败次数达到阈值({self.failure_threshold})，熔断器已打开",
                        extra={"failure_count": self.failure_count}
                    )
            
            raise e
    
    def reset(self):
        """重置熔断器"""
        with self.lock:
            self.is_open = False
            self.failure_count = 0
            self.last_failure_time = 0.0
    
    def get_state(self) -> str:
        """获取当前状态"""
        return "open" if self.is_open else "closed"


class CircuitBreakerManager:
    """熔断器管理器"""
    
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}
        self.lock = Lock()
    
    def get_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.breakers:
            with self.lock:
                if name not in self.breakers:
                    self.breakers[name] = CircuitBreaker(**kwargs)
        return self.breakers[name]


# 全局熔断器管理器
circuit_breaker_manager = CircuitBreakerManager()
