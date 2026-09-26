
from __future__ import annotations

import os
import time
import threading
from typing import Any

from ..llm.agent_runtime import run_json_task, _run_with_optional_timeout
from ..llm.context_budget import clip_utf8, MODEL_ITEM_BYTES
from ..llm.llm_service import coerce_hello_agents_llm_output_to_str
from .sqlite_document_store_compat import SQLiteDocumentStore

_EXTRACT_PROMPT_MAX_CHARS = 3600
_COMPRESSION_LOCKS = [threading.Lock() for _ in range(32)]


def _stateless_llm_chat(llm: Any, user_prompt: str, **invoke_kwargs: Any) -> str:
    """Keep optional memory LLM calls independent of previous agent turns."""
    output = _run_with_optional_timeout(
        lambda: llm.invoke([{"role": "user", "content": clip_utf8(user_prompt)}], **invoke_kwargs), 12.0,
    )
    return coerce_hello_agents_llm_output_to_str(output)


class MemoryStoreConfig:

    working_ttl_minutes: int = 60
    working_capacity: int = 80
    short_capacity: int = 200
    min_importance_for_context: float = 0.35
    max_context_items: int = 10

class MemoryStore:

    def __init__(self, db_path: str, config: MemoryStoreConfig | None = None) -> None:
        # Reader memory uses synthetic papergraph:* identities and therefore must
        # not share the application memories table, whose user_id references
        # authenticated users. Keep one sidecar DB beside the application DB.
        root = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(root, exist_ok=True)
        self.db_path = os.path.join(root, "reader_memory.db")
        self.config = config or MemoryStoreConfig()
        self.store = SQLiteDocumentStore(db_path=self.db_path)

    @staticmethod
    def _user_id_for(scope: str, paper_id: int | None) -> str:
        if scope == "global":
            return "papergraph:global"
        return f"papergraph:paper:{paper_id or 0}"

    @staticmethod
    def _properties(scope: str, paper_id: int | None, kind: str, meta: dict[str, Any | None]) -> dict[str, Any]:
        p: dict[str, Any] = {}
        p["scope"] = scope
        p["paper_id"] = int(paper_id) if paper_id is not None else None
        p["kind"] = kind
        if meta:
            p.update(meta)
        return p

    @staticmethod
    def _content_of(doc: dict) -> str:
        return str(doc.get("content") or "").strip()

    @staticmethod
    def _memory_id_of(doc: dict) -> str:
        return str(doc.get("memory_id") or "").strip()

    @staticmethod
    def _ts_of(doc: dict) -> int:
        return int(doc.get("timestamp") or 0)

    @staticmethod
    def _imp_of(doc: dict, default: float = 0.0) -> float:
        try:
            return float(doc.get("importance") or default)
        except Exception:
            return default

    @staticmethod
    def _type_of(doc: dict) -> str:
        return str(doc.get("memory_type") or "").strip() or "unknown"

    @staticmethod
    def _parse_scope_and_paper(kwargs: dict) -> tuple[str, int | None]:
        scope = str(kwargs.get("scope") or "paper")
        paper_id = kwargs.get("paper_id")
        return scope, int(paper_id) if paper_id is not None else None

    def _delete_docs(self, docs: list[dict]) -> int:
        deleted = 0
        for d in docs:
            mid = self._memory_id_of(d)
            if not mid:
                continue
            try:
                if self.store.delete_memory(mid):
                    deleted += 1
            except Exception:
                continue
        return deleted

    @staticmethod
    def _word_overlap(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / max(len(words_a), len(words_b))

    def _llm_is_duplicate(self, a: str, b: str) -> bool:
        try:
            from ..llm.llm_service import get_llm
            import json as _json
            llm = get_llm()
            prompt = f"Are these two research notes semantically the same topic? Answer JSON only: {{\"duplicate\":true/false}}\n1: {a[:200]}\n2: {b[:200]}"
            txt = _stateless_llm_chat(llm, prompt, temperature=0.0, max_tokens=30).strip()
            d = _json.loads(txt) if txt.startswith("{") else {}
            return bool(d.get("duplicate", False))
        except Exception:
            return False

    @staticmethod
    def _score_memory(doc: dict, query_tokens: set | None = None) -> float:
        content = str(doc.get("content") or "")
        imp = float(doc.get("importance") or 0.5)
        ts = int(doc.get("timestamp") or 0)
        import math
        delta = max(time.time() - ts, 0)
        rec = math.exp(-delta / 3600)
        if query_tokens:
            doc_tokens = set(content.lower().split())
            rel = len(query_tokens & doc_tokens) / max(1, len(query_tokens))
        else:
            rel = 0.0
        return 0.5 * imp + 0.3 * rec + 0.2 * rel

    def add(
        self,
        *,
        scope: str,
        paper_id: int | None,
        kind: str,
        content: str,
        importance: float = 0.5,
        meta: dict[str, Any | None] = None,
    ) -> str:
        now = int(time.time())
        user_id = self._user_id_for(scope, paper_id)
        props = self._properties(scope, paper_id, kind, meta)

        existing = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=[kind], limit_per_kind=10)
        for doc in existing:
            ov = self._word_overlap(content, self._content_of(doc))
            if ov > 0.7 or (ov > 0.35 and self._llm_is_duplicate(content, self._content_of(doc))):
                old_mid = self._memory_id_of(doc)
                new_imp = max(importance, self._imp_of(doc))
                if old_mid:
                    self.store.delete_memory(old_mid)
                return self.store.add_memory(
                    user_id=user_id,
                    content=content,
                    memory_type=kind,
                    importance=new_imp,
                    metadata=props,
                )

        result = self.store.add_memory(
            user_id=user_id,
            content=content,
            memory_type=kind,
            importance=float(importance),
            metadata=props,
        )

        if kind == "working":
            working_docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=["working"], limit_per_kind=100)
            if len(working_docs) > 50:
                working_docs.sort(key=lambda d: self._ts_of(d), reverse=True)
                to_compress = working_docs[20:]
                if to_compress:
                    self._compress_docs(to_compress, scope=scope, paper_id=paper_id)

        return result

    def execute(self, action: str, **kwargs) -> str:
        def _add():
            scope, pid = self._parse_scope_and_paper(kwargs)
            kind = str(kwargs.get("kind") or kwargs.get("memory_type") or "working")
            content = str(kwargs.get("content") or "").strip()
            importance = float(kwargs.get("importance") or 0.5)
            if not content:
                return "❌ content 不能为空"
            mid = self.add(scope=scope, paper_id=pid, kind=kind, content=content, importance=importance)
            return f"✅ 记忆已添加 (ID: {mid})"

        def _search():
            scope, pid = self._parse_scope_and_paper(kwargs)
            query = str(kwargs.get("query") or "").strip()
            kind = kwargs.get("kind") or kwargs.get("memory_type")
            limit = int(kwargs.get("limit") or 5)
            return self.search(scope=scope, paper_id=pid, query=query, kind=str(kind) if kind else None, limit=limit)

        def _summary():
            scope, pid = self._parse_scope_and_paper(kwargs)
            limit = int(kwargs.get("limit") or 8)
            return self.summary(scope=scope, paper_id=pid, limit=limit)

        def _stats():
            scope, pid = self._parse_scope_and_paper(kwargs)
            return self.stats(scope=scope, paper_id=pid)

        def _remove():
            memory_id = str(kwargs.get("memory_id") or "").strip()
            if not memory_id:
                return "❌ memory_id 不能为空"
            ok = bool(self.store.delete_memory(memory_id))
            return "✅ 已删除" if ok else "⚠️ 未找到该记忆"

        def _clear():
            scope, pid = self._parse_scope_and_paper(kwargs)
            n = self.clear_all(scope=scope, paper_id=pid)
            return f"✅ 已清空 {n} 条记忆"

        def _forget():
            scope, pid = self._parse_scope_and_paper(kwargs)
            kind = str(kwargs.get("kind") or kwargs.get("memory_type") or "working")
            threshold = float(kwargs.get("threshold") or kwargs.get("min_importance") or 0.3)
            n = self.forget_by_importance(scope=scope, paper_id=pid, kind=kind, threshold=threshold)
            return f"✅ 已遗忘 {n} 条低重要性记忆"

        def _consolidate():
            scope, pid = self._parse_scope_and_paper(kwargs)
            from_kind = str(kwargs.get("from_type") or kwargs.get("from_kind") or "working")
            to_kind = str(kwargs.get("to_type") or kwargs.get("to_kind") or "short")
            threshold = float(kwargs.get("importance_threshold") or 0.6)
            n = self.consolidate(scope=scope, paper_id=pid, from_kind=from_kind, to_kind=to_kind, threshold=threshold)
            return f"✅ 已整合 {n} 条记忆 ({from_kind} → {to_kind})"

        a = (action or "").strip().lower()
        handlers = {
            "add": _add,
            "search": _search,
            "summary": _summary,
            "stats": _stats,
            "remove": _remove,
            "delete": _remove,
            "clear_all": _clear,
            "clear": _clear,
            "forget": _forget,
            "consolidate": _consolidate,
        }
        handler = handlers.get(a)
        if handler is None:
            return "不支持的操作: " + action
        try:
            return handler()
        except Exception as e:
            return f"❌ 记忆操作失败: {e}"

    def upsert_single(
        self,
        *,
        scope: str,
        paper_id: int | None,
        kind: str,
        content: str,
        importance: float = 0.6,
        meta: dict[str, Any | None] = None,
    ) -> None:
        now = int(time.time())
        user_id = self._user_id_for(scope, paper_id)
        props = self._properties(scope, paper_id, kind, meta)
        memory_id = f"{user_id}:{kind}:singleton"
        self.store.add_memory(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            memory_type=kind,
            timestamp=now,
            importance=float(importance),
            properties=props,
        )

    def _list_recent_docs(
        self,
        *,
        scope: str,
        paper_id: int | None,
        kinds: list[str],
        limit_per_kind: int = 40,
    ) -> list[dict[str, Any]]:
        user_id = self._user_id_for(scope, paper_id)
        docs: list[dict[str, Any]] = []
        for k in [x for x in kinds if x.strip()]:
            try:
                items = self.store.search_memories(user_id=user_id, memory_type=k, limit=limit_per_kind)
            except Exception:
                items = []
            for d in items or []:
                if isinstance(d, dict):
                    docs.append(d)
        return docs

    def search(self, *, scope: str, paper_id: int | None, query: str, kind: str | None = None, limit: int = 5) -> str:
        q = (query or "").strip().lower()
        kinds = [kind] if kind else ["working", "short", "long", "paper_summary", "preference"]
        docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=kinds, limit_per_kind=max(40, limit * 10))
        scored: list[tuple[int, dict[str, Any]]] = []
        for d in docs:
            c = self._content_of(d)
            if not c:
                continue
            hay = c.lower()
            if q and q not in hay:
                continue
            ts = self._ts_of(d)
            scored.append((ts, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        lines: list[str] = []
        for i, (_ts, d) in enumerate(scored[: max(1, limit)], start=1):
            mt = self._type_of(d)
            imp = self._imp_of(d)
            c = self._content_of(d)
            lines.append(f"{i}. [{mt}] {c[:220]} (重要性: {imp:.2f})")
        if not lines:
            return "🔍 未找到相关记忆"
        return "🔍 找到 {} 条相关记忆:\n{}".format(len(lines), "\n".join(lines))

    def stats(self, *, scope: str, paper_id: int | None) -> str:
        kinds = ["working", "short", "long", "paper_summary", "preference"]
        docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=kinds, limit_per_kind=200)
        by_kind: dict[str, int] = {}
        for d in docs:
            k = self._type_of(d)
            by_kind[k] = by_kind.get(k, 0) + 1
        total = sum(by_kind.values())
        parts = [f"{k}:{by_kind[k]}" for k in sorted(by_kind.keys())]
        who = "global" if scope == "global" else f"paper:{paper_id or 0}"
        return "📈 记忆系统统计\n对象: {}\n总记忆数(近似): {}\n分布: {}".format(who, total, ", ".join(parts) if parts else "—")

    def summary(self, *, scope: str, paper_id: int | None, limit: int = 8) -> str:
        kinds = ["preference", "paper_summary", "long", "short", "working"]
        docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=kinds, limit_per_kind=120)
        items: list[tuple[int, str, float]] = []
        for d in docs:
            c = self._content_of(d)
            if not c:
                continue
            ts = self._ts_of(d)
            mt = self._type_of(d)
            imp = self._imp_of(d)
            items.append((ts, mt, imp))
        items.sort(key=lambda x: x[0], reverse=True)
        lines: list[str] = []
        for ts, mt, imp in items[: max(1, limit)]:
            lines.append(f"- [{mt}] (重要性:{imp:.2f}, ts:{ts})")
        if not lines:
            return "📋 记忆摘要：暂无"
        return "📋 记忆摘要:\n" + "\n".join(lines)

    def forget_by_importance(self, *, scope: str, paper_id: int | None, kind: str, threshold: float = 0.3) -> int:
        docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=[kind], limit_per_kind=500)
        to_delete = [d for d in docs if self._imp_of(d) < float(threshold)]
        return self._delete_docs(to_delete)

    def _summarize_via_llm(self, docs: list[dict]) -> str:
        contents = [self._content_of(d) for d in docs if self._content_of(d)]
        if not contents:
            return ""
        prompt = (
            "你是一个学术文献阅读助手的记忆管理模块。请将以下用户阅读过程中的关注点和问答摘要"
            "综合为一段不超过 300 字的紧凑摘要，保留关键术语、用户兴趣方向和研究问题。"
            "只输出摘要文本，不要加前缀或解释。\n\n"
            + "\n".join(f"- {c}" for c in contents)
        )
        if len(prompt.encode("utf-8")) > MODEL_ITEM_BYTES:
            return ""
        try:
            from ..llm.llm_service import get_llm
            llm = get_llm()
            summary = _stateless_llm_chat(llm, prompt, temperature=0.3, max_tokens=400)
            return str(summary or "").strip()
        except Exception:
            return ""

    def compress_working(self, *, scope: str = "paper", paper_id: int | None = None, min_entries: int = 6) -> str:
        entries = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=["working"], limit_per_kind=999)
        if len(entries) < min_entries:
            return "not enough entries to compress"

        to_compress = entries[5:]
        if not to_compress:
            return "nothing to compress"
        return "compressed" if self._compress_docs(to_compress, scope=scope, paper_id=paper_id) else "compression failed"

    def _compress_docs(self, docs: list[dict], *, scope: str, paper_id: int | None) -> bool:
        lock = _COMPRESSION_LOCKS[hash((self.db_path, scope, paper_id)) % len(_COMPRESSION_LOCKS)]
        if not lock.acquire(blocking=False):
            return False
        try:
            batch: list[dict] = []
            size = 0
            # Choose whole notes within the prompt bound, oldest first. Unsent
            # notes (including oversize notes) remain available for a future run.
            for doc in reversed(docs):
                content = self._content_of(doc)
                cost = len(content.encode("utf-8")) + 4
                if not content or size + cost > 7600:
                    continue
                batch.append(doc)
                size += cost
                if len(batch) == 20:
                    break
            if not batch:
                return False
            summary = self._summarize_via_llm(batch)
            if not summary:
                return False
            # Persist the replacement before removing its exact source notes.
            saved = self.store.add_memory(
                user_id=self._user_id_for(scope, paper_id), content=summary,
                memory_type="long", importance=0.6,
                metadata=self._properties(scope, paper_id, "long", {
                    "summarized_memory_ids": [self._memory_id_of(doc) for doc in batch],
                }),
            )
            if not saved:
                return False
            self._delete_docs(batch)
            return True
        finally:
            lock.release()

    def consolidate(self, *, scope: str, paper_id: int | None, from_kind: str, to_kind: str, threshold: float = 0.6) -> int:
        docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=[from_kind], limit_per_kind=400)
        moved = 0
        for d in docs:
            try:
                imp = self._imp_of(d)
            except Exception:
                imp = 0.0
            if imp < float(threshold):
                continue
            content = self._content_of(d)
            if not content:
                continue
            self.add(scope=scope, paper_id=paper_id, kind=to_kind, content=content, importance=max(imp, 0.65))
            mid = self._memory_id_of(d)
            if mid:
                try:
                    self.store.delete_memory(mid)
                except Exception:
                    pass
            moved += 1
            if moved >= 50:
                break
        return moved

    def clear_all(self, *, scope: str, paper_id: int | None) -> int:
        kinds = ["working", "short", "long", "paper_summary", "preference"]
        docs = self._list_recent_docs(scope=scope, paper_id=paper_id, kinds=kinds, limit_per_kind=800)
        return self._delete_docs(docs)

    def list_recent_contents(
        self,
        *,
        scope: str,
        paper_id: int | None,
        kinds: list[str],
        limit: int = 10,
    ) -> list[str]:
        ks = [k for k in kinds if k.strip()]
        if not ks:
            return []
        user_id = self._user_id_for(scope, paper_id)
        out: list[tuple] = []
        for k in ks:
            docs = self.store.search_memories(user_id=user_id, memory_type=k, limit=limit)
            for d in docs:
                out.append((self._ts_of(d), self._content_of(d)))
        out.sort(key=lambda x: x[0], reverse=True)
        contents: list[str] = []
        for _, c in out:
            if c:
                contents.append(c)
            if len(contents) >= limit:
                break
        return contents

    def _collect_packets(
        self, *, scope: str, paper_id: int | None, kinds: list[str], limit_per_kind: int, label: str
    ) -> list[tuple[str, str, float]]:
        """Fetch recent docs and project them onto ``(label, content, score)`` packets."""
        return [
            (label, self._content_of(doc), self._score_memory(doc))
            for doc in self._list_recent_docs(
                scope=scope, paper_id=paper_id, kinds=kinds, limit_per_kind=limit_per_kind,
            )
        ]

    def build_context_block(self, *, paper_id: int, use_cache: bool = True, max_tokens: int = 1200) -> str:

        _ttl = self.config.working_ttl_minutes or 60
        _cutoff = int(time.time()) - _ttl * 60
        for _uid in ["papergraph:global"]:
            for _d in (self.store.search_memories(user_id=_uid, memory_type="working", limit=500) or []):
                if self._ts_of(_d) < _cutoff:
                    self.store.delete_memory(str(_d.get("memory_id")))

        if not use_cache:

            for _d in self._list_recent_docs(
                scope="paper", paper_id=paper_id,
                kinds=["working", "short", "long", "paper_summary"],
                limit_per_kind=200,
            ):
                _ts = self._ts_of(_d)
                _imp = self._imp_of(_d, 0.5)
                _age_hours = max(0, (int(time.time()) - _ts)) / 3600.0
                if _age_hours >= 1:
                    _new_imp = max(0.1, _imp - 0.03 * _age_hours)
                    if _new_imp < _imp - 0.01:
                        _mid = self._memory_id_of(_d)
                        if _mid:
                            _oc = self._content_of(_d)
                            _ot = str(_d.get("memory_type") or "working").strip()
                            _props = _d.get("properties") or {}
                            try:
                                self.store.delete_memory(_mid)
                            except Exception:
                                continue
                            self.add(
                                scope="paper", paper_id=paper_id, kind=_ot,
                                content=_oc, importance=_new_imp, meta=_props,
                            )

            _docs = self._list_recent_docs(
                scope="paper", paper_id=paper_id,
                kinds=["working", "short"],
                limit_per_kind=200,
            )
            if len(_docs) > 3:
                _docs.sort(key=lambda d: -self._ts_of(d))
                _to_del = [d for d in _docs[3:] if self._imp_of(d, 0.5) < 0.15]
                self._delete_docs(_to_del)

        packets: list[tuple[str, str, float]] = []
        packets += self._collect_packets(
            scope="global", paper_id=None, kinds=["preference"], limit_per_kind=5, label="preference",
        )
        packets += self._collect_packets(
            scope="paper", paper_id=paper_id, kinds=["paper_summary", "long"], limit_per_kind=3, label="long",
        )
        packets += self._collect_packets(
            scope="paper", paper_id=paper_id, kinds=["short", "working"], limit_per_kind=10, label="working",
        )

        packets.sort(key=lambda x: x[2], reverse=True)
        selected: list[str] = []
        # max_tokens is a legacy API name. Enforce a conservative UTF-8 byte
        # ceiling for the complete block, including labels and separators.
        max_bytes = max(0, min(int(max_tokens), MODEL_ITEM_BYTES))
        used_bytes = 0
        for kind, content, _score in packets:
            if not content:
                continue
            prefix = f"[{kind}] "
            overhead = len(prefix.encode("utf-8")) + (1 if selected else 0)
            room = max_bytes - used_bytes - overhead
            if room <= 0:
                continue
            fragment = clip_utf8(content, room)
            if not fragment:
                continue
            selected.append(prefix + fragment)
            used_bytes += overhead + len(fragment.encode("utf-8"))

        return "\n".join(selected)

    def get_context_for_query(self, *, paper_id: int, query: str, limit: int = 6) -> str:
        q = (query or "").strip().lower()
        if not q:
            return ""
        paper_docs = self._list_recent_docs(
            scope="paper",
            paper_id=paper_id,
            kinds=["short", "working", "paper_summary", "long"],
            limit_per_kind=120,
        )
        global_docs = self._list_recent_docs(
            scope="global",
            paper_id=None,
            kinds=["preference"],
            limit_per_kind=80,
        )
        candidates = paper_docs + global_docs
        matched: list[tuple[int, str]] = []
        for d in candidates:
            c = self._content_of(d)
            if not c:
                continue
            if q not in c.lower():
                continue
            ts = self._ts_of(d)
            matched.append((ts, c))
        matched.sort(key=lambda x: x[0], reverse=True)
        picked = [c for _ts, c in matched[: max(1, limit)]]
        if not picked:
            return ""
        bullets = "\n".join(f"- {x[:260]}" for x in picked)
        return "【与当前问题相关的记忆（检索匹配）】\n" + bullets

    def extract_memory_via_llm(self, paper_id: int, user_msg: str, assistant_reply: str) -> None:
        from ..llm.llm_service import get_llm

        prev_pref = self.list_recent_contents(scope="global", paper_id=None, kinds=["preference"], limit=1)
        prev_short = self.list_recent_contents(scope="paper", paper_id=paper_id, kinds=["short"], limit=8)

        prompt = (
            '你是论文阅读助手的"记忆抽取器"。\n'
            "请从对话中抽取值得写入记忆的内容，输出且仅输出一个 JSON：\n"
            '{"paper_short": [{"content": "...", "importance": 0.0}], '
            '"paper_long_update": {"content": "..."} | null, '
            '"global_preference_append": ["..."]}\n'
            "规则：paper_short 最多3条，每条<=60字；paper_long_update <=220字；global_preference_append 最多2条。"
        )

        # Match the reader's current-question limit and bound accumulated
        # preferences/notes separately. These are character, not token, limits.
        preference = (prev_pref[0] if prev_pref else "（无）")[:600]
        recent = " ".join(f"- {x[:240]}" for x in prev_short if x)[:600]
        user = (
            f"【已有全局偏好】\n{preference}\n\n"
            f"【该论文已有近期记忆】\n{recent}\n\n"
            f"【用户最新问题】\n{(user_msg or '')[:900]}\n\n"
            f"【助手回复】\n{(assistant_reply or '')[:1200]}"
        )[:_EXTRACT_PROMPT_MAX_CHARS]

        data = run_json_task(
            task_name="memory_extract",
            agent_name="papergraph_memory_extractor",
            llm=get_llm(),
            system_prompt=prompt,
            user_prompt=user,
            timeout_sec=12.0,
            retries=1,
            default={},
        )

        for it in (data.get("paper_short") or [])[:3]:
            if isinstance(it, dict) and (c := self._content_of(it)):
                imp = float(it.get("importance") or 0.6)
                self.add(scope="paper", paper_id=paper_id, kind="short", content=c[:240], importance=max(0.0, min(1.0, imp)))

        if isinstance(plu := data.get("paper_long_update"), dict) and (c := self._content_of(plu)):
            self.upsert_single(scope="paper", paper_id=paper_id, kind="paper_summary", content=c[:900], importance=0.75)

        if adds := [f"- {str(x).strip()[:240]}" for x in (data.get("global_preference_append") or [])[:2] if str(x).strip()]:
            prev = self.list_recent_contents(scope="global", paper_id=None, kinds=["preference"], limit=1)
            base = (prev[0] if prev else "").strip()
            merged = "\n".join(((base + "\n" if base else "") + "\n".join(adds)).splitlines()[-40:])
            self.upsert_single(scope="global", paper_id=None, kind="preference", content=merged, importance=0.85)
