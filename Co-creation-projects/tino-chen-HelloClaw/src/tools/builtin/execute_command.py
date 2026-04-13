"""命令执行工具 - 安全地执行 shell 命令"""

import subprocess
import re
import os
from typing import List, Dict, Any

from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action


# 白名单命令（只允许这些基础命令）
ALLOWED_COMMANDS = [
    "ls", "cat", "echo", "pwd", "git", "npm", "pnpm", "uv", "python",
    "python3", "node", "yarn", "pip", "pip3", "mkdir", "touch", "cp",
    "mv", "grep", "find", "head", "tail", "wc", "sort", "uniq",
]

# 危险命令模式（正则表达式）
DANGEROUS_PATTERNS = [
    r"rm\s+-rf",           # 递归强制删除
    r"rm\s+-fr",           # 递归强制删除（变体）
    r"sudo",               # 提权命令
    r"chmod\s+777",        # 危险权限设置
    r">\s*/dev/",          # 写入设备文件
    r"mkfs",               # 格式化命令
    r"dd\s+if=",           # 磁盘复制
    r">\s*/etc/",          # 写入系统配置
    r"shutdown",           # 关机命令
    r"reboot",             # 重启命令
    r"init\s+[06]",        # 切换运行级别
    r"kill\s+-9\s+1",      # 杀死 init 进程
    r":(){ :\|:& };:",     # Fork 炸弹
    r">\s*\$HOME",         # 覆盖用户目录
    r">\s*~",              # 覆盖用户目录
]


