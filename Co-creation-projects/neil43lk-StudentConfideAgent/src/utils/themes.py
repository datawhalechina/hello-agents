"""从倾诉文本里抽取主题标签，供专属记忆使用。"""

from __future__ import annotations

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "考试压力": ("考试", "高考", "期中", "期末", "成绩", "排名", "考砸"),
    "作业负担": ("作业", "ddl", "截止", "论文", "复习", "课业"),
    "亲子沟通": ("爸妈", "父母", "妈妈", "爸爸", "家长", "家里"),
    "同伴关系": ("同学", "朋友", "室友", "孤立", "霸凌", "小组"),
    "睡眠与疲惫": ("睡不着", "失眠", "好累", "疲惫", "熬夜"),
    "自我怀疑": ("没用", "挫败", "自卑", "比不上", "焦虑", "失望"),
}


def extract_themes(text: str) -> list[str]:
    """返回命中的主题，顺序稳定。"""
    if not text:
        return []
    lowered = text.lower()
    found = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            found.append(theme)
    return found
