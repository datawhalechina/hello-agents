"""
会话持久化存储模块
================
使用 JSONL 格式存储每轮对话的消息记录，遵循 vector_uploader_service/file_record.py 的 JSONL 模式。

职责:
  - 消息序列化/反序列化（LangChain 消息对象 ↔ JSON dict）
  - 会话文件 CRUD（保存、加载、列表、删除）
  - Todo 状态持久化（与会话关联）
"""

import json
import os
import datetime

from langchain_core.messages import (
    HumanMessage, AIMessage, ToolMessage, SystemMessage, BaseMessage
)

from tool.config_handler import Session_Config, System_Config
from tool.path_tool import get_project_root, get_abs_path
from tool.logger_handler import logger


# ═══════════════════════════════════════════════════════════
#  路径工具
# ═══════════════════════════════════════════════════════════

def _get_session_dir() -> str:
    """获取会话存储目录的绝对路径，不存在则自动创建"""
    dir_config = Session_Config.get("sessions_dir", "sessions")
    abs_dir = os.path.join(get_abs_path(get_project_root()), dir_config)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


def _sanitize_session_id(session_id: str) -> str:
    """清洁化 session_id，只保留安全字符 [a-zA-Z0-9_-]"""
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', session_id)
    if not sanitized:
        sanitized = Session_Config.get("default_session_id", "default")
    return sanitized


def _get_session_path(session_id: str) -> str:
    """获取指定会话的 JSONL 文件绝对路径"""
    sid = _sanitize_session_id(session_id)
    return os.path.join(_get_session_dir(), f"{sid}.jsonl")


# ═══════════════════════════════════════════════════════════
#  消息序列化
# ═══════════════════════════════════════════════════════════

def serialize_message(msg) -> dict:
    """将任意消息（dict 或 LangChain 消息对象）转换为 JSON 兼容的 dict"""
    # 用户输入是原始 dict: {'role': 'user', 'content': query}
    if isinstance(msg, dict):
        return {
            "type": "human",
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        }

    # LangChain 消息对象
    msg_type = type(msg).__name__.replace("Message", "").lower()
    type_map = {"human": "human", "ai": "ai", "tool": "tool", "system": "system"}
    record_type = type_map.get(msg_type, msg_type)

    record = {
        "type": record_type,
        "content": getattr(msg, "content", ""),
    }

    # AIMessage 特有的 tool_calls
    if record_type == "ai":
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            record["tool_calls"] = list(tool_calls)

    # ToolMessage 特有的字段
    if record_type == "tool":
        record["name"] = getattr(msg, "name", None)
        record["tool_call_id"] = getattr(msg, "tool_call_id", None)

    # 附加的额外参数
    additional_kwargs = getattr(msg, "additional_kwargs", None)
    if additional_kwargs:
        record["additional_kwargs"] = additional_kwargs

    return record


def deserialize_message(record: dict):
    """将序列化的 dict 恢复为原始消息对象（或原始 dict）"""
    msg_type = record.get("type", "human")
    content = record.get("content", "")

    # 用户消息恢复为原始 dict（保持与 Agent.stream 的兼容性）
    if msg_type == "human":
        return {"role": "user", "content": content}

    # 重建 LangChain 消息对象
    if msg_type == "ai":
        kwargs = {"content": content}
        tool_calls = record.get("tool_calls")
        if tool_calls:
            kwargs["tool_calls"] = tool_calls
        additional = record.get("additional_kwargs")
        if additional:
            kwargs["additional_kwargs"] = additional
        return AIMessage(**kwargs)

    if msg_type == "tool":
        kwargs = {"content": content}
        if record.get("name"):
            kwargs["name"] = record["name"]
        if record.get("tool_call_id"):
            kwargs["tool_call_id"] = record["tool_call_id"]
        return ToolMessage(**kwargs)

    if msg_type == "system":
        return SystemMessage(content=content)

    # __todo__ 是 todo 状态记录，不是对话消息，加载消息时跳过
    if msg_type == "__todo__":
        return None

    # 未知类型回退为 human dict
    logger.warning(f"[session] 未知消息类型 '{msg_type}'，回退为 human dict")
    return {"role": "user", "content": content}


