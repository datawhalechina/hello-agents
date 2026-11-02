"""数据模型。

本模块定义请求、审稿结论、单轮记录与最终结果的 pydantic 模型，
前端、API、CLI 与编排层共用同一套校验规则（FR-01、6.1、6.2）。
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_Keyword = Annotated[str, Field(min_length=1, max_length=20)]


class Genre(str, Enum):
    """支持的创作体裁。"""

    NOVEL = "novel"
    SCRIPT = "script"
    POEM = "poem"

    @property
    def label(self) -> str:
        """中文名称，用于提示词与展示。"""
        return {"novel": "小说", "script": "剧本", "poem": "诗歌"}[self.value]


class Severity(str, Enum):
    """审稿问题严重级别，fatal 会直接否决稿件。"""

    FATAL = "fatal"
    MAJOR = "major"
    MINOR = "minor"

    @property
    def rank(self) -> int:
        """排序权重，数值越小越严重。"""
        return {"fatal": 0, "major": 1, "minor": 2}[self.value]


class RunStatus(str, Enum):
    """一次运行的最终状态（6.3 状态机）。"""

    APPROVED = "approved"
    MAX_ROUNDS_REACHED = "max_rounds_reached"
    DEGRADED = "degraded"
    FAILED = "failed"


class TokenUsage(BaseModel):
    """Token 用量统计，支持跨轮次累加。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_api(cls, usage: dict | None) -> "TokenUsage":
        """从 OpenAI 兼容接口返回的 usage 字典构造统计对象。

        Args:
            usage: 形如 ``{"prompt_tokens": 1, "completion_tokens": 2,
                "total_tokens": 3}``。

        Returns:
            归一化后的 :class:`TokenUsage`，缺失字段按 0 处理。
        """
        if not usage:
            return cls()
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        total = int(usage.get("total_tokens", prompt + completion) or 0)
        return cls(
            prompt_tokens=prompt, completion_tokens=completion, total_tokens=total
        )

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """累加两次调用的用量。"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class StoryRequest(BaseModel):
    """一次创作请求。

    Attributes:
        prompt: 创作需求，去除首尾空白后 10–2000 字符。
        genre: 体裁。
        style: 风格描述，可为空。
        target_length: 目标长度；小说/剧本按字数，诗歌约按字数换算行数。
        must_include: 必须包含的元素，最多 5 项，每项不超过 20 字符。
        forbidden: 禁止出现的元素，最多 5 项，每项不超过 20 字符。
        max_rounds: 最大修订轮次，0 表示只生成不修订（仍审稿）。
    """

    model_config = ConfigDict(extra="ignore")

    prompt: str = Field(min_length=10, max_length=2000)
    genre: Genre
    style: str | None = Field(default=None, max_length=100)
    target_length: int = Field(default=1200, ge=200, le=5000)
    must_include: list[_Keyword] = Field(default_factory=list, max_length=5)
    forbidden: list[_Keyword] = Field(default_factory=list, max_length=5)
    max_rounds: int = Field(default=2, ge=0, le=3)

    @field_validator("prompt", mode="before")
    @classmethod
    def _strip_prompt(cls, value: object) -> object:
        """去除提示词首尾空白，空白串交由长度约束拦截。"""
        return value.strip() if isinstance(value, str) else value

    @field_validator("style", mode="before")
    @classmethod
    def _normalize_style(cls, value: object) -> object:
        """空字符串归一为 None。"""
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("must_include", "forbidden", mode="before")
    @classmethod
    def _normalize_keywords(cls, value: object) -> object:
        """支持字符串（``|``/`,`/`、` 分隔）输入，并去重、去空白。"""
        if value is None:
            return []
        if isinstance(value, str):
            items: list[object] = re.split(r"[|,，、]", value)
        elif isinstance(value, (list, tuple, set)):
            items = list(value)
        else:
            return value

        normalized: list[str] = []
        for item in items:
            text = str(item).strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized


class ReviewIssue(BaseModel):
    """单条审稿问题（规则层与 LLM 层共用）。"""

    severity: Severity
    category: str = Field(min_length=1, max_length=40)
    quote: str = Field(default="", max_length=300)
    problem: str = Field(min_length=1, max_length=500)
    suggestion: str = Field(default="", max_length=500)


class ReviewScores(BaseModel):
    """四维评分，分值 0–100。"""

    relevance: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    genre_format: int = Field(ge=0, le=100)
    style: int = Field(ge=0, le=100)

    @property
    def weighted(self) -> int:
        """按 40/20/20/20 权重计算加权总分（四舍五入）。"""
        raw = (
            self.relevance * 0.4
            + self.completeness * 0.2
            + self.genre_format * 0.2
            + self.style * 0.2
        )
        return int(round(raw))


class ReviewResult(BaseModel):
    """一轮审稿结论。

    Notes:
        - ``overall_score`` 与四维加权结果偏差超过 5 分时，以加权结果为准（6.2）。
        - 未通过时 ``revision_instructions`` 不得为空，否则视为解析失败。
    """

    approved: bool
    overall_score: int = Field(ge=0, le=100)
    scores: ReviewScores
    issues: list[ReviewIssue] = Field(default_factory=list, max_length=5)
    revision_instructions: list[str] = Field(default_factory=list, max_length=8)
    summary: str = Field(min_length=20, max_length=300)

    @field_validator("summary", mode="before")
    @classmethod
    def _strip_summary(cls, value: object) -> object:
        """去除摘要首尾空白。"""
        return value.strip() if isinstance(value, str) else value

    @field_validator("revision_instructions", mode="before")
    @classmethod
    def _normalize_instructions(cls, value: object) -> object:
        """清洗修订建议：去空白、去重、忽略空项。"""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            return value
        result: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result

    @model_validator(mode="after")
    def _enforce_consistency(self) -> "ReviewResult":
        """校正总分并校验“未通过必须有修订建议”。"""
        weighted = self.scores.weighted
        if abs(self.overall_score - weighted) > 5:
            self.overall_score = weighted
        if not self.approved and not self.revision_instructions:
            raise ValueError("未通过时 revision_instructions 不能为空")
        return self


class RoundRecord(BaseModel):
    """一轮“生成/修订 + 审稿”的完整记录。"""

    round: int = Field(ge=1)
    draft: str
    review: ReviewResult | None = None
    rule_issues: list[ReviewIssue] = Field(default_factory=list)
    merged_issues: list[ReviewIssue] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = Field(default=0, ge=0)
    approved: bool = False
    overall_score: int = Field(default=0, ge=0, le=100)
    degraded: bool = False
    error: str | None = None

    @property
    def scores(self) -> ReviewScores | None:
        """本轮四维评分（降级时为 None）。"""
        return self.review.scores if self.review else None


class GenerationResult(BaseModel):
    """一次运行的最终返回结果。"""

    run_id: str
    request: StoryRequest
    status: RunStatus
    final_text: str = ""
    rounds: list[RoundRecord] = Field(default_factory=list)
    best_round: int | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    error: str | None = None
    model: str = ""
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


def sort_issues(issues: list[ReviewIssue]) -> list[ReviewIssue]:
    """按严重级别稳定排序问题列表。

    Args:
        issues: 待排序问题。

    Returns:
        新列表，顺序为 fatal → major → minor。
    """
    return sorted(issues, key=lambda issue: issue.severity.rank)


def merge_issues(
    rule_issues: list[ReviewIssue], llm_issues: list[ReviewIssue]
) -> list[ReviewIssue]:
    """合并规则层与 LLM 层问题并去重。

    去重键为 ``(severity, category, quote 前 60 字, problem 前 60 字)``，
    避免同一问题在两处重复展示。

    Args:
        rule_issues: 规则层问题。
        llm_issues: LLM 审稿问题。

    Returns:
        去重并按严重级别排序的问题列表。
    """
    merged: list[ReviewIssue] = []
    seen: set[tuple[str, str, str, str]] = set()
    for issue in list(rule_issues) + list(llm_issues):
        key = (
            issue.severity.value,
            issue.category,
            issue.quote[:60],
            issue.problem[:60],
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(issue)
    return sort_issues(merged)

