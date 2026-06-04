"""用户画像服务 - 从对话中提取用户偏好并持久化到本地md文件

内存缓存策略（参考 Claude Code 记忆模式）：
- 首次读取后缓存到 _profile_cache，避免重复磁盘 I/O
- 通过文件 mtime 检测外部修改，自动刷新缓存
- 写入时同时更新缓存和文件，保证读写一致性
- 每条用户画像使用 frontmatter 记录元数据（更新时间、来源会话）
"""

import time
from pathlib import Path
from typing import Optional
from ..services.llm_service import get_llm
from ..database import get_db

# 用户画像存储目录
PROFILES_DIR = Path(__file__).parent.parent.parent / "user_profiles"

# 内存缓存：user_id -> (profile_text, mtime, cached_at)
# mtime：文件最后修改时间（用于检测外部修改）
# cached_at：缓存写入时间（用于 TTL 过期）
_profile_cache: dict[int, tuple[str, float, float]] = {}

# 会话级快照缓存：session_id -> context_text
# 同一场对话内首条消息固话，后续消息复用，保证 LLM prompt cache 命中
_session_snapshot_cache: dict[int, str] = {}

# 缓存 TTL：300 秒（5 分钟内认为缓存新鲜，无需 stat 文件）
_CACHE_TTL = 300

# 提取画像的 LLM 提示词
EXTRACT_PROFILE_PROMPT = """你是一个用户偏好分析专家。请根据用户的对话消息，提取该用户的旅行偏好。

## 核心规则
1. 只从「用户消息」中提取用户**自己表达**的偏好，不要提取AI助手的建议或推荐
2. 如果用户消息需要结合对话历史才能理解（如"好的"、"这个不错"、"是的"），参考上下文来推断用户偏好
3. 不要提取一次性信息（如"明天去故宫"），只提取稳定的偏好特征（如"喜欢历史文化景点"）
4. 每条控制在20字以内，总条目不超过8条
5. 宁缺毋滥，只输出有明显依据的偏好

## 冲突处理（重要）
将新提取的偏好与「已有画像」逐条对比：
- **冲突**：如果新消息表达的偏好与某条旧画像矛盾（如"喜欢安静" vs "喜欢热闹"），删除旧条目，用新条目替代
- **一致**：如果新消息与旧画像一致，保留旧画像条目（不重复添加）
- **新增**：如果新消息表达了旧画像中没有的偏好，作为新条目添加
- **无关**：如果用户消息不包含偏好信息，跳过本轮提取

## 输出格式
只输出更新后的完整画像，每行一条，以"- "开头，不要输出任何其他内容：

- 偏好1
- 偏好2

---

已有画像：
{existing_profile}

对话历史（用于理解上下文）：
{conversation_context}

最新用户消息：{user_message}

请输出更新后的完整画像：
"""


def _ensure_profiles_dir():
    """确保画像目录存在"""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _profile_path(user_id: int) -> Path:
    """获取用户画像文件路径"""
    return PROFILES_DIR / f"user_{user_id}.md"


def _read_file_with_frontmatter(path: Path) -> tuple[str, str]:
    """
    读取 md 文件，分离 frontmatter 和正文
    返回: (frontmatter_yaml, body)
    无 frontmatter 时 frontmatter 返回空字符串
    """
    if not path.exists():
        return "", ""

    content = path.read_text(encoding="utf-8").strip()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()
            return frontmatter, body

    return "", content


def _build_frontmatter(user_id: int) -> str:
    """构建 YAML frontmatter"""
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    return (
        f"---\n"
        f"user_id: {user_id}\n"
        f"updated_at: '{now}'\n"
        f"---"
    )


def _invalidate_cache(user_id: int):
    """清除指定用户的缓存"""
    _profile_cache.pop(user_id, None)


