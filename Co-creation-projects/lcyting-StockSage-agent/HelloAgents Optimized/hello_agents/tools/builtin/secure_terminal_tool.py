"""SecureTerminalTool - 带审批流程的安全终端工具

继承自 TerminalTool，集成 ApprovalManager 实现人机协作审批流程。

增强功能：
- 风险等级自动分类
- 路径访问验证
- 敏感文件检测
- 与审批管理器联动

向后兼容：
- 完全兼容 TerminalTool 接口
- 当 approval_manager=None 时行为与原版一致
"""

from __future__ import annotations

import os
import re
import shlex
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .terminal_tool import TerminalTool
from .approval_manager import (
    ApprovalManager,
    ApprovalStatus,
    ApprovalRequest,
    RiskLevel,
)


class SecureTerminalTool(TerminalTool):
    """带审批流程的安全终端工具

    在 TerminalTool 基础上增加了：
    - 风险等级自动分类
    - 敏感文件访问检测
    - 路径逃逸防护
    - 人机协作审批流程

    用法示例：
    ```python
    from hello_agents.tools import ApprovalManager, SecureTerminalTool

    # 初始化
    manager = ApprovalManager()
    terminal = SecureTerminalTool(
        workspace="./project",
        approval_manager=manager,
    )

    # 低风险操作 - 直接执行
    result = terminal.run({"command": "ls -la"})

    # 高风险操作 - 需要审批
    result = terminal.run({"command": "python -c 'import os; os.system(\"rm -rf .\")'"})
    # 返回: 等待审批中，请使用 manager.approve(request_id) 批准

    # 审批后执行
    manager.approve("request_id")
    ```

    风险等级：
    - LOW: 只读操作，直接执行
    - MEDIUM: 代码执行，需确认
    - HIGH: 代码执行 + 敏感路径，需审批
    - CRITICAL: 危险操作，强制审批 + 二次确认
    """

    SENSITIVE_PATTERNS = [
        r"\.env$",
        r"\.env\.\w+$",
        r"\.key$",
        r"\.pem$",
        r"\.cert$",
        r"password",
        r"secret",
        r"token",
        r"credential",
        r"\.p12$",
        r"\.pfx$",
        r"id_rsa",
        r"id_dsa",
        r"aws_access",
        r"api_key",
    ]

    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+",
        r"rm\s+-r\s+",
        r"dd\s+if=",
        r"mkfs",
        r":\(\)\{",  # bash fork bomb
        r">\s*/dev/sd",
        r">\s*/etc/",
        r"chmod\s+777",
        r"curl.*\|.*sh",
        r"wget.*\|.*sh",
    ]

    DANGEROUS_SUB_PATTERNS = [
        r"del\s+/[fq]",  # Windows del /f /q
        r"format\s+",  # format drive
        r"rd\s+/[fs]\s+",  # Windows rd /s /f
        r"rmdir\s+/[fs]\s+",  # Windows rmdir /s /f
        r"remove-item.*-recurse",  # PowerShell recursive delete
        r"remove-item.*-force",  # PowerShell force delete
        r"shutdown\s+/",
        r"taskkill\s+/",
    ]

    def __init__(
        self,
        workspace: str = ".",
        timeout: int = 30,
        max_output_size: int = 10 * 1024 * 1024,
        allow_cd: bool = True,
        os_type: str = "auto",
        approval_manager: Optional[ApprovalManager] = None,
        agent_id: str = "default_agent",
        auto_approve_patterns: Optional[List[str]] = None,
        sensitive_file_warning: bool = True,
    ):
        """初始化安全终端工具

        Args:
            workspace: 工作目录
            timeout: 命令超时时间（秒）
            max_output_size: 最大输出大小（字节）
            allow_cd: 是否允许 cd 命令
            os_type: 操作系统类型（auto/windows/linux/mac）
            approval_manager: 审批管理器，None则不启用审批
            agent_id: 智能体ID，用于标识审批请求来源
            auto_approve_patterns: 自动批准的命令模式（正则表达式列表）
            sensitive_file_warning: 是否警告敏感文件访问
        """
        super().__init__(
            workspace=workspace,
            timeout=timeout,
            max_output_size=max_output_size,
            allow_cd=allow_cd,
            os_type=os_type,
        )

        self.name = "secure_terminal"
        self.description = "带审批流程的安全终端工具 - 执行命令前进行风险评估和必要审批"

        self.approval_manager = approval_manager
        self.agent_id = agent_id
        self.auto_approve_patterns = auto_approve_patterns or []
        self.sensitive_file_warning = sensitive_file_warning

        self._pending_requests: Dict[str, str] = {}
        self._lock = threading.Lock()

        self._execution_results: Dict[str, str] = {}

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具

        Args:
            parameters: 包含 command 的参数字典

        Returns:
            str: 执行结果或审批提示
        """
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败"

        command = parameters.get("command", "").strip()

        if not command:
            return "❌ 命令不能为空"

        parsed = self._parse_command(command)
        if parsed is None:
            return f"❌ 命令解析失败: {command}"

        base_command, args = parsed

        if base_command not in self.ALLOWED_COMMANDS:
            return f"❌ 不允许的命令: {base_command}\n允许的命令: {', '.join(sorted(self.ALLOWED_COMMANDS))}"

        if base_command == "cd":
            return self._handle_cd(args)

        risk_level = self._classify_risk(command, base_command, args)

        if risk_level == RiskLevel.LOW:
            return self._execute_command(command)
        elif self.approval_manager is None:
            if risk_level == RiskLevel.CRITICAL:
                return f"❌ 极高风险操作被拦截: {command}\n\n⚠️ 这是一个危险命令，可能导致数据丢失。"
            else:
                return f"⚠️ 中高风险操作: {command}\n\n请初始化 ApprovalManager 以执行此操作。"

        if self._is_auto_approved(command):
            return self._execute_command(command)

        if risk_level == RiskLevel.HIGH or risk_level == RiskLevel.CRITICAL:
            risk_summary = self._build_risk_summary(command, risk_level)
            return f"⏳ 等待审批中...\n\n命令: {command}\n\n风险等级: {risk_level.value.upper()}\n风险摘要: {risk_summary}\n\n请使用 approval_manager.approve(request_id) 批准执行。"

        request_id = self.approval_manager.request_approval(
            agent_id=self.agent_id,
            command=command,
            risk_level=risk_level,
            context={
                "workspace": str(self.workspace),
                "current_dir": str(self.current_dir),
                "risk_summary": self._build_risk_summary(command, risk_level),
            },
        )

        with self._lock:
            self._pending_requests[request_id] = command

        return f"⏳ 审批请求已提交\n\nrequest_id: {request_id}\n命令: {command}\n风险等级: {risk_level.value.upper()}\n\n等待期间请使用 manager.approve('{request_id}') 批准执行。"

    def _parse_command(self, command: str) -> Optional[Tuple[str, List[str]]]:
        """解析命令"""
        try:
            parts = shlex.split(command)
            if not parts:
                return None
            return parts[0], parts[1:]
        except ValueError:
            return None

    def _classify_risk(
        self, command: str, base_command: str, args: List[str]
    ) -> RiskLevel:
        """分类风险等级"""
        command_lower = command.lower()

        if self._is_dangerous_pattern(command_lower):
            return RiskLevel.CRITICAL

        if self._is_dangerous_subcommand(command_lower, args):
            return RiskLevel.CRITICAL

        if self._contains_path_traversal(command):
            return RiskLevel.HIGH

        full_path = self._resolve_path(args)
        if full_path and self._is_sensitive_path(full_path):
            return RiskLevel.HIGH

        if base_command in [
            "python",
            "python3",
            "node",
            "bash",
            "sh",
            "powershell",
            "cmd",
        ]:
            if full_path and self._is_sensitive_path(full_path):
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM

        if full_path and self._is_sensitive_path(full_path):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _is_dangerous_pattern(self, command_lower: str) -> bool:
        """检查是否匹配危险模式"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command_lower):
                return True
        return False

    def _is_dangerous_subcommand(self, command_lower: str, args: List[str]) -> bool:
        """检查子命令中是否包含危险操作（如 cmd /c del ..., powershell -c Remove-Item ...）"""
        for pattern in self.DANGEROUS_SUB_PATTERNS:
            if re.search(pattern, command_lower):
                return True

        if args and any(
            base in command_lower for base in ["powershell", "cmd", "bash", "sh"]
        ):
            code_arg = None
            skip_next = False
            code_flags = {"-c", "-e", "--eval", "--command", "/c"}

            for i, arg in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue
                if arg in code_flags:
                    skip_next = True
                    continue
                if arg.startswith("-"):
                    continue
                if arg.startswith('"') or arg.startswith("'"):
                    code_arg = arg
                    break

            if code_arg:
                code_lower = code_arg.lower()
                for pattern in self.DANGEROUS_SUB_PATTERNS:
                    if re.search(pattern, code_lower):
                        return True

        return False

    def _contains_path_traversal(self, command: str) -> bool:
        """检查是否包含路径遍历"""
        path_pattern = r"\.\.\/|\.\.\\"
        return bool(re.search(path_pattern, command))

    def _resolve_path(self, args: List[str]) -> Optional[str]:
        """解析命令参数中的路径

        排除代码执行参数（如 python -c "code", node -e "code"）
        只识别真正的文件路径
        """
        if not args:
            return None

        CODE_EXEC_ARGS = {"-c", "-e", "--eval", "--command", "/c"}  # 代码执行参数
        path_arg = None
        skip_next = False

        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue

            if arg in CODE_EXEC_ARGS:
                skip_next = True
                continue

            if arg.startswith("-"):
                continue

            if arg.startswith('"') or arg.startswith("'"):
                continue

            path_arg = arg
            break

        if not path_arg:
            return None

        try:
            if Path(path_arg).is_absolute():
                return str(Path(path_arg).resolve())
            else:
                return str((self.current_dir / path_arg).resolve())
        except Exception:
            return None

    def _is_sensitive_path(self, path: str) -> bool:
        """检查是否为敏感路径"""
        path_lower = path.lower()

        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, path_lower):
                return True

        system_paths = [
            "/etc/",
            "/root/",
            "/home/",
            "/var/",
            "/usr/",
            "/bin/",
            "/sbin/",
        ]
        if os.name == "nt":
            system_paths.extend(["C:\\Windows", "C:\\Program Files", "C:\\Users"])

        for sys_path in system_paths:
            if sys_path.lower() in path_lower:
                return True

        return False

    def _is_auto_approved(self, command: str) -> bool:
        """检查命令是否自动批准"""
        command_lower = command.lower()

        for pattern in self.auto_approve_patterns:
            if re.search(pattern, command_lower):
                return True

        return False

    def _build_risk_summary(self, command: str, risk_level: RiskLevel) -> str:
        """构建风险摘要"""
        if risk_level == RiskLevel.LOW:
            return "✅ 低风险：只读操作，不涉及敏感内容"

        summaries = []

        if self._is_dangerous_pattern(command.lower()):
            summaries.append("检测到危险命令模式")

        if self._contains_path_traversal(command):
            summaries.append("包含路径遍历操作")

        if self._resolve_path(
            self._parse_command(command)[1] if self._parse_command(command) else []
        ):
            resolved = self._resolve_path(
                self._parse_command(command)[1] if self._parse_command(command) else []
            )
            if resolved and self._is_sensitive_path(resolved):
                summaries.append(f"访问敏感路径: {resolved}")

        base_command = (
            self._parse_command(command)[0] if self._parse_command(command) else ""
        )
        if base_command in ["python", "node", "bash", "sh"]:
            summaries.append("执行代码命令，可能执行任意代码")

        if not summaries:
            if risk_level == RiskLevel.MEDIUM:
                return "⚠️ 中风险：代码执行命令"
            else:
                return "🔴 高风险：代码执行 + 敏感操作"

        return "⚠️ " + "\n⚠️ ".join(summaries)

    def execute_approved(self, request_id: str) -> str:
        """执行已批准的请求

        Args:
            request_id: 审批请求ID

        Returns:
            str: 执行结果
        """
        if self.approval_manager is None:
            return "❌ 未配置审批管理器"

        status = self.approval_manager.get_status(request_id)
        if status is None:
            return f"❌ 审批请求不存在: {request_id}"

        if status.status != ApprovalStatus.APPROVED:
            return f"❌ 请求尚未批准，当前状态: {status.status.value}"

        with self._lock:
            command = self._pending_requests.pop(request_id, None)

        if command is None:
            command = status.command

        result = self._execute_command(command)

        self.approval_manager.set_execution_result(request_id, result)
        self._execution_results[request_id] = result

        return result

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """获取待审批请求列表"""
        if self.approval_manager is None:
            return []
        return self.approval_manager.list_pending()

    def get_execution_result(self, request_id: str) -> Optional[str]:
        """获取执行结果

        Args:
            request_id: 审批请求ID

        Returns:
            Optional[str]: 执行结果
        """
        if request_id in self._execution_results:
            return self._execution_results[request_id]

        if self.approval_manager:
            result = self.approval_manager.get_execution_result(request_id)
            if result:
                return result.get("result")

        return None

    def set_approval_manager(self, manager: ApprovalManager) -> None:
        """设置审批管理器（运行时配置）"""
        self.approval_manager = manager

    def get_risk_level(self, command: str) -> RiskLevel:
        """获取命令的风险等级（不执行）"""
        parsed = self._parse_command(command)
        if parsed is None:
            return RiskLevel.MEDIUM

        base_command, args = parsed

        if base_command not in self.ALLOWED_COMMANDS:
            return RiskLevel.CRITICAL

        return self._classify_risk(command, base_command, args)

    def preview_command(self, command: str) -> Dict[str, Any]:
        """预览命令信息和风险评估

        Args:
            command: 待执行的命令

        Returns:
            Dict: 包含命令信息和风险评估的字典
        """
        risk_level = self.get_risk_level(command)
        risk_summary = self._build_risk_summary(command, risk_level)

        parsed = self._parse_command(command)
        resolved_path = None
        if parsed:
            resolved_path = self._resolve_path(parsed[1])

        return {
            "command": command,
            "base_command": parsed[0] if parsed else None,
            "resolved_path": resolved_path,
            "risk_level": risk_level.value,
            "risk_summary": risk_summary,
            "requires_approval": risk_level
            in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL],
            "auto_approved": self._is_auto_approved(command),
        }


def create_with_approval(
    workspace: str,
    approval_manager: ApprovalManager,
    agent_id: str = "default",
    **kwargs,
) -> SecureTerminalTool:
    """工厂函数：创建带审批的终端工具

    Args:
        workspace: 工作目录
        approval_manager: 审批管理器
        agent_id: 智能体ID
        **kwargs: 其他参数

    Returns:
        SecureTerminalTool: 配置好的安全终端
    """
    return SecureTerminalTool(
        workspace=workspace,
        approval_manager=approval_manager,
        agent_id=agent_id,
        **kwargs,
    )
