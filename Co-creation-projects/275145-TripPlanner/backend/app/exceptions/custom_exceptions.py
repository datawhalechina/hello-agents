"""
自定义异常类
定义业务相关的异常类型
"""
from typing import Optional, Dict, Any
from app.exceptions.error_codes import ErrorCode, get_error_message


class BaseAppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常
        
        Args:
            error_code: 错误码
            message: 错误消息，如果为None则使用错误码对应的默认消息
            details: 额外的错误详情
        """
        self.error_code = error_code
        self.message = message or get_error_message(error_code)
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将异常转换为字典格式
        
        Returns:
            异常信息字典
        """
        return {
            "error_code": self.error_code.value,
            "error_message": self.message,
            "details": self.details
        }


class BusinessException(BaseAppException):
    """业务异常"""
    pass


class ServiceException(BaseAppException):
    """服务异常"""
    pass


class ValidationException(BaseAppException):
    """参数验证异常"""
    pass


class ExternalServiceException(ServiceException):
    """外部服务异常"""
    pass


class LLMServiceException(ExternalServiceException):
    """LLM服务异常"""
    pass


class MapServiceException(ExternalServiceException):
    """地图服务异常"""
    pass


class ImageServiceException(ExternalServiceException):
    """图片服务异常"""
    pass

