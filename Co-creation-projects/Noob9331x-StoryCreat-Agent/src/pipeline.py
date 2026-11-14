"""闭环编排（FR-06、FR-07、FR-08）。

职责：轮次控制、规则层 + LLM 层合并判定、最佳稿保留、降级与落盘。
写作与审稿 Agent 通过构造函数注入，便于用 FakeLLM 做离线单测。
"""

from __future__ import annotations

from hello_agents import HelloAgentsLLM

from .agents.base import AgentOutput
from .agents.reviewer import ReviewerAgent
from .agents.writer import WriterAgent
from .config import Settings, get_settings
from .errors import LLMNotConfiguredError, StoryAgentError
from .logging_utils import get_logger
from .models import (
    GenerationResult,
    ReviewIssue,
    ReviewScores,
    RoundRecord,
    RunStatus,
    Severity,
    StoryRequest,
    TokenUsage,
    merge_issues,
    sort_issues,
)
from .prompts import REVIEWER_PROMPT_VERSION
from .rules import run_rule_review
from .storage import RunStorage

logger = get_logger("pipeline")

_SEVERITY_DELTA = {Severity.FATAL: 30, Severity.MAJOR: 12, Severity.MINOR: 4}
_SCORE_KEY_BY_CATEGORY = {
    "relevance": "relevance",
    "keyword": "relevance",
    "meta": "relevance",
    "structure": "genre_format",
    "genre_format": "genre_format",
    "format": "genre_format",
    "length": "completeness",
    "completeness": "completeness",
    "style": "style",
    "repetition": "style",
}


def build_llm(settings: Settings) -> HelloAgentsLLM:
    """按配置创建 LLM 客户端。

    Args:
        settings: 运行配置。

    Returns:
        ``HelloAgentsLLM`` 实例。

    Raises:
        LLMNotConfiguredError: 模型名、API Key 或 Base URL 缺失。
    """
    settings.require_llm_config()
    return HelloAgentsLLM(
        model=settings.llm_model_id,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )


def rule_only_scores(issues: list[ReviewIssue]) -> ReviewScores:
    """在审稿降级时，仅依据规则层问题估算四维评分。

    该评分只用于展示与选择最佳稿，不代表 LLM 判断；降级状态会单独标记。

    Args:
        issues: 规则层（或合并后）问题列表。

    Returns:
        0–100 的四维评分。
    """
    values = {"relevance": 95, "completeness": 95, "genre_format": 95, "style": 95}
    for issue in issues:
        key = _SCORE_KEY_BY_CATEGORY.get(issue.category.lower(), "completeness")
        values[key] = max(0, values[key] - _SEVERITY_DELTA[issue.severity])
    return ReviewScores(**values)


def fallback_instructions(issues: list[ReviewIssue]) -> list[str]:
    """把规则层问题转换为可执行的修订指令。"""
    instructions = [
        f"[{issue.category}] {issue.suggestion or issue.problem}"
        for issue in issues
        if issue.severity is not Severity.MINOR
    ]
    return instructions[:5] or ["请对照用户需求逐段检查，修正遗漏的要素与格式问题。"]


def pick_best_round(rounds: list[RoundRecord]) -> RoundRecord | None:
    """选择历史最高分稿；同分时优先更靠后的轮次、更少 fatal 问题。"""
    if not rounds:
        return None
    best = rounds[0]
    for record in rounds[1:]:
        if record.overall_score > best.overall_score:
            best = record
        elif record.overall_score == best.overall_score:
            current_fatal = sum(
                1 for item in record.merged_issues if item.severity is Severity.FATAL
            )
            best_fatal = sum(
                1 for item in best.merged_issues if item.severity is Severity.FATAL
            )
            if current_fatal <= best_fatal:
                best = record
    return best


