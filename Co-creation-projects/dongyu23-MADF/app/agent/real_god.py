import json
import logging
import re
from typing import Any, Dict, Generator, List, Optional

from hello_agents import ReActAgent, ToolRegistry
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from app.agent.agent import create_helloagents_config, create_helloagents_llm, run_simple_agent
from app.core.config import settings
from app.agent.stepsearch import StepSearchMCPClient, StepSearchPersonaTool
from utils import parse_json_from_response

logger = logging.getLogger(__name__)


class _StepSearchToolAdapter(Tool):
    """Expose StepSearch MCP search/fetch through the HelloAgents Tool API."""

    def __init__(self, backend: StepSearchPersonaTool):
        super().__init__(
            name="search_persona_sources",
            description="使用 StepSearch MCP 搜索并抓取真实人物资料。",
        )
        self.backend = backend

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="人物或领域及待核实事实的搜索关键词",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        query = str(parameters.get("query", "")).strip()
        if not query:
            return ToolResponse.error(code="INVALID_QUERY", message="搜索关键词不能为空")
        try:
            text = self.backend.search(query)
            return ToolResponse.success(text=text, data={"query": query, "provider": "stepsearch"})
        except Exception:
            logger.exception("StepSearch MCP request failed")
            return ToolResponse.error(code="SEARCH_FAILED", message="搜索服务暂时不可用")


