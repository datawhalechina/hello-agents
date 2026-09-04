"""
文件管理工具 + 用户确认工具。

提供两个 @tool 装饰的函数：
  - ask_for_answer: 向用户提问并获得确认（通用工具）
  - file_manage: 文件系统 CRUD 操作（支持 manual/auto 双模式）

manual 模式: 读操作自由，写/删/建目录需通过 ask_for_answer 获取用户批准
auto 模式:   自由 CRUD，但拦截删除目录、操作系统敏感路径等风险操作
"""
import os
import datetime
from typing import Any
from langchain_core.tools import tool
from tool.config_handler import FileManage_Config
from tool.logger_handler import logger
from tool.path_tool import get_project_root
from agent_tools.file_safety import (
    resolve_safe_path,
    is_blocked_pattern,
    is_allowed_write_extension,
    check_file_size,
    is_risky_auto_operation,
    check_max_depth,
    is_manual_mode,
    is_auto_mode,
    get_mode,
    _format_size,
)

# ---- 模块级配置 ----
_FILE_MODE = get_mode()
_ALLOWED_EXTENSIONS = FileManage_Config.get("allowed_write_extensions", [])
_MAX_READ = FileManage_Config.get("max_file_size_read", 1_048_576)
_MAX_WRITE = FileManage_Config.get("max_file_size_write", 5_242_880)
_FILE_OPS_LOG_DIR = FileManage_Config.get("file_ops_log_dir", "logs/file_operations")


# ---- 工具 1: ask_for_answer ----

