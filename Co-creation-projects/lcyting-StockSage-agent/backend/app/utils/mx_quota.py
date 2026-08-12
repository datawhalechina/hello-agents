"""妙想 API 额度类错误识别与前端提示文案"""


MX_QUOTA_HINT = (
    "今日妙想 Skills 调用额度已用尽，以下为缓存数据（若有）；"
    "升级或次日重置额度后可获取最新数据。"
)


def quota_exhausted_no_cache_message(upstream_error: str | None) -> str:
    """额度用尽且无进程内缓存时的提示（附上游原文，便于核对 Key 是否生效、是否真为 113 等）"""
    base = MX_QUOTA_HINT + "（暂无可用缓存）"
    u = (upstream_error or "").strip()
    if not u:
        return base
    return f"{base} 上游提示：{u}"


def is_mx_quota_exhausted(error_text: str | None) -> bool:
    """判断是否命中免费版日限额（状态码 113 等）"""
    if not error_text:
        return False
    s = str(error_text)
    if "状态码 113" in s:
        return True
    if "调用次数已达到上限" in s:
        return True
    if "今日调用次数已达到上限" in s:
        return True
    # 避免宽泛匹配：仅当同时涉及「免费版 + 上限」且明显与调用次数相关时才视为额度类
    if "免费版" in s and "上限" in s:
        if any(k in s for k in ("调用", "次数", "配额", "限额", "Skills")):
            return True
    return False
