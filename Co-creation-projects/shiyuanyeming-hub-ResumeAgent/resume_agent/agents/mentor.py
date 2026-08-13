"""Structured fact-audit and evidence-question specialist agents."""

import json
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

from resume_agent.agents.prompts import FACT_AUDIT_PROMPT, QUESTION_WRITER_PROMPT
from resume_agent.agents.structured import AgentRunner, run_structured
from resume_agent.application.question_planner import QuestionPlan
from resume_agent.domain.models import (
    CareerFactBase,
    CareerTarget,
    ConfidenceStatus,
    Experience,
    FactProposal,
    FactValue,
    InterviewSession,
    QualityDimension,
    Specificity,
)
from resume_agent.domain.quality import evaluate_experience


class ProposedFactPayload(BaseModel):
    text: str
    confidence: Literal["unverified", "estimated"] = "unverified"
    specificity: Specificity = Specificity.PRESENT
    sensitive: bool = False


class FactAuditPayload(BaseModel):
    dimension: QualityDimension
    values: List[ProposedFactPayload] = Field(min_length=1)
    rationale: str = ""


class QuestionPayload(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def validate_single_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be empty")
        if stripped.count("?") + stripped.count("？") != 1:
            raise ValueError("response must contain exactly one question")
        return stripped


class StructuredFactAuditAgent:
    def __init__(self, runner: AgentRunner) -> None:
        self.runner = runner

    def propose(
        self,
        message: str,
        session: InterviewSession,
        base: CareerFactBase,
    ) -> FactProposal:
        if session.active_experience_id is None:
            raise ValueError("fact audit requires an active experience")
        experience = base.get_experience(session.active_experience_id)
        prompt = (
            f"{FACT_AUDIT_PROMPT}\n"
            f"目标岗位：{base.target.model_dump_json()}\n"
            f"当前经历：{experience.model_dump_json()}\n"
            f"用户本轮回答：{message}\n"
            "输出字段：dimension、values、rationale。"
        )
        payload = run_structured(self.runner, prompt, FactAuditPayload)
        source_ids = [
            item.id for item in session.messages[-1:] if item.role == "user"
        ]
        values = [
            FactValue(
                text=value.text,
                confidence=ConfidenceStatus(value.confidence),
                specificity=value.specificity,
                sensitive=value.sensitive,
                source_message_ids=source_ids,
            )
            for value in payload.values
        ]
        return FactProposal(
            fact_base_revision=base.revision,
            experience_id=session.active_experience_id,
            dimension=payload.dimension,
            values=values,
            rationale=payload.rationale,
        )


class StructuredQuestionWriterAgent:
    def __init__(self, runner: AgentRunner) -> None:
        self.runner = runner

    def write(
        self,
        plan: QuestionPlan,
        experience: Experience,
        target: CareerTarget,
    ) -> str:
        report = evaluate_experience(experience)
        prompt = (
            f"{QUESTION_WRITER_PROMPT}\n"
            f"目标岗位：{target.model_dump_json()}\n"
            f"经历：{experience.model_dump_json()}\n"
            f"当前质量评分：{report.model_dump_json()}\n"
            f"本轮维度：{plan.dimension.value}\n"
            f"追问阶段：{plan.escalation}\n"
        )
        return run_structured(self.runner, prompt, QuestionPayload).question


class DeterministicQuestionWriter:
    """Offline fallback that still follows the mentor escalation contract."""

    _DIRECT = {
        QualityDimension.CONTEXT: "这段经历当时要解决的具体问题或背景是什么？",
        QualityDimension.RESPONSIBILITY: "在这项工作中，哪一部分是你本人直接负责的？",
        QualityDimension.ACTION: "为了完成这项工作，你本人具体采取了什么行动？",
        QualityDimension.METHOD: "你完成这项工作时使用了哪些工具、方法或判断过程？",
        QualityDimension.RESULT: "这项工作最终产生了什么结果或变化？",
        QualityDimension.EVIDENCE: "有什么数字、交付物或反馈可以证明这项工作的效果？",
    }

    _RECALL_ANCHORS = {
        QualityDimension.CONTEXT: "回想一下当时触发这项工作的具体背景、业务需求或要解决的问题是什么？",
        QualityDimension.RESPONSIBILITY: "回想当时的分工，哪一部分是明确交给你本人负责的？",
        QualityDimension.ACTION: "回想执行过程：你当时先做了哪一步，接着具体做了什么？",
        QualityDimension.METHOD: "回想一下你当时如何判断、用了什么工具或方法来推进这项工作？",
        QualityDimension.RESULT: "回想这项工作前后，例如服务人数、频率、耗时或效果发生了什么变化？",
        QualityDimension.EVIDENCE: "回想可佐证的线索：有没有数字、交付物、采用情况或负责人反馈？",
    }

    _ALTERNATIVE_EVIDENCE = {
        QualityDimension.CONTEXT: "如果暂时想不起具体场景，能否从当时的背景、需求或要解决的问题来说明？",
        QualityDimension.RESPONSIBILITY: "如果没有正式职责说明，能否从分工或同事交给你的任务来说明你本人负责什么？",
        QualityDimension.ACTION: "如果不记得完整步骤，能否从你当时的第一步或一个具体动作开始回忆？",
        QualityDimension.METHOD: "如果不记得具体工具，能否说明你采用的流程、判断方法或协作方式？",
        QualityDimension.RESULT: "如果没有数字，能否说明上线采用、流程变化或其他结果？",
        QualityDimension.EVIDENCE: "如果没有数字，是否有交付物、上线采用、流程变化或负责人反馈等替代证据？",
    }

    def write(
        self,
        plan: QuestionPlan,
        experience: Experience,
        target: CareerTarget,
    ) -> str:
        if plan.escalation == "recall_anchors":
            return self._RECALL_ANCHORS[plan.dimension]
        if plan.escalation == "alternative_evidence":
            return self._ALTERNATIVE_EVIDENCE[plan.dimension]
        return self._DIRECT[plan.dimension]
