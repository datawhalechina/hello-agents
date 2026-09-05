"""Lazy, validated runtime assembly for optional HelloAgents specialists."""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Callable, Mapping, Optional, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, Field, SecretStr

from resume_agent.agents.mentor import (
    StructuredFactAuditAgent,
    StructuredQuestionWriterAgent,
)
from resume_agent.agents.prompts import FACT_AUDIT_PROMPT, QUESTION_WRITER_PROMPT
from resume_agent.agents.unavailable import AgentUnavailableError
from resume_agent.application.ports import FactAuditAgent, QuestionWriterAgent


class RunnableAgent(Protocol):
    def run(self, prompt: str) -> str: ...


class AgentRuntimeSettings(BaseModel):
    model: str
    api_key: SecretStr
    base_url: str
    timeout: int = Field(default=60, ge=1, le=300)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=128, le=32768)

    @classmethod
    def from_environ(
        cls,
        environ: Mapping[str, str],
    ) -> "AgentRuntimeSettings":
        model = environ.get("LLM_MODEL_ID", "").strip()
        if not model:
            raise ValueError("LLM_MODEL_ID is required")
        api_key = (
            environ.get("LLM_API_KEY", "").strip()
            or environ.get("DEEPSEEK_API_KEY", "").strip()
        )
        if not api_key:
            raise ValueError("LLM_API_KEY is required")
        lowered_key = api_key.lower()
        if any(marker in lowered_key for marker in ("your-api-key", "replace-me", "example")):
            raise ValueError("LLM_API_KEY contains a placeholder value")
        base_url = environ.get("LLM_BASE_URL", "").strip().rstrip("/")
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("LLM_BASE_URL must be an absolute HTTP(S) URL")

        timeout = cls._integer(environ, "LLM_TIMEOUT", 60)
        max_tokens = cls._integer(environ, "LLM_MAX_TOKENS", 2048)
        temperature = cls._number(environ, "LLM_TEMPERATURE", 0.2)
        if not 1 <= timeout <= 300:
            raise ValueError("LLM_TIMEOUT must be between 1 and 300")
        if not 0 <= temperature <= 2:
            raise ValueError("LLM_TEMPERATURE must be between 0 and 2")
        if not 128 <= max_tokens <= 32768:
            raise ValueError("LLM_MAX_TOKENS must be between 128 and 32768")
        return cls(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _integer(
        environ: Mapping[str, str],
        name: str,
        default: int,
    ) -> int:
        raw = environ.get(name, str(default)).strip()
        try:
            return int(raw)
        except ValueError as error:
            raise ValueError(f"{name} must be an integer") from error

    @staticmethod
    def _number(
        environ: Mapping[str, str],
        name: str,
        default: float,
    ) -> float:
        raw = environ.get(name, str(default)).strip()
        try:
            return float(raw)
        except ValueError as error:
            raise ValueError(f"{name} must be a number") from error


class AgentCapabilityStatus(BaseModel):
    status: str = "degraded"
    api: bool = True
    mentor: bool = False
    fact_audit: bool = False
    question_writer: bool = False
    rendering: bool = True
    exports: list[str] = Field(default_factory=lambda: ["html", "md", "docx", "pdf"])
    framework: str = "HelloAgents"
    model: str = ""
    reason: str = ""

    @classmethod
    def offline(cls, reason: str, *, model: str = "") -> "AgentCapabilityStatus":
        return cls(model=model, reason=reason)

    @classmethod
    def ready(cls, model: str) -> "AgentCapabilityStatus":
        return cls(
            status="ready",
            mentor=True,
            fact_audit=True,
            question_writer=True,
            model=model,
        )


@dataclass(frozen=True)
class MentorRuntime:
    fact_auditor: Optional[FactAuditAgent]
    question_writer: Optional[QuestionWriterAgent]
    capabilities: AgentCapabilityStatus


class FreshAgentRunner:
    """Create a new stateful framework Agent for every isolated invocation."""

    def __init__(self, factory: Callable[[], RunnableAgent]) -> None:
        self.factory = factory

    def run(self, prompt: str) -> str:
        try:
            return str(self.factory().run(prompt))
        except AgentUnavailableError:
            raise
        except Exception as error:
            raise AgentUnavailableError(
                "mentor model request failed; check model configuration and connectivity"
            ) from error


def _load_hello_agents() -> ModuleType:
    return import_module("hello_agents")


def _private_agent_config(framework):
    return framework.Config(
        trace_enabled=False,
        session_enabled=False,
        skills_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
        subagent_enabled=False,
    )


def build_mentor_runtime(
    environ: Optional[Mapping[str, str]] = None,
    *,
    framework_loader: Optional[Callable[[], object]] = None,
) -> MentorRuntime:
    values = os.environ if environ is None else environ
    try:
        settings = AgentRuntimeSettings.from_environ(values)
    except ValueError as error:
        return MentorRuntime(
            fact_auditor=None,
            question_writer=None,
            capabilities=AgentCapabilityStatus.offline(str(error)),
        )

    try:
        framework = (framework_loader or _load_hello_agents)()
    except ImportError:
        return MentorRuntime(
            fact_auditor=None,
            question_writer=None,
            capabilities=AgentCapabilityStatus.offline(
                "HelloAgents is not installed; install the agents optional dependency",
                model=settings.model,
            ),
        )

    try:
        llm = framework.HelloAgentsLLM(
            model=settings.model,
            api_key=settings.api_key.get_secret_value(),
            base_url=settings.base_url,
            timeout=settings.timeout,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
    except Exception as error:
        return MentorRuntime(
            fact_auditor=None,
            question_writer=None,
            capabilities=AgentCapabilityStatus.offline(
                f"HelloAgents initialization failed ({type(error).__name__})",
                model=settings.model,
            ),
        )

    audit_runner = FreshAgentRunner(
        lambda: framework.SimpleAgent(
            name="简历事实审计",
            llm=llm,
            system_prompt=FACT_AUDIT_PROMPT,
            config=_private_agent_config(framework),
        )
    )
    question_runner = FreshAgentRunner(
        lambda: framework.SimpleAgent(
            name="简历导师追问",
            llm=llm,
            system_prompt=QUESTION_WRITER_PROMPT,
            config=_private_agent_config(framework),
        )
    )
    return MentorRuntime(
        fact_auditor=StructuredFactAuditAgent(audit_runner),
        question_writer=StructuredQuestionWriterAgent(question_runner),
        capabilities=AgentCapabilityStatus.ready(settings.model),
    )
