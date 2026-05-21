
from __future__ import annotations

import json
import logging
from typing import Any
from collections.abc import Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

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
                "返回该章节完整正文（max 24000 字符），适合深入分析特定部分"
                "若用户要按参考文献检索，用 ``reader_paper_lookup``"
            ),
        )
        self._get_snap = get_snap
        self._on_parsed = on_parsed

    def get_parameters(self) -> list[ToolParameter]:
        return [
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
                description="只提取匹配此关键词的章节完整内容（如 'experiment'、'Sec 4'、'实验'），忽略 max_chapter_chars 截断限制",
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
        focus = str(parameters.get("focus_section") or "").strip()

        try:
            snap = self._get_snap() or {}
        except Exception as exc:
            logger.debug("reader_pdf_structure_get_snap_failed", exc_info=exc)
            return ToolResponse.error("SNAP_FAILED", f"reader_pdf_structure：读取快照失败：{exc}")

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
            return ToolResponse.error("IMPORT_FAILED", f"reader_pdf_structure：解析模块不可用。{exc}")

        if focus:
            obj = parse_pdf_merged_text_to_json(merged, max_chapter_chars=50000, max_chapters=99)
            chapters = obj.get("chapters") or []
            matched = None
            focus_lower = focus.lower()
            for ch in chapters:
                h = (ch.get("heading") or "").lower()
                t = (ch.get("text") or "")[:200].lower()
                if focus_lower in h or focus_lower in t:
                    matched = ch
                    break
            if not matched:
                for ch in chapters:
                    h = (ch.get("heading") or "").lower()
                    if any(kw in h for kw in focus_lower.split()):
                        matched = ch
                        break
            if matched:
                heading = matched.get("heading", "(未命名)")
                text = matched.get("text", "")
                result = f"## {heading}\n\n{text}"
                if len(result) > 24000:
                    result = result[:24000] + "\n\n…(内容过长已截断)"
                return ToolResponse.success(text=result)
            else:
                avail = ", ".join(ch.get("heading","?") for ch in chapters[:12])
                return ToolResponse.success(
                    text=f"未找到匹配「{focus}」的章节。可用章节：{avail}\n请用其中某个名称重试。"
                )

        try:
            obj = parse_pdf_merged_text_to_json(merged, max_chapter_chars=mcc, max_chapters=mch)
        except Exception as exc:
            logger.debug("reader_pdf_structure_parse_failed", exc_info=exc)
            return ToolResponse.error("PARSE_FAILED", f"reader_pdf_structure：解析失败：{exc}")

        if callable(self._on_parsed):
            try:
                self._on_parsed(obj)
            except Exception as exc:
                logger.debug("reader_pdf_structure_on_parsed_failed", exc_info=exc)

        try:
            payload = json.dumps(obj, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            return ToolResponse.error("JSON_FAILED", f"reader_pdf_structure：序列化失败：{exc}")

        cap = 14000
        if len(payload) > cap:
            payload = payload[:cap] + "\n…(json 已截断，完整条目见 references.entries 前几项；可减小 max_chapter_chars)"

        return ToolResponse.success(
            text="reader_pdf_structure：以下为 JSON（可直接阅读 chapters / references）：\n" + payload
        )
