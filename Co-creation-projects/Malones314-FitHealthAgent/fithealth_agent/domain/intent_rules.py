"""本地意图识别与安全绕过规则（main.py 拆分：阶段 3b）。"""

from __future__ import annotations

import re

from fithealth_agent.health_safety import clause_bounds


def is_training_related(text: str) -> bool:
    keywords = (
        "训练", "锻炼", "健身", "动作", "组", "次数", "重量", "rpe",
        "跑步", "跳绳", "有氧", "力量", "热身", "拉伸", "卧推", "深蹲",
        "硬拉", "划船", "视频", "youtube",
    )
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def is_training_record_query(text: str) -> bool:
    """Recognize local training-record requests before invoking the agent."""
    normalized = re.sub(r"\s+", "", text)
    return bool(
        # 中间留 16 个字符：「查询 2026-08-18 的训练记录」去空格后光日期就占 11 个，
        # 原先的 .{0,8} 会漏掉所有带日期的问法，而带日期恰恰是离线查记录的主要场景。
        re.search(r"(?:查看|查询|看|回顾).{0,16}(?:训练记录|锻炼记录|运动记录)", normalized)
        or "我的训练记录" in normalized
    )


def is_profile_query(text: str) -> bool:
    """识别"查看个人信息/档案"这类纯本地读请求（BUG-02 的离线兜底）。

    刻意写得比较窄：只认明确的"查看/查询"动词加上档案类名词，避免把
    "我的器械有哪些，顺便安排今天的训练"这种复合请求也短路掉。
    """
    normalized = re.sub(r"\s+", "", text)
    return bool(
        re.search(r"(?:查看|查询|看看?|回顾).{0,6}(?:个人信息|个人档案|我的档案|我的信息|用户档案|基础资料)", normalized)
        or re.fullmatch(r"(?:我的)?(?:个人信息|个人档案|档案|基础资料)[?？。！]?", normalized)
    )


def navigation_only_message(text: str) -> bool:
    """Return whether a local view request has no second user request.

    Unknown wording deliberately returns ``False``. Calling the agent once is
    cheaper than silently dropping a request that happened to share a message
    with a local navigation command.
    """
    normalized = re.sub(r"\s+", "", str(text or "")).strip()
    date_token = r"(?:今天|昨日|昨天|前天|本周|这周|\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)?"
    polite = r"(?:(?:请|麻烦|帮我|给我|我想|能否|可以))*"
    action = r"(?:打开|查看|查询|查一下|看一下|看看|看|回顾一下|回顾)"
    target = r"(?:我的)?(?:训练记录|锻炼记录|运动记录|运动数据|营养记录|饮食记录|营养数据|饮食数据|摄入数据|个人信息|个人档案|档案|基础资料)"
    return bool(re.fullmatch(
        rf"{polite}{action}?{date_token}(?:的)?{target}(?:吗|呢)?[?？。！]?",
        normalized,
    ))


def current_instruction_override(message: str) -> bool:
    normalized = re.sub(r"\s+", "", message)
    return bool(
        re.search(
            r"(?:今天|今日|这次|本次).{0,8}(?:"
            r"不想练|不练|别练|不要练|改练|换成|改为|休息|跳过|"
            r"(?:想|要|准备|打算)?(?:练|做)(?!什么|啥|哪)|"
            r"(?:想|要|准备|打算)?(?:有氧|跑步|跳绳|瑜伽|普拉提)"
            r")",
            normalized,
        )
    )


_SAFETY_BYPASS_PATTERN = re.compile(
    # 「忽略我的腰伤」「不用管肩膀的限制」——限定词与"伤/限制"之间常常夹着
    # 部位名，所以这里留一个**长度受限**的中文缺口（最多 3 字），既能覆盖
    # 常见写法，又不至于把"忽略顺序问题"这类无关句子吞进来。
    r"(?:忽略|无视|不用管|别管|不考虑)(?:我的|这些|那些|上面的)?[一-龥]{0,3}?(?:伤病|伤痛|受伤|伤|限制|约束|禁忌|医嘱)"
    r"|跳过(?:安全|健康)?限制"
    r"|照常(?:训练|练|上强度)"
    r"|(?:伤|伤病|限制).{0,6}(?:没关系|不要紧|无所谓|不用管|别管)"
    r"|硬(?:练|上)"
)


_SAFETY_BYPASS_VETO_BEFORE = re.compile(
    r"不想|不要|不能|不该|不应|不建议|为什么|为何|能不能|可不可以|算不算"
)


def _is_safety_bypass_request(message: str) -> bool:
    """Return True only for an affirmative request to bypass a safety rule."""
    normalized = re.sub(r"\s+", "", str(message or ""))
    for match in _SAFETY_BYPASS_PATTERN.finditer(normalized):
        clause_start, clause_end = clause_bounds(
            normalized, match.start(), match.end()
        )
        before = normalized[max(clause_start, match.start() - 8):match.start()]
        after = normalized[match.end():clause_end]
        separator = normalized[clause_end:clause_end + 1]
        is_question = after.endswith(("吗", "么")) or separator in {"？", "?"}
        if not is_question and not _SAFETY_BYPASS_VETO_BEFORE.search(before):
            return True
    return False
