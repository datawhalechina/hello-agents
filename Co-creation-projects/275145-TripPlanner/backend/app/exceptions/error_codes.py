"""
错误码定义
统一管理所有错误码和错误消息
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """错误码枚举"""
    # 通用错误 (1000-1999)
    SUCCESS = 0
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    MISSING_PARAMETER = 1002
    INVALID_PARAMETER = 1003
    
    # 业务错误 (2000-2999)
    TRIP_PLAN_FAILED = 2000
    DESTINATION_NOT_FOUND = 2001
    INVALID_DATE_RANGE = 2002
    BUDGET_TOO_LOW = 2003
    NO_ATTRACTIONS_FOUND = 2004
    NO_HOTELS_FOUND = 2005
    WEATHER_QUERY_FAILED = 2006
    UNSUPPORTED_CITY = 2007
    
    # 服务错误 (3000-3999)
    LLM_SERVICE_ERROR = 3000
    LLM_TIMEOUT = 3001
    LLM_RATE_LIMIT = 3002
    MAP_SERVICE_ERROR = 3003
    IMAGE_SERVICE_ERROR = 3004
    
    # 系统错误 (4000-4999)
    DATABASE_ERROR = 4000
    EXTERNAL_API_ERROR = 4001
    CIRCUIT_BREAKER_OPEN = 4002
    RATE_LIMIT_EXCEEDED = 4003
    
    # 认证授权错误 (5000-5999)
    UNAUTHORIZED = 5000
    FORBIDDEN = 5001
    TOKEN_EXPIRED = 5002


# 错误消息映射
ERROR_MESSAGES = {
    ErrorCode.SUCCESS: "操作成功",
    ErrorCode.UNKNOWN_ERROR: "未知错误",
    ErrorCode.INVALID_REQUEST: "无效的请求",
    ErrorCode.MISSING_PARAMETER: "缺少必需参数",
    ErrorCode.INVALID_PARAMETER: "参数无效",
    
    ErrorCode.TRIP_PLAN_FAILED: "行程规划失败",
    ErrorCode.DESTINATION_NOT_FOUND: "未找到目的地信息",
    ErrorCode.INVALID_DATE_RANGE: "日期范围无效",
    ErrorCode.BUDGET_TOO_LOW: "预算过低，无法规划行程",
    ErrorCode.NO_ATTRACTIONS_FOUND: "未找到相关景点",
    ErrorCode.NO_HOTELS_FOUND: "未找到相关酒店",
    ErrorCode.WEATHER_QUERY_FAILED: "天气查询失败",
    ErrorCode.UNSUPPORTED_CITY: "该城市暂不支持精细规划",
    
    ErrorCode.LLM_SERVICE_ERROR: "LLM服务错误",
    ErrorCode.LLM_TIMEOUT: "LLM服务超时",
    ErrorCode.LLM_RATE_LIMIT: "LLM服务限流",
    ErrorCode.MAP_SERVICE_ERROR: "地图服务错误",
    ErrorCode.IMAGE_SERVICE_ERROR: "图片服务错误",
    
    ErrorCode.DATABASE_ERROR: "数据库错误",
    ErrorCode.EXTERNAL_API_ERROR: "外部API调用失败",
    ErrorCode.CIRCUIT_BREAKER_OPEN: "服务暂时不可用，请稍后重试",
    ErrorCode.RATE_LIMIT_EXCEEDED: "请求过于频繁，请稍后再试",
    
    ErrorCode.UNAUTHORIZED: "未授权",
    ErrorCode.FORBIDDEN: "禁止访问",
    ErrorCode.TOKEN_EXPIRED: "令牌已过期",
}


def get_error_message(error_code: ErrorCode) -> str:
    """
    获取错误消息
    
    Args:
        error_code: 错误码
    
    Returns:
        错误消息
    """
    return ERROR_MESSAGES.get(error_code, "未知错误")

