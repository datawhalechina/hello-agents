"""Expose bundled paper workflows through HelloAgents' on-demand skill tool."""

from pathlib import Path
from typing import Any

from hello_agents.skills import SkillLoader
from hello_agents.tools.base import ToolParameter
from hello_agents.tools.builtin.skill_tool import SkillTool
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.response import ToolResponse


class PaperSkillTool(SkillTool):
    def __init__(self) -> None:
        # Resolve from the source file so custom DATA_DIR and working directories
        # do not hide the bundled skills or copy them into runtime storage.
        skills_dir = Path(__file__).resolve().parents[3] / "skills"
        super().__init__(skill_loader=SkillLoader(skills_dir=skills_dir))
        # Keep the framework's existing Skill tool for user-provided skills.
        self.name = "PaperSkill"

    def get_parameters(self) -> list[ToolParameter]:
        # These self-contained workflows need no free-form argument expansion.
        return [parameter for parameter in super().get_parameters() if parameter.name == "skill"]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        name = parameters.get("skill")
        available = self.skill_loader.list_skills()
        if not isinstance(name, str) or name not in available:
            # Do not echo arbitrary model-supplied arguments into its context.
            return ToolResponse.error(ToolErrorCode.NOT_FOUND, "请选择一个可用论文技能：" + ", ".join(available))
        return super().run({"skill": name})
