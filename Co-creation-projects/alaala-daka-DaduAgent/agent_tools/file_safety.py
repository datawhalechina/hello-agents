"""
文件管理安全校验模块。
所有函数都是纯函数 —— 接收输入，返回 (passed: bool, detail: str) 元组。
不产生副作用，不管理状态，不依赖 Agent。
"""
import os
import fnmatch
import re
from pathlib import PurePosixPath
from tool.config_handler import FileManage_Config
from tool.logger_handler import logger
from tool.path_tool import get_project_root


# ---- 内部辅助 ----

def _get_project_root() -> str:
    """获取项目根目录的绝对路径"""
    return os.path.abspath(get_project_root())


def _get_allowed_roots() -> list[str]:
    """获取所有允许的根目录（解析为绝对路径）"""
    project_root = _get_project_root()
    allowed = FileManage_Config.get("allowed_paths", ["."])
    resolved = []
    for p in allowed:
        # 相对于项目根解析
        abs_p = os.path.abspath(os.path.normpath(os.path.join(project_root, p)))
        resolved.append(abs_p)
    return resolved


def _normalize_path(path: str) -> str:
    """
    标准化路径：反斜杠转正斜杠，去除尾部斜杠，转小写。
    用于模式匹配时的路径规范化。
    """
    normalized = path.replace("\\", "/").rstrip("/")
    return normalized.lower()


def _to_posix(abs_path: str) -> str:
    """将绝对路径转换为正斜杠格式"""
    return abs_path.replace("\\", "/")


# ---- 公开校验函数 ----

def resolve_safe_path(user_path: str) -> tuple[str | None, str | None]:
    """
    解析用户提供的路径，进行安全校验。

    校验步骤:
    1. 检测路径遍历攻击 (../ 或 ..\\)
    2. 规范化并解析为绝对路径
    3. 检查是否在允许的目录范围内

    Returns:
        (absolute_path, error_reason)
        - 成功: (resolved_abs_path, None)
        - 失败: (None, error_description)
    """
    # 步骤 1: 检测裸路径遍历
    raw = user_path.strip()
    if not raw:
        return None, "路径不能为空"

    # 检测 ../ 或 ..\（在输入中存在但尚未被解析的）
    if ".." in raw.replace("\\", "/").split("/"):
        return None, "路径遍历攻击被阻止：路径中包含 '..'"

    # 步骤 2: 解析为绝对路径
    project_root = _get_project_root()

    try:
        # 如果是绝对路径，直接使用；否则相对项目根
        if os.path.isabs(raw):
            candidate = os.path.abspath(os.path.normpath(raw))
        else:
            candidate = os.path.abspath(os.path.normpath(
                os.path.join(project_root, raw)
            ))
    except Exception as e:
        logger.warning(f"路径解析异常: {raw} -> {e}")
        return None, f"路径解析失败: {e}"

    # 解析符号链接（在 Windows 上，os.path.realpath 也可用）
    try:
        candidate = os.path.realpath(candidate)
    except Exception:
        pass  # 文件可能尚不存在，使用已解析的路径

    # 步骤 3: 沙箱检查
    in_sandbox, allowed_root = is_within_sandbox(candidate)
    if not in_sandbox:
        allowed_roots = _get_allowed_roots()
        roots_str = ", ".join(allowed_roots)
        return None, (
            f"路径不在允许的目录范围内。\n"
            f"  目标路径: {candidate}\n"
            f"  允许范围: {roots_str}"
        )

    return candidate, None


def is_within_sandbox(abs_path: str) -> tuple[bool, str]:
    """
    检查绝对路径是否在允许的根目录之一内。

    Returns:
        (is_allowed, matched_root_or_error)
    """
    allowed_roots = _get_allowed_roots()
    normalized_path = os.path.normpath(abs_path)

    for root in allowed_roots:
        normalized_root = os.path.normpath(root)
        # 检查路径是否以根目录开头
        if normalized_path == normalized_root:
            return True, normalized_root
        if normalized_path.startswith(normalized_root + os.sep):
            return True, normalized_root

    # 特殊处理：如果 allowed_paths 包含 "."，允许项目根下的所有内容
    # 但上面已经处理过了，这里列出实际的允许范围
    return False, "不在允许的目录内"


