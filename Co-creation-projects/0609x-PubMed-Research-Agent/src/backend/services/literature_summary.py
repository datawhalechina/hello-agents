"""
Literature Summary Service

Uses OpenAI-compatible LLM APIs to analyze multiple PubMed abstracts
and produce structured research summaries.

Supported model providers (any OpenAI-compatible endpoint):
- OpenAI GPT (gpt-4o, gpt-4o-mini, ...)
- Qwen (via DashScope / vLLM)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Any local vLLM / Ollama endpoint

Usage:
    summarizer = LiteratureSummarizer(
        api_base="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o",
    )
    result = summarizer.summarize(articles, language="zh")
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Models
# ---------------------------------------------------------------------------

class ResearchHotspot(BaseModel):
    topic: str = Field(description="Name of the research hotspot")
    description: str = Field(description="Brief description of this hotspot")
    evidence: list[str] = Field(default_factory=list)


class FutureDirection(BaseModel):
    direction: str = Field(description="Proposed future research direction")
    rationale: str = Field(description="Why this direction is promising")
    challenges: list[str] = Field(default_factory=list)


class ExperimentalMethod(BaseModel):
    method: str = Field(description="Name of the method")
    purpose: str = Field(description="What this method was used for")
    frequency: int = Field(default=0)


class LiteratureSummary(BaseModel):
    research_background: str = Field(description="Comprehensive research background (2-3 paragraphs)")
    current_hotspots: list[ResearchHotspot] = Field(description="Top 3-5 current research hotspots")
    main_findings: list[str] = Field(description="Key findings across the reviewed literature (5-8 bullet points)")
    experimental_methods: list[ExperimentalMethod] = Field(description="Experimental validation methods identified")
    future_directions: list[FutureDirection] = Field(description="3-5 future research directions")
    model_used: str = Field(default="")
    token_usage: dict = Field(default_factory=dict)
    elapsed_seconds: float = Field(default=0.0)


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert biomedical research analyst. Your task is to analyze "
    "a set of PubMed abstracts and produce a structured literature summary.\n\n"
    "Follow these rules strictly:\n"
    "1. Base all analysis ONLY on the provided abstracts. Do not fabricate.\n"
    "2. Output valid JSON matching the specified schema exactly.\n"
    "3. If information for a field is not found, use an empty string/list.\n"
    "4. Cite PMIDs when referencing specific findings.\n"
    "5. Write in {language}."
)

USER_PROMPT_TEMPLATE = (
    "Analyze the following {count} PubMed abstracts and produce a structured "
    "literature summary.\n\n"
    "Return a JSON object with:\n"
    '- "research_background": string (2-3 paragraphs)\n'
    '- "current_hotspots": [{{"topic": "string", "description": "string", "evidence": ["PMID:..."]}}]\n'
    '- "main_findings": ["string", ...]\n'
    '- "experimental_methods": [{{"method": "string", "purpose": "string", "frequency": int}}]\n'
    '- "future_directions": [{{"direction": "string", "rationale": "string", "challenges": ["string"]}}]\n\n'
    "ABSTRACTS:\n{articles_text}"
)


# ---------------------------------------------------------------------------
# Model Presets
# ---------------------------------------------------------------------------

MODEL_PRESETS: dict[str, dict] = {
    "gpt-4o": {
        "api_base": "https://api.openai.com/v1",
        "description": "OpenAI GPT-4o",
    },
    "gpt-4o-mini": {
        "api_base": "https://api.openai.com/v1",
        "description": "OpenAI GPT-4o Mini",
    },
    "deepseek-chat": {
        "api_base": "https://api.deepseek.com/v1",
        "description": "DeepSeek V3 Chat",
    },
    "deepseek-reasoner": {
        "api_base": "https://api.deepseek.com/v1",
        "description": "DeepSeek R1 Reasoner",
    },
    "deepseek-flash": {
        "api_base": "https://api.deepseek.com/v1",
        "description": "DeepSeek Flash (fast)",
    },
    "qwen-turbo": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "Qwen Turbo",
    },
    "qwen-plus": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "Qwen Plus",
    },
    "qwen-max": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "Qwen Max",
    },
}


# ---------------------------------------------------------------------------
# LiteratureSummarizer
# ---------------------------------------------------------------------------

class LiteratureSummarizer:
    """Summarize PubMed abstracts using OpenAI-compatible LLM APIs."""

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 240.0,
        verify_ssl: bool = True,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required.")

        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.Client] = None

        logger.info(
            "LiteratureSummarizer initialized (model=%s, base=%s)",
            model, api_base,
        )

    @classmethod
    def from_preset(
        cls,
        model: str,
        api_key: str,
        api_base: Optional[str] = None,
        **kwargs,
    ) -> "LiteratureSummarizer":
        preset = MODEL_PRESETS.get(model)
        if preset is None:
            raise ValueError(
                f"Unknown model preset: {model}. "
                f"Available: {list(MODEL_PRESETS.keys())}"
            )
        base = api_base or preset["api_base"]
        return cls(api_base=base, api_key=api_key, model=model, **kwargs)

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                verify=self.verify_ssl,
            )
        return self._client

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def summarize(
        self,
        articles: list[dict],
        language: str = "en",
    ) -> LiteratureSummary:
        if not articles:
            raise ValueError("At least one article is required.")

        start_time = time.perf_counter()
        logger.info("Summarizing %d articles (language=%s)", len(articles), language)

        articles_text = self._format_articles(articles)
        system_prompt = SYSTEM_PROMPT.format(language=language)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            count=len(articles),
            articles_text=articles_text,
        )

        summary = self._summarize_with_retry(system_prompt, user_prompt)
        summary.model_used = self.model
        summary.elapsed_seconds = round(time.perf_counter() - start_time, 3)

        logger.info(
            "Summary completed in %.2fs (hotspots=%d, findings=%d, directions=%d)",
            summary.elapsed_seconds,
            len(summary.current_hotspots),
            len(summary.main_findings),
            len(summary.future_directions),
        )

        return summary

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------

    def _format_articles(self, articles: list[dict]) -> str:
        blocks = []
        for i, art in enumerate(articles, 1):
            pmid = art.get("pmid", f"UNKNOWN_{i}")
            title = art.get("title", "")
            abstract = art.get("abstract", "")
            if len(abstract) > 1500:
                abstract = abstract[:1500] + "..."
            blocks.append(
                f"[{i}] PMID:{pmid}\n"
                f"Title: {title}\n"
                f"Abstract: {abstract}\n"
            )
        return "\n".join(blocks)

    def _summarize_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LiteratureSummary:
        """Call the LLM and parse/validate its JSON, retrying once on failure.

        Retrying with a larger token budget rescues outputs that were
        truncated mid-string because of the max_tokens limit.
        """
        last_error: Optional[str] = None
        for attempt in range(1, 3):
            max_tokens = (
                int(self.max_tokens * 2.0) if attempt > 1 else self.max_tokens
            )
            timeout = self.timeout * 1.5 if attempt > 1 else None
            try:
                raw_json = self._call_llm(
                    system_prompt, user_prompt, max_tokens, timeout=timeout
                )
            except LiteratureSummaryError as exc:
                last_error = f"LLM call failed: {exc}"
                logger.warning("LLM call failed (attempt %d/2): %s", attempt, exc)
                continue
            data = self._parse_llm_json(raw_json)
            if data is not None:
                try:
                    return LiteratureSummary(**data)
                except (TypeError, ValueError) as exc:
                    last_error = f"schema validation failed: {exc}"
            else:
                last_error = "JSON parse failed"
            logger.warning(
                "LLM output invalid (attempt %d/2): %s", attempt, last_error
            )
        raise LiteratureSummaryError(
            f"LLM returned invalid output after 2 attempts ({last_error})"
        )

    def _parse_llm_json(self, raw: str) -> Optional[dict]:
        """Parse LLM JSON with progressive recovery.

        Attempts, in order: direct parse, light repair (code fences /
        trailing commas), then salvage of truncated output. Returns the
        parsed object or None when every attempt fails.
        """
        repaired = self._repair_json(raw)
        candidates = [raw, repaired]
        salvaged = self._salvage_truncated_json(repaired)
        if salvaged != repaired:
            candidates.append(salvaged)
        for candidate in candidates:
            data = self._extract_json_object(candidate)
            if data is not None:
                return data
        return None

    @staticmethod
    def _extract_json_object(text: str):
        """Locate and decode the first complete JSON object in arbitrary text.

        Handles responses that prefix/suffix the JSON with prose (e.g. a
        model explaining itself before the object) by scanning every '{'
        position with ``raw_decode``.
        """
        decoder = json.JSONDecoder()
        start = 0
        while True:
            idx = text.find("{", start)
            if idx == -1:
                return None
            try:
                obj, _ = decoder.raw_decode(text[idx:])
            except json.JSONDecodeError:
                start = idx + 1
                continue
            if isinstance(obj, dict):
                return obj
            start = idx + 1

    @staticmethod
    def _salvage_truncated_json(raw: str) -> str:
        """Recover the longest valid JSON prefix from truncated output.

        Handles the two common truncation patterns:
          - output cut mid-string ("Unterminated string")
          - output cut before the final closing brace
        """
        decoder = json.JSONDecoder()

        # 1) Drop an unterminated tail by trying prefixes that end right
        #    after a closing brace/bracket, longest first.
        cut_points = {len(raw)}
        for match in re.finditer(r"[}\]]", raw):
            cut_points.add(match.end())
        for end in sorted(cut_points, reverse=True):
            candidate = raw[:end]
            try:
                decoder.raw_decode(candidate)
            except json.JSONDecodeError:
                continue
            return candidate

        # 2) Auto-close a truncated object/array that is missing its
        #    closing bracket(s). Multiple candidates cover nested objects
        #    and unterminated arrays.
        for extra in (
            "}", "}}", "}}}", "}}}}",
            "]}", "]}}", "]}}}",
            "}]}", "}]}}", "}]}}}",
        ):
            candidate = raw + extra
            try:
                decoder.raw_decode(candidate)
            except json.JSONDecodeError:
                continue
            return candidate

        return raw

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> str:
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        request_kwargs: dict = {"json": payload, "headers": headers}
        if timeout is not None:
            request_kwargs["timeout"] = timeout
        try:
            response = self.client.post(url, **request_kwargs)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("LLM API HTTP error: %s", exc.response.text[:500])
            raise LiteratureSummaryError(
                f"LLM API returned {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("LLM API request error: %s", exc)
            raise LiteratureSummaryError(
                f"LLM API request failed: {exc}"
            ) from exc

        choices = body.get("choices", [])
        if not choices:
            raise LiteratureSummaryError("LLM returned empty choices.")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise LiteratureSummaryError("LLM returned empty content.")
        return content.strip()

    @staticmethod
    def _repair_json(raw: str) -> str:
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)
        return raw


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class LiteratureSummaryError(Exception):
    """Raised when literature summarization fails."""
