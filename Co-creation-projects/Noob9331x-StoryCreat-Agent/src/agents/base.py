"""智能体公共类型与配置。"""

from __future__ import annotations

from dataclasses import dataclass, field

from hello_agents import Config

from ..models import TokenUsage


@dataclass
class AgentOutput:
    """一次 Agent 文本生成的返回值。

    Attributes:
        text: 清洗后的正文。
        usage: 本次调用的 token 用量。
        latency_ms: 本次调用耗时（毫秒）。
        prompt_version: 使用的提示词版本，用于追踪。
        meta: 附加信息（例如重试次数），写入 trace。
    """

    text: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: int = 0
    prompt_version: str = ""
    meta: dict[str, object] = field(default_factory=dict)


def build_agent_config() -> Config:
    """构造轻量 Agent 配置。

    关闭 trace / session / skills / todo 等与演示无关的持久化能力，
    避免在仓库中生成额外目录，同时保留 ``SimpleAgent`` 的核心行为。

    Returns:
        适用于本项目的 ``Config`` 实例。
    """
    return Config(
        trace_enabled=False,
        session_enabled=False,
        skills_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
        circuit_enabled=False,
        subagent_enabled=False,
        stream_enabled=False,
        context_window=32000,
    )