# ═══════════════════════════════════════════════════════════
#  会话 CRUD
# ═══════════════════════════════════════════════════════════

def save_session_messages(session_id: str, messages: list) -> None:
    """将消息列表保存为 JSONL 文件，覆写已有内容"""
    filepath = _get_session_path(session_id)
    encoding = System_Config.get("encoding", "utf-8")

    with open(filepath, "w", encoding=encoding) as f:
        for msg in messages:
            record = serialize_message(msg)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.debug(f"[session] 已保存会话 '{_sanitize_session_id(session_id)}'，{len(messages)} 条消息")


def load_session_messages(session_id: str) -> list | None:
    """从 JSONL 文件加载消息列表。会话不存在返回 None，空文件返回 []"""
    filepath = _get_session_path(session_id)
    encoding = System_Config.get("encoding", "utf-8")

    if not os.path.exists(filepath):
        return None

    messages = []
    with open(filepath, "r", encoding=encoding) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                msg = deserialize_message(record)
                if msg is None:
                    continue  # __todo__ 等非对话记录
                # 跳过历史遗留的空用户消息（避免空气泡 & 浪费上下文）
                if isinstance(msg, dict) and not (msg.get("content") or "").strip():
                    continue
                messages.append(msg)
            except json.JSONDecodeError as e:
                logger.warning(f"[session] 跳过无效行 {line_num}: {e}")
            except Exception as e:
                logger.warning(f"[session] 跳过消息行 {line_num}: {e}")

    logger.debug(f"[session] 已加载会话 '{_sanitize_session_id(session_id)}'，{len(messages)} 条消息")
    return messages


def list_sessions() -> list[dict]:
    """列出所有会话及其元数据，按创建时间倒序（最新创建的在最前）"""
    sessions_dir = _get_session_dir()
    if not os.path.exists(sessions_dir):
        return []

    sessions = []
    for fname in os.listdir(sessions_dir):
        if fname.endswith(".jsonl") and not fname.startswith("_"):
            sid = fname[:-len(".jsonl")]
            filepath = os.path.join(sessions_dir, fname)
            try:
                stat = os.stat(filepath)
                user_count, first_user_text = _scan_user_stats(filepath)
                stored_title = load_session_title(sid)
                sessions.append({
                    "session_id": sid,
                    # 存储标题优先；无存储标题时回退为第一条用户消息的截断
                    "title": stored_title if stored_title else (truncate_title(first_user_text) if first_user_text else ""),
                    "message_count": _count_jsonl_lines(filepath),
                    "user_message_count": user_count,
                    "created_at": _format_timestamp(stat.st_ctime),
                    "updated_at": _format_timestamp(stat.st_mtime),
                    "size_bytes": stat.st_size,
                })
            except OSError:
                continue

    # 按创建时间倒序
    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """删除指定会话文件及其标题 sidecar。返回是否成功删除"""
    filepath = _get_session_path(session_id)
    if os.path.exists(filepath):
        os.remove(filepath)
        meta_path = _get_meta_path(session_id)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        logger.info(f"[session] 已删除会话 '{_sanitize_session_id(session_id)}'")
        return True
    return False


def get_session_info(session_id: str) -> dict | None:
    """获取单个会话的详细信息"""
    filepath = _get_session_path(session_id)
    if not os.path.exists(filepath):
        return None

    try:
        stat = os.stat(filepath)
        user_count, first_user_text = _scan_user_stats(filepath)
        stored_title = load_session_title(session_id)
        return {
            "session_id": _sanitize_session_id(session_id),
            "title": stored_title if stored_title else (truncate_title(first_user_text) if first_user_text else ""),
            "message_count": _count_jsonl_lines(filepath),
            "user_message_count": user_count,
            "created_at": _format_timestamp(stat.st_ctime),
            "updated_at": _format_timestamp(stat.st_mtime),
            "size_bytes": stat.st_size,
            "size_human": _format_size(stat.st_size),
        }
    except OSError:
        return None


def session_exists(session_id: str) -> bool:
    """检查会话是否存在"""
    return os.path.exists(_get_session_path(session_id))


# ═══════════════════════════════════════════════════════════
#  Todo 状态持久化
# ═══════════════════════════════════════════════════════════

