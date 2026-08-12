"""HelloClaw CLI 入口

使用 click 实现命令行接口。
"""

import os
import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# 禁用 PYTHONSTARTUP 以避免 I/O 问题
os.environ.pop("PYTHONSTARTUP", None)

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="helloclaw")
def cli():
    """HelloClaw - 你的个性化 AI 助手"""
    pass


@cli.command()
@click.option("--session", "-s", "session_id", default=None, help="指定会话 ID")
@click.option("--workspace", "-w", default=None, help="指定工作空间路径")
def chat(session_id: Optional[str], workspace: Optional[str]):
    """启动交互式对话（REPL 模式）"""
    from ..channels.cli_channel import CLIChannel
    from ..agent.helloclaw_agent import HelloClawAgent
    from ..workspace.manager import WorkspaceManager

    # 确定工作空间路径
    workspace_path = workspace or os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")

    # 初始化工作空间
    ws = WorkspaceManager(workspace_path)
    ws.ensure_workspace_exists()

    # 初始化 Agent
    try:
        agent = HelloClawAgent(workspace_path=workspace_path)
    except Exception as e:
        console.print(f"[red]❌ 初始化 Agent 失败: {e}[/red]")
        raise SystemExit(1)

    # 启动 CLI Channel
    channel = CLIChannel(agent, session_id=session_id)
    asyncio.run(channel.run())


@cli.command()
@click.argument("question")
@click.option("--session", "-s", "session_id", default=None, help="指定会话 ID")
@click.option("--workspace", "-w", default=None, help="指定工作空间路径")
@click.option("--no-stream", is_flag=True, help="禁用流式输出")
def ask(question: str, session_id: Optional[str], workspace: Optional[str], no_stream: bool):
    """单次提问，输出结果后退出"""
    from ..agent.helloclaw_agent import HelloClawAgent
    from ..workspace.manager import WorkspaceManager

    # 确定工作空间路径
    workspace_path = workspace or os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")

    # 初始化工作空间
    ws = WorkspaceManager(workspace_path)
    ws.ensure_workspace_exists()

    # 初始化 Agent
    try:
        agent = HelloClawAgent(workspace_path=workspace_path)
    except Exception as e:
        console.print(f"[red]❌ 初始化 Agent 失败: {e}[/red]")
        raise SystemExit(1)

    if no_stream:
        # 同步模式
        response = agent.chat(question, session_id=session_id)
        console.print(Markdown(response))
    else:
        # 流式模式
        async def run_stream():
            async for event in agent.achat(question, session_id=session_id):
                if event.type.value == "llm_chunk":
                    console.print(event.chunk, end="")

        asyncio.run(run_stream())
        console.print()  # 换行


@cli.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--workspace", "-w", default=None, help="指定工作空间路径")
@click.option("--list", "-l", "list_all", is_flag=True, help="列出所有配置")
@click.option("--edit", "-e", is_flag=True, help="用编辑器打开配置文件")
def config(key: Optional[str], value: Optional[str], workspace: Optional[str], list_all: bool, edit: bool):
    """配置管理

    用法:
      helloclaw config              # 显示所有配置
      helloclaw config model_id     # 显示指定配置项
      helloclaw config model_id glm-4  # 设置配置项
      helloclaw config --edit       # 用编辑器打开配置文件
    """
    from ..workspace.manager import WorkspaceManager

    workspace_path = workspace or os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")
    ws = WorkspaceManager(workspace_path)
    ws.ensure_workspace_exists()

    config_path = os.path.join(ws.workspace_path, "config.json")

    if edit:
        # 用编辑器打开配置文件
        editor = os.getenv("EDITOR", "nano")
        os.system(f"{editor} {config_path}")
        return

    # 读取配置
    llm_config = ws.get_llm_config()

    if list_all or (key is None and value is None):
        # 显示所有配置
        console.print(Panel(
            "\n".join([f"[cyan]{k}:[/cyan] {v}" for k, v in llm_config.items()]) or "[dim]暂无配置[/dim]",
            title="HelloClaw 配置",
            border_style="blue"
        ))
    elif key and value is None:
        # 显示单个配置项
        if key in llm_config:
            console.print(f"[cyan]{key}:[/cyan] {llm_config[key]}")
        else:
            console.print(f"[yellow]配置项 '{key}' 不存在[/yellow]")
    elif key and value:
        # 设置配置项
        import json
        llm_config[key] = value
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(llm_config, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✓[/green] 已设置 {key} = {value}")


@cli.command()
@click.option("--workspace", "-w", default=None, help="指定工作空间路径")
@click.option("--list", "-l", "list_all", is_flag=True, help="列出所有会话")
@click.option("--delete", "-d", "delete_id", default=None, help="删除指定会话")
@click.option("--clear", is_flag=True, help="清除所有会话")
def sessions(workspace: Optional[str], list_all: bool, delete_id: Optional[str], clear: bool):
    """会话管理

    用法:
      helloclaw sessions           # 列出所有会话
      helloclaw sessions --list    # 列出所有会话
      helloclaw sessions --delete <id>  # 删除指定会话
      helloclaw sessions --clear   # 清除所有会话
    """
    from ..workspace.manager import WorkspaceManager
    from datetime import datetime
    import glob

    workspace_path = workspace or os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace")
    ws = WorkspaceManager(workspace_path)
    ws.ensure_workspace_exists()

    sessions_dir = os.path.join(ws.workspace_path, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    if delete_id:
        # 删除指定会话
        filepath = os.path.join(sessions_dir, f"{delete_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            console.print(f"[green]✓[/green] 已删除会话: {delete_id}")
        else:
            console.print(f"[red]✗[/red] 会话不存在: {delete_id}")
    elif clear:
        # 清除所有会话
        session_files = glob.glob(os.path.join(sessions_dir, "*.json"))
        if session_files:
            for f in session_files:
                os.remove(f)
            console.print(f"[green]✓[/green] 已清除 {len(session_files)} 个会话")
        else:
            console.print("[yellow]没有会话需要清除[/yellow]")
    else:
        # 列出所有会话
        session_files = glob.glob(os.path.join(sessions_dir, "*.json"))
        if not session_files:
            console.print("[dim]暂无会话[/dim]")
            return

        # 按修改时间排序
        session_list = []
        for filepath in session_files:
            stat = os.stat(filepath)
            session_id = os.path.basename(filepath)[:-5]  # 去掉 .json
            session_list.append({
                "id": session_id,
                "updated_at": stat.st_mtime,
            })

        session_list.sort(key=lambda x: x["updated_at"], reverse=True)

        for s in session_list:
            updated = datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M")
            console.print(f"[cyan]{s['id']}[/cyan] - {updated}")


def main():
    """CLI 主入口"""
    cli()


if __name__ == "__main__":
    main()
