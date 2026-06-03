"""用户画像服务 - 从对话中提取用户偏好并持久化到本地md文件"""

from pathlib import Path
from ..services.llm_service import get_llm

# 用户画像存储目录
PROFILES_DIR = Path(__file__).parent.parent.parent / "user_profiles"

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


def load_profile_text(user_id: int) -> str:
    """
    加载用户画像文本

    Returns:
        用户画像文本（仅保留有效条目行），如果不存在则返回空字符串
    """
    path = _profile_path(user_id)
    if path.exists():
        content = path.read_text(encoding="utf-8").strip()
        # 跳过 YAML frontmatter（如果有）
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        # 只保留以 "- " 开头的行（有效条目）
        lines = []
        for line in content.split("\n"):
            line_stripped = line.strip()
            if line_stripped.startswith("- "):
                lines.append(line_stripped)
        return "\n".join(lines)
    return ""


def save_profile(user_id: int, profile_text: str):
    """
    保存用户画像到md文件

    格式：
    # 用户画像
    - 条目1
    - 条目2
    """
    _ensure_profiles_dir()
    content = f"# 用户旅行画像\n\n{profile_text}\n"
    path = _profile_path(user_id)
    path.write_text(content, encoding="utf-8")


def extract_and_update_profile(user_id: int, user_message: str, history: list = None):
    """
    从用户消息中提取偏好，与现有画像对比合并（冲突时以最新为准），然后更新保存

    Args:
        user_id: 用户ID
        user_message: 用户发送的消息
        history: 完整对话历史消息列表，用于提供上下文理解模糊消息
    """
    user_msg = user_message.strip()
    # 太短或纯语气词，跳过
    if len(user_msg) < 3:
        return

    # 加载现有画像
    existing = load_profile_text(user_id)

    # 构建对话上下文（取用户消息之前的最近几轮）
    context_lines = []
    if history:
        # 取最近3轮对话（最多6条消息）作为上下文
        recent = history[-6:]
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                context_lines.append(f"用户：{content[:150]}")
            elif role == "assistant":
                context_lines.append(f"助手：{content[:150]}")

    conversation_context = "\n".join(context_lines) if context_lines else "（无）"

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


def get_profile_context(user_id: int) -> str:
    """
    获取用户画像上下文文本（用于注入到系统提示词）

    Returns:
        格式化的画像上下文，如果不存在则返回空字符串
    """
    profile = load_profile_text(user_id)
    if profile:
        return (
            f"\n## 关于用户\n"
            f"根据过往对话，我了解到该用户的一些偏好：\n{profile}\n"
            f"**注意：用户当前的问题/要求始终优先于历史偏好。"
            f"如果用户现在的说法与历史偏好矛盾，以用户现在说的为准。**\n"
        )
    return ""
