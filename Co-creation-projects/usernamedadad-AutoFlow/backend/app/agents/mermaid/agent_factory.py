from hello_agents import Config, SimpleAgent, ToolRegistry

from app.prompts.standard_code_prompt import STANDARD_CODE_PROMPT
from app.prompts.standard_prompt import STANDARD_PROMPT
from app.prompts.inspire_prompt import INSPIRE_PROMPT
from app.services.llm_service import LLMService
from app.tools.mermaid_validator_tool import MermaidValidatorTool

EXECUTION_HINT = "执行要求：先调用 MermaidValidatorTool 校验；若返回 INVALID 再修复并调用一次；最终仅输出 Mermaid 代码。"


def _prompt_by_mode(mode: str) -> str:
    if mode == "standard-code":
        return STANDARD_CODE_PROMPT
    if mode == "standard":
        return STANDARD_PROMPT
    return INSPIRE_PROMPT


def _fast_config() -> Config:
    return Config(
        trace_enabled=False,
        skills_enabled=False,
        session_enabled=False,
        subagent_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
        stream_enabled=False,
        enable_smart_compression=False,
        temperature=0.2,
    )


def build_agent(mode: str, validator: MermaidValidatorTool) -> SimpleAgent:
    registry = ToolRegistry()
    registry.register_tool(validator)

    return SimpleAgent(
        name=f"plan2flow-{mode}-agent",
        llm=LLMService.create_llm(),
        system_prompt=f"{_prompt_by_mode(mode)}\n{EXECUTION_HINT}",
        tool_registry=registry,
        config=_fast_config(),
        enable_tool_calling=True,
        max_tool_iterations=2,
    )
