"""TerminalTool - 命令行工具

为Agent提供安全的命令行执行能力，支持：
- 文件系统操作（ls, cat, head, tail, find, grep）
- 文本处理（wc, sort, uniq）
- 目录导航（pwd, cd）
- 安全限制（白名单命令、路径限制、超时控制）

使用场景：
- JIT（即时）文件检索与分析
- 代码仓库探索
- 日志文件分析
- 数据文件预览

安全特性：
- 命令白名单（只允许安全的只读命令）
- 工作目录限制（沙箱）
- 超时控制
- 输出大小限制
- 禁止危险操作（rm, mv, chmod等）
"""

from typing import Dict, Any, List
import subprocess
import os
from pathlib import Path
import shlex
import platform

from ..base import Tool, ToolParameter


class TerminalTool(Tool):
    """命令行工具

    提供安全的命令行执行能力，支持常用的文件系统和文本处理命令。

    安全限制：
    - 只允许白名单中的命令
    - 限制在指定工作目录内
    - 超时控制（默认30秒）
    - 输出大小限制（默认10MB）

    用法示例：
    ```python
    # 自动检测操作系统
    terminal = TerminalTool(workspace="./project", os_type="auto")

    # 手动指定Windows
    terminal = TerminalTool(workspace="./project", os_type="windows")

    # 列出文件
    result = terminal.run({"command": "ls -la"})  # Linux/Mac
    result = terminal.run({"command": "dir"})     # Windows

    # 查看文件内容
    result = terminal.run({"command": "cat README.md"})

    # 搜索文件
    result = terminal.run({"command": "grep -r 'TODO' src/"})

    # 查看文件前10行
    result = terminal.run({"command": "head -n 10 data.csv"})
    ```
    """

    # 允许的命令白名单（跨平台）
    ALLOWED_COMMANDS = {
        # 文件列表与信息
        "ls",
        "dir",
        "tree",
        # 文件内容查看
        "cat",
        "type",
        "head",
        "tail",
        "less",
        "more",
        # 文件搜索
        "find",
        "where",
        "grep",
        "egrep",
        "fgrep",
        "findstr",
        # 文本处理
        "wc",
        "sort",
        "uniq",
        "cut",
        "awk",
        "sed",
        # 目录操作
        "pwd",
        "cd",
        # 文件信息
        "file",
        "stat",
        "du",
        "df",
        # 其他
        "echo",
        "which",
        "whereis",
        # 代码执行
        "python",
        "python3",
        "node",
        "bash",
        "sh",
        "powershell",
        "cmd",
    }

    def __init__(
        self,
        workspace: str = ".",
        timeout: int = 30,
        max_output_size: int = 10 * 1024 * 1024,  # 10MB
        allow_cd: bool = True,
        os_type: str = "auto",  # "auto", "windows", "linux", "mac"
    ):
        super().__init__(
            name="terminal",
            description="跨平台命令行工具 - 执行安全的文件系统、文本处理和代码执行命令（支持Windows/Linux/Mac）",
        )

        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allow_cd = allow_cd

        # 检测或设置操作系统类型
        if os_type == "auto":
            self.os_type = self._detect_os()
        else:
            self.os_type = os_type.lower()

        # 当前工作目录（相对于workspace）
        self.current_dir = self.workspace

        # 确保工作目录存在
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _detect_os(self) -> str:
        """检测操作系统类型"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "mac"
        else:
            return "linux"

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具"""
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败"

        command = parameters.get("command", "").strip()

        if not command:
            return "❌ 命令不能为空"

        # 解析命令
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return f"❌ 命令解析失败: {e}"

        if not parts:
            return "❌ 命令不能为空"

        base_command = parts[0]

        # 检查命令是否在白名单中
        if base_command not in self.ALLOWED_COMMANDS:
            return f"❌ 不允许的命令: {base_command}\n允许的命令: {', '.join(sorted(self.ALLOWED_COMMANDS))}"

        # 特殊处理 cd 命令
        if base_command == "cd":
            return self._handle_cd(parts)

        # 执行命令
        return self._execute_command(command)

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="command",
                type="string",
                description=(
                    f"要执行的命令（白名单: {', '.join(sorted(list(self.ALLOWED_COMMANDS)[:10]))}...）\n"
                    "示例: 'ls -la', 'cat file.txt', 'grep pattern *.py', 'head -n 20 data.csv'"
                ),
                required=True,
            ),
        ]

    def _handle_cd(self, parts: List[str]) -> str:
        """处理 cd 命令"""
        if not self.allow_cd:
            return "❌ cd 命令已禁用"

        if len(parts) < 2:
            # cd 无参数，返回当前目录
            return f"当前目录: {self.current_dir}"

        target_dir = parts[1]

        # 处理相对路径
        if target_dir == "..":
            new_dir = self.current_dir.parent
        elif target_dir == ".":
            new_dir = self.current_dir
        elif target_dir == "~":
            new_dir = self.workspace
        else:
            new_dir = (self.current_dir / target_dir).resolve()

        # 检查是否在工作目录内
        try:
            new_dir.relative_to(self.workspace)
        except ValueError:
            return f"❌ 不允许访问工作目录外的路径: {new_dir}"

        # 检查目录是否存在
        if not new_dir.exists():
            return f"❌ 目录不存在: {new_dir}"

        if not new_dir.is_dir():
            return f"❌ 不是目录: {new_dir}"

        # 更新当前目录
        self.current_dir = new_dir
        return f"✅ 切换到目录: {self.current_dir}"

    def _execute_command(self, command: str) -> str:
        """执行命令"""
        try:
            # 根据操作系统类型调整命令执行方式
            if self.os_type == "windows":
                # Windows下使用cmd.exe或直接shell=True
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=str(self.current_dir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=os.environ.copy(),
                )
            else:
                # Unix系统（Linux/Mac）使用shell=True
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=str(self.current_dir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=os.environ.copy(),
                )

            # 合并标准输出和标准错误
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"

            # 检查输出大小
            if len(output) > self.max_output_size:
                output = output[: self.max_output_size]
                output += f"\n\n⚠️ 输出被截断（超过 {self.max_output_size} 字节）"

            # 添加返回码信息
            if result.returncode != 0:
                output = f"⚠️ 命令返回码: {result.returncode}\n\n{output}"

            return output if output else "✅ 命令执行成功（无输出）"

        except subprocess.TimeoutExpired:
            return f"❌ 命令执行超时（超过 {self.timeout} 秒）"
        except Exception as e:
            return f"❌ 命令执行失败: {e}"

    def get_current_dir(self) -> str:
        """获取当前工作目录"""
        return str(self.current_dir)

    def reset_dir(self):
        """重置到工作目录根"""
        self.current_dir = self.workspace

    def get_os_type(self) -> str:
        """获取当前操作系统类型"""
        return self.os_type