class ExecuteCommandTool(Tool):
    """命令执行工具

    提供安全的 shell 命令执行能力，包括：
    - 命令白名单机制
    - 危险命令拦截
    - 工作目录限制
    - 执行超时控制
    """

    def __init__(
        self,
        allowed_commands: List[str] = None,
        dangerous_patterns: List[str] = None,
        max_output_size: int = 10000,
        timeout: int = 30,
        allowed_directories: List[str] = None,
    ):
        """初始化命令执行工具

        Args:
            allowed_commands: 允许的命令列表，默认使用 ALLOWED_COMMANDS
            dangerous_patterns: 危险命令模式列表，默认使用 DANGEROUS_PATTERNS
            max_output_size: 最大输出大小（字符），默认 10000
            timeout: 命令执行超时时间（秒），默认 30
            allowed_directories: 允许的工作目录列表，None 表示不限制
        """
        super().__init__(
            name="execute_command",
            description="安全地执行 shell 命令，支持命令白名单和危险命令拦截",
            expandable=True
        )

        self.allowed_commands = allowed_commands or ALLOWED_COMMANDS
        self.dangerous_patterns = dangerous_patterns or DANGEROUS_PATTERNS
        self.max_output_size = max_output_size
        self.timeout = timeout
        self.allowed_directories = allowed_directories

        # 编译危险模式正则表达式
        self._dangerous_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行命令（默认行为）"""
        command = parameters.get("command", "")
        workdir = parameters.get("workdir")
        return self._execute_command(command, workdir)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="要执行的 shell 命令",
                required=True
            ),
            ToolParameter(
                name="workdir",
                type="string",
                description="工作目录（可选）",
                required=False
            ),
        ]

    def _validate_command(self, command: str) -> tuple[bool, str]:
        """验证命令是否安全

        Args:
            command: 要验证的命令

        Returns:
            (is_safe, reason): 是否安全，不安全的原因
        """
        # 检查危险模式
        for pattern in self._dangerous_regex:
            if pattern.search(command):
                return False, f"命令包含危险模式: {pattern.pattern}"

        # 提取基础命令（命令行的第一个词）
        # 处理带路径的命令（如 /usr/bin/ls）
        command_parts = command.strip().split()
        if not command_parts:
            return False, "命令为空"

        base_cmd = os.path.basename(command_parts[0])

        # 检查白名单
        if base_cmd not in self.allowed_commands:
            return False, f"命令 '{base_cmd}' 不在白名单中。允许的命令: {', '.join(self.allowed_commands[:10])}..."

        return True, ""

    def _validate_workdir(self, workdir: str) -> tuple[bool, str]:
        """验证工作目录

        Args:
            workdir: 工作目录路径

        Returns:
            (is_valid, reason): 是否有效，无效的原因
        """
        # 如果没有设置 allowed_directories，允许所有目录
        if not self.allowed_directories:
            return True, ""

        # 检查目录是否在允许列表中
        abs_workdir = os.path.abspath(workdir)
        for allowed_dir in self.allowed_directories:
            abs_allowed = os.path.abspath(allowed_dir)
            if abs_workdir.startswith(abs_allowed):
                return True, ""

        return False, f"工作目录 '{workdir}' 不在允许的目录列表中"

    def _execute_command(
        self,
        command: str,
        workdir: str = None,
        timeout: int = None,
    ) -> ToolResponse:
        """执行命令的核心实现

        Args:
            command: 要执行的命令
            workdir: 工作目录
            timeout: 超时时间（秒）

        Returns:
            ToolResponse: 执行结果
        """
        if not command:
            return ToolResponse.error(
                code="INVALID_INPUT",
                message="命令不能为空"
            )

        # 验证命令安全性
        is_safe, reason = self._validate_command(command)
        if not is_safe:
            return ToolResponse.error(
                code="COMMAND_BLOCKED",
                message=f"命令被拦截: {reason}"
            )

        # 验证工作目录
        if workdir:
            is_valid, reason = self._validate_workdir(workdir)
            if not is_valid:
                return ToolResponse.error(
                    code="DIRECTORY_NOT_ALLOWED",
                    message=f"工作目录无效: {reason}"
                )

        # 执行命令
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=workdir,
                timeout=timeout or self.timeout,
            )

            # 截断过长的输出
            stdout = result.stdout
            stderr = result.stderr

            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + f"\n... (输出已截断，共 {len(result.stdout)} 字符)"
            if len(stderr) > self.max_output_size:
                stderr = stderr[:self.max_output_size] + f"\n... (错误输出已截断，共 {len(result.stderr)} 字符)"

            # 构建响应
            output_parts = []
            if stdout:
                output_parts.append(f"输出:\n{stdout}")
            if stderr:
                output_parts.append(f"错误:\n{stderr}")

            output_text = "\n\n".join(output_parts) if output_parts else "命令执行完成（无输出）"

            return ToolResponse.success(
                text=output_text,
                data={
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "command": command,
                    "workdir": workdir,
                }
            )

        except subprocess.TimeoutExpired:
            return ToolResponse.error(
                code="TIMEOUT",
                message=f"命令执行超时（{timeout or self.timeout}秒）"
            )
        except Exception as e:
            return ToolResponse.error(
                code="EXECUTION_ERROR",
                message=f"命令执行失败: {str(e)}"
            )

    @tool_action("exec_run", "执行 shell 命令")
    def _run_command(
        self,
        command: str,
        workdir: str = None,
        timeout: int = None,
    ) -> str:
        """执行 shell 命令

        Args:
            command: 要执行的命令
            workdir: 工作目录（可选）
            timeout: 超时时间（秒，可选）
        """
        response = self._execute_command(command, workdir, timeout)
        return response.text

    @tool_action("exec_allowed_commands", "列出允许的命令")
    def _list_allowed_commands(self) -> str:
        """列出所有允许执行的命令"""
        return "允许的命令:\n" + "\n".join(f"- {cmd}" for cmd in sorted(self.allowed_commands))

    @tool_action("exec_dangerous_patterns", "列出危险命令模式")
    def _list_dangerous_patterns(self) -> str:
        """列出所有会被拦截的危险命令模式"""
        return "危险命令模式:\n" + "\n".join(f"- {pattern}" for pattern in self.dangerous_patterns)
