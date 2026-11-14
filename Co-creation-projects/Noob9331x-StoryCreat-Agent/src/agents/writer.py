"""写作 Agent（FR-03、FR-07）。

基于 hello-agents 的 ``SimpleAgent``，负责首稿生成与按审稿意见修订。
每次调用前清空历史，避免不同请求之间串上下文（C-03 / R-06）。
"""

from __future__ import annotations

import re

from hello_agents import HelloAgentsLLM, SimpleAgent

from ..config import Settings, get_settings
from ..errors import WriterGenerationError
from ..llm_utils import invoke_with_retry
from ..models import ReviewIssue, StoryRequest, TokenUsage
from ..prompts import (
    REVISION_PROMPT_VERSION,
    WRITER_PROMPT_VERSION,
    WRITER_SYSTEM_PROMPT,
    build_revision_user_prompt,
    build_writer_user_prompt,
)
from ..rules import looks_like_refusal
from .base import AgentOutput, build_agent_config

_META_PREAMBLE = re.compile(
    r"^(?:好的|当然|没问题)[，,。!！].*$"
    r"|^以下是.*$"
    r"|^下面(?:是|为)(?:你|您).*$"
    r"|^根据(?:你|您)的(?:需求|要求).*$"
    r"|^我(?:将|来|会)(?:为|帮)(?:你|您).*$"
    r"|^(?:正文|正文如下|作品|故事|小说|剧本|诗歌)[:：]\s*$"
)
_META_CLOSING = re.compile(r"^(?:希望|祝)(?:你|您)(?:喜欢|满意).*$|^以上(?:就是|是).*$")
_CORRECTION_HINT = (
    "\n\n注意：上一次输出为空或包含“作为 AI”“以下是”等元话语。"
    "请直接输出完整正文，不要任何解释、前言或结语。"
)


def clean_generated_text(raw: str) -> str:
    """清洗模型输出，只保留正文。

    处理内容：统一换行、去除代码围栏、去除“好的，以下是……”等前置语、
    去除“希望你喜欢”等结语、去除首尾空行。

    Args:
        raw: 模型原始输出。

    Returns:
        清洗后的正文（可能为空字符串）。
    """
    text = (raw or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    text = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*$", "", text, flags=re.MULTILINE)
    text = text.replace("```", "")

    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and _META_PREAMBLE.match(lines[0].strip()):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and _META_CLOSING.match(lines[-1].strip()):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return "\n".join(lines).strip()


class WriterAgent(SimpleAgent):
    """写作人智能体：生成首稿与修订稿。"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        settings: Settings | None = None,
        name: str = "WriterAgent",
    ) -> None:
        """初始化写作 Agent。

        Args:
            llm: 已配置的 LLM 客户端。
            settings: 运行配置，缺省读取环境变量。
            name: Agent 名称，写入 trace。
        """
        self.settings = settings or get_settings()
        super().__init__(
            name=name,
            llm=llm,
            system_prompt=WRITER_SYSTEM_PROMPT,
            config=build_agent_config(),
            enable_tool_calling=False,
        )

    def generate(self, request: StoryRequest) -> AgentOutput:
        """根据需求生成首稿。

        Args:
            request: 创作请求。

        Returns:
            清洗后的正文、用量、耗时与提示词版本。

        Raises:
            WriterGenerationError: 连续两次输出为空或拒答。
            LLMCallError: LLM 调用重试后仍失败。
        """
        prompt = build_writer_user_prompt(request)
        return self._generate_checked(prompt, WRITER_PROMPT_VERSION)

    def revise(
        self,
        request: StoryRequest,
        draft: str,
        issues: list[ReviewIssue],
        revision_instructions: list[str],
    ) -> AgentOutput:
        """根据审稿意见修订稿件。

        Args:
            request: 原始创作请求（完整保留用户需求）。
            draft: 当前稿件全文。
            issues: 合并后的审稿问题。
            revision_instructions: 审稿人的修订指令。

        Returns:
            修订后的完整新稿。

        Raises:
            WriterGenerationError: 连续两次输出为空或拒答。
            LLMCallError: LLM 调用重试后仍失败。
        """
        prompt = build_revision_user_prompt(
            request, draft, issues, revision_instructions
        )
        return self._generate_checked(prompt, REVISION_PROMPT_VERSION)

    def _generate_checked(self, user_prompt: str, prompt_version: str) -> AgentOutput:
        """调用 LLM 并对空输出/拒答做一次重试。"""
        last_text = ""
        total_usage = TokenUsage()
        total_latency = 0
        for attempt in range(1, 3):
            self.clear_history()
            prompt = user_prompt if attempt == 1 else user_prompt + _CORRECTION_HINT
            messages = [
                {"role": "system", "content": self.system_prompt or ""},
                {"role": "user", "content": prompt},
            ]
            response = invoke_with_retry(
                self.llm,
                messages,
                temperature=self.settings.writer_temperature,
            )
            usage = TokenUsage.from_api(getattr(response, "usage", None))
            latency = int(getattr(response, "latency_ms", 0) or 0)
            total_usage = total_usage + usage
            total_latency += latency

            text = clean_generated_text(getattr(response, "content", "") or "")
            last_text = text
            if not looks_like_refusal(text):
                return AgentOutput(
                    text=text,
                    usage=total_usage,
                    latency_ms=total_latency,
                    prompt_version=prompt_version,
                    meta={"attempts": attempt},
                )

        raise WriterGenerationError(
            "写作 Agent 连续两次返回空正文或拒答内容，已终止本次生成。"
            f"最后一次输出片段：{(last_text or '（空）')[:100]}"
        )
