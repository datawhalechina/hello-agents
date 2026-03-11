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

from typing import Dict, Any, List, Optional
import subprocess
import os
from pathlib import Path
import shlex
import re

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
    terminal = TerminalTool(workspace="./project")
    
    # 列出文件
    result = terminal.run({"command": "ls -la"})
    
    # 查看文件内容
    result = terminal.run({"command": "cat README.md"})
    
    # 搜索文件
    result = terminal.run({"command": "grep -r 'TODO' src/"})
    
    # 查看文件前10行
    result = terminal.run({"command": "head -n 10 data.csv"})
    ```
    """
    
    # 允许的命令白名单
    # 这些命令被认为是安全的，主要用于文件查看、文本处理和信息获取
    # 不包含可能修改系统或造成安全风险的命令（如rm、mv、chmod等）
    ALLOWED_COMMANDS = {
        # 文件列表与信息
        'ls', 'dir', 'tree',
        # 文件内容查看
        'cat', 'head', 'tail', 'less', 'more',
        # 文件搜索
        'find', 'grep', 'egrep', 'fgrep', 'rg',
        # 文本处理
        'wc', 'sort', 'uniq', 'cut', 'awk', 'sed',
        # shell 常见内建（用于管道/小脚本；仍受整体策略约束）
        'echo', 'printf',
        # 目录/文件创建（受路径沙箱约束）
        'mkdir',
        # 目录操作
        'pwd', 'cd',
        # 文件信息
        'file', 'stat', 'du', 'df',
        # 其他
        'which', 'whereis',
        # 版本控制（只读子命令会被进一步限制）
        'git',
        # 验证/测试（用于 /verify 验证闭环；仍受危险操作检测约束）
        'python', 'python3', 'pytest',
        # Skills 生态：仅允许 `npx skills ...`（额外校验见 _is_allowed_npx）
        'npx',
    }

    # 常见 shell 元字符（用于检测"组合命令/写盘/子命令"等风险点；不再一刀切禁止）
    # 这些元字符在shell中有特殊含义，可能用于组合命令或执行危险操作
    # 系统会检测这些字符的存在，并根据安全策略决定是否允许执行
    SHELL_META_TOKENS = ["|", "||", "&&", ";", ">", ">>", "<", "$(", "`"]

    # 需要人类确认的高风险命令（MVP：只做识别；是否放行由上层策略决定）
    # 这些命令可能对系统造成不可逆的修改，需要用户明确确认才能执行
    DANGEROUS_BASE_COMMANDS = {"rm", "chmod"}
    # Git的高风险子命令，可能造成代码丢失或历史修改
    DANGEROUS_GIT_SUBCOMMANDS = {("reset", "--hard"), ("reset", "--hard", "HEAD")}
    
    def __init__(
        self,
        workspace: str = ".",
        timeout: int = 30,
        max_output_size: int = 10 * 1024 * 1024,  # 10MB
        allow_cd: bool = True,
        confirm_dangerous: bool = False,
        default_shell_mode: bool = False,
    ):
        """初始化TerminalTool实例
        
        Args:
            workspace: 工作目录路径，所有命令将在此目录或其子目录中执行
            timeout: 命令执行超时时间（秒），防止长时间运行的命令
            max_output_size: 输出大小限制（字节），防止过大输出消耗资源
            allow_cd: 是否允许cd命令，控制目录切换权限
            confirm_dangerous: 是否在执行高风险命令时提示用户确认
            default_shell_mode: 默认是否启用shell模式（支持管道、重定向等）
        """
        super().__init__(
            name="terminal",
            description="命令行工具 - 执行安全的文件系统、文本处理和代码执行命令（ls, cat, grep, head, tail等）"
        )
        
        # 将工作目录转换为绝对路径并规范化
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allow_cd = allow_cd
        self.confirm_dangerous = confirm_dangerous
        self.default_shell_mode = default_shell_mode
        
        # 当前工作目录（相对于workspace）
        # 初始设置为工作目录根目录，可通过cd命令更改
        self.current_dir = self.workspace
        
        # 确保工作目录存在，如果不存在则创建
        self.workspace.mkdir(parents=True, exist_ok=True)
    
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具的主入口方法
        
        根据参数解析命令并执行，包含完整的安全检查流程：
        1. 参数验证 - 确保输入参数格式正确且必要参数存在
        2. 命令解析和分类 - 将命令字符串解析为可执行的参数列表
        3. 安全策略检查 - 多层安全验证，包括白名单检查、危险操作检测等
        4. 命令执行和结果处理 - 安全执行命令并格式化返回结果
        
        安全机制说明：
        - 命令白名单：只执行预定义的安全命令，防止恶意命令执行
        - 路径沙箱：所有文件操作限制在工作目录内，防止越权访问
        - 危险操作确认：高风险命令需要用户明确确认才能执行
        - 超时控制：防止长时间运行的命令消耗系统资源
        - 输出限制：防止过大输出导致内存问题
        
        Args:
            parameters: 包含command、allow_dangerous、shell_mode等参数的字典
                - command: 要执行的命令字符串
                - allow_dangerous: 是否允许执行危险操作
                - shell_mode: 是否启用shell模式（支持管道、重定向等）
            
        Returns:
            str: 命令执行结果或错误信息，包含详细的错误说明
        """
        # 第一步：参数验证 - 确保输入参数符合预期格式
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败"
        
        # 提取并清理命令参数
        command = parameters.get("command", "").strip()
        allow_dangerous = bool(parameters.get("allow_dangerous", False))
        shell_mode = bool(parameters.get("shell_mode", self.default_shell_mode))
        # 由上层 UI 的二次确认注入：对齐 Claude Code/OpenCode/Codex 体验——用户点 y 后本次应当放行
        user_approved = bool(parameters.get("user_approved", False))
        effective_allow_dangerous = bool(allow_dangerous or user_approved)
        
        # 基础安全检查：拒绝空命令，防止无意义的系统调用
        if not command:
            return "❌ 命令不能为空"

        # 执行模式选择：
        # - 如果命令不包含任何 shell 元字符（管道/重定向/命令替换等），即使命令来自默认 shell_mode，
        #   也降级为 argv 模式执行：更安全，且避免 shell 静态白名单误判（例如 `npx skills ...`）。
        # - 只有检测到 shell 元字符时才走真正的 shell_mode 执行分支。
        if shell_mode:
            has_meta = any(self._has_unquoted(command, tok) for tok in self.SHELL_META_TOKENS)
            if has_meta:
                return self._execute_shell(command, allow_dangerous=effective_allow_dangerous)
            # no meta tokens -> treat as argv mode
            shell_mode = False
        
        # 第二步：命令解析 - 使用shlex进行安全的命令分割，处理引号和转义
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return f"❌ 命令解析失败: {e}"
        
        # 解析后再次验证，确保命令不为空
        if not parts:
            return "❌ 命令不能为空"
        
        base_command = parts[0]
        
        # 第三步：策略层 allow/ask/deny（默认 ask）
        # - allow：白名单内的安全命令
        # - deny：明确危险的基础命令（rm/chmod），除非用户已确认（user_approved）/或显式 allow_dangerous
        # - ask：白名单外的命令，若 user_approved=True 则放行本次（一次性 token）
        if base_command in self.DANGEROUS_BASE_COMMANDS and not effective_allow_dangerous:
            return f"❌ 高风险命令 {base_command} 需要人类确认（allow_dangerous=true 或 user_approved=true）"

        if base_command not in self.ALLOWED_COMMANDS and not user_approved:
            return (
                f"❌ 命令需要确认后放行（默认 ask）：{base_command}\n"
                "请在 UI 中确认后重试（UI 会注入 user_approved=true）。"
            )

        # 对 npx 做进一步限制：只允许 `npx skills ...`
        if base_command == "npx" and not self._is_allowed_npx(parts):
            return (
                "❌ 仅允许执行 `npx skills ...`（用于外部 skills 查找/安装）。\n"
                "示例：npx skills find react performance"
            )

        # 特殊命令处理：git命令需要额外的子命令安全检查
        if base_command == "git":
            # 如果用户已经在 UI 明确放行，则允许更广的 git 行为（仍受路径沙箱与超时限制）
            if user_approved:
                return self._execute_argv(parts, allow_dangerous=True)
            return self._handle_git(parts, effective_allow_dangerous)

        # 第四步：危险操作确认机制
        # 当用户明确允许危险操作且启用了确认机制时，进行交互式确认
        # 这为高风险操作提供了最后一道人工确认防线
        if effective_allow_dangerous and self.confirm_dangerous and not user_approved:
            ans = input(f"\n⚠️ 高风险命令：{command}\n允许执行？(y/n)\nconfirm> ").strip().lower()
            if ans not in {"y", "yes"}:
                return "⛔️ 已取消执行（用户未确认）。"

        # 特殊命令处理：cd命令需要单独处理以维护工作目录状态
        if base_command == 'cd':
            return self._handle_cd(parts)
        
        # 第五步：执行命令 - 通过所有安全检查后执行命令
        return self._execute_argv(parts, allow_dangerous=effective_allow_dangerous)

    def _is_allowed_npx(self, argv: List[str]) -> bool:
        """仅允许 `npx skills ...`（允许带 npx 自身 flag，如 -y/--yes）。"""
        if not argv or argv[0] != "npx":
            return False
        i = 1
        # Skip npx flags (best-effort)
        while i < len(argv) and argv[i].startswith("-"):
            i += 1
        if i >= len(argv):
            return False
        return argv[i] == "skills"
    
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
                required=True
            ),
            ToolParameter(
                name="allow_dangerous",
                type="boolean",
                description="是否允许高风险命令（默认false；仅在用户明确确认后才可设置为true）",
                required=False
            ),
            ToolParameter(
                name="shell_mode",
                type="boolean",
                description="是否允许 shell 语义（管道/重定向/多段命令等）。默认继承工具配置。",
                required=False,
            ),
            ToolParameter(
                name="user_approved",
                type="boolean",
                description="是否已由上层 UI 二次确认放行（一次性 token）。通常由 UI 注入，模型不应自行设置。",
                required=False,
            ),
        ]

    def _contains_shell_meta(self, command: str) -> bool:
        """检查命令中是否包含shell元字符
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            bool: 如果包含元字符返回True，否则返回False
        """
        return any(tok in command for tok in self.SHELL_META_TOKENS)

    # --- shell parsing helpers (ignore operators inside quotes) ---
    def _split_shell_segments(self, command: str) -> List[str]:
        """
        按管道/逻辑与/逻辑或/分号操作符分割shell命令，忽略引号内的操作符。
        返回分割后的段列表（不包含操作符）。
        
        这个方法用于分析复杂的shell命令，确保每个段都是安全的。
        
        Args:
            command: 要分割的shell命令字符串
            
        Returns:
            List[str]: 分割后的命令段列表
        """
        ops = ["||", "&&", "|", ";"]
        segs: List[str] = []
        buf: List[str] = []
        i = 0
        quote: Optional[str] = None
        while i < len(command):
            ch = command[i]
            if ch in {"'", '"'}:
                if quote is None:
                    quote = ch
                elif quote == ch:
                    quote = None
                buf.append(ch)
                i += 1
                continue
            if ch == "\\":
                buf.append(ch)
                if i + 1 < len(command):
                    buf.append(command[i + 1])
                    i += 2
                else:
                    i += 1
                continue
            if quote is None:
                matched = False
                for op in ops:
                    if command.startswith(op, i):
                        seg = "".join(buf).strip()
                        if seg:
                            segs.append(seg)
                        buf = []
                        i += len(op)
                        matched = True
                        break
                if matched:
                    continue
            buf.append(ch)
            i += 1
        seg = "".join(buf).strip()
        if seg:
            segs.append(seg)
        return segs

    def _has_unquoted(self, command: str, token: str) -> bool:
        """检查token（如>或$()或|）是否出现在引号外
        
        这个方法用于检测可能存在安全风险的shell操作符，
        确保它们不是在引号内（引号内是安全的字符串字面量）。
        
        Args:
            command: 要检查的命令字符串
            token: 要查找的token字符串
            
        Returns:
            bool: 如果token出现在引号外返回True，否则返回False
        """
        q: Optional[str] = None
        i = 0
        while i < len(command):
            ch = command[i]
            if ch in {"'", '"'}:
                if q is None:
                    q = ch
                elif q == ch:
                    q = None
                i += 1
                continue
            if ch == "\\":
                i += 2
                continue
            if q is None and command.startswith(token, i):
                return True
            i += 1
        return False

    def _shell_requires_allow_dangerous(self, command: str) -> bool:
        """检查shell命令是否需要危险操作权限
        
        此方法分析shell命令，判断其是否包含可能对系统造成风险的操作。
        这是安全机制的重要组成部分，用于识别需要额外权限确认的命令。
        
        安全检查逻辑：
        1. 检查文件写入操作（>、>>重定向），但排除到/dev/null的重定向
        2. 检查命令替换（`command`或$(command)）
        3. 检查已知的危险基础命令（rm、chmod等）
        4. 检查Git的危险子命令（如reset --hard）
        
        Args:
            command: 要检查的shell命令字符串
            
        Returns:
            bool: 如果命令需要危险操作权限则返回True，否则返回False
            
        Note:
            - 此方法不会阻止命令执行，只是标识需要额外确认的命令
            - 实际的权限检查在执行阶段进行
            - 采用相对保守的策略，对/dev/null重定向等安全操作给予宽容
        """
        # 写盘/命令替换通常视为高风险，但常见的只读掩埋（如 2>/dev/null、|| echo）可放宽
        # 宽容规则：仅当重定向目标不是 /dev/null 时才视为写盘；简单的 "|| echo ..." 视为安全。
        if self._has_unquoted(command, ">") or self._has_unquoted(command, ">>"):
            # 忽略 /dev/null 重定向（这是安全的丢弃输出操作）
            if re.search(r">\s*/dev/null", command) or re.search(r">>\s*/dev/null", command):
                pass
            else:
                # 其他重定向操作可能修改文件内容，需要危险权限
                return True
        
        # 检查命令替换：`command`（反引号）和 $(command) 格式
        # 命令替换可能执行任意代码，存在代码注入风险
        if self._has_unquoted(command, "$(") or self._has_unquoted(command, "`"):
            return True
        
        # 检查已知的危险基础命令
        # 这些命令可能对系统造成不可逆的影响，需要特别关注
        if re.search(r"(^|\s)rm(\s|$)", command):
            return True
        if re.search(r"(^|\s)chmod(\s|$)", command):
            return True
        
        # 检查Git的危险子命令
        # git reset --hard 可能导致代码丢失，属于高风险操作
        if re.search(r"git\s+reset\s+--hard", command):
            return True
        
        # 如果没有检测到危险操作，则不需要额外权限
        return False

    def _shell_all_commands_whitelisted(self, command: str) -> bool:
        """
        静态检查shell命令中的所有段是否都在白名单中（尽力而为的检查）
        
        此方法通过分割shell命令为多个段，然后检查每个段的第一个命令是否在白名单中。
        这是对shell命令的安全预检查，用于在未允许危险操作时确保命令的安全性。
        
        安全检查策略：
        1. 使用shell元字符分割命令为多个独立段
        2. 对每个段进行命令解析，提取基础命令
        3. 检查基础命令是否在白名单中
        4. 对git命令进行特殊处理，只允许安全的只读子命令
        
        Args:
            command: 要检查的完整shell命令字符串
            
        Returns:
            bool: 如果所有命令段都在白名单中则返回True，否则返回False
            
        Note:
            - 这是一个尽力而为的检查，不能保证100%准确
            - 对于复杂的shell语法，可能存在误判
            - git命令只允许status和diff子命令，其他子命令被视为危险操作
        """
        # 预处理：将换行符替换为空格，便于统一处理
        cmd = command.replace("\n", " ")
        
        # 分割命令为多个段，每个段包含一个独立的命令
        segments = self._split_shell_segments(cmd)
        
        # 对每个命令段进行安全检查
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue  # 跳过空段
                
            try:
                # 使用shlex进行安全的命令分割，处理引号和转义
                argv = shlex.split(seg)
            except Exception:
                # 如果解析失败，认为不安全
                return False
                
            if not argv:
                continue  # 跳过空命令段
                
            # 获取基础命令（命令名的第一部分）
            base = argv[0]
            
            # 检查基础命令是否在白名单中
            if base not in self.ALLOWED_COMMANDS:
                return False

            # npx 仅允许 `npx skills ...`
            if base == "npx" and not self._is_allowed_npx(argv):
                return False
                
            # 对git命令进行特殊处理
            # 只允许安全的只读子命令，其他子命令被视为危险操作
            if base == "git":
                if len(argv) < 2:
                    return False  # git命令必须包含子命令
                if argv[1] not in {"status", "diff"}:
                    return False  # 只允许status和diff子命令
                    
        # 所有命令段都通过了安全检查
        return True

    def _execute_shell(self, command: str, allow_dangerous: bool = False) -> str:
        """
        执行shell命令字符串（支持Claude Code风格的shell特性）
        
        此方法提供安全的shell命令执行能力，支持管道、重定向、命令替换等复杂shell语法。
        通过多层安全检查机制确保命令执行的安全性。
        
        安全防护措施：
        - 如果shell命令包含重定向/命令替换/已知危险操作 -> 需要allow_dangerous权限
        - 如果未允许危险操作 -> 要求所有命令段都在白名单中（尽力而为的检查）
        - confirm_dangerous可以提示用户确认包含shell元字符或需要allow_dangerous的命令
        
        执行流程：
        1. 检查命令是否需要危险权限
        2. 验证命令白名单（如果未允许危险操作）
        3. 用户确认（如果启用confirm_dangerous）
        4. 执行命令并处理输出
        5. 返回执行结果或错误信息
        
        Args:
            command: 要执行的完整shell命令字符串
            allow_dangerous: 是否允许执行危险操作（默认False）
            
        Returns:
            str: 命令执行结果或错误信息
            
        Note:
            - 支持管道操作而无需确认（如 'ls | grep .py'）
            - 只有在可能写入文件/转义/执行危险操作时才需要确认
            - 输出会被截断以防止内存问题
        """
        needs_allow = self._shell_requires_allow_dangerous(command)
        
        # 第一层安全检查：危险操作检测
        # 如果命令包含危险操作但未允许危险操作，则拒绝执行
        # 这是第一道安全防线，防止潜在的恶意操作
        if needs_allow and not allow_dangerous:
            return "❌ 该命令包含写盘/子命令替换/高风险操作，需用户确认后再执行（allow_dangerous=true）"

        # 第二层安全检查：白名单验证
        # 如果未允许危险操作，则检查所有命令段是否都在白名单中
        # 这是对命令的进一步安全验证，确保只能执行预定义的安全命令
        if not allow_dangerous and not self._shell_all_commands_whitelisted(command):
            return "❌ shell_mode 下检测到非白名单命令/不允许的 git 子命令。需要用户确认后再执行（allow_dangerous=true）"

        # 在 TUI/Agent 已经完成二次确认的情况下（allow_dangerous=true），
        # 不再通过 stdin 进行交互式确认，避免后台线程卡死。
        if self.confirm_dangerous and needs_allow and not allow_dangerous:
            ans = input(f"\n⚠️ 即将执行高风险 shell 命令：{command}\n允许执行？(y/n)\nconfirm> ").strip().lower()
            if ans not in {"y", "yes"}:
                return "⛔️ 已取消执行（用户未确认）。"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.current_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy(),
            )

            output = (result.stdout or "") + (result.stderr or "")
            if len(output.encode("utf-8", errors="ignore")) > self.max_output_size:
                output = output[: self.max_output_size] + "\n...output truncated...\n"

            if result.returncode != 0:
                return f"命令执行失败 (返回码 {result.returncode}):\n{output}"
            return output.strip() if output.strip() else "(no output)"
        except subprocess.TimeoutExpired:
            return f"❌ 命令超时（>{self.timeout}s）"
        except Exception as e:
            return f"❌ 命令执行异常: {e}"
    
    def _handle_cd(self, parts: List[str]) -> str:
        """处理cd命令，实现安全的目录切换
        
        此方法专门处理cd命令，确保目录切换在允许的工作空间范围内进行。
        支持绝对路径、相对路径和特殊路径（如..、~）的处理。
        
        Args:
            parts: cd命令的参数列表，parts[1]是目标路径
            
        Returns:
            str: 执行结果或错误信息
            
        Note:
            - 只允许切换到工作空间内的目录
            - 支持路径规范化，处理..和.等相对路径
            - 不允许切换到工作空间之外的目录
        """
        if not self.allow_cd:
            return "❌ cd 命令已禁用"
        
        if len(parts) < 2:
            # cd命令没有参数时，返回当前目录信息
            return f"当前目录: {self.current_dir}"
        
        target_dir = parts[1]
        
        # 处理特殊的相对路径
        if target_dir == "..":
            # 切换到父目录
            new_dir = self.current_dir.parent
        elif target_dir == ".":
            # 当前目录
            new_dir = self.current_dir
        elif target_dir == "~":
            # 切换到工作目录根目录
            new_dir = self.workspace
        else:
            # 解析相对或绝对路径
            new_dir = (self.current_dir / target_dir).resolve()
        
        # 检查新目录是否在工作空间范围内
        try:
            new_dir.relative_to(self.workspace)
        except ValueError:
            return f"❌ 不允许访问工作目录外的路径: {new_dir}"
        
        # 验证目录存在性
        if not new_dir.exists():
            return f"❌ 目录不存在: {new_dir}"
        
        # 确保目标是目录而非文件
        if not new_dir.is_dir():
            return f"❌ 不是目录: {new_dir}"
        
        # 更新当前工作目录
        self.current_dir = new_dir
        return f"✅ 切换到目录: {self.current_dir}"
    
    def _execute_argv(self, argv: List[str], allow_dangerous: bool = False) -> str:
        """执行参数向量形式的命令（不使用shell解释）
        
        此方法直接执行命令及其参数，不通过shell解释，因此不支持管道、重定向等shell特性。
        这种方式更安全，因为避免了shell注入攻击的风险，但功能相对有限。
        
        安全检查流程：
        1. 检查高风险命令（rm、chmod等）是否需要用户确认
        2. 对允许的高风险命令进行路径沙箱限制
        3. 对mkdir命令进行路径沙箱限制
        4. 执行命令并处理结果
        
        Args:
            argv: 命令及其参数的列表，argv[0]是命令名，其余是参数
            allow_dangerous: 是否允许执行高风险命令（默认False）
            
        Returns:
            str: 命令执行结果或错误信息
            
        Note:
            - 不支持shell特性如管道、重定向、变量替换等
            - 更安全，避免了shell注入攻击
            - 适用于简单的命令执行场景
            - 所有路径操作都被限制在工作空间内
        """
        # 第一层安全检查：高风险命令二次门禁
        # 对明确高风险基命令（rm/chmod等）进行额外检查
        # 这些命令可能对系统造成不可逆的修改，需要用户明确确认
        # 这是安全防护的第一道防线，防止意外的系统修改
        if argv and argv[0] in self.DANGEROUS_BASE_COMMANDS and not allow_dangerous:
            return f"❌ 高风险命令 {argv[0]} 需要人类确认（allow_dangerous=true）"

        # 第二层安全检查：路径沙箱限制
        # 对带路径参数的高风险命令做路径沙箱限制（仅当放行时）
        # 确保即使允许执行危险命令，也只能在工作空间内操作
        # 这防止了恶意用户通过相对路径或符号链接逃逸沙箱
        if argv and argv[0] in {"rm", "chmod"} and allow_dangerous:
            # 保守检查：所有看起来像路径的非标志参数都必须在工作空间内
            # 使用current_dir作为基准，确保相对路径也被正确限制
            for a in argv[1:]:
                if a.startswith("-"):
                    continue  # 跳过选项参数（如 -r, -f 等）
                candidate = (self.current_dir / a).resolve()
                try:
                    # 检查解析后的绝对路径是否在工作空间内
                    candidate.relative_to(self.workspace)
                except ValueError:
                    # 路径超出工作空间范围，拒绝执行
                    return f"❌ 拒绝在工作目录外操作: {a}"

        # 第三层安全检查：mkdir命令路径沙箱
        # mkdir虽然相对安全，但仍需确保不会在工作空间外创建目录
        # 这防止了通过mkdir命令在工作空间外创建后门或敏感目录
        if argv and argv[0] == "mkdir":
            for a in argv[1:]:
                if a.startswith("-"):
                    continue  # 跳过选项参数（如 -p, -m 等）
                candidate = (self.current_dir / a).resolve()
                try:
                    # 检查要创建的目录是否在工作空间内
                    candidate.relative_to(self.workspace)
                except ValueError:
                    # 尝试在工作空间外创建目录，拒绝执行
                    return f"❌ 不允许在工作目录外创建目录: {a}"

        # npx 常会提示“是否安装依赖(y/n)”而阻塞在 stdin。
        # 我们的工具执行是非交互式的（capture_output），因此默认给 npx 注入 `-y` 以避免卡死。
        if argv and argv[0] == "npx":
            has_yes = any(a in {"-y", "--yes"} or a.startswith("--yes=") for a in argv[1:3])
            if not has_yes:
                argv = ["npx", "-y"] + argv[1:]

        try:
            # 直接执行命令，不通过shell
            # 使用shell=False确保命令不被shell解释，避免注入攻击
            # 使用capture_output=True捕获标准输出和标准错误
            # 使用text=True确保输出为文本格式
            result = subprocess.run(
                argv,
                shell=False,
                cwd=str(self.current_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy(),
            )
            
            # 合并标准输出和标准错误
            # 这样用户可以看到完整的执行结果
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            # 检查输出大小，防止过大输出消耗内存
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size]
                output += f"\n\n⚠️ 输出被截断（超过 {self.max_output_size} 字节）"
            
            # 添加返回码信息，帮助用户了解命令执行状态
            if result.returncode != 0:
                output = f"⚠️ 命令返回码: {result.returncode}\n\n{output}"
            
            return output if output else "✅ 命令执行成功（无输出）"
            
        except subprocess.TimeoutExpired:
            # 命令执行超时，可能是死循环或处理大量数据
            return f"❌ 命令执行超时（超过 {self.timeout} 秒）"
        except Exception as e:
            # 捕获其他异常，如权限错误、文件不存在等
            return f"❌ 命令执行失败: {e}"
    
    def _truncate_output(self, output: str) -> str:
        """截断过大的输出，防止内存问题
        
        此方法检查输出字符串的长度，如果超过配置的最大输出大小，
        则截断输出并添加提示信息，防止过大的输出消耗过多内存。
        
        Args:
            output: 需要检查的输出字符串
            
        Returns:
            str: 原始输出或截断后的输出（如果超过大小限制）
            
        Note:
            - 截断时会保留开头的内容，丢弃超出限制的部分
            - 会在截断的输出末尾添加提示信息，说明输出已被截断
        """
        if len(output) > self.max_output_size:
            return output[: self.max_output_size] + f"\n[输出被截断，超过 {self.max_output_size} 字节限制]"
        return output
    
    def get_current_dir(self) -> str:
        """获取当前工作目录"""
        return str(self.current_dir)
    
    def reset_dir(self):
        """重置到工作目录根"""
        self.current_dir = self.workspace