def _refresh_from_disk(user_id: int) -> str:
    """从磁盘加载用户画像正文（跳过 frontmatter），更新缓存"""
    path = _profile_path(user_id)
    if not path.exists():
        _profile_cache[user_id] = ("", 0.0, time.time())
        return ""

    mtime = path.stat().st_mtime
    _, body = _read_file_with_frontmatter(path)
    _profile_cache[user_id] = (body, mtime, time.time())
    return body


def load_profile_text(user_id: int) -> str:
    """
    加载用户画像文本（带内存缓存）

    缓存策略：
    1. 缓存命中且未超过 TTL → 直接返回
    2. 缓存命中但超过 TTL → stat 检查文件 mtime，未变则续期缓存
    3. 缓存未命中或文件已变 → 重新从磁盘读取

    Returns:
        用户画像正文（仅 "- " 开头的条目行），不存在则返回空字符串
    """
    path = _profile_path(user_id)
    cached = _profile_cache.get(user_id)
    now = time.time()

    if cached is not None:
        body, mtime, cached_at = cached

        # TTL 内：直接返回缓存
        if now - cached_at < _CACHE_TTL:
            return body

        # TTL 已过：检查文件 mtime
        if path.exists():
            current_mtime = path.stat().st_mtime
            if current_mtime == mtime:
                # 文件未变，续期缓存
                _profile_cache[user_id] = (body, mtime, now)
                return body

    # 缓存失效或文件变更，从磁盘重新加载
    return _refresh_from_disk(user_id)


def save_profile(user_id: int, profile_text: str):
    """
    保存用户画像到 md 文件（frontmatter + 正文）

    格式：
    ---
    user_id: 1
    updated_at: '2026-06-04 12:00:00'
    ---
    # 用户旅行画像
    - 条目1
    - 条目2
    """
    _ensure_profiles_dir()
    frontmatter = _build_frontmatter(user_id)
    content = f"{frontmatter}\n\n# 用户旅行画像\n\n{profile_text}\n"
    path = _profile_path(user_id)

    # 先写磁盘，再更新缓存（保证缓存与磁盘一致）
    path.write_text(content, encoding="utf-8")
    mtime = path.stat().st_mtime

    # 只缓存有效条目行作为正文
    lines = [l for l in profile_text.split("\n") if l.strip().startswith("- ")]
    body = "\n".join(lines)
    _profile_cache[user_id] = (body, mtime, time.time())


def extract_and_update_profile(
    user_id: int,
    user_message: str,
    history: Optional[list] = None,
    cross_session_context: str = "",
):
    """
    从用户消息中提取偏好，与现有画像对比合并（冲突时以最新为准），然后更新保存

    与旧版的关键区别：
    1. 支持传入跨会话上下文（cross_session_context），让 LLM 能理解
       用户在其他会话中表达过的偏好，避免将长期偏好误判为一次性信息
    2. 内存缓存：每次提取后自动更新缓存，后续 load 直接命中

    Args:
        user_id: 用户ID
        user_message: 用户发送的消息
        history: 当前会话的最近消息列表（用于理解上下文）
        cross_session_context: 跨会话上下文文本（来自其他会话的消息摘要）
    """
    user_msg = user_message.strip()
    # 太短或纯语气词，跳过
    if len(user_msg) < 3:
        return

    # 加载现有画像（走缓存）
    existing = load_profile_text(user_id)

    # 构建对话上下文
    context_parts = []

    # 优先注入跨会话上下文
    if cross_session_context:
        context_parts.append("=== 历史会话摘要 ===\n" + cross_session_context)

    # 当前会话的最近消息作为细粒度上下文
    if history:
        recent = history[-6:]  # 最近 3 轮对话（最多 6 条）
        context_parts.append("=== 当前会话 ===")
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                context_parts.append(f"用户：{content[:150]}")
            elif role == "assistant":
                context_parts.append(f"助手：{content[:150]}")

    conversation_context = "\n".join(context_parts) if context_parts else "（无）"

    # 构建提取提示
    prompt = EXTRACT_PROFILE_PROMPT.format(
        existing_profile=existing or "（无）",
        conversation_context=conversation_context,
        user_message=user_msg[:300],
    )

    try:
        llm = get_llm()
        response = llm.invoke(messages=[{"role": "user", "content": prompt}])
        new_profile = response.content if hasattr(response, 'content') else str(response)

        # 清理输出
        new_profile = new_profile.strip()
        if not new_profile:
            return

        # 解析有效条目
        lines = []
        for line in new_profile.split("\n"):
            line = line.strip()
            if line.startswith("- ") and len(line) > 3:
                lines.append(line)

        if lines:
            save_profile(user_id, "\n".join(lines))
            print(f"  ✅ 用户 {user_id} 画像更新成功 ({len(lines)} 条)")
    except Exception as e:
        print(f"  ⚠️ 用户画像提取失败: {e}")


