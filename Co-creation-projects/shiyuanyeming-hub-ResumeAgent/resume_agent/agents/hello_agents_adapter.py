"""Small bridge from HelloAgents-style agents to ResumeAgent ports."""

from dataclasses import dataclass
from typing import Protocol

from resume_agent.agents.mentor import (
    StructuredFactAuditAgent,
    StructuredQuestionWriterAgent,
)


class SimpleAgentLike(Protocol):
    def run(self, prompt: str) -> str: ...


class HelloAgentsRunner:
    """Wrap any HelloAgents `SimpleAgent`-compatible object lazily."""

    def __init__(self, agent: SimpleAgentLike) -> None:
        self.agent = agent

    def run(self, prompt: str) -> str:
        return str(self.agent.run(prompt))


@dataclass(frozen=True)
class MentorAgentPair:
    fact_auditor: StructuredFactAuditAgent
    question_writer: StructuredQuestionWriterAgent


def build_mentor_agents(
    audit_agent: SimpleAgentLike,
    question_agent: SimpleAgentLike,
) -> MentorAgentPair:
    """Adapt two configured HelloAgents agents into mentor application ports."""

    return MentorAgentPair(
        fact_auditor=StructuredFactAuditAgent(HelloAgentsRunner(audit_agent)),
        question_writer=StructuredQuestionWriterAgent(
            HelloAgentsRunner(question_agent)
        ),
    )
