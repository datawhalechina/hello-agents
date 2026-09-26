
from __future__ import annotations

import json
import logging
import math
import re
import time
from collections import Counter
from typing import Any

import os
from .sqlite_document_store_compat import SQLiteDocumentStore

logger = logging.getLogger(__name__)


def _memory_db_path() -> str:
    from ...settings import get_settings
    root = get_settings().data_dir
    os.makedirs(root, exist_ok=True)
    # Agent coordination memory uses synthetic identities (papergraph:agent:*),
    # so it must not share the application DB whose memories.user_id references users.id.
    return os.path.join(root, "agent_memory.db")

def _agent_user_id(agent_name: str) -> str:
    return f"papergraph:agent:{str(agent_name or 'unknown').strip()[:48]}"

def _shared_user_id() -> str:
    return "papergraph:shared"

# ── TF-IDF keyword scoring (borrowed from CrewAI's semantic weighting strategy) ──
_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "s", "t", "just", "don", "now", "and", "or", "but", "if", "while",
    "about", "against", "between", "into", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没",
    "看", "好", "自己", "这", "那", "它", "他", "她", "们", "什么", "怎么",
}

def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: split on non-word chars, filter stopwords, lowercase."""
    tokens = re.findall(r"\w{2,}", (text or "").lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) >= 2]

def _tfidf_score(query_tokens: list[str], doc_text: str, idf_map: dict[str, float] | None = None) -> float:
    """Score a document against query tokens using TF-IDF-like weighting.

    Unlike pure substring matching, this downweights common words and upweights
    distinctive terms. Falls back gracefully if no IDF map provided.
    """
    if not query_tokens or not doc_text:
        return 0.0
    doc_tokens = _tokenize(doc_text)
    if not doc_tokens:
        return 0.0
    doc_counter = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        tf = doc_counter.get(qt, 0)
        if tf == 0:
            continue
        # IDF: if we have a corpus IDF map, use it; otherwise assume 1.0
        idf = (idf_map or {}).get(qt, 1.0)
        score += (tf / doc_len) * idf
    return score

def _query_relevant_memories(query: str, memories: list[str], limit: int = 4) -> list[str]:
    """Select memories most relevant to a query using TF-IDF scoring.

    Replaces the old `ql[:8] in x.lower()` substring matching.
    """
    if not query or not memories:
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    scored = [(_tfidf_score(q_tokens, m), m) for m in memories]
    scored.sort(key=lambda x: -x[0])
    # Only return memories with score > 0 (at least one query token matched)
    return [m for s, m in scored[:limit] if s > 0]


class AgentMemory:

    # Maximum long-term memories per agent before LRU eviction
    MAX_EPISODIC_PER_AGENT = 20
    # Maximum shared working memories before compression
    MAX_SHARED_WORKING = 15
    # TF-IDF similarity threshold for dedup (borrowed from CrewAI's 0.85)
    DEDUP_THRESHOLD = 0.75

    def __init__(self, *, db_path: str | None = None) -> None:
        self.db_path = db_path or _memory_db_path()
        self.store = SQLiteDocumentStore(db_path=self.db_path)

    def _find_similar(self, uid: str, memory_type: str, content: str, limit: int = 10) -> tuple[str | None, float]:
        """Find the most similar existing memory via TF-IDF cosine similarity.

        Returns (memory_id, similarity_score) or (None, 0.0).
        """
        try:
            rows = self.store.search_memories(user_id=uid, memory_type=memory_type, limit=limit)
            if not rows:
                return None, 0.0
            new_tokens = _tokenize(content)
            if not new_tokens:
                return None, 0.0
            new_counter = Counter(new_tokens)
            new_len = max(1, len(new_tokens))

            best_id: str | None = None
            best_score = 0.0
            for r in rows:
                if not isinstance(r, dict):
                    continue
                existing = str(r.get("content") or "").strip()
                if not existing:
                    continue
                # Cosine similarity of TF vectors
                ext_tokens = _tokenize(existing)
                if not ext_tokens:
                    continue
                ext_counter = Counter(ext_tokens)
                ext_len = max(1, len(ext_tokens))

                # Cosine similarity
                all_terms = set(new_counter) | set(ext_counter)
                dot = sum(new_counter[t] * ext_counter[t] for t in all_terms)
                mag_new = math.sqrt(sum(v * v for v in new_counter.values()))
                mag_ext = math.sqrt(sum(v * v for v in ext_counter.values()))
                if mag_new == 0 or mag_ext == 0:
                    continue
                sim = dot / (mag_new * mag_ext)
                if sim > best_score:
                    best_score = sim
                    best_id = str(r.get("memory_id") or r.get("id") or "")
            return best_id, best_score
        except Exception:
            return None, 0.0

    def add(self, *, agent_name: str, content: str, memory_type: str = "working",
            importance: float = 0.5, shared: bool = False, meta: dict[str, Any] | None = None,
            tags: list[str] | None = None) -> str:
        """Add a memory entry with dedup checking.

        If an existing memory has TF-IDF cosine similarity > DEDUP_THRESHOLD,
        the new memory is not added (the existing one is kept, possibly with
        bumped importance). This prevents near-duplicate accumulation.

        Args:
            tags: Optional action tags for selective sharing (e.g. ["search", "reader"]).
        """
        now = int(time.time())
        uid = _shared_user_id() if shared else _agent_user_id(agent_name)
        mt = str(memory_type or "working").strip()[:32] or "working"
        c = str(content or "").strip()[:420]
        if not c:
            return ""

        # Dedup check: find similar existing memory
        similar_id, sim_score = self._find_similar(uid, mt, c)
        if similar_id and sim_score >= self.DEDUP_THRESHOLD:
            logger.debug("[AgentMemory] dedup: similarity=%.3f >= %.2f, skipping add", sim_score, self.DEDUP_THRESHOLD)
            return similar_id  # Return existing memory ID instead of adding duplicate

        props: dict[str, Any] = {"shared": bool(shared), "agent": str(agent_name or "")[:48]}
        if tags:
            props["tags"] = [str(t).strip().lower() for t in tags if str(t).strip()]
        if meta:
            props.update(meta)
        # The store assigns a UUID: multiple distinct memories in one second
        # must not overwrite each other through INSERT OR REPLACE.
        mid = self.store.add_memory(
            user_id=uid, content=c, memory_type=mt, timestamp=now,
            importance=float(importance or 0.0), properties=props)

        # LRU eviction for episodic memories
        if mt == "episodic":
            self._evict_old_memories(uid, mt, self.MAX_EPISODIC_PER_AGENT)

        # Auto-compress shared working memories when too many (borrowed from MemGPT tiered memory)
        if shared and mt == "working":
            self._compress_shared_working(uid)

        return mid

    def _evict_old_memories(self, uid: str, memory_type: str, max_count: int) -> None:
        """Evict lowest-scoring memories when count exceeds max_count.

        Score = importance * recency_decay (borrowed from CrewAI's composite scoring).
        """
        try:
            rows = self.store.search_memories(user_id=uid, memory_type=memory_type, limit=max_count + 10)
            if not rows or len(rows) <= max_count:
                return
            now = int(time.time())
            scored: list[tuple[float, str]] = []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                mid = str(r.get("memory_id") or r.get("id") or "")
                if not mid:
                    continue
                imp = float(r.get("importance") or 0.5)
                ts = int(r.get("timestamp") or 0)
                # Recency decay: 0.1 per day old (min 0.1)
                age_days = max(0, (now - ts) / 86400)
                recency = max(0.1, 1.0 - age_days * 0.05)
                score = imp * recency
                scored.append((score, mid))
            scored.sort()  # ascending — lowest scores first
            # Delete the excess (lowest scoring)
            excess = len(rows) - max_count
            for _, mid in scored[:excess]:
                self.store.delete_memory(mid)
        except Exception:
            pass

    def _compress_shared_working(self, uid: str) -> None:
        """Compress old shared working memories into a single episodic summary.

        When shared working memories exceed MAX_SHARED_WORKING, the oldest ones
        are summarized into a single episodic memory (borrowed from MemGPT's
        tiered memory: working → recall → archival).
        """
        try:
            rows = self.store.search_memories(user_id=uid, memory_type="working",
                                              limit=self.MAX_SHARED_WORKING + 10)
            if not rows or len(rows) <= self.MAX_SHARED_WORKING:
                return

            # Sort by timestamp ascending (oldest first)
            sorted_rows = sorted(
                [r for r in rows if isinstance(r, dict)],
                key=lambda r: int(r.get("timestamp") or 0)
            )

            # Take the oldest 8 to compress, keep the newest MAX_SHARED_WORKING - 8
            to_compress = sorted_rows[:8]
            if not to_compress:
                return

            # Build summary: concatenate contents (simple compression — no LLM call to avoid blocking)
            contents = [str(r.get("content") or "").strip() for r in to_compress]
            contents = [c for c in contents if c]
            if not contents:
                return

            summary = " | ".join(contents)[:420]
            now = int(time.time())

            # Write the compressed summary as episodic
            self.store.add_memory(
                user_id=uid, content=f"[压缩] {summary}", memory_type="episodic",
                timestamp=now, importance=0.6,
                properties={"shared": True, "agent": "system", "compressed": True},
            )

            # Delete the original working memories that were compressed
            for r in to_compress:
                mid = str(r.get("memory_id") or r.get("id") or "")
                if mid:
                    self.store.delete_memory(mid)

            logger.info("[AgentMemory] compressed %d shared working → 1 episodic", len(to_compress))
        except Exception:
            logger.debug("[AgentMemory] compress_shared_working failed", exc_info=True)

    def stats(self) -> dict[str, Any]:
        """Return memory statistics for observability."""
        try:
            all_memories = self.store.search_memories(
                user_id=_shared_user_id(), memory_type="", limit=1000
            )
            agent_memories = self.store.search_memories(
                user_id=_agent_user_id("paper_analysis"), memory_type="", limit=1000
            )

            def _count(rows: list) -> dict[str, int]:
                counts: dict[str, int] = {}
                for r in (rows or []):
                    if not isinstance(r, dict):
                        continue
                    mt = str(r.get("memory_type") or "unknown")
                    counts[mt] = counts.get(mt, 0) + 1
                return counts

            return {
                "shared_total": len(all_memories or []),
                "shared_by_type": _count(all_memories),
                "agent_total": len(agent_memories or []),
                "agent_by_type": _count(agent_memories),
            }
        except Exception as e:
            return {"error": str(e)}

    def recent(self, *, agent_name: str, memory_types: list[str], limit: int, shared: bool,
               tags: list[str] | None = None) -> list[str]:
        """Read recent memories, optionally filtered by tags.

        Args:
            tags: If provided, only return memories that have at least one matching tag.
                  This implements selective sharing (borrowed from MetaGPT's cause_by).
        """
        uid = _shared_user_id() if shared else _agent_user_id(agent_name)
        out: list[tuple[int, str]] = []
        for mt in [str(x).strip() for x in (memory_types or []) if str(x).strip()]:
            for r in (self.store.search_memories(user_id=uid, memory_type=mt, limit=int(limit)) or []):
                if not isinstance(r, dict):
                    continue
                # Tag filtering: skip memories that don't match requested tags
                if tags:
                    mem_tags = r.get("properties", {})
                    if isinstance(mem_tags, str):
                        try:
                            mem_tags = json.loads(mem_tags)
                        except Exception:
                            mem_tags = {}
                    mem_tag_list = mem_tags.get("tags", []) if isinstance(mem_tags, dict) else []
                    if mem_tag_list and not set(tags) & set(mem_tag_list):
                        continue
                c = str(r.get("content") or "").strip()
                if c:
                    out.append((int(r.get("timestamp") or 0), c))
        return [c for _, c in sorted(out, key=lambda x: -x[0])[:max(1, int(limit))]]

    def build_context_block(self, *, agent_name: str, query: str | None = None,
                            tags: list[str] | None = None, max_chars: int = 1200) -> str:
        """Build a formatted context block from shared and agent-specific memories.

        Args:
            tags: If provided, filter shared memories by these action tags.
                   E.g. reader agent passes ["reader", "search"] to get only
                   memories tagged as reader or search insights.
            max_chars: Aggregate character budget, including section labels.
                       This is a character limit, not a tokenizer estimate.
        """
        pref = self.get_preferences()
        agent_lines = self.recent(agent_name=agent_name, memory_types=["working"], limit=12, shared=False)
        agent_epi = self.recent(agent_name=agent_name, memory_types=["episodic"], limit=24, shared=False)
        # Cross-paper shared insights — filtered by tags if provided
        shared_lines = self.recent(agent_name="shared", memory_types=["working"], limit=8, shared=True, tags=tags)
        # Query-relevant shared memories using TF-IDF scoring (replaces old substring match)
        query_lines: list[str] = []
        if query:
            all_shared = self.recent(agent_name="shared", memory_types=["working", "episodic"], limit=30, shared=True, tags=tags)
            query_lines = _query_relevant_memories(query, all_shared, limit=4)
        lines: list[str] = []
        if pref:
            lines.append(f"【用户偏好（全局）】\n{pref}")
        if shared_lines:
            lines.append(f"【跨论文共享记忆】\n" + "\n".join(f"- {x}" for x in reversed(shared_lines)))
        if query_lines:
            lines.append(f"【与当前问题相关的历史记忆】\n" + "\n".join(f"- {x}" for x in query_lines))
        if agent_lines:
            lines.append(f"【{agent_name} 独立记忆（近期）】\n" + "\n".join(f"- {x}" for x in reversed(agent_lines)))
        if agent_epi:
            lines.append(f"【{agent_name} 独立记忆（长期）】\n" + "\n".join(f"- {x}" for x in reversed(agent_epi[:8])))
        return "\n\n".join(lines)[:max(0, int(max_chars))] if lines else ""

    def get_preferences(self) -> str:
        rows = self.store.search_memories(user_id=_shared_user_id(), memory_type="preference", limit=1)
        for r in (rows or []):
            c = str((r if isinstance(r, dict) else {}).get("content") or "").strip()
            if c:
                return c
        return ""

    def keywords_from_shared(self, *, limit_lines: int = 40, tokens_cap: int = 120) -> set[str]:
        from ...utils.common import tokenize_for_keywords
        lines = self.recent(agent_name="shared", memory_types=["working", "episodic"], limit=max(1, int(limit_lines)), shared=True)
        if not lines:
            return set()
        out: set[str] = set()
        for ln in lines:
            for w in tokenize_for_keywords(str(ln), min_len=3, max_len=26):
                if len(out) >= int(tokens_cap):
                    break
                out.add(w.lower())
            if len(out) >= int(tokens_cap):
                break
        return out

_agent_memory_singleton: AgentMemory | None = None

def get_agent_memory() -> AgentMemory:
    global _agent_memory_singleton
    if _agent_memory_singleton is None:
        _agent_memory_singleton = AgentMemory()
    return _agent_memory_singleton