def save_session_todos(session_id: str, todos: list[dict], todo_counter: int) -> None:
    """将会话的 todo 状态追加到会话 JSONL 文件末尾（作为特殊记录）"""
    if not Session_Config.get("save_todos", True):
        return

    filepath = _get_session_path(session_id)
    encoding = System_Config.get("encoding", "utf-8")

    # 读取现有内容（排除旧的 __todo__ 记录）
    existing_lines = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding=encoding) as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    if record.get("type") != "__todo__":
                        existing_lines.append(line.rstrip('\n'))
                except json.JSONDecodeError:
                    existing_lines.append(line.rstrip('\n'))

    # 追加新的 todo 记录
    todo_record = {
        "type": "__todo__",
        "todos": todos,
        "todo_counter": todo_counter,
        "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(filepath, "w", encoding=encoding) as f:
        for line in existing_lines:
            f.write(line + "\n")
        f.write(json.dumps(todo_record, ensure_ascii=False) + "\n")


def load_session_todos(session_id: str) -> tuple[list[dict], int] | None:
    """从会话文件中加载 todo 状态。返回 (todos, counter) 或 None"""
    filepath = _get_session_path(session_id)
    if not os.path.exists(filepath):
        return None

    encoding = System_Config.get("encoding", "utf-8")
    with open(filepath, "r", encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("type") == "__todo__":
                    return (record.get("todos", []), record.get("todo_counter", 0))
            except json.JSONDecodeError:
                continue

    return None


# ═══════════════════════════════════════════════════════════
#  内部工具函数
# ═══════════════════════════════════════════════════════════

def _count_jsonl_lines(filepath: str) -> int:
    """统计 JSONL 文件的行数（排除 __todo__ 记录）"""
    try:
        count = 0
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line.strip())
                        if record.get("type") != "__todo__":
                            count += 1
                    except json.JSONDecodeError:
                        count += 1
        return count
    except Exception:
        return 0


def _scan_user_stats(filepath: str) -> tuple[int, str]:
    """单遍扫描会话文件，返回 (用户消息数, 第一条非空用户消息原文)。

    用户消息数只统计 content 非空的 human 记录（历史遗留的空用户记录不计入）。
    first_user_text 不做截断，由调用方决定；坏行跳过，异常返回 (0, "")。
    """
    def _content_text(content) -> str:
        """将 content 归一化为纯文本（兼容字符串 / content block 列表）"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    parts.append(str(block.get("text", "")))
            return "".join(parts)
        return str(content)

    user_count = 0
    first_user_text = ""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "human":
                    continue
                text = _content_text(record.get("content", "")).strip()
                if not text:
                    continue
                user_count += 1
                if not first_user_text:
                    first_user_text = text
    except Exception:
        return (0, "")
    return (user_count, first_user_text)


def _get_meta_path(session_id: str) -> str:
    """获取会话标题 sidecar 文件的绝对路径"""
    sid = _sanitize_session_id(session_id)
    return os.path.join(_get_session_dir(), f"{sid}.meta.json")


def load_session_title(session_id: str) -> str:
    """读取会话标题；文件缺失/损坏时返回空字符串，绝不抛异常"""
    meta_path = _get_meta_path(session_id)
    try:
        with open(meta_path, "r", encoding=System_Config.get("encoding", "utf-8")) as f:
            record = json.load(f)
            title = record.get("title", "")
            return title if isinstance(title, str) else ""
    except (OSError, ValueError):
        return ""


def save_session_title(session_id: str, title: str) -> None:
    """将会话标题写入 sidecar 文件（与消息 JSONL 解耦，不受整文件覆写影响）"""
    meta_path = _get_meta_path(session_id)
    with open(meta_path, "w", encoding=System_Config.get("encoding", "utf-8")) as f:
        json.dump({"title": title}, f, ensure_ascii=False)


def truncate_title(text: str, max_len: int = 20) -> str:
    """将文本压平空白并截断为不超过 max_len 字符的标题；空输入返回 ''"""
    if not text:
        return ""
    flat = " ".join(text.split())
    if not flat:
        return ""
    return flat[:max_len]


def _format_timestamp(ts: float) -> str:
    """将 Unix 时间戳格式化为可读字符串"""
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _format_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
