"""需求澄清多智能体工作流。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

from hello_agents.tools import ToolRegistry

from .agents import AgentLike, AgentTeam


MAX_REQUIREMENT_LENGTH = 50_000


class WorkflowExecutionError(RuntimeError):
    """工作流输入或某个智能体阶段执行失败。"""


@dataclass(frozen=True)
class WorkflowResult:
    """保留全部中间产物，便于追踪和测试。"""

    requirement: str
    audit: dict[str, object]
    analysis: str
    architecture: str
    risk_review: str
    report: str
    quality: dict[str, object]


class RequirementClarifierWorkflow:
    """协调四个 HelloAgents 智能体完成顺序协作。"""

    def __init__(self, team: AgentTeam, tool_registry: ToolRegistry) -> None:
        self.team = team
        self.tool_registry = tool_registry

    def run(self, requirement: str) -> WorkflowResult:
        """执行确定性初检、三阶段分析、报告整合和结构质检。"""

        requirement = self._validate_requirement(requirement)
        self._clear_agent_histories()
        try:
            return self._run_validated(requirement)
        finally:
            self._clear_agent_histories()

    def _run_validated(self, requirement: str) -> WorkflowResult:
        """处理已校验的单次需求，调用方负责清理 Agent 历史。"""

        audit = self._run_tool(
            "requirement_audit", {"requirement_text": requirement}, "需求初检"
        )

        analysis = self._run_agent(
            "需求分析",
            self.team.analyst,
            "请分析以下原始需求，并参考确定性初检结果。\n\n"
            f"{self._tagged('requirement', requirement)}\n\n"
            f"{self._tagged('audit', json.dumps(audit, ensure_ascii=False, indent=2))}",
        )
        architecture = self._run_agent(
            "方案设计",
            self.team.architect,
            "请根据原始需求和需求分析提出可交付的 MVP 技术方案。\n\n"
            f"{self._tagged('requirement', requirement)}\n\n"
            f"{self._tagged('analysis', analysis)}",
        )
        risk_review = self._run_agent(
            "风险审查",
            self.team.reviewer,
            "请独立审查以下需求分析和技术方案。\n\n"
            f"{self._tagged('requirement', requirement)}\n\n"
            f"{self._tagged('analysis', analysis)}\n\n"
            f"{self._tagged('architecture', architecture)}",
        )
        report = self._run_agent(
            "报告整合",
            self.team.synthesizer,
            "请把以下材料整合为最终需求澄清与技术方案报告。\n\n"
            f"{self._tagged('requirement', requirement)}\n\n"
            f"{self._tagged('audit', json.dumps(audit, ensure_ascii=False, indent=2))}\n\n"
            f"{self._tagged('analysis', analysis)}\n\n"
            f"{self._tagged('architecture', architecture)}\n\n"
            f"{self._tagged('risk_review', risk_review)}",
        )

        quality = self._run_tool(
            "report_quality_check", {"report_text": report}, "报告质检"
        )

        return WorkflowResult(
            requirement=requirement,
            audit=audit,
            analysis=analysis,
            architecture=architecture,
            risk_review=risk_review,
            report=report,
            quality=quality,
        )

    @staticmethod
    def save_report(result: WorkflowResult, output_path: str | Path) -> Path:
        """以 UTF-8 保存最终 Markdown 报告。"""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.report.rstrip() + "\n", encoding="utf-8")
        return path

    @staticmethod
    def _validate_requirement(requirement: str) -> str:
        if not isinstance(requirement, str):
            raise WorkflowExecutionError("需求必须是字符串")
        requirement = requirement.strip()
        if not requirement:
            raise WorkflowExecutionError("需求不能为空")
        if len(requirement) > MAX_REQUIREMENT_LENGTH:
            raise WorkflowExecutionError(
                f"需求文本不能超过 {MAX_REQUIREMENT_LENGTH} 个字符"
            )
        return requirement

    @staticmethod
    def _run_agent(stage: str, agent: AgentLike, prompt: str) -> str:
        try:
            response = agent.run(prompt)
        except Exception as exc:
            raise WorkflowExecutionError(f"{stage}阶段执行失败：{exc}") from exc
        if not isinstance(response, str) or not response.strip():
            raise WorkflowExecutionError(f"{stage}阶段返回了空结果")
        return response.strip()

    def _run_tool(
        self, name: str, parameters: dict[str, object], stage: str
    ) -> dict[str, object]:
        """通过官方 ToolRegistry 获取工具并解析其字符串协议。"""

        tool = self.tool_registry.get_tool(name)
        if tool is None:
            raise WorkflowExecutionError(f"{stage}失败：工具 {name} 未注册")
        try:
            raw_result = tool.run(parameters)
        except Exception as exc:
            raise WorkflowExecutionError(f"{stage}失败：工具执行异常：{exc}") from exc
        try:
            payload = json.loads(raw_result)
        except (TypeError, ValueError) as exc:
            raise WorkflowExecutionError(f"{stage}失败：工具返回的不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise WorkflowExecutionError(f"{stage}失败：工具结果必须是 JSON 对象")
        if not payload.get("ok"):
            raise WorkflowExecutionError(
                f"{stage}失败：{payload.get('message', '未知工具错误')}"
            )
        return payload

    def _clear_agent_histories(self) -> None:
        """避免多次运行时把上一条需求带入下一条需求。"""

        for agent in (
            self.team.analyst,
            self.team.architect,
            self.team.reviewer,
            self.team.synthesizer,
        ):
            clear_history = getattr(agent, "clear_history", None)
            if callable(clear_history):
                clear_history()

    @staticmethod
    def _tagged(tag: str, content: str) -> str:
        """转义不可信内容，防止内容伪造工作流边界标签。"""

        return f"<{tag}>\n{escape(content, quote=False)}\n</{tag}>"
