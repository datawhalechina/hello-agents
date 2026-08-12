import re
from typing import Any, Dict, List

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


MERMAID_PREFIXES = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "journey",
    "gantt",
    "pie",
    "gitGraph",
    "mindmap",
    "timeline",
)


class MermaidValidatorTool(Tool):
    def __init__(self):
        super().__init__(
            name="MermaidValidatorTool",
            description="校验并修复 Mermaid 代码，返回可渲染代码",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="待校验的 Mermaid 代码",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        code = str(parameters.get("code", "")).strip()
        if not code:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="code 参数不能为空",
            )

        normalized = self._normalize(code)
        valid, errors = self._validate_structure(normalized)

        if valid:
            return ToolResponse.success(
                text=f"VALID\n{normalized}",
                data={"valid": True, "fixed_code": normalized, "errors": []},
            )

        return ToolResponse.partial(
            text=f"INVALID\n{normalized}\n错误: {'; '.join(errors)}",
            data={"valid": False, "fixed_code": normalized, "errors": errors},
        )

    def _normalize(self, code: str) -> str:
        code = code.strip()
        code = code.replace("```mermaid", "").replace("```", "").strip()
        code = code.replace("→", "-->")

        lines = [ln.rstrip() for ln in code.splitlines() if ln.strip()]
        if not lines:
            return "flowchart TD\n    A[空图]"

        first = lines[0].strip()
        if not first.startswith(MERMAID_PREFIXES):
            # 兜底为 flowchart
            lines.insert(0, "flowchart TD")

        return "\n".join(lines)

    def _validate_structure(self, code: str):
        errors = []
        lines = code.splitlines()

        if not lines:
            return False, ["代码为空"]

        first = lines[0].strip()
        if not first.startswith(MERMAID_PREFIXES):
            errors.append("缺少 Mermaid 图类型声明")

        bracket_pairs = [("(", ")"), ("[", "]"), ("{", "}")]
        for left, right in bracket_pairs:
            if code.count(left) != code.count(right):
                errors.append(f"括号不匹配: {left}{right}")

        # flowchart 常见错误：仅有声明但无节点
        if first.startswith(("flowchart", "graph")):
            has_node = any(re.search(r"\w+\s*-->|\w+\[|\w+\(|\w+\{", ln) for ln in lines[1:])
            if not has_node:
                errors.append("flowchart 缺少节点或连线")

        return len(errors) == 0, errors
