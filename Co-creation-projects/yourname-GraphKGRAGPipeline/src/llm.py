from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    backend: str  # "openai" | "ollama" | "none"
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None


def load_llm_config(enable_llm: bool) -> LLMConfig:
    if not enable_llm:
        return LLMConfig(backend="none", model="")

    if os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"):
        return LLMConfig(
            backend="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"):
        return LLMConfig(
            backend="ollama",
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    return LLMConfig(backend="none", model="")


def chat_json(config: LLMConfig, system: str, user: str) -> Dict[str, Any]:
    """Return a JSON object. Raises on parsing failure."""

    if config.backend == "none":
        raise RuntimeError("LLM backend is disabled/unconfigured")

    if config.backend == "openai":
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openai package not installed; add openai to requirements") from exc

        client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        resp = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)

    if config.backend == "ollama":
        try:
            import requests
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("requests not installed; pip install requests") from exc

        url = config.base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "stream": False,
        }
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content") or "{}"
        return json.loads(content)

    raise RuntimeError(f"Unsupported LLM backend: {config.backend}")
