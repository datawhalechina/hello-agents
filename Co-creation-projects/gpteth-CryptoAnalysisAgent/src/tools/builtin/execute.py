"""Restricted Python / shell execution."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter

from ...compat import first_text

ALLOWED_COMMANDS = {
    "ls", "pwd", "cat", "head", "tail", "wc", "echo", "python", "python3",
    "pip", "pip3", "git", "grep", "find", "sort", "uniq", "date",
}
DANGEROUS = [
    re.compile(p, re.I) for p in (
        r"rm\s+-r?f", r"sudo", r"chmod\s+777", r"mkfs", r"dd\s+if=",
        r"shutdown", r"reboot", r":\(\)\s*\{", r">\s*/etc/",
    )
]


class ExecuteTool(Tool):
    def __init__(self, cwd: str, timeout: int = 20):
        super().__init__(
            name="execute_code",
            description=(
                "在工作空间内执行代码或白名单命令。"
                "action=python 时执行 Python 片段；action=shell 时执行基础命令。"
            ),
        )
        self.cwd = os.path.abspath(cwd)
        self.timeout = timeout

    def run(self, parameters: Dict[str, Any]) -> str:
        action = str(parameters.get("action") or "python").strip().lower()
        if action == "python":
            code = first_text(parameters, "code")
            if not code:
                return "错误: 请提供 code"
            return self._run(["python3", "-c", code])
        if action == "shell":
            command = first_text(parameters, "command")
            if not command:
                return "错误: 请提供 command"
            if any(rx.search(command) for rx in DANGEROUS):
                return "拒绝执行：命令匹配危险模式"
            binary = command.strip().split()[0]
            if os.path.basename(binary) not in ALLOWED_COMMANDS:
                return f"拒绝执行：{binary} 不在白名单"
            return self._run(command, shell=True)
        return "未知 action，请使用 python 或 shell"

    def _run(self, args, shell: bool = False) -> str:
        try:
            completed = subprocess.run(
                args,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=shell,
            )
        except subprocess.TimeoutExpired:
            return f"执行超时（{self.timeout}s）"
        except Exception as exc:
            return f"执行失败: {exc}"
        output = (completed.stdout or "") + (completed.stderr or "")
        if len(output) > 8000:
            output = output[:8000] + "\n…(truncated)"
        code = completed.returncode
        return output.strip() or f"(exit {code}, 无输出)"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="python 或 shell", required=True),
            ToolParameter(name="code", type="string", description="Python 代码", required=False),
            ToolParameter(name="command", type="string", description="白名单 shell 命令", required=False),
        ]
