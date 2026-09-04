"""
全局异常处理器
统一处理所有异常并返回标准格式的错误响应
"""
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.exceptions.custom_exceptions import BaseAppException
from app.exceptions.error_codes import ErrorCode, get_error_message
from app.observability.logger import default_logger as logger, get_request_id


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    
    Args:
        request: FastAPI请求对象
        exc: 异常对象
    
    Returns:
        JSON格式的错误响应
    """
    request_id = get_request_id()
    
    # 处理自定义异常
    if isinstance(exc, BaseAppException):
        logger.error(
            f"业务异常: {exc.message}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "error_code": exc.error_code.value,
                "error_message": exc.message,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error_code": exc.error_code.value,
                "error_message": exc.message,
                "details": exc.details,
                "request_id": request_id
            }
        )
    
    # 处理FastAPI验证异常
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        logger.warning(
            f"请求验证失败: {errors}",
            extra={
                "request_id": request_id,
                "errors": errors,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error_code": ErrorCode.INVALID_PARAMETER.value,
                "error_message": "请求参数验证失败",
                "details": {"validation_errors": errors},
                "request_id": request_id
            }
        )
    
    # 处理HTTP异常
    if isinstance(exc, (StarletteHTTPException, HTTPException)):
        status_code = exc.status_code if hasattr(exc, 'status_code') else 500
        detail = exc.detail if hasattr(exc, 'detail') else str(exc)
        
        # 429 Too Many Requests 特殊处理
        if status_code == 429:
            error_code = ErrorCode.RATE_LIMIT_EXCEEDED.value
        else:
            error_code = ErrorCode.UNKNOWN_ERROR.value
        
        logger.warning(
            f"HTTP异常: {detail}",
            extra={
                "request_id": request_id,
                "status_code": status_code,
                "detail": detail,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error_code": error_code,
                "error_message": detail,
                "request_id": request_id
            }
        )
    
    # 处理其他未知异常
    logger.error(
        f"未处理的异常: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": ErrorCode.UNKNOWN_ERROR.value,
            "error_message": "服务器内部错误",
            "details": {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)
            },
            "request_id": request_id
        }
    )

