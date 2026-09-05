"""异常体系"""

class HelloAgentsException(Exception):
    """HelloAgents基础异常类"""
    pass

class LLMException(HelloAgentsException):
    """LLM相关异常"""
    pass

class AgentException(HelloAgentsException):
    """Agent相关异常"""
    pass

class ConfigException(HelloAgentsException):
    """配置相关异常"""
    pass

class ToolException(HelloAgentsException):
    """工具相关异常"""
    pass
