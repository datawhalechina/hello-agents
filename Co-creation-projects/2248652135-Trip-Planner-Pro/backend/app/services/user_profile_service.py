"""用户画像服务 - 从对话中提取用户偏好并持久化到本地md文件"""

import os
import re
from pathlib import Path
from ..services.llm_service import get_llm

# 用户画像存储目录
PROFILES_DIR = Path(__file__).parent.parent.parent / "user_profiles"

# 提取画像的 LLM 提示词
EXTRACT_PROFILE_PROMPT = """你是一个用户偏好分析专家。请根据以下用户和AI助手的对话，提取该用户的旅行偏好画像。

要求：
1. 只提取与旅行相关的明确偏好或信息
2. 保持简洁，每条不超过20字
3. 最多输出5条，宁缺毋滥
4. 只输出有明显依据的信息，不要猜测
5. 输出格式：每条一行，以"- "开头

示例输出：
- 喜欢历史文化景点
- 偏好经济型住宿
- 倾向自由行

现有画像：
{existing_profile}

最新对话：
用户：{user_message}
助手：{ai_reply}

请只输出更新后的完整画像（包含现有和新提取的信息），不要输出其他内容：
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


def extract_and_update_profile(user_id: int, user_message: str, ai_reply: str):
    """
    从对话中提取用户偏好并更新画像

    Args:
        user_id: 用户ID
        user_message: 用户发送的消息
        ai_reply: AI的回复
    """
    # 加载现有画像
    existing = load_profile_text(user_id)

    # 如果用户消息太短或明显不是偏好相关的，跳过
    if len(user_message.strip()) < 4:
        return

    # 构建提取提示
    prompt = EXTRACT_PROFILE_PROMPT.format(
        existing_profile=existing or "暂无",
        user_message=user_message[:500],  # 截断避免过长
        ai_reply=ai_reply[:800],
    )

    try:
        llm = get_llm()
        response = llm.invoke(messages=[{"role": "user", "content": prompt}])
        new_profile = response.content if hasattr(response, 'content') else str(response)

        # 清理和验证输出
        new_profile = new_profile.strip()
        if not new_profile:
            return

        # 确保每行以 "- " 开头
        lines = []
        for line in new_profile.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                if not line.startswith("- "):
                    line = "- " + line
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
        return f"\n## 关于用户\n根据过往对话，我了解到该用户的一些偏好：\n{profile}\n"
    return ""
