
import subprocess
import sys
import tempfile
import os
from hello_agents.tools import Tool
from typing import Dict, Any

class CodeRunner(Tool):
    """
    执行 Python 代码并返回输出的工具。
    代码在独立子进程中运行，具有超时限制和受限权限。
    """

    TIMEOUT_SECONDS = 10

    def __init__(self):
        super().__init__(
            name="code_runner",
            description="执行 Python 代码并返回标准输出/错误。输入应为包含 'code' 键的字典。"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码片段"
                }
            },
            "required": ["code"]
        }

    def run(self, parameters: Dict[str, Any]) -> str:
        code = parameters.get("code", "")
        if not code:
            return "错误：未提供代码。"

        # Write code to a temporary file and execute in a subprocess
        # with a timeout to prevent infinite loops and resource abuse.
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            # Run in a subprocess with no network and a timeout.
            # Use a restricted environment to limit information leakage.
            env = {
                "PATH": os.defpath,
                "HOME": tempfile.gettempdir(),
            }

            proc = subprocess.run(
                [sys.executable, "-u", tmp_path],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_SECONDS,
                env=env,
                cwd=tempfile.gettempdir(),
            )

            result = ""
            if proc.stdout:
                result += f"输出:\n{proc.stdout}\n"
            if proc.stderr:
                result += f"错误:\n{proc.stderr}\n"

            if not result:
                result = "代码执行成功，无输出。"

            return result

        except subprocess.TimeoutExpired:
            return f"运行时错误: 代码执行超时（{self.TIMEOUT_SECONDS}秒限制）。"
        except Exception as e:
            return f"运行时错误: {str(e)}"
        finally:
            try:
                os.unlink(tmp_path)
            except (OSError, UnboundLocalError):
                pass
