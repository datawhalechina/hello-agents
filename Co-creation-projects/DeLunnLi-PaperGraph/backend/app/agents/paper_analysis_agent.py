"""论文分析智能体 —— PDF 全文解析、表格提取与深度问答."""

from __future__ import annotations

import logging
import copy
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from hello_agents import SimpleAgent
from hello_agents.tools.registry import ToolRegistry

from app.core.paper_paths import normalize_library_category_display

from ..utils import parse_llm_json
from ..services.llm.context_budget import clip_utf8
from ..services.llm.agent_config import papergraph_agent_config
from ..services.llm.llm_service import is_llm_configured
from .base import BaseAgent
from .support.paper_analysis_helpers import (
    clip_text as _clip,
    clip_reader_history as _clip_reader_history,
    clean_library_tag as _clean_library_tag,
    dedupe_tags as _dedupe_tags,
    nearest_major_in as _nearest_major_in,
    parse_taxonomy_majors as _parse_taxonomy_majors,
    prioritize_reader_context as _prioritize_reader_context,
    top_similar_categories as _top_similar_categories,
)
from .support.reader_pdf_parse_tool import ReaderPdfParseTool
from .support.reader_table_tool import ReaderTableTool
from .support.paper_skill_tool import PaperSkillTool
from .support.reader_paper_lookup_tool import ReaderPaperLookupTool
from .support.reader_reference_lookup_tool import (
    READER_RECOMMEND_MAX_RESULTS, ReaderReferenceLookupTool,
    READER_RELATED_FROM_BIBLIOGRAPHY, READER_RELATED_FROM_REF_BLOCK,
    paper_matches_reader_snap, parse_reader_recommendation_intent,
    prioritize_reader_related_pairs_refs_first, reader_user_allows_external_paper_lookup,
    rerank_reader_pairs_by_anchor_refs_first, resolve_references_via_openalex,
    strip_reader_reco_boilerplate, user_message_may_need_reference_lookup,
)

from .prompts.paper_analysis import ANALYSIS_SYSTEM, READER_CHAT_SYSTEM

logger = logging.getLogger(__name__)

_READER_PROMPT_MAX_CHARS = 7200
_READER_MEMORY_MAX_CHARS = 1200

def _reader_resolve_user_hint(user_message: str, snap: Dict[str, Any], *, want_reco: bool) -> str:
    um = (user_message or "").strip()
    if not want_reco:
        return um[:900]
    core = strip_reader_reco_boilerplate(um) or um
    if len(core) >= 28:
        return um[:900]
    title = str(snap.get("title") or "").strip()
    ab = str(snap.get("abstract") or "").strip()[:520]
    bits = [x for x in (core, title, ab) if x]
    return "\n".join(bits).strip()[:900] or um[:900]

_MAJOR_LOCK = threading.Lock()
_MAJOR_WHITELIST: Optional[Tuple[str, ...]] = None

class ReaderReply(tuple):
    """Three-value legacy reply plus explicit generation status for cache callers."""

    def __new__(cls, text, papers, sources, *, generated: bool):
        result = super().__new__(cls, (text, papers, sources))
        result.generated = generated
        return result


@dataclass
class TaskSpec:
    name: str
    agent: Any
    parser: Optional[Callable[[str], Any]] = None
    max_chars: int = 6000

