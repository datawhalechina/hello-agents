"""CLI Channel - 命令行交互渠道

提供 REPL 交互循环，支持：
- 多轮对话
- 流式输出
- 退出命令
- 丰富的终端输出
"""

import asyncio
import sys
from typing import Optional, TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text

if TYPE_CHECKING:
    from ..agent.helloclaw_agent import HelloClawAgent


class CLIChannel:
    """CLI 交互渠道

    实现 REPL 交互循环，处理用户输入和 Agent 输出。

    Attributes:
        agent: HelloClaw Agent 实例
        session_id: 当前会话 ID
        console: Rich Console 实例
    """

    # 退出命令
    EXIT_COMMANDS = {"exit", "quit", "q", "bye", "退出"}

    # 帮助命令
    HELP_COMMANDS = {"help", "h", "帮助", "?"}

    # 清屏命令
    CLEAR_COMMANDS = {"clear", "cls", "清屏"}

    def __init__(
        self,
        agent: "HelloClawAgent",
        session_id: Optional[str] = None,
    ):
        """初始化 CLI Channel

        Args:
            agent: HelloClaw Agent 实例
            session_id: 会话 ID（可选，默认创建新会话）
        """
        self.agent = agent
        self.session_id = session_id
        self.console = Console()

        # 运行状态
        self._running = False

    async def run(self):
        """启动 REPL 交互循环"""
        self._running = True

        # 打印欢迎信息
        self._print_welcome()

        # 主循环
        while self._running:
            try:
                # 获取用户输入
                user_input = await self._get_input()

                if user_input is None:
                    # 用户输入为空（可能是 EOF）
                    break

                # 处理命令
                if not self._handle_command(user_input):
                    # 不是命令，发送给 Agent
                    await self._chat(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]收到中断信号，输入 'exit' 退出[/yellow]")
            except EOFError:
                self.console.print("\n[yellow]再见！[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]错误: {e}[/red]")

        # 打印告别信息
        self._print_goodbye()

    async def _get_input(self) -> Optional[str]:
        """获取用户输入

        Returns:
            用户输入的文本，如果为空或 EOF 则返回 None
        """
        try:
            # 使用 Prompt 获取输入
            user_input = Prompt.ask("\n[bold cyan]你[/bold cyan]")

            # 去除首尾空白
            user_input = user_input.strip()

            # 空输入
            if not user_input:
                return None

            return user_input

        except (KeyboardInterrupt, EOFError):
            return None

    def _handle_command(self, input_text: str) -> bool:
        """处理特殊命令

        Args:
            input_text: 用户输入

        Returns:
            是否是命令（True = 已处理，False = 不是命令）
        """
        # 转小写比较
        cmd = input_text.lower().strip()

        # 退出命令
        if cmd in self.EXIT_COMMANDS:
            self._running = False
            return True

        # 帮助命令
        if cmd in self.HELP_COMMANDS:
            self._print_help()
            return True

        # 清屏命令
        if cmd in self.CLEAR_COMMANDS:
            self.console.clear()
            self._print_welcome(compact=True)
            return True

        # 不是命令
        return False

    async def _chat(self, message: str):
        """与 Agent 对话

        Args:
            message: 用户消息
        """
        # 显示 Agent 正在思考
        with self.console.status("[bold green]思考中...[/bold green]"):
            # 收集响应
            response_text = Text()

            try:
                # 流式获取响应
                async for event in self.agent.achat(message, session_id=self.session_id):
                    event_type = event.type.value

                    if event_type == "llm_chunk":
                        # 文本块
                        chunk = event.chunk or ""
                        response_text.append(chunk)
                        # 实时输出
                        self.console.print(chunk, end="")

                    elif event_type == "tool_call_start":
                        # 工具调用开始
                        tool_name = getattr(event, "tool_name", "unknown")
                        self.console.print(f"\n[dim]🔧 调用工具: {tool_name}...[/dim]")

                    elif event_type == "tool_call_finish":
                        # 工具调用完成
                        pass  # 静默处理

                    elif event_type == "agent_finish":
                        # 对话完成
                        if hasattr(event, "result") and event.result:
                            # 确保换行
                            self.console.print()

                # 保存会话 ID
                if hasattr(self.agent, "_current_session_id"):
                    self.session_id = self.agent._current_session_id

            except Exception as e:
                self.console.print(f"\n[red]❌ Agent 错误: {e}[/red]")

    def _print_welcome(self, compact: bool = False):
        """打印欢迎信息"""
        if compact:
            self.console.print(Panel(
                f"[bold]{self.agent.name}[/bold] - 你的个性化 AI 助手",
                border_style="blue"
            ))
        else:
            self.console.print(Panel(
                f"[bold]{self.agent.name}[/bold] - 你的个性化 AI 助手\n\n"
                "[dim]输入消息开始对话[/dim]\n"
                "[dim]输入 'help' 查看帮助，'exit' 退出[/dim]",
                title="HelloClaw",
                border_style="blue"
            ))

    def _print_goodbye(self):
        """打印告别信息"""
        self.console.print("\n[bold blue]再见！期待下次见到你 👋[/bold blue]\n")

    def _print_help(self):
        """打印帮助信息"""
        help_text = """[bold]可用命令：[/bold]

[cyan]exit, quit, q[/cyan]  - 退出对话
[cyan]help, h, ?[/cyan]     - 显示帮助
[cyan]clear, cls[/cyan]     - 清屏

[bold]提示：[/bold]
- 直接输入消息与 AI 对话
- 支持多轮对话，上下文会被保留
- 使用 Ctrl+C 可以中断当前操作"""
        self.console.print(Panel(help_text, title="帮助", border_style="green"))
