from __future__ import annotations

from typing import Any, Protocol


class ResponseFormatStrategy(Protocol):
    name: str

    def json_response_formats(
        self,
        agent_name: str,
        input_json: dict[str, Any],
        configured_format: str,
        schema: dict[str, Any],
    ) -> list[dict[str, Any] | None]:
        ...

    def should_fallback_response_format(self, exc: Exception) -> bool:
        ...


class OpenAIResponseFormatStrategy:
    name = "openai"

    def json_response_formats(
        self,
        agent_name: str,
        input_json: dict[str, Any],
        configured_format: str,
        schema: dict[str, Any],
    ) -> list[dict[str, Any] | None]:
        if response_format_disabled(configured_format):
            return [None]
        if configured_format == "json_object":
            return [{"type": "json_object"}, None]
        return [
            {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{agent_name}Output",
                    "strict": False,
                    "schema": schema,
                },
            },
            {"type": "json_object"},
            None,
        ]

    def should_fallback_response_format(self, exc: Exception) -> bool:
        return is_response_format_request_error(exc)


class DeepSeekResponseFormatStrategy:
    name = "deepseek"

    def json_response_formats(
        self,
        agent_name: str,
        input_json: dict[str, Any],
        configured_format: str,
        schema: dict[str, Any],
    ) -> list[dict[str, Any] | None]:
        if response_format_disabled(configured_format):
            return [None]
        return [{"type": "json_object"}, None]

    def should_fallback_response_format(self, exc: Exception) -> bool:
        return is_response_format_request_error(exc)


class PlainPromptResponseFormatStrategy:
    name = "plain_prompt"

    def json_response_formats(
        self,
        agent_name: str,
        input_json: dict[str, Any],
        configured_format: str,
        schema: dict[str, Any],
    ) -> list[dict[str, Any] | None]:
        return [None]

    def should_fallback_response_format(self, exc: Exception) -> bool:
        return False


MODEL_STRATEGY_REGISTRY: dict[str, type[ResponseFormatStrategy]] = {
    "deepseek-chat": DeepSeekResponseFormatStrategy,
    "deepseek-v4-pro": DeepSeekResponseFormatStrategy,
    "deepseek-v4-flash": DeepSeekResponseFormatStrategy,
    "gpt-5.5": OpenAIResponseFormatStrategy,
    "gpt-5.4": OpenAIResponseFormatStrategy,
    "gpt-5.4-min": OpenAIResponseFormatStrategy,
}

PROVIDER_STRATEGY_REGISTRY: dict[str, type[ResponseFormatStrategy]] = {
    "deepseek": DeepSeekResponseFormatStrategy,
    "openai": OpenAIResponseFormatStrategy,
    "plain": PlainPromptResponseFormatStrategy,
    "none": PlainPromptResponseFormatStrategy,
}


def resolve_response_format_strategy(
    provider: str | None,
    model_id: str | None,
    base_url: str | None,
) -> ResponseFormatStrategy:
    provider_key = normalize_key(provider)
    if provider_key in PROVIDER_STRATEGY_REGISTRY:
        return PROVIDER_STRATEGY_REGISTRY[provider_key]()

    model_key = normalize_key(model_id)
    if model_key in MODEL_STRATEGY_REGISTRY:
        return MODEL_STRATEGY_REGISTRY[model_key]()
    if model_key.startswith(("gpt-", "o1", "o3", "o4")):
        return OpenAIResponseFormatStrategy()
    if model_key.startswith("deepseek"):
        return DeepSeekResponseFormatStrategy()

    base_url_key = normalize_key(base_url)
    if "deepseek" in base_url_key:
        return DeepSeekResponseFormatStrategy()
    if "openai" in base_url_key:
        return OpenAIResponseFormatStrategy()

    return DeepSeekResponseFormatStrategy()


def response_format_disabled(configured_format: str) -> bool:
    return configured_format in {"", "none", "off", "disabled"}


def normalize_key(value: str | None) -> str:
    return (value or "").strip().lower()


def is_response_format_request_error(exc: Exception) -> bool:
    text = error_text(exc)
    if "response_format" not in text:
        return False

    status_code = error_status_code(exc)
    payload = error_payload(exc)
    error_type = normalize_key(payload.get("type") if isinstance(payload, dict) else None)
    error_code = normalize_key(payload.get("code") if isinstance(payload, dict) else None)
    error_param = normalize_key(payload.get("param") if isinstance(payload, dict) else None)

    if error_param == "response_format":
        return True
    if status_code == 400 and (error_type == "invalid_request_error" or error_code == "invalid_request_error"):
        return True

    return any(
        marker in text
        for marker in [
            "unsupported",
            "not support",
            "not supported",
            "unavailable",
            "not available",
            "unknown parameter",
            "invalid parameter",
            "extra fields not permitted",
            "json_schema",
        ]
    )


def error_payload(exc: Exception) -> dict[str, Any]:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        return error if isinstance(error, dict) else body

    response = getattr(exc, "response", None)
    if response is not None:
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, dict):
            error = data.get("error")
            return error if isinstance(error, dict) else data

    return {}


def error_text(exc: Exception) -> str:
    parts = [str(exc)]
    payload = error_payload(exc)
    if payload:
        parts.extend(str(value) for value in payload.values() if value is not None)
    return " ".join(parts).lower()


def error_status_code(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status
    return None
