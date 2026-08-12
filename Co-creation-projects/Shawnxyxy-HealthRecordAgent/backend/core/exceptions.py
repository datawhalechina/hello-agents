"""
HealthRecordAgent 项目异常体系
"""

class HealthAgentException(Exception):
    """ 基础异常类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AgentException(HealthAgentException):
    """Agent 执行异常"""
    pass


class ValidationException(HealthAgentException):
    """输入 / 输出校验异常"""
    pass


class LLMException(HealthAgentException):
    """LLM 调用异常"""
    pass


class TimeoutException(HealthAgentException):
    """超时异常"""
    pass