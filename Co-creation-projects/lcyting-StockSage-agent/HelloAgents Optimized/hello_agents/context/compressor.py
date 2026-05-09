"""混合压缩策略实现

提供多种压缩方法的统一接口：
- Truncation: 按段落截断
- SlidingWindow: 滑动窗口压缩
- LLMSummarize: LLM 智能摘要
- Hybrid: 自适应混合压缩
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

import tiktoken


class ContentType(Enum):
    STRUCTURED = "structured"
    FREE_TEXT = "free_text"
    MIXED = "mixed"


class LatencyRequirement(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BudgetUrgency(Enum):
    SAFE = 0.8
    NORMAL = 1.0
    HIGH = 1.3
    CRITICAL = 1.5


@dataclass
class CompressionResult:
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    strategy_used: str
    saved_tokens: int = 0

    def __post_init__(self):
        self.saved_tokens = self.original_tokens - self.compressed_tokens


@dataclass
class HybridOptions:
    enable_llm: bool = True
    llm_model: str = "gpt-4o-mini"
    window_size: int = 2000
    window_overlap: int = 200
    truncate_threshold: float = 0.9
    llm_threshold: float = 1.2
    latency_requirement: LatencyRequirement = LatencyRequirement.MEDIUM


class CompressionStrategy(ABC):
    @abstractmethod
    def compress(self, text: str, max_tokens: int) -> CompressionResult:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class TruncationStrategy(CompressionStrategy):
    @property
    def name(self) -> str:
        return "truncation"

    def compress(self, text: str, max_tokens: int) -> CompressionResult:
        original_tokens = count_tokens(text)

        if original_tokens <= max_tokens:
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy_used=self.name,
            )

        lines = text.split("\n")
        result = []
        used = 0

        for line in lines:
            line_tokens = count_tokens(line)
            if used + line_tokens > max_tokens:
                break
            result.append(line)
            used += line_tokens

        return CompressionResult(
            compressed_text="\n".join(result),
            original_tokens=original_tokens,
            compressed_tokens=used,
            strategy_used=self.name,
        )


class SlidingWindowStrategy(CompressionStrategy):
    def __init__(self, window_size: int = 2000, overlap: int = 200):
        self.window_size = window_size
        self.overlap = overlap

    @property
    def name(self) -> str:
        return "sliding_window"

    def compress(self, text: str, max_tokens: int) -> CompressionResult:
        original_tokens = count_tokens(text)

        if original_tokens <= max_tokens:
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy_used=self.name,
            )

        lines = text.split("\n")
        section_boundaries = self._find_sections(lines)

        windows = self._create_windows(lines, section_boundaries)
        selected = self._select_windows(windows, max_tokens)

        compressed = self._merge_windows(selected)

        return CompressionResult(
            compressed_text=compressed,
            original_tokens=original_tokens,
            compressed_tokens=count_tokens(compressed),
            strategy_used=self.name,
        )

    def _find_sections(self, lines: List[str]) -> List[int]:
        boundaries = [0]
        for i, line in enumerate(lines):
            if re.match(r"^\[.+\]$", line.strip()):
                boundaries.append(i)
        return boundaries

    def _create_windows(
        self, lines: List[str], boundaries: List[int]
    ) -> List[List[str]]:
        windows = []
        prev_start = -1
        for start in boundaries:
            if start == prev_start:
                continue
            end = min(start + self.window_size, len(lines))
            windows.append(lines[start:end])
            if end >= len(lines):
                break
            prev_start = start
        return windows

    def _select_windows(
        self, windows: List[List[str]], max_tokens: int
    ) -> List[List[str]]:
        if not windows:
            return []

        # Score windows: first window gets priority boost
        window_scores = []
        for i, window in enumerate(windows):
            score = len(window)
            if i == 0:
                score *= 1.5
            if i == len(windows) - 1 and len(windows) > 1:
                score *= 1.2
            window_scores.append((score, i))

        window_scores.sort(key=lambda x: x[0], reverse=True)

        # Select windows that fit in budget, truncate if needed
        selected = []
        used = 0
        for _, i in window_scores:
            window_text = "\n".join(windows[i])
            window_tokens = count_tokens(window_text)

            if used + window_tokens <= max_tokens:
                selected.append(window_text)
                used += window_tokens
            else:
                # Truncate last window to fit budget
                remaining = max_tokens - used
                if remaining > 0:
                    truncated = self._truncate_to_tokens(window_text, remaining)
                    selected.append(truncated)
                    used += count_tokens(truncated)
                break

        # If nothing selected due to budget being too small
        if not selected and windows:
            # Truncate the first window to fit budget
            first_text = "\n".join(windows[0])
            selected = [self._truncate_to_tokens(first_text, max_tokens)]

        return [w.split("\n") for w in selected]

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within max_tokens"""
        lines = text.split("\n")
        result = []
        used = 0

        for line in lines:
            line_tokens = count_tokens(line)
            if used + line_tokens > max_tokens:
                # Truncate this line if possible
                remaining = max_tokens - used
                if remaining > 0:
                    result.append(line[: remaining * 4])
                break
            result.append(line)
            used += line_tokens

        return "\n".join(result)

    def _merge_windows(self, windows: List[List[str]]) -> str:
        return "\n".join(line for window in windows for line in window)