class StoryPipeline:
    """智能故事生成闭环编排器。"""

    def __init__(
        self,
        writer: WriterAgent,
        reviewer: ReviewerAgent,
        settings: Settings,
        storage: RunStorage,
    ) -> None:
        """注入依赖。

        Args:
            writer: 写作 Agent。
            reviewer: 审稿 Agent。
            settings: 运行配置。
            storage: 结果存储。
        """
        self.writer = writer
        self.reviewer = reviewer
        self.settings = settings
        self.storage = storage

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "StoryPipeline":
        """按配置创建完整流水线（会创建真实 LLM 客户端）。

        Args:
            settings: 运行配置，缺省读取环境变量。

        Returns:
            可执行的 :class:`StoryPipeline`。

        Raises:
            LLMNotConfiguredError: 缺少 LLM 配置。
        """
        settings = settings or get_settings()
        llm = build_llm(settings)
        return cls(
            writer=WriterAgent(llm, settings),
            reviewer=ReviewerAgent(llm, settings),
            settings=settings,
            storage=RunStorage(settings.output_dir),
        )

    def run(
        self, request: StoryRequest, run_id: str | None = None
    ) -> GenerationResult:
        """执行完整的“生成 → 审稿 → 修订 → 定稿”流程。

        Args:
            request: 已校验的创作请求。
            run_id: 可选的运行 ID；缺省自动生成。

        Returns:
            最终结果。运行期异常（写作失败、超时等）会转换为 ``failed`` 状态，
            而不是抛出；仅 LLM 未配置时抛出 :class:`LLMNotConfiguredError`。
        """
        self.settings.require_llm_config()
        run_id = run_id or self.storage.new_run_id()
        self.storage.prepare_run(run_id, request)
        result = GenerationResult(
            run_id=run_id,
            request=request,
            status=RunStatus.FAILED,
            model=self.settings.llm_model_id,
        )
        run_path = self.storage.runs_dir / run_id
        storage_ok = (run_path / "request.json").exists()
        total_rounds = max(1, request.max_rounds)
        current_text = ""
        last_issues: list[ReviewIssue] = []
        last_instructions: list[str] = []
        degraded_any = False
        final_status: RunStatus | None = None

        try:
            for round_no in range(1, total_rounds + 1):
                if round_no == 1:
                    agent_output = self.writer.generate(request)
                else:
                    agent_output = self.writer.revise(
                        request, current_text, last_issues, last_instructions
                    )

                current_text = agent_output.text
                result.usage = result.usage + agent_output.usage
                self._record_prompt_version(result, agent_output)
                storage_ok = self.storage.save_draft(
                    run_id, round_no, current_text
                ) and storage_ok
                storage_ok = (
                    self._trace(
                        run_id=run_id,
                        round_no=round_no,
                        stage="writer",
                        agent="WriterAgent",
                        prompt_version=agent_output.prompt_version,
                        latency_ms=agent_output.latency_ms,
                        usage=agent_output.usage,
                        status="success",
                    )
                    and storage_ok
                )

                rule_issues = run_rule_review(request, current_text)
                outcome = self.reviewer.review(request, current_text)
                result.usage = result.usage + outcome.usage
                result.prompt_versions.setdefault(
                    "reviewer", REVIEWER_PROMPT_VERSION
                )
                storage_ok = (
                    self._trace(
                        run_id=run_id,
                        round_no=round_no,
                        stage="reviewer",
                        agent="ReviewerAgent",
                        prompt_version=REVIEWER_PROMPT_VERSION,
                        latency_ms=outcome.latency_ms,
                        usage=outcome.usage,
                        status="success" if outcome.result else "degraded",
                        error=outcome.error,
                    )
                    and storage_ok
                )

                llm_result = outcome.result
                if llm_result is None:
                    merged = sort_issues(rule_issues)
                    scores = rule_only_scores(merged)
                    overall = scores.weighted
                    approved = not any(
                        item.severity is Severity.FATAL for item in merged
                    )
                    instructions = fallback_instructions(merged)
                else:
                    merged = merge_issues(rule_issues, llm_result.issues)
                    scores = llm_result.scores
                    overall = scores.weighted
                    approved = (
                        llm_result.approved
                        and overall >= self.settings.approve_score
                        and scores.relevance >= self.settings.min_relevance_score
                        and not any(
                            item.severity is Severity.FATAL for item in merged
                        )
                    )
                    instructions = (
                        llm_result.revision_instructions
                        or fallback_instructions(merged)
                    )

                record = RoundRecord(
                    round=round_no,
                    draft=current_text,
                    review=llm_result,
                    rule_issues=rule_issues,
                    merged_issues=merged,
                    usage=agent_output.usage + outcome.usage,
                    latency_ms=agent_output.latency_ms + outcome.latency_ms,
                    approved=approved,
                    overall_score=overall,
                    degraded=llm_result is None,
                    error=outcome.error,
                )
                result.rounds.append(record)
                storage_ok = (
                    self.storage.save_review(
                        run_id,
                        round_no,
                        {
                            "review": (
                                llm_result.model_dump(mode="json")
                                if llm_result
                                else None
                            ),
                            "raw_text": outcome.raw_text,
                            "error": outcome.error,
                            "rule_issues": [
                                item.model_dump(mode="json") for item in rule_issues
                            ],
                            "merged_issues": [
                                item.model_dump(mode="json") for item in merged
                            ],
                            "approved": approved,
                            "overall_score": overall,
                        },
                    )
                    and storage_ok
                )


                last_issues = merged
                last_instructions = instructions

                if llm_result is None:
                    degraded_any = True
                    final_status = RunStatus.DEGRADED
                    result.error = outcome.error
                    break
                if approved:
                    final_status = RunStatus.APPROVED
                    result.error = None
                    break

            if final_status is None:
                final_status = (
                    RunStatus.DEGRADED if degraded_any else RunStatus.MAX_ROUNDS_REACHED
                )
                if final_status is RunStatus.MAX_ROUNDS_REACHED:
                    result.error = (
                        f"已达到最大轮次（{total_rounds} 轮）仍未通过审稿，"
                        "已返回历史最高分稿。"
                    )
        except LLMNotConfiguredError:
            raise
        except StoryAgentError as exc:
            final_status = RunStatus.FAILED
            result.error = str(exc)
            logger.error("运行 %s 失败：%s", run_id, exc)
        except Exception as exc:  # noqa: BLE001 - 兜底，保证接口有可读返回
            final_status = RunStatus.FAILED
            result.error = f"生成过程中发生未预期错误：{exc}"
            logger.exception("运行 %s 发生未预期错误", run_id)

        result.status = final_status or RunStatus.FAILED
        best = pick_best_round(result.rounds)
        if best is not None:
            result.best_round = best.round
            result.final_text = best.draft
        elif result.status is RunStatus.FAILED and not result.error:
            result.error = "生成失败，未产生可用稿件。"
        if result.status is RunStatus.DEGRADED and not result.error:
            result.error = "审稿已降级为仅规则层判定，结果仅供参考。"

        if not storage_ok and result.status is not RunStatus.FAILED:
            result.status = RunStatus.DEGRADED
            result.error = result.error or "结果落盘失败，已返回内存中的结果。"

        saved = self.storage.save_result(run_id, result)
        saved = self.storage.save_final(run_id, result) and saved
        if not saved and result.status is not RunStatus.FAILED:
            result.status = RunStatus.DEGRADED
            result.error = result.error or "结果落盘失败，已返回内存中的结果。"
            self.storage.save_result(run_id, result)
        self.storage.cleanup(self.settings.cleanup_keep_runs)
        return result

    @staticmethod
    def _record_prompt_version(
        result: GenerationResult, output: AgentOutput
    ) -> None:
        """记录本轮写作/修订使用的提示词版本。"""
        key = "revision" if "revision" in output.prompt_version else "writer"
        result.prompt_versions[key] = output.prompt_version

    def _trace(
        self,
        *,
        run_id: str,
        round_no: int,
        stage: str,
        agent: str,
        prompt_version: str,
        latency_ms: int,
        usage: TokenUsage,
        status: str,
        error: str | None = None,
    ) -> bool:
        """写入一行 trace.jsonl，返回是否成功。"""
        return self.storage.append_trace(
            run_id,
            {
                "run_id": run_id,
                "round": round_no,
                "stage": stage,
                "agent": agent,
                "model": self.settings.llm_model_id,
                "prompt_version": prompt_version,
                "latency_ms": latency_ms,
                "usage": usage.model_dump(mode="json"),
                "status": status,
                "error": error,
            },
        )

