"""服务端的训练计划草稿缓存（对应需求清单 BUG-05）。

**要解决的问题**

"保存刚才的训练计划"以前是从聊天历史里把计划正文捞回来的
（`most_recent_complete_training_plan(history)`）。但那份 history 已经被
`context_budget._normalize_history` 做过两级截断：

* 单条上限 `HISTORY_ITEM_MAX_CHARS = 4000`，超出会追加 `[历史消息已截断]`；
* 总量上限 `HISTORY_TOTAL_MAX_CHARS = 12000`，超出会追加 `[历史上下文预算已用尽]`。

一份正常的训练计划轻松超过 4000 字符，而完整性判断只要求 ≥300 字符，
于是**被截断的残缺计划照样通过检查并原样落盘**；`plan_store` 又按
content_hash 去重，用户重存一次也修不回来。

同一条路径上还有两个副作用：
* `HISTORY_CONTEXT_MAX_ITEMS = 8`，生成计划后再聊 8 轮，它就彻底不在
  history 里了；
* 前端的 `sessionConversationHistory` 是内存变量，刷新页面或新开标签页
  即归零，"保存刚才的计划"直接 400。

**做法**

生成计划时就把**完整正文**在服务端存一份，保存时按 id 取原文，不再回捞
聊天历史。history 只作为进程重启后的兜底。

这是一个进程内的短期缓存，不做持久化：它服务的是"刚生成完、马上保存"
这个窗口，重启后回退到原有行为即可。单用户本地应用，因此不区分会话。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4


DEFAULT_MAX_ITEMS = 20
DEFAULT_TTL_SECONDS = 6 * 60 * 60


@dataclass(frozen=True)
class PlanDraft:
    id: str
    content: str
    subject: str
    title: str
    suggested_date: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PlanDraftCache:
    """进程内、有上限、带 TTL 的计划草稿缓存。"""

    def __init__(
        self,
        *,
        max_items: int = DEFAULT_MAX_ITEMS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._max_items = max_items
        self._ttl = timedelta(seconds=ttl_seconds)
        self._drafts: list[PlanDraft] = []
        self._lock = threading.Lock()

    # ── 内部 ──────────────────────────────────────────────────────────
    def _prune(self, now: datetime) -> None:
        cutoff = now - self._ttl
        self._drafts = [draft for draft in self._drafts if draft.created_at > cutoff]
        if len(self._drafts) > self._max_items:
            self._drafts = self._drafts[-self._max_items:]

    # ── 对外 ──────────────────────────────────────────────────────────
    def remember(
        self,
        *,
        content: str,
        subject: str = "",
        title: str = "",
        suggested_date: str = "",
        now: datetime | None = None,
    ) -> PlanDraft:
        """记住一份刚生成的完整计划，返回带 id 的草稿。"""
        now = now or datetime.now(timezone.utc)
        draft = PlanDraft(
            id=uuid4().hex,
            content=content,
            subject=subject,
            title=title,
            suggested_date=suggested_date,
            created_at=now,
        )
        with self._lock:
            self._drafts.append(draft)
            self._prune(now)
        return draft

    def get(self, draft_id: str | None, *, now: datetime | None = None) -> PlanDraft | None:
        if not draft_id:
            return None
        now = now or datetime.now(timezone.utc)
        with self._lock:
            self._prune(now)
            for draft in reversed(self._drafts):
                if draft.id == draft_id:
                    return draft
        return None

    def latest(self, *, now: datetime | None = None) -> PlanDraft | None:
        """最近一次生成且未过期的计划。"""
        now = now or datetime.now(timezone.utc)
        with self._lock:
            self._prune(now)
            return self._drafts[-1] if self._drafts else None

    def find(
        self,
        *,
        subject: str = "",
        suggested_date: str = "",
        now: datetime | None = None,
    ) -> PlanDraft | None:
        """按科目/日期挑一份草稿，取不到再回落到最近一份。

        一个会话里可能生成过多份计划（先练背、又改练腿），无条件用
        `latest()` 会在用户说"保存那份腿的计划"时静默存错。这里按线索
        从新到旧找：科目+日期都对上最优先，其次任一对上，最后才是最近一份。
        """
        now = now or datetime.now(timezone.utc)
        wanted_subject = (subject or "").strip()
        wanted_date = (suggested_date or "").strip()
        with self._lock:
            self._prune(now)
            candidates = list(reversed(self._drafts))
        if not candidates:
            return None
        if wanted_subject and wanted_date:
            for draft in candidates:
                if draft.subject == wanted_subject and draft.suggested_date == wanted_date:
                    return draft
        if wanted_subject:
            for draft in candidates:
                if draft.subject == wanted_subject:
                    return draft
        if wanted_date:
            for draft in candidates:
                if draft.suggested_date == wanted_date:
                    return draft
        return candidates[0]

    def clear(self) -> None:
        with self._lock:
            self._drafts.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._drafts)


TRUNCATED_CONTENT_ERROR = (
    "这份计划正文是被上下文长度限制截断过的残缺内容，已拒绝保存。"
    "请让 Agent 重新生成完整计划后再保存。"
)


def resolve_plan_save_content(
    payload: dict,
    cache: PlanDraftCache,
    *,
    is_truncated: Callable[[str], bool],
) -> tuple[str, str | None]:
    """决定保存计划时用哪份正文，返回 `(content, error)`。

    抽成纯函数是为了让这段判断能被真正调用着测——原先它内联在 `/plans`
    路由里，测试只能对 main.py 做字符串断言，改个变量名测试就绿着失效。
    截断判断由调用方注入（而不是在这里 import context_budget），这样按文件
    路径单独加载本模块时也不需要包上下文（对照 ARCH-02）。

    顺序很关键（BUG-05）：**先取服务端草稿**。draft_id 的设计目的就是绕过
    任何中途加工，若先校验前端 content，一个带合法 draft_id 的请求会因为
    前端那份恰好带了截断标记而先被拒，服务端的完整原文根本没机会生效。
    只有回落到前端正文时才需要截断拦截——`plan_store` 按 content_hash 去重，
    残缺版本一旦落盘，用户重存一次也覆盖不掉。
    """
    draft = cache.get(str(payload.get("draft_id") or ""))
    if draft is not None and draft.content:
        return draft.content, None
    content = str(payload.get("content") or "")
    if is_truncated(content):
        return "", TRUNCATED_CONTENT_ERROR
    return content, None
