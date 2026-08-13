"""Reliable structured-output execution for LLM-backed agents."""

import json
from typing import Any, Dict, Protocol, Type, TypeVar

from pydantic import BaseModel, ValidationError


class AgentRunner(Protocol):
    def run(self, prompt: str) -> str: ...


class AgentOutputError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        attempts: int,
        last_output: str,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_output = last_output


def extract_json_object(text: str) -> Dict[str, Any]:
    """Return the first complete JSON object embedded in a response."""

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("agent response contains no complete JSON object")


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


def run_structured(
    runner: AgentRunner,
    prompt: str,
    response_model: Type[ResponseModel],
) -> ResponseModel:
    """Run an agent with one schema-guided retry on invalid output."""

    current_prompt = prompt
    last_output = ""
    last_error: Exception = ValueError("agent did not run")
    for attempt in range(1, 3):
        last_output = str(runner.run(current_prompt))
        try:
            payload = extract_json_object(last_output)
            return response_model.model_validate(payload)
        except (ValueError, ValidationError) as error:
            last_error = error
            if attempt == 1:
                schema = json.dumps(
                    response_model.model_json_schema(),
                    ensure_ascii=False,
                )
                current_prompt = (
                    f"{prompt}\n\n"
                    "Your previous response failed JSON validation. "
                    f"Validation error: {error}. "
                    "Return only one JSON object matching this schema: "
                    f"{schema}"
                )

    raise AgentOutputError(
        f"agent output failed validation after 2 attempts: {last_error}",
        attempts=2,
        last_output=last_output,
    )