class RealGodAgent:
    """Persona generator implemented with HelloAgents ReActAgent and tools."""

    def __init__(self, max_steps: int = 6):
        self.max_steps = max_steps

    @staticmethod
    def _supports_persona_search() -> bool:
        return "stepfun.com" in settings.final_base_url.lower()

    def _get_persona_count(self, prompt: str) -> int:
        if self._explicit_requested_name(prompt):
            return 1
        messages = [
            {"role": "system", "content": "从用户描述中提取角色数量，只输出 1 到 5 的整数；未指定时输出 1。"},
            {"role": "user", "content": prompt},
        ]
        try:
            content = run_simple_agent(
                "PersonaCountAgent",
                messages[0]["content"],
                messages[1]["content"],
            )
            match = re.search(r"\d+", content)
            return min(max(int(match.group()), 1), 5) if match else 1
        except Exception:
            return 1

    @staticmethod
    def _explicit_requested_name(prompt: str) -> Optional[str]:
        """Extract a directly named person while leaving topic requests flexible."""
        text = prompt.strip().strip("。！？!?.,，")
        for pattern in (
            r"必须生成\s*([^，。；;！？!?]{2,40}?)\s*本人",
            r"(?:请)?(?:创建|生成|塑造|扮演)(?:一位|一个|一名)?\s*真实人物\s*([^，。；;！？!?]{2,40})",
        ):
            named_match = re.search(pattern, text)
            if named_match:
                return named_match.group(1).strip(" 《》\"'“”‘’")
        match = re.fullmatch(
            r"(?:请)?(?:创建|生成|塑造|扮演)(?:一位|一个|一名)?\s*([^，。！？!?]{2,40}?)(?:这个)?(?:角色|人物)?",
            text,
        )
        if not match:
            return None

        candidate = match.group(1).strip(" 《》\"'“”‘’")
        generic_endings = (
            "专家", "学者", "科学家", "工程师", "教授", "医生", "律师", "主持人",
            "角色", "人物", "代表", "顾问", "创业者", "程序员", "设计师", "作家",
        )
        if not candidate or candidate.endswith(generic_endings):
            return None
        return candidate

    @staticmethod
    def _normalize_person_name(value: str) -> str:
        return re.sub(r"[\s·•・.\-_《》'\"“”‘’]", "", value).casefold()

    def _build_agent(self, system_prompt: str) -> ReActAgent:
        registry = ToolRegistry()
        if not self._supports_persona_search():
            raise RuntimeError("MADF requires the StepFun model endpoint and StepSearch MCP tool")
        stepsearch = StepSearchPersonaTool()
        registry.register_tool(_StepSearchToolAdapter(stepsearch))
        return ReActAgent(
            name="RealGodAgent",
            llm=create_helloagents_llm(),
            tool_registry=registry,
            system_prompt=system_prompt,
            config=create_helloagents_config(),
            max_steps=self.max_steps,
        )

    @staticmethod
    def _matches_user_request(prompt: str, persona: Dict[str, Any]) -> bool:
        """Reject a grounded result that researched the wrong named person or topic."""
        explicit_name = RealGodAgent._explicit_requested_name(prompt)
        if explicit_name:
            expected = RealGodAgent._normalize_person_name(explicit_name)
            actual = RealGodAgent._normalize_person_name(str(persona.get("name", "")))
            identity_text = RealGodAgent._normalize_person_name(
                " ".join(
                    str(persona.get(field, ""))
                    for field in ("name", "title", "bio", "stance", "system_prompt")
                )
            )
            if expected not in actual and actual not in expected and expected not in identity_text:
                return False

        messages = [
            {
                "role": "system",
                "content": (
                    "判断候选人物是否满足用户的角色生成需求。重点检查用户点名的人物、职业和主题是否一致。"
                    "如果用户说‘创建X’且X本身是明确人物或角色名，候选人物必须就是X，不能创建同一作品或领域的其他人物。"
                    "只输出 YES 或 NO；主题型开放请求只要合理匹配就输出 YES。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户需求：{prompt}\n"
                    f"候选人物：{json.dumps(persona, ensure_ascii=False)}"
                ),
            },
        ]
        try:
            content = run_simple_agent(
                "PersonaAlignmentAgent",
                messages[0]["content"],
                messages[1]["content"],
            ).strip().upper()
            return content.startswith("YES")
        except Exception:
            logger.exception("Persona request-alignment check failed")
            # Provider-side verification failure must not discard an otherwise
            # valid grounded result; generation errors still use the normal path.
            return True

    @staticmethod
    def _parse_persona(agent: ReActAgent, raw: str) -> Optional[Dict[str, Any]]:
        persona = parse_json_from_response(raw)
        if not isinstance(persona, (dict, list)):
            repair = agent.run(
                "上一次输出不是可解析 JSON。请不要解释、不要 Markdown，只返回一个紧凑且完整的合法 JSON 对象；"
                "必须包含 name、title、bio、theories（7 个字符串）、stance、system_prompt。"
            )
            persona = parse_json_from_response(repair)
        if isinstance(persona, list):
            persona = persona[0] if persona else None
        return persona if isinstance(persona, dict) else None

    def _generate_one(
        self,
        prompt: str,
        index: int,
        total: int,
        generated_names: List[str],
        existing_names: List[str],
    ) -> Dict[str, Any]:
        excluded = generated_names + existing_names
        research_instruction = (
            "必须使用注册的 StepSearch 搜索工具核实人物背景，再返回结果。"
            if "stepfun.com" in settings.final_base_url.lower()
            else "必须使用注册的搜索工具核实人物背景，再返回结果。"
            if self._supports_persona_search()
            else "当前模型端点未配置兼容的外部搜索工具；请依据可靠常识生成，并避免无法核实的细节。"
        )
        system_prompt = f"""
你是负责创建真实、立体人物角色的研究智能体。{research_instruction}
返回一个合法 JSON 对象，不要 Markdown 代码块，不要额外解释。对象必须包含：
name、title、bio、theories、stance、system_prompt。theories 必须是 7 个字符串的数组；
bio 与 stance 应具体、有事实依据，system_prompt 使用第一人称并指导角色自然参与讨论。
若用户未指定具体人物，应选择符合主题且有公开资料的人物。禁止捏造真实人物经历。
""".strip()
        agent = self._build_agent(system_prompt)
        task = f"""
用户需求：{prompt}
当前生成第 {index} 位，共 {total} 位。
不得生成这些已有角色：{json.dumps(excluded, ensure_ascii=False)}
当用户在同一需求中依次描述了多个角色时，必须严格生成第 {index} 个描述对应的角色，
不得用其他序号的角色替代；其职业、立场、风险偏好等关键要求都必须与第 {index} 个描述一致。
如果用户明确点名某个人物（例如“创建哈利波特”），必须生成该人物本人，禁止生成同一作品、家族或领域中的原创人物。
请生成一个与已有角色不同的角色 JSON。
""".strip()
        persona = self._parse_persona(agent, agent.run(task))
        alignment_request = (
            f"{prompt}\n当前只校验第 {index} 位（共 {total} 位）；"
            f"候选角色不得与这些已生成角色重复：{json.dumps(excluded, ensure_ascii=False)}。"
        )
        if persona and not self._matches_user_request(alignment_request, persona):
            logger.warning(
                "Generated persona %r did not match the user request; retrying once",
                persona.get("name"),
            )
            retry_agent = self._build_agent(system_prompt)
            retry_task = (
                f"{task}\n\n上一次生成了不符合用户需求的人物 {persona.get('name', 'Unknown')}，已被拒绝。"
                "必须严格遵循用户点名的人物或主题，重新使用搜索工具核实后生成；不得再次返回被拒绝的人物。"
            )
            persona = self._parse_persona(retry_agent, retry_agent.run(retry_task))
            if persona and not self._matches_user_request(alignment_request, persona):
                raise ValueError("HelloAgents returned a persona unrelated to the user request")
        if not isinstance(persona, dict) or not persona.get("name"):
            raise ValueError("HelloAgents ReActAgent did not return a valid persona JSON object")
        return persona

    def run(
        self,
        prompt: str,
        n: Optional[int] = None,
        generated_names: Optional[List[str]] = None,
        db_existing_names: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        generated_names = generated_names if generated_names is not None else []
        existing_names = db_existing_names or []
        total = min(max(n or self._get_persona_count(prompt), 1), 5)
        yield {"type": "count", "content": total}

        for index in range(1, total + 1):
            yield {"type": "thought_start", "content": f"开始研究并生成第 {index} 位角色（共 {total} 位）"}
            yield {"type": "progress", "current": index, "total": total}
            try:
                persona = self._generate_one(prompt, index, total, generated_names, existing_names)
            except Exception as exc:
                logger.exception("RealGod generation failed")
                yield {"type": "error", "content": "角色生成失败，请稍后重试"}
                continue
            generated_names.append(persona["name"])
            yield {"type": "result", "content": [persona]}
