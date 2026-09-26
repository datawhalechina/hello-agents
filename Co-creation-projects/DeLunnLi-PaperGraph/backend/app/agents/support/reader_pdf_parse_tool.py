"""PDF 解析工具 —— MuPDF 正文提取、分段清洗与结构化输出."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from collections.abc import Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from ...services.llm.context_budget import clip_utf8, TOOL_ITEM_BYTES

logger = logging.getLogger(__name__)

class ReaderPdfParseTool(Tool):

    def __init__(
        self,
        *,
        get_snap: Callable[[], dict[str, Any]],
        on_parsed: Callable[[dict[str, Any | None], None]] = None,
    ) -> None:
        super().__init__(
            name="reader_pdf_structure",
            description=(
                "解析当前文献 PDF 文本为结构化 JSON。两种模式："
                "1) 目录模式：返回 chapters 列表（各章节标题+内容摘要）和 references 条目"
                "2) 聚焦模式：指定 focus_section 关键词（如 'experiment'、'实验'、'method'），"
                "分页返回章节正文（单次最多约 5000 字节），适合深入分析特定部分"
                "若用户要按参考文献检索，用 ``reader_paper_lookup``"
            ),
        )
        self._get_snap = get_snap
        self._on_parsed = on_parsed

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="offset", type="integer", description="聚焦章节正文的字符偏移，默认 0；使用回复给出的 next_offset 继续读取", required=False, default=0),
            ToolParameter(
                name="max_chapter_chars",
                type="integer",
                description="每个章节正文在 JSON 中的最大字符数（默认 8000）",
                required=False,
                default=8000,
            ),
            ToolParameter(
                name="max_chapters",
                type="integer",
                description="最多返回多少个章节块（默认 20）",
                required=False,
                default=20,
            ),
            ToolParameter(
                name="focus_section",
                type="string",
                description="只提取匹配此关键词的章节内容（如 'experiment'、'Sec 4'、'实验'）；长章节可用 offset 继续读取",
                required=False,
                default="",
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        try:
            mcc = int(parameters.get("max_chapter_chars") or 8000)
        except (TypeError, ValueError):
            mcc = 8000
        mcc = max(800, min(20000, mcc))
        try:
            mch = int(parameters.get("max_chapters") or 20)
        except (TypeError, ValueError):
            mch = 20
        mch = max(4, min(40, mch))
        focus = clip_utf8(str(parameters.get("focus_section") or "").strip(), 160)
        try:
            offset = max(0, int(parameters.get("offset") or 0))
        except (TypeError, ValueError):
            offset = 0

        try:
            snap = self._get_snap() or {}
        except Exception as exc:
            logger.debug("reader_pdf_structure_get_snap_failed", exc_info=exc)
            return ToolResponse.error("SNAP_FAILED", f"reader_pdf_structure：读取快照失败：{clip_utf8(str(exc), 200)}")

        merged = str(snap.get("_pdf_merged_for_structure") or "").strip()
        if len(merged) < 200:
            return ToolResponse.success(
                text=(
                    "reader_pdf_structure：当前无足够长的合并 PDF 文本（需本地 PDF 且阅读上下文已加载）。"
                    "请确认文献已入库且可抽取文本；扫描版或缺文件时无法解析。"
                ),
            )

        try:
            from ...services.reader.paper_reader_structure import parse_pdf_merged_text_to_json
        except Exception as exc:
            logger.warning("reader_pdf_structure_import_failed", exc_info=exc)
            return ToolResponse.error("IMPORT_FAILED", f"reader_pdf_structure：解析模块不可用。{clip_utf8(str(exc), 200)}")

        if focus:
            obj = parse_pdf_merged_text_to_json(merged, max_chapter_chars=len(merged), max_chapters=99)
            chapters = obj.get("chapters") or []
            matched = None
            focus_lower = re.sub(r"^(?:sec(?:tion)?\.?\s*|第\s*)", "", focus.lower()).removesuffix("节").strip()
            for ch in chapters:
                h = (ch.get("heading") or "").lower()
                t = (ch.get("text") or "")[:200].lower()
                if focus_lower == str(ch.get("number") or "") or focus_lower in h or focus_lower in t:
                    matched = ch
                    break
            if not matched:
                for ch in chapters:
                    h = (ch.get("heading") or "").lower()
                    if any(kw in h for kw in focus_lower.split()):
                        matched = ch
                        break
            if matched:
                heading = clip_utf8(matched.get("heading", "(未命名)"), 180)
                text = matched.get("text", "")
                page = clip_utf8(text[offset:], 5000)
                number = clip_utf8(matched.get("number", ""), 80)
                result = f"## {number} {heading}\n\n{page}"
                if offset + len(page) < len(text):
                    result += f"\n\n…(本页结束；next_offset={offset + len(page)})"
                return ToolResponse.success(text=clip_utf8(result, TOOL_ITEM_BYTES))
            else:
                avail = ", ".join(clip_utf8(f"{ch.get('number', '')} {ch.get('heading', '?')}", 120) for ch in chapters[:12])
                return ToolResponse.success(
                    text=f"未找到匹配「{focus}」的章节。可用章节：{avail}\n请用其中某个名称重试。"
                )

        try:
            obj = parse_pdf_merged_text_to_json(merged, max_chapter_chars=mcc, max_chapters=mch)
        except Exception as exc:
            logger.debug("reader_pdf_structure_parse_failed", exc_info=exc)
            return ToolResponse.error("PARSE_FAILED", f"reader_pdf_structure：解析失败：{clip_utf8(str(exc), 200)}")

        if callable(self._on_parsed):
            try:
                self._on_parsed(obj)
            except Exception as exc:
                logger.debug("reader_pdf_structure_on_parsed_failed", exc_info=exc)

        # Keep valid JSON at every budget size. Raw references duplicate entries;
        # retain counts and truncation flags rather than cutting serialized bytes.
        refs = obj["references"]
        refs["raw_truncated"] = bool(refs.get("raw"))
        refs["raw"] = ""
        refs["entries"] = [clip_utf8(x, 300) for x in refs["entries"][:8]]
        for chapter in obj["chapters"]:
            original = chapter["text"]
            chapter["text"] = clip_utf8(original, 360)
            chapter["truncated"] = chapter["truncated"] or chapter["text"] != original
        prefix = "reader_pdf_structure：以下为 JSON（可直接阅读 chapters / references）：\n"
        obj["chapter_count"] = len(obj["chapters"])
        refs["entries_truncated"] = True
        while True:
            payload = json.dumps(obj, ensure_ascii=False)
            if len((prefix + payload).encode("utf-8")) <= TOOL_ITEM_BYTES - 16:
                break
            candidates = [ch for ch in obj["chapters"] if ch["text"]]
            if candidates:
                largest = max(candidates, key=lambda ch: len(ch["text"].encode("utf-8")))
                largest["text"] = clip_utf8(largest["text"], len(largest["text"].encode("utf-8")) // 2)
                largest["truncated"] = True
            elif refs["entries"]:
                refs["entries"].pop()
            elif obj["chapters"]:
                obj["chapters"].pop()
            else:
                break
        refs["entries_truncated"] = len(refs["entries"]) < refs["entry_count"]
        # Reserve room for the final flag during serialization.
        return ToolResponse.success(text=prefix + json.dumps(obj, ensure_ascii=False))
