# -*- coding: utf-8 -*-
"""Biomedical literature translation service.

Translates PubMed titles/abstracts into a target language (default: Chinese)
using any OpenAI-compatible chat endpoint (DeepSeek / Qwen / GPT / vLLM).

The translation keeps gene names, protein symbols, MeSH terms, numbers and
PMIDs unchanged, which is critical for biomedical text.

Usage:
    translator = LiteratureTranslator(
        api_base="https://api.deepseek.com/v1",
        api_key="sk-...",
        model="deepseek-chat",
    )
    zh = translator.translate("SEC61G is overexpressed in NSCLC.", "zh")
    article_zh = translator.translate_article(article, "zh")
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

LANGUAGE_NAMES: dict[str, str] = {
    "zh": "Simplified Chinese",
    "en": "English",
}

SYSTEM_PROMPT = (
    "You are a professional biomedical translator. Translate the given text "
    "into {target_language}. Rules:\n"
    "1. Keep gene/protein symbols, MeSH terms, numbers, and PMIDs unchanged.\n"
    "2. Keep the original paragraph structure.\n"
    "3. Output ONLY the translation, without explanations or quotation marks."
)

# Split long abstracts so each chunk stays well under the token budget.
_CHUNK_CHARS = 1800


class TranslationError(Exception):
    """Raised when the translation LLM call fails."""


class LiteratureTranslator:
    """Translate biomedical text via an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: float = 120.0,
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
            "LiteratureTranslator initialized (model=%s, base=%s)",
            model, api_base,
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                verify=self.verify_ssl,
            )
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self, text: str, target_language: str = "zh") -> str:
        """Translate a single text block into the target language."""
        text = (text or "").strip()
        if not text:
            return ""
        language = LANGUAGE_NAMES.get(target_language, target_language)
        chunks = self._chunk_text(text)
        translated: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            logger.info(
                "Translating chunk %d/%d (%d chars) -> %s",
                index, len(chunks), len(chunk), target_language,
            )
            if len(chunks) > 1:
                prompt = (
                    f"[Part {index}/{len(chunks)}] Translate this part and "
                    f"output only the translation:\n\n{chunk}"
                )
            else:
                prompt = chunk
            translated.append(self._translate_chunk(prompt, language))
        return "\n".join(translated)

    def translate_article(
        self,
        article: dict,
        target_language: str = "zh",
    ) -> dict:
        """Return a copy of the article with translated title/abstract.

        The translated fields are added as ``title_zh`` / ``abstract_zh``
        (or ``_en`` depending on the target language) so the original text
        is preserved.
        """
        result = dict(article)
        suffix = "_zh" if target_language == "zh" else "_en"
        result[f"title{suffix}"] = self.translate(
            article.get("title", ""), target_language
        )
        result[f"abstract{suffix}"] = self.translate(
            article.get("abstract", ""), target_language
        )
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _translate_chunk(self, text: str, language: str) -> str:
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(target_language=language),
                },
                {"role": "user", "content": text},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Translation API HTTP error: %s", exc.response.text[:500])
            raise TranslationError(
                f"Translation API returned {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Translation API request error: %s", exc)
            raise TranslationError(f"Translation API request failed: {exc}") from exc

        choices = body.get("choices", [])
        if not choices:
            raise TranslationError("Translation API returned empty choices.")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise TranslationError("Translation API returned empty content.")
        return content.strip()

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        """Split long text at sentence/paragraph boundaries."""
        if len(text) <= _CHUNK_CHARS:
            return [text]
        chunks: list[str] = []
        remaining = text
        while len(remaining) > _CHUNK_CHARS:
            cut = remaining.rfind("\n\n", 0, _CHUNK_CHARS)
            if cut == -1:
                cut = remaining.rfind(". ", 0, _CHUNK_CHARS)
            if cut == -1:
                cut = _CHUNK_CHARS
            else:
                cut += 1  # keep the paragraph/sentence separator with the chunk
            chunks.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()
        if remaining:
            chunks.append(remaining)
        return chunks
