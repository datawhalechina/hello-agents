"""
会话管理工具 -- Agent 可调用的 @tool
====================================
提供会话列表、创建、切换、删除、信息查看功能。
遵循与 file_manage_tools 相同的子命令分发模式。

切换会话通过 _pending_switch 全局变量桥接到 Agent / REPL。
"""

from langchain_core.tools import tool
from tool.logger_handler import logger


# ── 跨模块桥接：待切换的会话 ID ──
_pending_switch: str | None = None


def get_pending_switch() -> str | None:
    """获取并清除待切换的会话 ID（供 Agent/REPL 轮询）"""
    global _pending_switch
    sid = _pending_switch
    _pending_switch = None
    return sid


# ── Agent 引用（由 Agent.__init__ 设置）──
_current_agent = None


def set_current_agent(agent) -> None:
    """注册当前 Agent 实例，供 session 工具使用"""
    global _current_agent
    _current_agent = agent


def _get_agent():
    """获取当前 Agent 实例"""
    if _current_agent is None:
        raise RuntimeError("Session 工具未初始化：Agent 尚未注册")
    return _current_agent


# ── 帮助文本 ──

_SESSION_HELP = """📋 会话管理工具 -- 使用指南
═══════════════════════════════
list                    列出所有已保存的会话
info [会话ID]           查看会话详情（默认当前会话）
create <名称>           创建新会话并切换过去
switch <会话ID>         切换到指定会话
delete <会话ID>         删除指定会话
current                 显示当前会话 ID
save                    手动保存当前会话状态

示例:
  'list'
  'create 项目开发会话'
  'switch abc12345'
  'delete old_session'
  'info'
  'info abc12345'"""


# ═══════════════════════════════════════════════════════════
#  Tool 定义
# ═══════════════════════════════════════════════════════════

@tool(description="""会话管理工具，用于查看、创建、切换、删除和保存对话会话。

每个会话独立保存对话上下文和待办清单数据，支持在不同会话间切换。

操作命令:
  list                          → 列出所有会话（当前会话标记 *）
  info [会话ID]                 → 查看会话详情（默认当前会话）
  create <名称>                 → 创建新会话并切换过去
  switch <会话ID>               → 切换到指定会话（自动保存当前会话）
  delete <会话ID>               → 删除指定会话（不能删除当前会话）
  current                       → 显示当前会话 ID
  save                          → 手动保存当前会话状态

示例:
  'list'                      列出所有会话
  'create 代码重构项目'        创建新会话
  'switch abc12345'           切换到 abc12345
  'delete old_chat'           删除 old_chat
  'info'                      查看当前会话
  'info abc12345'             查看会话 abc12345 详情""")
def session(command: str) -> str:
    """会话管理工具入口，分发到各子命令"""
    cmd = command.strip()
    if not cmd:
        return _SESSION_HELP

    parts = cmd.split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    try:
        if action == "list":
            return _cmd_list()
        elif action == "info":
            return _cmd_info(arg)
        elif action == "create":
            return _cmd_create(arg)
        elif action == "switch":
            return _cmd_switch(arg)
        elif action == "delete":
            return _cmd_delete(arg)
        elif action == "current":
            return _cmd_current()
        elif action == "save":
            return _cmd_save()
        else:
            return f"错误: 未知操作 '{action}'。支持: list / info / create / switch / delete / current / save"
    except RuntimeError as e:
        return f"错误: {e}"
    except Exception as e:
        logger.error(f"[session_tool] {action} 操作异常: {e}")
        return f"错误: 会话 {action} 操作失败 —— {e}"


# ═══════════════════════════════════════════════════════════
#  子命令实现
# ═══════════════════════════════════════════════════════════

def _cmd_list() -> str:
    """列出所有会话"""
    agent = _get_agent()
    sessions = agent.list_sessions()
    if not sessions:
        return "📭 暂无保存的会话。\n💡 使用 'create <名称>' 创建新会话。"

    lines = ["📋 会话列表", "─" * 50]
    current = agent.session_id
    for s in sessions:
        marker = "← 当前" if s["session_id"] == current else ""
        size_str = _format_size_str(s.get("size_bytes", 0))
        lines.append(
            f"  [{s['session_id']}] {s.get('message_count', 0)} 条消息 "
            f"| {size_str} | {s.get('updated_at', '')} {marker}"
        )
    return "\n".join(lines)


def _cmd_info(arg: str) -> str:
    """查看会话详情"""
    agent = _get_agent()
    sid = arg if arg else agent.session_id
    if not sid:
        return "📭 当前无活跃会话。使用 'create <名称>' 创建新会话。"

    info = agent.get_session_info(sid)
    if info is None:
        return f"❌ 会话 [{sid}] 不存在。"

    current_mark = " (当前)" if sid == agent.session_id else ""
    lines = [
        f"📋 会话 [{sid}]{current_mark}",
        "─" * 40,
        f"  消息数: {info.get('message_count', 0)}",
        f"  文件大小: {info.get('size_human', '未知')}",
        f"  创建时间: {info.get('created_at', '未知')}",
        f"  更新时间: {info.get('updated_at', '未知')}",
    ]
    return "\n".join(lines)


def _cmd_create(arg: str) -> str:
    """创建新会话并切换过去"""
    agent = _get_agent()
    name = arg if arg else "默认会话"
    sid = agent.new_session(name)
    return f"✅ 已创建并切换到新会话 [{sid}] —— {name}"


def _cmd_switch(arg: str) -> str:
    """切换到指定会话"""
    if not arg:
        return "错误: 用法 'switch <会话ID>'"

    agent = _get_agent()
    ok = agent.switch_session(arg)
    if ok:
        return f"✅ 已切换到会话 [{arg}]"
    return f"❌ 会话 [{arg}] 不存在"


def _cmd_delete(arg: str) -> str:
    """删除指定会话"""
    if not arg:
        return "错误: 用法 'delete <会话ID>'"

    agent = _get_agent()
    ok = agent.delete_session(arg)
    if ok:
        return f"🗑 已删除会话 [{arg}]"
    return f"❌ 无法删除会话 [{arg}]（不存在或为当前活跃会话）"


def _cmd_current() -> str:
    """显示当前会话 ID"""
    agent = _get_agent()
    sid = agent.session_id
    if not sid:
        return "📭 当前无活跃会话。使用 'create <名称>' 创建新会话。"
    info = agent.get_session_info(sid)
    msg_count = info.get("message_count", 0) if info else "?"
    return f"📋 当前会话 [{sid}] —— {msg_count} 条消息"


def _cmd_save() -> str:
    """手动保存当前会话"""
    agent = _get_agent()
    sid = agent.session_id
    if not sid:
        return "📭 当前无活跃会话，无需保存。"
    agent._save_session_state()
    return f"✅ 已保存当前会话 [{sid}]"


def _format_size_str(size_bytes: int) -> str:
    """格式化文件大小为简短字符串"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"