def is_blocked_pattern(abs_path: str) -> tuple[bool, str]:
    """
    检查路径是否匹配任何全局禁止模式。

    使用 glob 风格的路径匹配，支持 ** 通配符。

    Returns:
        (is_blocked, matched_pattern_or_empty)
    """
    blocked = FileManage_Config.get("blocked_patterns", [])
    if not blocked:
        return False, ""

    normalized = _normalize_path(abs_path)

    for pattern in blocked:
        normalized_pattern = _normalize_path(pattern)

        # 使用 pathlib 的 match 方法支持 **
        try:
            path_obj = PurePosixPath(normalized)
            pattern_obj = PurePosixPath(normalized_pattern)

            # PurePosixPath.match() 支持 ** 模式
            if path_obj.match(str(pattern_obj)):
                return True, pattern
        except Exception:
            # 回退到简单的 fnmatch
            if fnmatch.fnmatch(normalized, normalized_pattern):
                return True, pattern

    return False, ""


def is_allowed_write_extension(abs_path: str) -> tuple[bool, str]:
    """
    检查文件扩展名是否在允许写入的白名单中。

    Returns:
        (is_allowed, extension)
    """
    allowed = FileManage_Config.get("allowed_write_extensions", [])
    if not allowed:
        return True, ""  # 空白名单表示全部允许

    _, ext = os.path.splitext(abs_path)
    ext_lower = ext.lower()

    if ext_lower in [a.lower() for a in allowed]:
        return True, ext_lower

    allowed_str = ", ".join(allowed)
    return False, f"扩展名 '{ext_lower}' 不在写入白名单中。允许: {allowed_str}"


def check_file_size(abs_path: str, max_bytes: int) -> tuple[bool, str]:
    """
    检查文件大小是否在限制内。

    对于不存在的文件返回通过（由写操作创建新文件是合法的）。

    Returns:
        (within_limit, detail)
    """
    if not os.path.exists(abs_path):
        return True, "文件不存在（将创建）"

    try:
        size = os.path.getsize(abs_path)
        if size > max_bytes:
            size_human = _format_size(size)
            limit_human = _format_size(max_bytes)
            return False, f"文件大小 {size_human} 超过限制 {limit_human}"
        return True, _format_size(size)
    except OSError as e:
        return False, f"无法获取文件大小: {e}"


def is_risky_auto_operation(
    abs_path: str, operation: str, is_directory: bool = False
) -> tuple[bool, str]:
    """
    Auto 模式下的额外风险操作检查。

    在 Auto 模式中禁止：
    - 删除整个目录（非空目录）
    - 在系统敏感路径上执行写/删操作

    Returns:
        (is_risky, reason_or_empty)
    """
    normalized = _normalize_path(abs_path)
    posix_path = _to_posix(abs_path)

    # 检查 1: 禁止删除目录
    if operation == "delete" and is_directory:
        return True, "Auto 模式下禁止删除目录（仅允许删除单个文件）"

    # 检查 2: 操作系统敏感路径
    auto_blocked = FileManage_Config.get("auto_mode_blocked_prefixes", [])
    for prefix in auto_blocked:
        normalized_prefix = _normalize_prefix(prefix)
        if normalized.startswith(normalized_prefix):
            return True, (
                f"Auto 模式下禁止操作此路径：匹配系统敏感前缀 '{prefix}'"
            )

    return False, ""


def check_max_depth(abs_path: str) -> tuple[bool, str]:
    """
    检查路径深度是否在限制内。
    用于 mkdir 和递归操作。

    Returns:
        (within_limit, detail)
    """
    max_depth = FileManage_Config.get("max_directory_depth", 20)
    project_root = _get_project_root()

    try:
        rel = os.path.relpath(abs_path, project_root)
    except ValueError:
        # 不同盘符
        rel = abs_path

    depth = len(rel.replace("\\", "/").strip("/").split("/"))

    if depth > max_depth:
        return False, f"路径深度 {depth} 超过最大限制 {max_depth}"
    return True, f"深度 {depth}"


# ---- 实用函数 ----

def _format_size(size_bytes: int) -> str:
    """格式化文件大小为人可读的字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _normalize_prefix(prefix: str) -> str:
    """
    标准化路径前缀，处理 ~ 和 Windows 路径。
    """
    if prefix.startswith("~"):
        prefix = os.path.expanduser(prefix)
    return _normalize_path(os.path.abspath(os.path.normpath(prefix)))


def get_mode() -> str:
    """获取当前文件管理模式"""
    return FileManage_Config.get("mode", "manual")


def is_manual_mode() -> bool:
    """检查是否处于手动模式"""
    return get_mode() == "manual"


def is_auto_mode() -> bool:
    """检查是否处于自动模式"""
    return get_mode() == "auto"