class PaperAnalysisAgent(BaseAgent):
    """论文分析核心智能体 —— 管理多个子 Agent 协同完成 PDF 解析、表格提取与问答."""

    def __init__(self) -> None:
        super().__init__()
        self._analysis = self._make_analysis()
        self._reader_lookup_lock = threading.Lock()
        self._reader_lookup_buffer: List[Tuple[Any, str]] = []
        self._reader_snap: Dict[str, Any] = {}
        self._reader_last_user_message: str = ""

        # Retain the inspection/custom-tool seam. Actual requests own a fresh agent,
        # tool registry and closures so framework history never crosses papers.
        self._reader = self._make_reader(
            get_snap=lambda: self._reader_snap,
            on_found=self._reader_tool_on_found,
            get_message=lambda: self._reader_last_user_message,
            on_parsed=self._reader_on_pdf_structure,
        )

    def _make_analysis(self):
        return SimpleAgent(
            name="papergraph_analysis", llm=self.llm, system_prompt=ANALYSIS_SYSTEM,
            config=papergraph_agent_config(),
        )

    def _make_reader(self, *, get_snap, on_found, get_message, on_parsed):
        registry = ToolRegistry()
        config = papergraph_agent_config()
        if config.skills_enabled and config.skills_auto_register:
            registry.register_tool(PaperSkillTool())
        registry.register_tool(ReaderPaperLookupTool(on_papers_found=on_found, get_snap=get_snap))
        registry.register_tool(ReaderReferenceLookupTool(
            get_snap=get_snap, on_papers_found=on_found, get_user_message=get_message,
        ))
        registry.register_tool(ReaderPdfParseTool(get_snap=get_snap, on_parsed=on_parsed))
        registry.register_tool(ReaderTableTool(get_snap=get_snap))
        return SimpleAgent(
            name="papergraph_paper_reader", llm=self.llm, system_prompt=READER_CHAT_SYSTEM,
            config=config, tool_registry=registry, enable_tool_calling=True, max_tool_iterations=5,
        )

    def _ensure_major_whitelist(self) -> None:
        global _MAJOR_WHITELIST
        if _MAJOR_WHITELIST is not None:
            return
        with _MAJOR_LOCK:
            if _MAJOR_WHITELIST is not None:
                return
            wl: Optional[Tuple[str, ...]] = None
            taxonomy_prompt = (
                "# 任务：为个人/小团队文献库生成顶层大类\n"
                '输出: {"majors":["名称1",...]}\n'
                "- 共 16～24 条；恰含一个「未分类」\n"
                "- 名称须具学术划分意义，覆盖计算机与交叉学科\n"
                "- 每条 2～10 个中文字；互异；禁含「/」及路径非法字符\n"
            )
            try:
                analysis = self._make_analysis()
                raw = analysis.run(taxonomy_prompt)
                parsed = _parse_taxonomy_majors(raw)
                if not parsed:
                    # Framework history includes the malformed answer, which may
                    # be far larger than the prompt. Retry the task from scratch.
                    analysis = self._make_analysis()
                    raw = analysis.run(taxonomy_prompt + '\n上次输出无法解析；请只输出合法 JSON。')
                    parsed = _parse_taxonomy_majors(raw)
                if parsed:
                    wl = tuple(parsed)
            except Exception:
                logger.exception("major_taxonomy_bootstrap_failed")
            if not wl:
                raise RuntimeError("major_taxonomy_bootstrap_failed")
            _MAJOR_WHITELIST = wl
            logger.info("paper_analysis_major_whitelist_ready", extra={"n": len(wl)})

    def _get_major_whitelist(self) -> Tuple[str, ...]:
        self._ensure_major_whitelist()
        if _MAJOR_WHITELIST is None:
            raise RuntimeError("major_whitelist_unavailable")
        return _MAJOR_WHITELIST

    def _cleanup_mixed_reader_response(self, reply: str, user_message: str) -> str:
        """Use one cleanup pass when tool output leaks into the final reply."""
        t = reply.strip()
        # Typical leak: disclaimer plus useful data, or raw tool JSON.
        has_disclaimer = any(x in t[:300] for x in ("材料不足", "缺少", "仅有标题")) or bool(re.search(r"基于.*推测", t[:300]))
        has_actual_data = len(t) > 600 and any(x in t for x in ("Tab.", "Table", "结果", "实验", "| "))
        has_tool_artifact = "reader_pdf_struct" in t or '"chapters"' in t[:500]

        if (has_disclaimer and has_actual_data) or has_tool_artifact:
            if not is_llm_configured():
                return reply
            logger.info("paper_reader: detected mixed response, running cleanup pass")
            try:
                um = (user_message or "").strip()[:200]
                # Keep extracted paper facts; drop wrapper noise.
                cleaned = re.sub(r"^.*?(?:当前文献材料说明|当前提供的材料).*?\n\n", "", t, flags=re.S)
                cleaned = re.sub(r"reader_pdf_struct\S*", "", cleaned)
                cleaned = cleaned.strip()[:6000]
                if cleaned:
                    prompt = (
                        f"用户问：{um}\n\n"
                        f"以下是从论文中提取的信息（可能含多个片段）：\n\n{cleaned}\n\n"
                        "请整合成一个连贯的回答。用中文分点说明。如有表格数据用 Markdown 表格呈现。"
                        "不要提及'材料不足'或'推测'——只基于已有信息回答，不确定的地方标注'论文未提供'。"
                    )
                    result = self._reader_chat_llm(prompt)
                    if result.strip():
                        return result.strip()
            except Exception:
                logger.debug("cleanup_mixed_response_failed", exc_info=True)
        return reply

    @staticmethod
    def _looks_like_raw_tool_output(text: str) -> bool:
        """Detect raw tool output that still needs interpretation."""
        t = (text or "").strip()
        if not t:
            return False
        if "reader_pdf_structure" in t:
            return True
        if t.startswith("## ") and len(t) > 300:
            first_line = t.split("\n")[0]
            if re.match(r"^## \d", first_line) or re.match(r"^## [A-Z]", first_line):
                return True
        if '"chapters"' in t[:500] or '"references"' in t[:500]:
            return True
        return False

    def _interpret_tool_output(self, tool_output: str, user_message: str) -> str:
        """Convert raw tool output into a user-facing answer."""
        if not is_llm_configured():
            return tool_output
        try:
            um = (user_message or "").strip()[:200]
            # Strip tool wrappers before asking the LLM to explain.
            cleaned = re.sub(r"^.*?reader_pdf_structure[：:]\s*", "", tool_output, flags=re.S)
            cleaned = re.sub(r"^以下为 JSON.*?\n", "", cleaned)
            cleaned = re.sub(r"^\s*\{\s*\"chapters\".*?\n", "", cleaned)
            cleaned = re.sub(r"reader_pdf_structu\S*$", "", cleaned)
            cleaned = re.sub(r"[\u007F-\u009F]", "", cleaned)
            cleaned = cleaned.strip()
            if not cleaned or len(cleaned) < 50:
                return "当前文献材料不足以回答该问题。PDF 文本提取不完整，建议确认 PDF 文件是否可读。"
            cleaned = cleaned[:6000]
            prompt = (
                f"用户问：{um}\n\n"
                f"以下是从论文中提取的相关章节内容：\n\n{cleaned}\n\n"
                "请用中文为用户解读这段内容。分点说明关键发现、方法和结论。"
                "用 Markdown 表格对比数据（如有）。\n"
                "重要：如果上面的内容不足以回答用户问题（如仅有章节标题无正文），"
                "请直接说明材料不足，严禁编造论文中不存在的数据、方法或结论。"
            )
            raw = self._reader_chat_llm(prompt)
            return raw.strip() or tool_output
        except Exception:
            logger.debug("interpret_tool_output_failed", exc_info=True)
            return tool_output

    def _reader_chat_llm(self, prompt: str) -> str:
        """Reader chat without tools."""
        from ..services.llm.llm_service import coerce_hello_agents_llm_output_to_str
        interpreter = SimpleAgent(
            name="papergraph_reader_interpreter", llm=self.llm,
            system_prompt=READER_CHAT_SYSTEM, config=papergraph_agent_config(),
            enable_tool_calling=False,
        )
        return coerce_hello_agents_llm_output_to_str(interpreter.run(clip_utf8(prompt)))

    def _reader_tool_on_found(self, papers: List[Any], source: str) -> None:
        with self._reader_lookup_lock:
            for p in papers or []:
                self._reader_lookup_buffer.append((p, source))

    def _reader_on_pdf_structure(self, obj: Dict[str, Any]) -> None:
        try:
            snap = getattr(self, "_reader_snap", None)
            if not isinstance(snap, dict):
                return
            refs = obj.get("references") or {}
            entries = refs.get("entries")
            if isinstance(entries, list) and entries:
                snap["references_from_structure"] = [str(x).strip() for x in entries if str(x).strip()]
        except Exception:
            logger.debug("reader_on_pdf_structure_failed", exc_info=True)

    @staticmethod
    def _dedupe_reader_paper_pairs(buffer: List[Tuple[Any, str]]) -> List[Tuple[Any, str]]:
        seen: set[str] = set()
        out: List[Tuple[Any, str]] = []
        for p, src in buffer:
            k = str(getattr(p, "title", "") or "").strip().lower()
            if not k or k in seen:
                continue
            seen.add(k)
            out.append((p, src))
        return out
    def _run_task(self, spec: TaskSpec, user: str) -> Any:
        prompt = clip_utf8(_clip(user, spec.max_chars))
        agent = self._make_analysis() if spec.agent is getattr(self, "_analysis", None) else spec.agent
        try:
            raw = agent.run(prompt)
        except Exception as exc:
            logger.exception("paper_analysis_llm_failed", extra={"task": spec.name})
            raise RuntimeError(f"paper_analysis_llm_failed:{spec.name}") from exc

        raw_text = (raw if isinstance(raw, str) else str(raw or "")).strip()

        if not spec.parser:
            if not raw_text:
                if spec.name == "paper_reader_reply":
                    return ""
                raise RuntimeError(f"paper_analysis_empty_response:{spec.name}")

            # Some tool responses need a final explanation pass.
            if spec.name == "paper_reader_reply" and self._looks_like_raw_tool_output(raw_text):
                logger.info("paper_reader: detected raw tool output, invoking interpreter")
                raw_text = self._interpret_tool_output(raw_text, user)

            return raw_text

        data = spec.parser(raw_text)
        if data is not None:
            return data

        try:
            # Parser tasks are classification tasks. Do not replay a malformed
            # assistant result through SimpleAgent's automatic conversation history.
            retry_agent = self._make_analysis()
            raw2 = retry_agent.run(clip_utf8("上次输出无法解析；请只输出合法 JSON。\n" + prompt))
            data2 = spec.parser((raw2 or "").strip())
            if data2 is not None:
                return data2
        except Exception:
            logger.exception("paper_analysis_json_retry_failed", extra={"task": spec.name})
        raise RuntimeError(f"paper_analysis_parse_failed:{spec.name}")

    def _record_preference_signals(
        self,
        *,
        signal: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        major: Optional[str] = None,
        shared: bool = True,
    ) -> None:
        try:
            from ..services.memory.agent_memory import get_agent_memory

            am = get_agent_memory()
            parts: List[str] = [f"偏好信号({signal})"]
            if title:
                parts.append(f"title={str(title).strip()[:120]}")
            if major:
                parts.append(f"major={str(major).strip()[:24]}")
            if category:
                parts.append(f"cat={str(category).strip()[:40]}")
            if tags:
                clean = [str(x).strip() for x in (tags or []) if str(x).strip()][:10]
                if clean:
                    parts.append("tags=" + ",".join(clean))
            line = " | ".join(parts)[:360]
            am.add(agent_name="paper_analysis", content=line, memory_type="working", importance=0.55, shared=bool(shared))
        except Exception:
            return

    def _parse_major_json(self, raw: str) -> Optional[str]:
        d = parse_llm_json(raw)
        if not isinstance(d, dict):
            return None
        m = str(d.get("major") or d.get("category") or "").strip()
        if not m:
            return None
        return _nearest_major_in(m, self._get_major_whitelist())

    def _parse_fine_classify_json(self, raw: str, major: str) -> Optional[Tuple[str, List[str]]]:
        d = parse_llm_json(raw)
        if not isinstance(d, dict):
            return None
        cat = normalize_library_category_display(str(d.get("category") or "未分类"))
        tags_raw = d.get("tags")
        extra: List[str] = []
        if isinstance(tags_raw, list):
            for x in tags_raw:
                c = _clean_library_tag(str(x))
                if c:
                    extra.append(c)
            extra = _dedupe_tags(extra)
        if not cat:
            return None
        if major and major != "未分类" and not (cat.startswith(major) or major in cat):
            cat = normalize_library_category_display(f"{major}/{cat.split('/')[-1]}")
        return cat, extra

    _venue_type_cache: dict[str, str] = {}

    def classify_venue_type(self, journal: str | None) -> str | None:
        if not journal or not str(journal).strip():
            return None
        j = str(journal).strip()
        if j.startswith("arXiv:"):
            return "preprint"
        if j in self._venue_type_cache:
            return self._venue_type_cache[j]
        try:
            prompt = f'判断以下学术来源名称是会议(conference)还是期刊(journal)。只回复一个单词：conference 或 journal。\n\n名称：{j}'
            resp = self._make_analysis().run(clip_utf8(prompt))
            result = str(resp).strip().lower()
            if "conference" in result:
                vt = "conference"
            elif "journal" in result:
                vt = "journal"
            else:
                vt = None
        except Exception:
            vt = None
        if vt:
            self._venue_type_cache[j] = vt
        return vt

    def classify_for_library(
        self,
        title: str,
        abstract: Optional[str],
        journal: Optional[str],
        keywords: Optional[List[str]] = None,
        existing_categories: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        kw = clip_utf8("、".join(str(x) for x in (keywords or [])[:32]), 400) or "（无）"
        journal = clip_utf8(journal, 240) or "（无）"
        abstract = clip_utf8((abstract or "").strip(), 3000) or "（无摘要）"
        title = clip_utf8(title, 600)
        seed = f"{title}\n{abstract[:800]}"

        cats_all = [str(x).strip() for x in (existing_categories or []) if str(x).strip()]
        candidates = _top_similar_categories(seed, cats_all, k=18)

        base_user = f"标题：{title}\n摘要：{abstract}\n来源：{journal}\n关键词：{kw}"

        wl = self._get_major_whitelist()
        major_list_block = "\n".join(f"- {m}" for m in wl)
        major_user = f"{base_user}\n\n【可选大类列表】\n{major_list_block}"

        major_fb = "未分类"
        major_user = (
            "# 任务：归类（大类）\n"
            "从【可选大类列表】中选一个最匹配的大类\n"
            '输出: {"major":"大类名"}\n'
            '- 必须从列表选；优先字面匹配，否则语义最接近；无法判断→"未分类"；禁列表外值\n\n'
            + major_user
        )
        major_spec = TaskSpec(
            name="classify_major",
            agent=self._analysis,
            parser=self._parse_major_json,
            max_chars=5200,
        )
        major = self._run_task(major_spec, major_user)
        if not isinstance(major, str) or not major.strip():
            major = major_fb
        major = _nearest_major_in(major, wl)

        if not candidates:
            cat0 = normalize_library_category_display(major)
            self._record_preference_signals(signal="classify", title=title, major=major, category=cat0, shared=True)
            return cat0, []

        prefixed = [c for c in candidates if c.startswith(major) or c.split("/")[0] == major]
        pool = prefixed if len(prefixed) >= 2 else candidates
        pool_block = "\n".join(f"- {clip_utf8(c, 120)}" for c in pool[:18])

        fine_user = (
            "# 任务：归类（路径与标签）\n"
            "给定大类，从候选已有路径中选择路径，生成标签\n"
            '输出: {"category":"路径","tags":["标签1",...]}\n'
            "- category：优先原样选候选；否则「大类／子类」，子类 2～8 个中文字\n"
            "- tags：3～8 个，单条 ≤24 字，不重复；无法判断可为 []\n"
            "- 禁含路径非法字符 \\ / : * ? \" < > |\n\n"
            f"{base_user}\n\n给定大类：{major}\n\n"
            f"【候选已有路径】（请优先从中复制一条作为 category）\n{pool_block}"
        )
        default_cat = normalize_library_category_display(major)

        def _fine_parser(raw: str) -> Optional[Tuple[str, List[str]]]:
            return self._parse_fine_classify_json(raw, major)

        fine_spec = TaskSpec(
            name="classify_fine",
            agent=self._analysis,
            parser=_fine_parser,
            max_chars=5500,
        )
        out = self._run_task(fine_spec, fine_user)
        if isinstance(out, tuple) and len(out) == 2:
            cat, tags = out[0], out[1]
            cat = normalize_library_category_display(str(cat or "未分类"))
            if isinstance(tags, list):
                cleaned: List[str] = []
                for x in tags:
                    c = _clean_library_tag(str(x))
                    if c:
                        cleaned.append(c)
                tags = _dedupe_tags(cleaned)
            else:
                tags = []
            self._record_preference_signals(signal="classify", title=title, major=major, category=cat, tags=tags, shared=True)
            return cat, tags
        return default_cat, []

    def paper_reader_reply(
        self,
        context_block: str,
        history_lines: str,
        user_message: str,
        reader_snap: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Any], List[str]]:
        snap: Dict[str, Any] = copy.deepcopy(reader_snap or {})
        request_pairs: List[Tuple[Any, str]] = []

        def on_found(papers, source):
            request_pairs.extend((paper, source) for paper in (papers or []))

        def on_parsed(obj):
            entries = (obj.get("references") or {}).get("entries") or []
            snap["references_from_structure"] = [str(x).strip() for x in entries if str(x).strip()]

        try:
            ctx = _prioritize_reader_context(context_block, max_chars=3600)
            hist = _clip_reader_history((history_lines or "").strip() or "（尚无此前对话）", max_chars=2200)
            um = _clip(user_message, 900)
            want_reco, reco_max = parse_reader_recommendation_intent(um)
            # Bound complete assembled items in bytes, retaining the latest question
            # and the tail of explicit per-paper history before optional memory.
            ctx = clip_utf8(ctx, 2700)
            hist = clip_utf8(hist, 2200, tail=True)
            reader = self._make_reader(
                get_snap=lambda: snap, on_found=on_found,
                get_message=lambda: um, on_parsed=on_parsed,
            ) if hasattr(self, "llm") else self._reader

            # Reserve current evidence, recent history and the question before
            # filling the remaining space with optional cross-paper memories.
            context_and_history = f"【当前文献材料】\n{ctx}\n\n【对话历史】\n{hist}\n\n"
            question = f"【用户最新问题】\n{um}"
            memory_header = "【共享/独立记忆】\n"
            memory_budget = min(_READER_MEMORY_MAX_CHARS, max(
                0, _READER_PROMPT_MAX_CHARS - len(context_and_history) - len(question)
                - len(memory_header) - len("\n\n"),
            ))
            try:
                from ..services.memory.agent_memory import get_agent_memory

                mem_block = get_agent_memory().build_context_block(
                    agent_name="paper_analysis", query=um, max_chars=memory_budget,
                ) if memory_budget else ""
            except Exception:
                mem_block = ""
            byte_room = 9000 - len((context_and_history + question + memory_header + "\n\n").encode("utf-8"))
            mem_block = clip_utf8(mem_block, min(900, max(0, byte_room)))
            user = (
                context_and_history
                + (f"{memory_header}{mem_block}\n\n" if mem_block else "")
                + question
            )
            spec = TaskSpec(
                name="paper_reader_reply",
                agent=reader,
                parser=None,
                max_chars=_READER_PROMPT_MAX_CHARS,
            )
            out = self._run_task(spec, user)
            # Clean up mixed tool/user-facing output.
            if isinstance(out, str) and out.strip():
                out = self._cleanup_mixed_reader_response(out, um)
            pairs = self._dedupe_reader_paper_pairs(request_pairs)
            bib_only = (
                (want_reco or user_message_may_need_reference_lookup(um))
                and not reader_user_allows_external_paper_lookup(um)
            )
            if bib_only:
                pairs = [(p, source) for p, source in pairs if source in (
                    READER_RELATED_FROM_BIBLIOGRAPHY, READER_RELATED_FROM_REF_BLOCK,
                )]
            if user_message_may_need_reference_lookup(um) and not pairs:
                try:
                    extra = resolve_references_via_openalex(
                        snap, max_results=reco_max if want_reco else 2,
                        user_hint=_reader_resolve_user_hint(um, snap, want_reco=want_reco),
                    )
                    pairs.extend((paper, READER_RELATED_FROM_BIBLIOGRAPHY) for paper in extra)
                except Exception:
                    logger.debug("reader_reference_server_fallback_failed", exc_info=True)

            pairs = [(p, source) for p, source in pairs if not paper_matches_reader_snap(snap, p)]
            if want_reco and pairs:
                try:
                    if is_llm_configured():
                        from ..services.reader.reader_recommend_llm import rerank_reader_recommend_pairs_by_llm

                        pairs = rerank_reader_recommend_pairs_by_llm(
                            snap,
                            pairs,
                            user_message=um,
                            history_lines=hist,
                            reco_max_hint=reco_max,
                        )
                    else:
                        pairs = rerank_reader_pairs_by_anchor_refs_first(snap, pairs, k=reco_max)
                except Exception:
                    logger.debug("reader_llm_recommend_rerank_failed", exc_info=True)
                    pairs = rerank_reader_pairs_by_anchor_refs_first(snap, pairs, k=reco_max)
            if pairs:
                pairs = prioritize_reader_related_pairs_refs_first(pairs)
            if want_reco and pairs:
                cap = max(1, min(int(reco_max or 2), READER_RECOMMEND_MAX_RESULTS, len(pairs)))
                pairs = pairs[:cap]
            papers = [p for p, _ in pairs]
            provenances = [s for _, s in pairs]
            text_out = (str(out) if out is not None else "").strip()
            generated = bool(text_out)
            if not text_out:
                if papers:
                    if snap.get("references_source") == "pdf_section":
                        text_out = (
                            "已根据 PDF 参考文献区摘录检索到相关论文，请点击下方「推荐论文」查看条目；"
                            "如需结合摘要或方法做对比，请告诉我关注点。"
                        )
                    else:
                        text_out = (
                            "已根据参考文献检索列出相关论文，请点击下方「推荐论文」查看条目；"
                            "如需结合摘要或方法做对比，请告诉我关注点。"
                        )
                elif user_message_may_need_reference_lookup(um) and not (snap.get("references") or []) and not (
                    snap.get("references_section_raw") or ""
                ).strip():
                    text_out = (
                        "未在库表中找到 references，且当前 PDF 摘录中未能定位到「参考文献 / References」标题后的文本块，"
                        "无法从原文区检索。若为扫描版、参考文献不在已抽取页范围内，或版式特殊，会出现此情况。"
                        "可从带参考文献的数据源重新保存该文，或直接粘贴英文题名 / DOI 以便检索。"
                    )
                elif user_message_may_need_reference_lookup(um) and (snap.get("references_section_raw") or "").strip():
                    text_out = (
                        "上下文中已含 PDF 参考文献区原文，但本轮未产生可展示的检索命中。"
                        "你可指定要查的一条英文题名或 DOI；或让我从摘录中逐条用检索工具核对。"
                    )
                elif user_message_may_need_reference_lookup(um):
                    text_out = (
                        "已按库表参考文献题录在 OpenAlex / arXiv / DBLP 中尝试解析，但未找到与题录足够一致的条目"
                        "（已过滤明显不符的综述/泛命中）。你可粘贴 DOI 或标准英文题名，我会用 reader_paper_lookup 检索并展示在下方列表。"
                    )
                else:
                    text_out = "（本次未收到模型有效正文。请稍后重试，或缩短问题后再次提问。）"

            try:
                from ..services.memory.agent_memory import get_agent_memory

                am = get_agent_memory()
                am.add(agent_name="paper_analysis", content=f"用户问：{um}", memory_type="working", importance=0.55, shared=False)
                am.add(agent_name="paper_analysis", content=f"助手答：{text_out[:240]}", memory_type="working", importance=0.5, shared=False)
                am.add(agent_name="paper_analysis", content=f"阅读问答要点：{text_out[:180]}", memory_type="working", importance=0.55, shared=True)
            except Exception:
                pass

            logger.info("reader_post: text_out_len=%d papers=%d want_reco=%s",
                        len(text_out or ""), len(papers), want_reco)
            return ReaderReply(text_out, papers, provenances, generated=generated)
        finally:
            # These objects belong to this request; clearing a singleton here would
            # destroy another in-flight request's PDF/tool results.
            request_pairs.clear()