class LLMSummarizeStrategy(CompressionStrategy):
    def __init__(
        self, llm_client=None, model: str = "gpt-4o-mini", max_retries: int = 2
    ):
        self.llm_client = llm_client
        self.model = model
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        return "llm_summarize"

    def compress(self, text: str, max_tokens: int) -> CompressionResult:
        original_tokens = count_tokens(text)

        if original_tokens <= max_tokens:
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy_used=self.name,
            )

        if self.llm_client is None:
            fallback = TruncationStrategy()
            return fallback.compress(text, max_tokens)

        prompt = self._build_prompt(text, max_tokens)

        for attempt in range(self.max_retries):
            try:
                result = asyncio.run(self._call_llm(prompt))
                return CompressionResult(
                    compressed_text=result,
                    original_tokens=original_tokens,
                    compressed_tokens=count_tokens(result),
                    strategy_used=self.name,
                )
            except Exception:
                if attempt == self.max_retries - 1:
                    fallback = TruncationStrategy()
                    return fallback.compress(text, max_tokens)

        return CompressionResult(
            compressed_text=text,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            strategy_used=self.name,
        )

    def _build_prompt(self, text: str, max_tokens: int) -> str:
        return f"""请将以下上下文压缩至约 {max_tokens} token，
保留关键信息、核心论据和结论。不要遗漏重要事实。

上下文：
{text}

压缩后："""

    async def _call_llm(self, prompt: str) -> str:
        response = await self.llm_client.complete(prompt)
        return response.text


class HybridStrategy(CompressionStrategy):
    def __init__(self, options: Optional[HybridOptions] = None, llm_client=None):
        self.options = options or HybridOptions(enable_llm=llm_client is not None)
        self.llm_client = llm_client

        self._strategies = {
            "truncation": TruncationStrategy(),
            "sliding_window": SlidingWindowStrategy(
                window_size=self.options.window_size,
                overlap=self.options.window_overlap,
            ),
            "llm_summarize": LLMSummarizeStrategy(llm_client, self.options.llm_model),
        }

    @property
    def name(self) -> str:
        return "hybrid"

    def compress(self, text: str, max_tokens: int) -> CompressionResult:
        original_tokens = count_tokens(text)

        if original_tokens <= max_tokens:
            return CompressionResult(
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy_used="none",
            )

        strategy = self._select_strategy(text, original_tokens, max_tokens)
        return strategy.compress(text, max_tokens)

    def _select_strategy(
        self, text: str, original_tokens: int, max_tokens: int
    ) -> CompressionStrategy:
        ratio = original_tokens / max_tokens
        latency = self.options.latency_requirement

        if ratio <= self.options.truncate_threshold:
            return self._strategies["truncation"]

        if latency == LatencyRequirement.LOW:
            return self._strategies["truncation"]

        content_type = self._classify_content(text)

        if not self.options.enable_llm:
            return self._strategies["sliding_window"]

        if content_type == ContentType.STRUCTURED:
            return self._strategies["sliding_window"]

        if ratio > self.options.llm_threshold:
            return self._strategies["llm_summarize"]

        if content_type == ContentType.FREE_TEXT:
            return self._strategies["llm_summarize"]

        return self._strategies["sliding_window"]

    def _classify_content(self, text: str) -> ContentType:
        structured_patterns = [
            r"^\s*[\[{]",
            r"^\s*\d+\.",
            r"^\s*[-*]\s",
            r"```",
            r"\|.+\|.+\|",
        ]

        for pattern in structured_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return ContentType.STRUCTURED

        if len(text) < 200:
            return ContentType.STRUCTURED

        return ContentType.FREE_TEXT


class HybridCompressor:
    def __init__(self, config: Optional[HybridOptions] = None, llm_client=None):
        self.config = config or HybridOptions(enable_llm=llm_client is not None)
        self.llm_client = llm_client

        self._strategy = HybridStrategy(self.config, llm_client)
        self._truncation = TruncationStrategy()
        self._sliding = SlidingWindowStrategy(
            window_size=self.config.window_size, overlap=self.config.window_overlap
        )

    def compress(
        self, text: str, max_tokens: int, strategy: str = "auto"
    ) -> CompressionResult:
        if strategy == "auto":
            return self._strategy.compress(text, max_tokens)

        if strategy == "truncation":
            return self._truncation.compress(text, max_tokens)

        if strategy == "sliding_window":
            return self._sliding.compress(text, max_tokens)

        if strategy == "llm_summarize":
            llm_strategy = LLMSummarizeStrategy(self.llm_client, self.config.llm_model)
            return llm_strategy.compress(text, max_tokens)

        if strategy == "hybrid":
            return self._strategy.compress(text, max_tokens)

        return self._truncation.compress(text, max_tokens)

    def select_strategy(
        self,
        text: str,
        max_tokens: int,
        latency_requirement: LatencyRequirement = LatencyRequirement.MEDIUM,
    ) -> str:
        original = count_tokens(text)

        if original <= max_tokens:
            return "none"

        ratio = original / max_tokens
        content_type = self._strategy._classify_content(text)

        if latency_requirement == LatencyRequirement.LOW:
            return "truncation"

        if not self.config.enable_llm:
            return "sliding_window"

        if content_type == ContentType.STRUCTURED:
            return "sliding_window"

        if ratio > self.config.llm_threshold:
            return "llm_summarize"

        return "hybrid"


def count_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def create_compressor(
    enable_llm: bool = True, llm_client=None, latency: str = "medium"
) -> HybridCompressor:
    latency_req = LatencyRequirement(latency)

    config = HybridOptions(
        enable_llm=enable_llm and llm_client is not None,
        llm_model="gpt-4o-mini",
        latency_requirement=latency_req,
    )

    return HybridCompressor(config, llm_client)
