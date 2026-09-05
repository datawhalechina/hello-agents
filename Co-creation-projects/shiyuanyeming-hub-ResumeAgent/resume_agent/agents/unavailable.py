"""Explicit offline behavior when no fact-audit model is configured."""


class AgentUnavailableError(RuntimeError):
    """Raised when an endpoint requires an agent that was not configured."""


class UnavailableFactAuditAgent:
    def propose(self, message, session, base):
        raise AgentUnavailableError(
            "fact-audit agent is not configured; connect a HelloAgents agent first"
        )
