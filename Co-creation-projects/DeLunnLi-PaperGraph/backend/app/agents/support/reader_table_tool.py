"""表格提取工具 —— PDF 表格检测、解析与上下文关联查询."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse

from ...services.llm.context_budget import clip_utf8, TOOL_ITEM_BYTES

logger = logging.getLogger(__name__)


class ReaderTableTool(Tool):
    """Extract a specific table from the current paper's PDF."""

    def __init__(self, *, get_snap: Callable[[], dict[str, Any]]) -> None:
        super().__init__(
            name="reader_pdf_table",
            description=(
                "获取当前论文 PDF 中的指定表格内容。当用户询问表格数据或论文提到 'Tab. 3'/'Table 4' 时调用。"
                "输入表号（如 '3'、'4'）或关键词（如 'ImageNet'、'ablation'），返回对应表格的 Markdown 内容。"
            ),
        )
        self._get_snap = get_snap

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="table_ref",
                type="string",
                description="表格编号（如 '3'）或关键词（如 'ImageNet'、'ablation'）",
                required=True,
            ),
        ]

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        ref = clip_utf8(str(parameters.get("table_ref") or "").strip(), 160)
        if not ref:
            return ToolResponse.error("NO_REF", "请指定表格编号或关键词，如 table_ref='3'")

        try:
            snap = self._get_snap() or {}
        except Exception as exc:
            return ToolResponse.error("SNAP_FAILED", f"读取快照失败：{clip_utf8(str(exc), 200)}")

        pdf_path = str(snap.get("_pdf_abspath") or "").strip()
        if not pdf_path:
            merged = str(snap.get("_pdf_merged_for_structure") or "").strip()
            if not merged or len(merged) < 200:
                return ToolResponse.success(
                    text="当前文献无可用 PDF。请先确认论文已保存且 PDF 已下载。"
                )
            tables = self._extract_tables_from_text(merged)
        else:
            try:
                from ...services.reader.paper_reader_context import extract_pdf_tables_markdown
                tables_md = extract_pdf_tables_markdown(pdf_path)
                if tables_md:
                    tables = self._parse_table_blocks(tables_md)
                else:
                    merged = str(snap.get("_pdf_merged_for_structure") or "").strip()
                    tables = self._extract_tables_from_text(merged) if merged else []
            except Exception:
                merged = str(snap.get("_pdf_merged_for_structure") or "").strip()
                tables = self._extract_tables_from_text(merged) if merged else []

        if not tables:
            return ToolResponse.success(
                text="未能从 PDF 中提取到表格。表格可能为图片格式或 PDF 文本提取不完整。"
            )

        matched = self._find_table(tables, ref)
        if not matched:
            available = [clip_utf8(t.get("label", f"表{i+1}"), 600) for i, t in enumerate(tables[:8])]
            return ToolResponse.success(
                text=clip_utf8(f"未找到匹配 '{ref}' 的表格。可用表格：{', '.join(available)}", TOOL_ITEM_BYTES)
            )

        result = f"## {clip_utf8(matched['label'], 600)}\n\n{matched['content']}"
        return ToolResponse.success(text=clip_utf8(result, TOOL_ITEM_BYTES))

    @staticmethod
    def _parse_table_blocks(md: str) -> list[dict[str, Any]]:
        tables: list[dict[str, Any]] = []
        rows: list[str] = []
        caption = ""

        def flush():
            nonlocal rows, caption
            if len(rows) >= 2:
                tables.append({"label": caption or f"表{len(tables) + 1}", "content": "\n".join(rows)})
            rows = []
            caption = ""

        for line in (md or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("|") and stripped.count("|") >= 2:
                rows.append(stripped)
            else:
                if rows:
                    flush()
                if re.match(r"^(?:#{1,6}\s*|Table\s*\d|Tab\.\s*\d|表\s*\d)", stripped, re.I):
                    caption = stripped.lstrip("# ")
                elif stripped:
                    caption = ""
        flush()
        return tables

    @staticmethod
    def _extract_tables_from_text(text: str) -> list[dict[str, Any]]:
        return ReaderTableTool._parse_table_blocks(text)

    @staticmethod
    def _find_table(tables: list[dict[str, Any]], ref: str) -> dict[str, Any] | None:
        ref_lower = ref.strip().lower()
        # Exact number match: "3" → "Table 3", "Tab. 3", "表3"
        if ref_lower.isdigit():
            patterns = [
                rf"\b(?:table|tab\.?|表)\s*{ref_lower}\b",
                rf"^{ref_lower}[\.\)]",
            ]
            for pat in patterns:
                for t in tables:
                    if re.search(pat, t["label"], re.I):
                        return t
                for t in tables:
                    if re.search(pat, t["content"], re.I):
                        return t

        # Keyword match in label or first rows
        for t in tables:
            blob = (t["label"] + " " + t["content"][:500]).lower()
            if ref_lower in blob:
                return t
        return None
