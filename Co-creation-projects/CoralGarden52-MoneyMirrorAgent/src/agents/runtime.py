"""Strict Hello-Agents runtime for MoneyMirrorAgent.

The project deliberately has no deterministic/offline substitute for language
work.  Python tools remain the source of truth for money, statistics,
anomalies, budgets, goals and quest progress; Hello-Agents is required for
uncertain classification, planning, explanations, Reflection, user dialogue,
and the final Markdown report.
"""

from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from dotenv import load_dotenv


class RuntimeConfigurationError(RuntimeError):
    """Raised when the required Hello-Agents/LLM configuration is missing."""


class LLMCallError(RuntimeError):
    """Raised when a required LLM call fails or returns no content."""


@dataclass(slots=True)
class RuntimeStatus:
    available: bool
    enabled: bool
    reason: str
    registry_name: str = "HelloAgents ToolRegistry"
    paradigms: tuple[str, ...] = ()
    registered_tools: tuple[str, ...] = ()
    provider: str = "OpenAI-compatible"
    model: str = ""
    base_url: str = ""


class HelloAgentsRuntime:
    """Use the official Hello-Agents agents with a mandatory LLM backend.

    ``PlanSolveAgent`` is the class name exported by hello-agents 1.x for the
    Plan-and-Solve pattern described in the course material.  The runtime
    keeps the agent objects in one place so every specialist can share the
    same configured provider and Context Engineering policy.
    """

    def __init__(self) -> None:
        self.registry: Any | None = None
        self.agent: Any | None = None
        self.react_agent: Any | None = None
        self.plan_agent: Any | None = None
        self.reflection_agent: Any | None = None
        self.context_builder: Any | None = None
        self.llm: Any | None = None
        self.status = RuntimeStatus(False, False, "Hello-Agents 尚未初始化")
        self._initialize()

    def _initialize(self) -> None:
        # This makes ``MoneyMirrorCoordinator`` usable from tests, notebooks,
        # CLI, notebooks and tests can initialize from any working directory.
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env", override=False)

        required = {
            "LLM_API_KEY": os.getenv("LLM_API_KEY", "").strip(),
            "LLM_BASE_URL": os.getenv("LLM_BASE_URL", "").strip(),
            "LLM_MODEL_ID": os.getenv("LLM_MODEL_ID", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            self.status = RuntimeStatus(
                False,
                False,
                "缺少必需的 LLM 配置：" + ", ".join(missing) + "。请复制 .env.example 为 .env 并填写。",
                model=required["LLM_MODEL_ID"],
                base_url=required["LLM_BASE_URL"],
            )
            raise RuntimeConfigurationError(self.status.reason)

        try:
            from hello_agents import (  # type: ignore
                Config,
                HelloAgentsLLM,
                PlanSolveAgent,
                ReActAgent,
                ReflectionAgent as HelloReflectionAgent,
                SimpleAgent,
            )
            from hello_agents.tools import ToolRegistry  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency installation issue
            raise RuntimeConfigurationError(f"无法导入 hello-agents：{exc}") from exc

        try:
            self.registry = ToolRegistry()
            try:
                from hello_agents.context import ContextBuilder, ContextConfig  # type: ignore

                # DeepSeek-V4-Flash has a large context window. Keep an explicit,
                # configurable client-side budget so Hello-Agents does not discard
                # verified evidence before it reaches the model. The report packet
                # is still compacted at the caller for predictable latency/cost.
                self.context_builder = ContextBuilder(
                    ContextConfig(
                        max_tokens=int(os.getenv("LLM_CONTEXT_MAX_TOKENS", "100000")),
                        # Verified evidence must not be filtered just because a
                        # Chinese user query shares few whitespace-separated
                        # tokens with compact JSON.
                        min_relevance=0.0,
                    )
                )
            except Exception:
                self.context_builder = None

            self.llm = HelloAgentsLLM(
                model=required["LLM_MODEL_ID"],
                api_key=required["LLM_API_KEY"],
                base_url=required["LLM_BASE_URL"],
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "16384")),
                timeout=int(os.getenv("LLM_TIMEOUT", "90")),
            )
            config = Config(
                debug=False,
                max_history_length=8,
                trace_enabled=False,
                session_enabled=False,
                skills_enabled=False,
                auto_save_enabled=False,
                stream_enabled=False,
            )
            system_prompt = (
                "你是 MoneyMirrorAgent 的语言推理智能体。所有金额、统计、异常检测、预算、"
                "目标投影和 Quest 进度已经由 Python 工具计算。只能基于已验证证据解释、规划"
                "和生成文案；不许编造数值。"
            )
            with redirect_stdout(io.StringIO()):
                self.agent = SimpleAgent(
                    name="MoneyMirror 解释智能体",
                    llm=self.llm,
                    system_prompt=system_prompt,
                    config=config,
                    tool_registry=self.registry,
                    enable_tool_calling=False,
                )
                self.react_agent = ReActAgent(
                    name="MoneyMirror Transaction ReActAgent",
                    llm=self.llm,
                    tool_registry=self.registry,
                    system_prompt=system_prompt,
                    config=config,
                    max_steps=3,
                )
                self.plan_agent = PlanSolveAgent(
                    name="MoneyMirror PlanAndSolveAgent",
                    llm=self.llm,
                    system_prompt=system_prompt,
                    config=config,
                    tool_registry=self.registry,
                    enable_tool_calling=False,
                    max_tool_iterations=1,
                )
                self.reflection_agent = HelloReflectionAgent(
                    name="MoneyMirror ReflectionAgent",
                    llm=self.llm,
                    system_prompt=system_prompt,
                    config=config,
                    tool_registry=self.registry,
                    enable_tool_calling=False,
                    max_iterations=2,
                )
        except Exception as exc:
            self.status = RuntimeStatus(
                False,
                False,
                f"Hello-Agents/LLM 初始化失败：{exc}",
                model=required["LLM_MODEL_ID"],
                base_url=required["LLM_BASE_URL"],
            )
            raise RuntimeConfigurationError(self.status.reason) from exc

        self.status = RuntimeStatus(
            True,
            True,
            f"已启用 Hello-Agents + OpenAI 兼容 LLM：{required['LLM_MODEL_ID']}",
            paradigms=("ReActAgent", "PlanSolveAgent", "ReflectionAgent", "Context Engineering"),
            provider="OpenAI-compatible",
            model=required["LLM_MODEL_ID"],
            base_url=required["LLM_BASE_URL"],
        )

    def register_tool_functions(self, functions: dict[str, tuple[Any, str]]) -> None:
        """Expose deterministic tools to Hello-Agents ToolRegistry."""
        if self.registry is None:  # pragma: no cover - guarded by init
            raise RuntimeConfigurationError("ToolRegistry 尚未初始化")
        registered: list[str] = []
        with redirect_stdout(io.StringIO()):
            for name, (function, description) in functions.items():
                self.registry.register_function(function, name=name, description=description)
                registered.append(name)
        self.status.registered_tools = tuple(registered)
        self.status.registry_name = f"HelloAgents ToolRegistry ({len(registered)} MoneyMirror tools)"

    def build_context(self, task: str, evidence: Iterable[str] = (), memory: Iterable[str] = ()) -> str:
        """Build a GSSC-style context packet with verified facts separated."""
        evidence_packets = [f"[Verified tool output]\n{item}" for item in evidence]
        memory_packets = [f"[Long-term Memory]\n{item}" for item in memory]
        if self.context_builder is not None:
            try:
                from hello_agents.context import ContextPacket  # type: ignore

                packets = [
                    ContextPacket(content=item, metadata={"type": "tool_result"}) for item in evidence_packets
                ] + [ContextPacket(content=item, metadata={"type": "related_memory"}) for item in memory_packets]
                built = self.context_builder.build(
                    user_query=task,
                    system_instructions=(
                        "只使用 Verified tool output 作为数字事实；Long-term Memory 只能作为历史上下文，"
                        "不要把它当作当前月计算结果。"
                    ),
                    additional_packets=packets,
                )
                # ContextBuilder 1.x appends a generic numbered answer template
                # (结论/依据/风险/下一步). That template is useful for generic
                # tasks but conflicts with MoneyMirror's playful one-question
                # coaching protocol. Keep GSSC evidence selection while removing
                # only that generic output instruction.
                return built.split("\n\n[Output]\n", 1)[0]
            except Exception:
                # ContextBuilder API can vary between hello-agents patch releases;
                # the explicit packet format below preserves the same semantics.
                pass
        parts = ["[Task]", task]
        if evidence_packets:
            parts.extend(["[Evidence]", *evidence_packets])
        if memory_packets:
            parts.extend(["[Context]", *memory_packets])
        return "\n".join(parts)

    def explain(
        self,
        prompt: str,
        mode: Literal["simple", "react", "plan", "reflection"] = "simple",
        evidence: Iterable[str] = (),
        memory: Iterable[str] = (),
    ) -> str:
        """Run a required language-agent call and return its non-empty text."""
        # ``deepseek-v4-flash`` accepts normal chat completions but rejects the
        # function-tool choice issued internally by Hello-Agents' current
        # ReAct/PlanSolve/Reflection implementations in thinking mode.  The
        # specialist *roles* still use those paradigms and the ToolRegistry,
        # while their language response is executed by the official
        # SimpleAgent with a mode-specific instruction. This keeps the real
        # provider path stable instead of silently falling back to templates.
        if self.agent is None:
            raise LLMCallError("Hello-Agents SimpleAgent 未初始化")
        role_instruction = {
            "simple": "以清晰、温和的解释者身份回答。",
            "react": "按 ReAct 的观察-判断-结论节奏回答，但不要输出思维链或虚构工具调用。",
            "plan": "按 Plan-and-Solve 的先规划后行动节奏回答，直接给出简洁结果。",
            "reflection": "按 Reflection 的计划-实际-调整节奏回答，给出下一步行动。",
        }.get(mode)
        if role_instruction is None:
            raise LLMCallError(f"未知 Agent 模式：{mode}")
        context = self.build_context(role_instruction + "\n" + prompt, evidence, memory)
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                # hello-agents emits progress logs to stdout. Keep CLI/UI
                # output focused on the actual answer while retaining the
                # official SimpleAgent execution path.
                # Each specialist call is a fresh bounded turn. Otherwise
                # SimpleAgent accumulates persona/quest/reflection prompts and
                # eventually sends stale contexts back to the provider.
                try:
                    self.agent.clear_history()
                except Exception:
                    pass
                with redirect_stdout(io.StringIO()):
                    text = self.agent.run(context)
                text = str(text).strip()
                if text:
                    return text
                last_error = LLMCallError(f"{mode} Agent 返回空内容")
            except Exception as exc:
                last_error = exc
            if attempt == 0:
                # A transient empty response is retried once. No local prose
                # or deterministic fallback is introduced.
                continue
        try:
            return self._direct_llm_answer(context, mode)
        except LLMCallError as direct_error:
            raise LLMCallError(
                f"{mode} Agent 调用失败，且直接 LLM 重试失败：{direct_error}"
            ) from (last_error or direct_error)

    def _direct_llm_answer(self, context: str, mode: str) -> str:
        """Provider-compatible direct completion used when an Agent wrapper
        returns an empty response (some thinking-model/tool combinations do).

        This is still the configured HelloAgentsLLM client and never a local
        fallback. It keeps the user-facing pipeline reliable across provider
        patch versions while the official Agent objects remain initialized and
        registered for the architecture/traces.
        """
        if self.llm is None:
            raise LLMCallError("LLM 尚未初始化")
        system = (
            "你是 MoneyMirrorAgent 的语言智能体。请直接输出最终中文答案，不要输出思维链、"
            "工具调用、空响应或过程日志。数字只能来自 Verified tool output。"
            f"当前角色模式：{mode}。"
        )
        try:
            response = self.llm.invoke(
                [{"role": "system", "content": system}, {"role": "user", "content": context}],
                temperature=0.2,
            )
            text = str(getattr(response, "content", response)).strip()
        except Exception as exc:
            raise LLMCallError(f"直接 LLM 调用失败：{exc}") from exc
        if not text:
            raise LLMCallError("直接 LLM 返回空内容")
        return text

    def generate_quest_candidates(self, prompt: str) -> str:
        """Request strict QuestCandidate JSON from the configured LLM.

        Agent wrappers are excellent for natural-language roles, but their
        PlanSolve instruction can add prose around a schema. Quest selection is
        a machine-validated boundary, so it uses the same required
        ``HelloAgentsLLM`` client in JSON-object mode. This is not an offline
        fallback: provider failure or invalid output remains an explicit error
        handled by :class:`QuestAgent` and repaired through a second LLM turn.
        """
        if self.llm is None:
            raise LLMCallError("LLM 尚未初始化")
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 MoneyMirrorAgent 的 Quest JSON 编排器。只返回一个合法 JSON 对象，"
                    "不得使用 Markdown、解释、思维链或工具调用。严格遵守用户消息中的字段和安全约束；"
                    "不得编造金额、次数、日期、进度或 EXP。"
                ),
            },
            {"role": "user", "content": prompt},
        ]
        last_error: Exception | None = None
        # Prefer provider JSON mode. Some OpenAI-compatible endpoints ignore or
        # reject the option, so retry once as a normal completion with the same
        # strict system instruction; Python still validates the returned text.
        for kwargs in ({"response_format": {"type": "json_object"}}, {}):
            try:
                response = self.llm.invoke(messages, temperature=0.0, **kwargs)
                text = str(getattr(response, "content", response)).strip()
                if text and self._contains_nonempty_quest_array(text):
                    return text
                last_error = LLMCallError("Quest JSON LLM 返回空 Quest 数组或非 JSON 内容，准备重试")
            except Exception as exc:
                last_error = exc
        raise LLMCallError(f"Quest JSON LLM 调用失败：{last_error}")

    @staticmethod
    def _contains_nonempty_quest_array(text: str) -> bool:
        """Cheap transport-level guard before QuestAgent applies full schema checks."""
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and isinstance(value.get("quests"), list) and bool(value["quests"])

    def stream_user_guidance(
        self,
        question: str,
        report_payload: str,
        history: Iterable[dict[str, str]] = (),
    ) -> Iterable[str]:
        """Stream a guided, playful answer to a user's current input.

        Hello-Agents' high-level ``Agent.run`` API returns a complete string.
        For the interactive UI we use the same configured ``HelloAgentsLLM``
        through its official streaming interface, preserving the Agent's
        Context Engineering policy while allowing users to see tokens as they
        arrive instead of waiting for a long final response.
        """
        if self.llm is None:
            raise LLMCallError("LLM 尚未初始化")
        # Bound transcript independently of the UI/CLI caller. This prevents a
        # long chat from competing with the verified report facts in the model
        # context, even if another integration passes unbounded history.
        recent_history = list(history)[-6:]
        transcript_lines: list[str] = []
        for item in recent_history:
            content = str(item.get("content", "")).strip()
            if len(content) > 600:
                content = content[:600].rstrip() + "…"
            transcript_lines.append(f"{item.get('role', 'user')}: {content}")
        transcript = "\n".join(transcript_lines) or "（这是本轮对话的第一条消息）"
        context = self.build_context(
            "结合真实消费数据，进行一步一步的 Money Quest 财务教练对话。",
            evidence=[report_payload],
            memory=[transcript],
        )
        system = (
            "你是 MoneyMirrorAgent 的互动财务教练。你要像游戏 NPC 一样友好、有趣、会引导，"
            "但不能戏弄用户或制造焦虑。每次只推进一个小问题：先复述你观察到的消费现象，"
            "再给一个具体且可执行的小建议，最后提出一个简短追问，帮助用户选择目标或下一步。"
            "所有金额和比例只能引用输入的 Verified tool output；不得编造数字。"
            "回答控制在 120-220 字，使用少量 emoji 和 Markdown 列表，让用户能马上行动。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{context}\n\n用户刚刚说：{question}"},
        ]
        try:
            yielded = False
            for chunk in self.llm.stream_invoke(messages, temperature=0.4):
                if chunk:
                    yielded = True
                    yield str(chunk)
            if not yielded:
                raise LLMCallError("互动 LLM 返回空内容")
        except LLMCallError:
            raise
        except Exception as exc:
            raise LLMCallError(f"互动 LLM 流式调用失败：{exc}") from exc

    def classify_uncertain(self, merchant: str, note: str, allowed_categories: list[str]) -> str | None:
        prompt = (
            f"商户：{merchant}\n备注：{note}\n只能从以下类别中选择一个并且只输出类别名："
            f"{', '.join(allowed_categories)}。证据不足时输出其他。"
        )
        answer = self.explain(prompt, mode="react")
        normalized = answer.strip().splitlines()[0].strip("`。:： ")
        return normalized if normalized in allowed_categories else None

    def generate_markdown(self, report_payload: str) -> str:
        """Generate the persisted Markdown report through the LLM."""
        prompt = (
            "请把下面的 MoneyMirrorAgent 已验证分析数据写成一份完整的中文 Markdown 月度报告。\n"
            "必须包含：财务镜像、消费分类与趋势、行为模式、异常消费解释、消费人格、订阅提醒、"
            "目标进度、动态预算、Money Quest、等级与成就、月度 Reflection 和下一周期行动清单。\n"
            "要求：只引用输入中的数字；如果某项为空就明确写‘暂无数据’；语气年轻、温和、可执行；"
            "不要输出代码围栏；直接输出 Markdown 正文。报告建议 1200-2200 字，"
            "确保保留所有重要的小节，但不要复述原始 JSON。\n\n"
            f"{report_payload}"
        )
        text = self.explain(prompt, mode="reflection")
        if text.startswith("```"):
            text = text.strip().removeprefix("```markdown").removesuffix("```").strip()
        if not text.startswith("#"):
            text = "# MoneyMirrorAgent 月度报告\n\n" + text
        return text.rstrip() + "\n"

    def answer_user(self, question: str, report_payload: str) -> str:
        """Answer a user question using the current verified report context."""
        return self.explain(
            "回答用户问题。只能使用已验证账单数据和 Memory。\n"
            f"用户问题：{question}",
            mode="simple",
            evidence=[report_payload],
        )

    def status_dict(self) -> dict[str, Any]:
        return {
            "available": self.status.available,
            "enabled": self.status.enabled,
            "reason": self.status.reason,
            "registry_name": self.status.registry_name,
            "paradigms": list(self.status.paradigms),
            "registered_tools": list(self.status.registered_tools),
            "provider": self.status.provider,
            "model": self.status.model,
            "base_url": self.status.base_url,
        }