def get_profile_context(user_id: int, session_id: int = None) -> str:
    """
    获取用户画像上下文文本（用于注入到系统提示词）

    支持会话级快照：传入 session_id 后，同一场对话内首条消息固话画像字符串，
    后续消息无论画像如何更新都复用该字符串，保证 LLM prompt cache 不变。

    缓存层级（从快到慢）：
    session snapshot → memory cache → disk

    Args:
        user_id: 用户ID
        session_id: 可选，会话ID。传入后启用会话级快照。

    Returns:
        格式化的画像上下文，如果不存在则返回空字符串
    """
    # 1. 会话级快照命中 → 直接返回（零开销）
    if session_id is not None and session_id in _session_snapshot_cache:
        return _session_snapshot_cache[session_id]

    # 2. 加载画像（走内存缓存 → disk）
    profile = load_profile_text(user_id)
    if not profile:
        return ""

    context = (
        f"\n## 关于用户\n"
        f"根据过往对话，我了解到该用户的一些偏好：\n{profile}\n"
        f"**注意：用户当前的问题/要求始终优先于历史偏好。"
        f"如果用户现在的说法与历史偏好矛盾，以用户现在说的为准。**\n"
    )

    # 3. 固话到会话级快照（后续同一 session 不再变动）
    if session_id is not None:
        _session_snapshot_cache[session_id] = context

    return context


def get_cross_session_context(user_id: int, max_sessions: int = 5, max_messages: int = 6) -> str:
    """
    获取用户跨会话的近期消息摘要（用于提取画像时的跨会话上下文）

    查询该用户最近 N 个会话的前几条消息，拼接为纯文本返回。
    这些文本不用于注入系统提示词，仅作为提取画像时的参考上下文。

    Args:
        user_id: 用户ID
        max_sessions: 最多取多少个会话
        max_messages: 每个会话最多取多少条消息

    Returns:
        格式化的跨会话上下文文本
    """
    conn = get_db()
    try:
        # 获取用户最近的会话
        sessions = conn.execute(
            """SELECT id, title, created_at FROM chat_sessions
               WHERE user_id = ?
               ORDER BY updated_at DESC LIMIT ?""",
            (user_id, max_sessions)
        ).fetchall()

        if not sessions:
            return ""

        parts = []
        for sess in sessions:
            sess_id = sess["id"]
            # 每个会话取前几条消息
            messages = conn.execute(
                """SELECT role, content FROM chat_messages
                   WHERE session_id = ?
                   ORDER BY id ASC LIMIT ?""",
                (sess_id, max_messages)
            ).fetchall()

            if messages:
                msg_text = []
                for msg in messages:
                    role_label = "用户" if msg["role"] == "user" else "助手"
                    content = msg["content"][:100]
                    msg_text.append(f"  {role_label}：{content}")
                parts.append(
                    f"【会话 {sess_id}】\n" + "\n".join(msg_text)
                )

        return "\n\n".join(parts) if parts else ""

    finally:
        conn.close()