@tool(description="""向用户请求确认或获取答案的通用工具。

在手动模式下执行潜在的破坏性文件操作（写入、追加、删除、创建目录）之前，
Agent 必须调用此工具获取用户批准。

输入格式: 一个字符串，描述需要向用户询问的问题。
系统会在终端打印此问题并等待用户输入。

返回: 用户在终端输入的原始回答。

使用示例:
  ask_for_answer("是否允许将内容写入文件 output.txt？内容长度: 42 字节")
  ask_for_answer("是否允许删除文件 temp/old_data.csv？")
""")
def ask_for_answer(question: str) -> str:
    """向用户提问并获得确认"""
    print()
    print("=" * 60)
    print("🔐 [Agent 请求确认]")
    print("-" * 60)
    print(question)
    print("-" * 60)
    try:
        answer = input("请输入您的回答 (yes/no 或任意回复): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "用户取消输入，操作视为被拒绝。"
    print("=" * 60)
    return f"用户回答: {answer}"


# ---- 工具 2: file_manage ----

_FILE_HELP = """file_manage 文件管理工具 — 用法:
  read <路径> [偏移行] [行数限制]    读取文件内容（读操作无需批准）
  write <路径> | <内容>              创建或覆写文件
  append <路径> | <内容>             追加内容到文件
  delete <路径>                      删除单个文件（不删目录）
  mkdir <路径>                       创建目录（含父目录）
  list [路径] [模式]                 列出目录内容，可选 glob 过滤
  info <路径>                        查看文件/目录元信息
  exists <路径>                      检查路径是否存在
  search <模式> [目录]               递归搜索匹配 glob 模式的文件
在手动模式下，write/append/delete/mkdir 需先获得批准后加 --approved 重试。"""


@tool(description=f"""文件系统管理工具，支持文件的读取、写入、追加、删除、目录操作和文件搜索。

当前模式: {_FILE_MODE}

子命令说明:
  read <路径> [偏移行] [行数限制]
      读取文件内容。偏移行从 0 开始，行数限制最大 2000。
      示例: read config/AgentConfig.yml
      示例: read src/large_file.py 100 50

  write [--approved] <路径> | <内容>
      创建或覆写文件。手动模式下需先通过 ask_for_answer 批准，然后加 --approved 重试。
      示例: write output.txt | Hello World
      示例: write --approved output.txt | Hello World

  append [--approved] <路径> | <内容>
      追加内容到文件末尾。手动模式规则同 write。
      示例: append log.txt | [2024-01-01] 任务完成

  delete [--approved] <路径>
      删除单个文件（不接受目录路径）。
      示例: delete temp/obsolete.csv

  mkdir [--approved] <路径>
      创建目录及必要的父目录。
      示例: mkdir output/reports/2024

  list [路径] [模式]
      列出目录内容。可选 glob 模式过滤（如 "*.py"）。
      不区分文件和目录时列出全部条目。
      示例: list config/
      示例: list . *.py

  info <路径>
      查看文件或目录元信息：类型、大小、修改时间、行数（文本文件）。
      示例: info config/AgentConfig.yml

  exists <路径>
      检查路径是否存在。返回 true 或 false。
      示例: exists output/report.pdf

  search <模式> [目录]
      递归搜索匹配 glob 模式的文件，返回相对路径列表。
      示例: search **/*.py agent_tools/
      示例: search *.yml config/

安全规则（始终生效）:
  - 禁止路径遍历攻击 (..)
  - 禁止操作 .env / .git / .exe / .dll 等被阻止的路径
  - 文件大小上限: 读 {_MAX_READ // 1024 // 1024}MB / 写 {_MAX_WRITE // 1024 // 1024}MB
  - 写入仅允许扩展名: {', '.join(_ALLOWED_EXTENSIONS[:8])}...
""")
def file_manage(command: str) -> str:
    """文件管理工具入口，分发到各子命令处理函数"""
    cmd = command.strip()
    if not cmd:
        return _FILE_HELP

    # 解析子命令
    parts = cmd.split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if action == "read":
        return _cmd_read(arg)
    elif action == "write":
        return _cmd_write(arg)
    elif action == "append":
        return _cmd_append(arg)
    elif action == "delete":
        return _cmd_delete(arg)
    elif action == "mkdir":
        return _cmd_mkdir(arg)
    elif action == "list":
        return _cmd_list(arg)
    elif action == "info":
        return _cmd_info(arg)
    elif action == "exists":
        return _cmd_exists(arg)
    elif action == "search":
        return _cmd_search(arg)
    else:
        return f"❌ 未知操作 '{action}'。\n支持: read / write / append / delete / mkdir / list / info / exists / search\n\n{_FILE_HELP}"


# ============================================================
# 手动模式批准逻辑
# ============================================================

def _check_manual_approval(action: str, path: str, detail: str) -> tuple[bool, str]:
    """
    检查手动模式下是否需要用户批准。

    Returns:
        (proceed, message)
        - proceed=True: 可以继续执行
        - proceed=False: 返回提示信息，要求先调用 ask_for_answer
    """
    if is_auto_mode():
        return True, ""

    # 手动模式: 检查是否包含 --approved 标记
    if "--approved" in action or "--approved" in path:
        return True, ""

    # 需要批准
    mode_label = f"[手动模式 - 需要用户批准]"
    msg = (
        f"\n{'═' * 60}\n"
        f"🔐 {mode_label}\n"
        f"{'═' * 60}\n"
        f"{detail}\n"
        f"{'─' * 60}\n"
        f"请先调用 ask_for_answer 获取用户批准，然后用以下命令重试：\n"
        f"  {action} --approved {path}\n"
        f"{'═' * 60}"
    )
    return False, msg


# ============================================================
# 安全校验管线
# ============================================================

def _safety_check(path: str, operation: str) -> tuple[str | None, str | None]:
    """
    对路径执行完整安全校验管线。

    Returns:
        (resolved_abs_path, error_reason)
        - 成功: (abs_path, None)
        - 失败: (None, error_string)
    """
    # [1] 路径遍历 + 沙箱检查
    abs_path, err = resolve_safe_path(path)
    if err:
        return None, f"❌ 安全校验失败: {err}"

    # [2] 全局禁止模式
    blocked, pattern = is_blocked_pattern(abs_path)
    if blocked:
        return None, f"❌ 路径被禁止: 匹配模式 '{pattern}' → {abs_path}"

    return abs_path, None


def _full_safety_pipeline(
    path: str, operation: str, content: str | None = None
) -> tuple[str | None, str | None]:
    """
    完整安全校验管线（用于写/删操作）。

    额外检查:
    - 文件大小限制
    - 写扩展名白名单
    - Auto 模式风险检查
    - 路径深度限制
    """
    # 基础安全检查
    abs_path, err = _safety_check(path, operation)
    if err:
        return None, err

    # 操作针对性检查
    if operation in ("write", "append"):
        # 扩展名白名单
        ok, detail = is_allowed_write_extension(abs_path)
        if not ok:
            return None, f"❌ {detail}"

        # 写入内容大小检查
        if content is not None:
            content_bytes = len(content.encode("utf-8"))
            if content_bytes > _MAX_WRITE:
                return None, (
                    f"❌ 内容大小 {_format_size(content_bytes)} 超过写入上限 "
                    f"{_format_size(_MAX_WRITE)}"
                )

        # 目标文件大小检查（仅对已存在的文件）
        ok, detail = check_file_size(abs_path, _MAX_WRITE)
        if not ok:
            return None, f"❌ {detail}"

    elif operation == "read":
        ok, detail = check_file_size(abs_path, _MAX_READ)
        if not ok:
            return None, f"❌ {detail}"

    elif operation == "delete":
        # 禁止删除目录
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            return None, "❌ 禁止删除目录。delete 仅支持删除单个文件。"

    # Auto 模式额外风险检查
    if is_auto_mode() and operation in ("write", "append", "delete", "mkdir"):
        is_dir = os.path.isdir(abs_path) if os.path.exists(abs_path) else False
        risky, reason = is_risky_auto_operation(abs_path, operation, is_dir)
        if risky:
            return None, f"❌ Auto 模式安全拦截: {reason}"

    # 路径深度检查
    if operation in ("mkdir", "search"):
        ok, detail = check_max_depth(abs_path)
        if not ok:
            return None, f"❌ {detail}"

    return abs_path, None


# ============================================================
# 读操作
# ============================================================

def _cmd_read(arg: str) -> str:
    """read <路径> [偏移行] [行数限制]"""
    tokens = arg.strip().split()
    if not tokens:
        return "❌ 用法: read <路径> [偏移行] [行数限制]"

    raw_path = tokens[0]
    offset = 0
    limit = 1000

    try:
        if len(tokens) >= 2:
            offset = int(tokens[1])
        if len(tokens) >= 3:
            limit = int(tokens[2])
    except ValueError:
        return "❌ 偏移行和行数限制必须是整数"

    limit = min(limit, 2000)  # 硬上限

    # 安全校验
    abs_path, err = _safety_check(raw_path, "read")
    if err:
        return err

    # 检查文件是否存在
    if not os.path.exists(abs_path):
        return f"❌ 文件不存在: {abs_path}"
    if not os.path.isfile(abs_path):
        return f"❌ 路径不是文件: {abs_path}"

    # 检查文件大小
    ok, detail = check_file_size(abs_path, _MAX_READ)
    if not ok:
        return f"❌ {detail}"

    # 读取文件
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        logger.exception(f"读取文件失败: {abs_path}")
        return f"❌ 读取文件失败: {e}"

    total_lines = len(lines)

    if offset >= total_lines:
        return f"❌ 偏移行 {offset} 超出文件总行数 {total_lines}"

    selected = lines[offset : offset + limit]
    actual_count = len(selected)
    content = "".join(selected)

    # 带行号的输出
    numbered = []
    for i, line in enumerate(selected, start=offset + 1):
        numbered.append(f"{i:>6} | {line.rstrip()}")

    result = "\n".join(numbered)

    header = (
        f"📄 文件: {os.path.basename(abs_path)}\n"
        f"   路径: {abs_path}\n"
        f"   大小: {_format_size(os.path.getsize(abs_path))} | "
        f"总行数: {total_lines} | "
        f"显示: {offset + 1}-{offset + actual_count} 行"
    )

    log_op("read", abs_path, f"读取 {actual_count} 行")

    return f"{header}\n{'-' * 60}\n{result}"


# ============================================================
# 写操作
# ============================================================

def _cmd_write(arg: str) -> str:
    """write [--approved] <路径> | <内容>"""
    return _cmd_write_append(arg, "write")


def _cmd_append(arg: str) -> str:
    """append [--approved] <路径> | <内容>"""
    return _cmd_write_append(arg, "append")


def _cmd_write_append(arg: str, action: str) -> str:
    """共用 write/append 逻辑"""
    approved = False
    remaining = arg.strip()

    # 解析 --approved 标记
    if remaining.startswith("--approved"):
        approved = True
        remaining = remaining[len("--approved"):].strip()

    # 解析路径和内容: <路径> | <内容>
    if "|" not in remaining:
        return f"❌ 用法: {action} [--approved] <路径> | <内容>"

    pipe_idx = remaining.index("|")
    raw_path = remaining[:pipe_idx].strip()
    content = remaining[pipe_idx + 1:].lstrip()  # | 后的前导空白视为分隔符的一部分

    if not raw_path:
        return "❌ 路径不能为空"

    # 手动模式批准检查
    if is_manual_mode() and not approved:
        abs_path, err = _safety_check(raw_path, action)
        if err:
            return err
        content_size = len(content.encode("utf-8"))
        preview = content[:200] + ("..." if len(content) > 200 else "")
        detail = (
            f"操作: {action.upper()}\n"
            f"路径: {abs_path}\n"
            f"内容大小: {_format_size(content_size)}\n"
            f"预览: {preview}"
        )
        proceed, msg = _check_manual_approval(action, f"{raw_path} | <内容>", detail)
        if not proceed:
            return msg

    # 完整安全校验
    abs_path, err = _full_safety_pipeline(raw_path, action, content)
    if err:
        return err

    # 确保父目录存在
    parent_dir = os.path.dirname(abs_path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            return f"❌ 无法创建父目录 {parent_dir}: {e}"

    # 执行写入
    mode = "a" if action == "append" else "w"
    try:
        with open(abs_path, mode, encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.exception(f"写入文件失败: {abs_path}")
        return f"❌ 写入文件失败: {e}"

    bytes_written = len(content.encode("utf-8"))
    file_size = os.path.getsize(abs_path)
    action_cn = "追加到" if action == "append" else "写入"
    log_op(action, abs_path, f"{action_cn} {_format_size(bytes_written)}")

    return (
        f"✅ 已{action_cn}文件\n"
        f"   路径: {abs_path}\n"
        f"   写入: {_format_size(bytes_written)} | 文件总大小: {_format_size(file_size)}"
    )


# ============================================================
# 删除操作
# ============================================================

def _cmd_delete(arg: str) -> str:
    """delete [--approved] <路径>"""
    approved = False
    remaining = arg.strip()

    if remaining.startswith("--approved"):
        approved = True
        remaining = remaining[len("--approved"):].strip()

    raw_path = remaining

    if not raw_path:
        return "❌ 用法: delete [--approved] <路径>"

    # 手动模式批准检查
    if is_manual_mode() and not approved:
        abs_path, err = _safety_check(raw_path, "delete")
        if err:
            return err

        if not os.path.exists(abs_path):
            return f"❌ 文件不存在: {abs_path}"

        file_size = os.path.getsize(abs_path) if os.path.isfile(abs_path) else 0
        detail = (
            f"操作: DELETE\n"
            f"路径: {abs_path}\n"
            f"大小: {_format_size(file_size)}"
        )
        proceed, msg = _check_manual_approval("delete", raw_path, detail)
        if not proceed:
            return msg

    # 完整安全校验
    abs_path, err = _full_safety_pipeline(raw_path, "delete")
    if err:
        return err

    # 确认是文件才删除
    if not os.path.exists(abs_path):
        return f"❌ 文件不存在: {abs_path}"
    if os.path.isdir(abs_path):
        return "❌ 禁止删除目录。delete 仅支持删除单个文件。"

    file_size = os.path.getsize(abs_path)

    try:
        os.remove(abs_path)
    except Exception as e:
        logger.exception(f"删除文件失败: {abs_path}")
        return f"❌ 删除文件失败: {e}"

    log_op("delete", abs_path, f"已删除 {_format_size(file_size)}")

    return (
        f"✅ 已删除文件\n"
        f"   路径: {abs_path}\n"
        f"   释放空间: {_format_size(file_size)}"
    )


# ============================================================
# 目录操作
# ============================================================

def _cmd_mkdir(arg: str) -> str:
    """mkdir [--approved] <路径>"""
    approved = False
    remaining = arg.strip()

    if remaining.startswith("--approved"):
        approved = True
        remaining = remaining[len("--approved"):].strip()

    raw_path = remaining

    if not raw_path:
        return "❌ 用法: mkdir [--approved] <路径>"

    # 手动模式批准检查
    if is_manual_mode() and not approved:
        abs_path, err = _safety_check(raw_path, "mkdir")
        if err:
            return err
        detail = (
            f"操作: MKDIR\n"
            f"路径: {abs_path}"
        )
        proceed, msg = _check_manual_approval("mkdir", raw_path, detail)
        if not proceed:
            return msg

    # 完整安全校验
    abs_path, err = _full_safety_pipeline(raw_path, "mkdir")
    if err:
        return err

    if os.path.exists(abs_path):
        if os.path.isdir(abs_path):
            return f"ℹ️  目录已存在: {abs_path}"
        else:
            return f"❌ 已存在同名文件，无法创建目录: {abs_path}"

    try:
        os.makedirs(abs_path, exist_ok=True)
    except Exception as e:
        logger.exception(f"创建目录失败: {abs_path}")
        return f"❌ 创建目录失败: {e}"

    log_op("mkdir", abs_path, "已创建目录")
    return f"✅ 已创建目录: {abs_path}"


# ============================================================
# 列表操作
# ============================================================

def _cmd_list(arg: str) -> str:
    """list [路径] [模式]"""
    tokens = arg.strip().split()
    raw_path = "."
    pattern = None

    if len(tokens) >= 1:
        raw_path = tokens[0]
    if len(tokens) >= 2:
        pattern = tokens[1]

    # 安全校验
    abs_path, err = _safety_check(raw_path, "list")
    if err:
        return err

    if not os.path.exists(abs_path):
        return f"❌ 路径不存在: {abs_path}"
    if not os.path.isdir(abs_path):
        return f"❌ 不是目录: {abs_path}"

    try:
        entries = sorted(os.listdir(abs_path))
    except PermissionError:
        return f"❌ 无权限读取目录: {abs_path}"
    except Exception as e:
        return f"❌ 读取目录失败: {e}"

    # 应用模式过滤
    if pattern:
        import fnmatch
        entries = [e for e in entries if fnmatch.fnmatch(e, pattern)]

    if not entries:
        return f"📂 目录为空（或无匹配项）: {abs_path}"

    # 格式化输出
    result_lines = [f"📂 目录: {abs_path}"]
    if pattern:
        result_lines.append(f"   过滤: {pattern}")
    result_lines.append(f"   条目数: {len(entries)}")
    result_lines.append("-" * 60)

    for entry in entries:
        entry_path = os.path.join(abs_path, entry)
        try:
            if os.path.isdir(entry_path):
                icon = "[D]"
            else:
                size = _format_size(os.path.getsize(entry_path))
                icon = f"[F] {size:>10}"
        except OSError:
            icon = "[?]"

        result_lines.append(f"  {icon}  {entry}")

    return "\n".join(result_lines)


# ============================================================
# 信息查询
# ============================================================

def _cmd_info(arg: str) -> str:
    """info <路径>"""
    raw_path = arg.strip()
    if not raw_path:
        return "❌ 用法: info <路径>"

    abs_path, err = _safety_check(raw_path, "info")
    if err:
        return err

    if not os.path.exists(abs_path):
        return f"❌ 路径不存在: {abs_path}"

    stat = os.stat(abs_path)
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    atime = datetime.datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S")

    result_lines = [f"📋 路径信息: {abs_path}"]
    result_lines.append("-" * 60)

    if os.path.isdir(abs_path):
        result_lines.append(f"  类型: 目录")
        result_lines.append(f"  修改时间: {mtime}")
    else:
        _, ext = os.path.splitext(abs_path)
        result_lines.append(f"  类型: 文件")
        result_lines.append(f"  扩展名: {ext if ext else '(无)'}")
        result_lines.append(f"  大小: {_format_size(stat.st_size)} ({stat.st_size:,} 字节)")
        result_lines.append(f"  修改时间: {mtime}")
        result_lines.append(f"  访问时间: {atime}")

        # 尝试统计文本文件行数
        if ext.lower() in _ALLOWED_EXTENSIONS:
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    line_count = sum(1 for _ in f)
                result_lines.append(f"  行数: {line_count:,}")
            except Exception:
                pass

    # 检查是否被封锁
    blocked, pattern = is_blocked_pattern(abs_path)
    if blocked:
        result_lines.append(f"  ⚠️  匹配禁止模式: {pattern}")

    return "\n".join(result_lines)


def _cmd_exists(arg: str) -> str:
    """exists <路径>"""
    raw_path = arg.strip()
    if not raw_path:
        return "❌ 用法: exists <路径>"

    abs_path, err = _safety_check(raw_path, "exists")
    if err:
        return err

    if os.path.exists(abs_path):
        kind = "目录" if os.path.isdir(abs_path) else "文件"
        return f"✅ 路径存在 ({kind}): {abs_path}"
    else:
        return f"❌ 路径不存在: {abs_path}"


def _cmd_search(arg: str) -> str:
    """search <模式> [目录]"""
    tokens = arg.strip().split()
    if not tokens:
        return "❌ 用法: search <模式> [目录]"

    pattern = tokens[0]
    search_root = tokens[1] if len(tokens) > 1 else "."

    abs_root, err = _safety_check(search_root, "search")
    if err:
        return err

    if not os.path.isdir(abs_root):
        return f"❌ 搜索根目录不存在或不是目录: {abs_root}"

    # 路径深度检查
    ok, detail = check_max_depth(abs_root)
    if not ok:
        return f"❌ {detail}"

    max_depth = FileManage_Config.get("max_directory_depth", 20)
    project_root = os.path.abspath(get_project_root())

    matches = []
    try:
        for dirpath, dirnames, filenames in os.walk(abs_root):
            # 检查深度
            try:
                rel = os.path.relpath(dirpath, project_root)
            except ValueError:
                rel = dirpath
            depth = len(rel.replace("\\", "/").strip("/").split("/"))
            if depth > max_depth:
                dirnames.clear()  # 不继续深入
                continue

            # 跳过被阻止的目录
            dirnames_to_remove = []
            for d in dirnames:
                full_d = os.path.join(dirpath, d)
                blocked, _ = is_blocked_pattern(full_d)
                if blocked:
                    dirnames_to_remove.append(d)
            for d in dirnames_to_remove:
                dirnames.remove(d)

            # 匹配文件
            import fnmatch
            for fname in filenames:
                full_f = os.path.join(dirpath, fname)
                blocked, _ = is_blocked_pattern(full_f)
                if blocked:
                    continue
                if fnmatch.fnmatch(fname, pattern):
                    # 同时检查完整路径的 glob 匹配
                    full_rel = os.path.relpath(full_f, abs_root)
                    if fnmatch.fnmatch(full_rel, pattern) or fnmatch.fnmatch(fname, pattern):
                        matches.append(full_f)

    except PermissionError as e:
        logger.warning(f"搜索权限不足: {e}")
    except Exception as e:
        return f"❌ 搜索失败: {e}"

    if not matches:
        return f"📂 未找到匹配 '{pattern}' 的文件（搜索范围: {abs_root}）"

    # 限制返回数量
    max_results = 200
    truncated = len(matches) > max_results
    if truncated:
        matches = matches[:max_results]

    result_lines = [
        f"📂 搜索: '{pattern}' 在 {abs_root}",
        f"   找到 {len(matches)} 个文件" + (" (仅显示前200个)" if truncated else ""),
        "-" * 60,
    ]

    for m in matches:
        try:
            rel_path = os.path.relpath(m, abs_root)
        except ValueError:
            rel_path = m
        try:
            size = _format_size(os.path.getsize(m))
        except OSError:
            size = "?"
        result_lines.append(f"  [{size:>10}]  {rel_path}")

    return "\n".join(result_lines)


# ============================================================
# 操作日志
# ============================================================

def log_op(action: str, path: str, detail: str = "") -> None:
    """记录文件操作"""
    logger.info(f"[file_manage] {action.upper()} | {path} | {detail}")

    # 写入专门的日志文件
    try:
        project_root = os.path.abspath(get_project_root())
        log_dir = os.path.join(project_root, _FILE_OPS_LOG_DIR)
        os.makedirs(log_dir, exist_ok=True)

        today = datetime.date.today().isoformat()
        log_file = os.path.join(log_dir, f"file_ops_{today}.log")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {action.upper():8} | {path} | {detail}\n")
    except Exception:
        pass  # 日志写入失败不应影响主操作
