"""审稿 Agent（FR-05）。

独立于写作 Agent，只接收「原始需求 + 稿件」，输出结构化 JSON。
解析策略：围栏清洗 → 截取首个 ``{`` 到最后一个 ``}`` → json.loads →
pydantic 校验 → 失败追加纠正提示重试 1 次 → 仍失败返回 None 交编排层降级。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from hello_agents import HelloAgentsLLM, SimpleAgent
from pydantic import ValidationError

from ..config import Settings, get_settings
from ..llm_utils import invoke_with_retry
from ..models import ReviewResult, StoryRequest, TokenUsage
from ..prompts import (
    REVIEWER_PROMPT_VERSION,
    REVIEWER_SYSTEM_PROMPT,
    build_reviewer_user_prompt,
)
from .base import build_agent_config

_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_CORRECTION_PROMPT = (
    "上一次输出不是合法 JSON，或字段不符合要求（必须是 approved / overall_score / "
    "scores / issues / revision_instructions / summary，分数 0–100，未通过时修订建议"
    "不得为空）。请只输出一个 JSON 对象，不要解释，不要代码围栏。"
)


@dataclass
class ReviewOutcome:
    """一次审稿调用的结果。

    Attributes:
        result: 解析成功的审稿结论；为 None 表示解析失败或调用异常。
        raw_text: 模型原始输出（用于落盘复盘）。
        usage: token 用量。
        latency_ms: 累计耗时（毫秒）。
        error: 失败原因，成功时为 None。
        attempts: 调用次数（1 或 2）。
    """

    result: ReviewResult | None
    raw_text: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: int = 0
    error: str | None = None
    attempts: int = 1


def parse_review_json(raw: str) -> ReviewResult | None:
    """从模型输出中提取并校验审稿 JSON。

    Args:
        raw: 模型原始输出，可能包含代码围栏或前后解释文字。

    Returns:
        校验通过的 :class:`ReviewResult`；无法解析或字段非法时返回 None。
    """
    if not raw:
        return None
    text = raw.strip().lstrip("\ufeff")
    fenced = _CODE_FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        payload = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None

    try:
        return ReviewResult.model_validate(payload)
    except ValidationError:
        return None


class ReviewerAgent(SimpleAgent):
    """审稿人智能体：独立判断稿件与需求是否相符。"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        settings: Settings | None = None,
        name: str = "ReviewerAgent",
    ) -> None:
        """初始化审稿 Agent。

        Args:
            llm: 已配置的 LLM 客户端。
            settings: 运行配置，缺省读取环境变量。
            name: Agent 名称，写入 trace。
        """
        self.settings = settings or get_settings()
        super().__init__(
            name=name,
            llm=llm,
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            config=build_agent_config(),
            enable_tool_calling=False,
        )

    def review(self, request: StoryRequest, draft: str) -> ReviewOutcome:
        """审稿并返回结构化结论。

        任何 LLM 异常都不会向上抛出，而是记录在 ``ReviewOutcome.error``，
        由编排层降级为仅规则层审稿（FR-08）。

        Args:
            request: 原始创作请求。
            draft: 待审稿件全文。

        Returns:
            审稿结果；无法解析时 ``result`` 为 None。
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt or ""},
            {"role": "user", "content": build_reviewer_user_prompt(request, draft)},
        ]
        raw_outputs: list[str] = []
        usage = TokenUsage()
        latency = 0

        for attempt in range(1, 3):
            try:
                response = invoke_with_retry(
                    self.llm,
                    messages,
                    temperature=self.settings.reviewer_temperature,
                )
            except Exception as exc:  # noqa: BLE001 - 统一降级处理
                return ReviewOutcome(
                    result=None,
                    raw_text="\n---\n".join(raw_outputs),
                    usage=usage,
                    latency_ms=latency,
                    error=f"审稿 LLM 调用失败：{exc}",
                    attempts=attempt,
                )

            usage = usage + TokenUsage.from_api(getattr(response, "usage", None))
            latency += int(getattr(response, "latency_ms", 0) or 0)
            raw = getattr(response, "content", "") or ""
            raw_outputs.append(raw)

            result = parse_review_json(raw)
            if result is not None:
                return ReviewOutcome(
                    result=result,
                    raw_text=raw,
                    usage=usage,
                    latency_ms=latency,
                    attempts=attempt,
                )

            if attempt == 1:
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": _CORRECTION_PROMPT},
                ]

        return ReviewOutcome(
            result=None,
            raw_text="\n---\n".join(raw_outputs),
            usage=usage,
            latency_ms=latency,
            error="审稿输出连续两次无法解析为合法 JSON，已降级为仅规则层审稿。",
            attempts=2,
        )
