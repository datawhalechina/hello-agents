"""项目自定义异常。

所有异常都继承自 :class:`StoryAgentError`，便于编排层与接口层统一捕获并
转换为可读的错误信息（不会向调用方泄露密钥等敏感数据）。
"""

from __future__ import annotations


class StoryAgentError(Exception):
    """智能故事生成器的所有业务异常基类。"""


class LLMNotConfiguredError(StoryAgentError):
    """未配置 LLM（模型名 / API Key / Base URL 缺失）时抛出。"""


class LLMCallError(StoryAgentError):
    """LLM 调用重试后仍然失败时抛出。"""


class WriterGenerationError(StoryAgentError):
    """写作 Agent 返回空内容、拒答或清洗后正文为空时抛出。"""


class ReviewParseError(StoryAgentError):
    """审稿输出无法解析为合法的 :class:`~src.models.ReviewResult` 时抛出。"""
