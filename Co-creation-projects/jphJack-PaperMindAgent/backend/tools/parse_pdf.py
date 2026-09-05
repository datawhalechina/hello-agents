"""步骤1 PDF 解析工具：用 PyMuPDF 解析 PDF，保留章节结构"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.tools.base import Tool

logger = logging.getLogger(__name__)


# ---------- 启发式规则 ----------

# 常见章节标题模式（英文 + 中文），用于辅助加粗短行的标题判定
_HEADING_PATTERN = re.compile(
    r"^("
    r"abstract|introduction|related\s+work|background|preliminar"
    r"|method|methods|methodology|approach|model|framework"
    r"|experiment|experiments|experimental|evaluation|results?"
    r"|discussion|conclusion|conclusions|references|acknowledg"
    r"|appendix|contribution"
    r"|摘要|引言|前言|相关工作|背景|方法|实验|结果|讨论|结论|参考文献|致谢|附录"
    r"|\d+\.?\s|\d+\.\d+\.?\s"
    r")",
    re.IGNORECASE,
)

# 图表标题模式：Figure X / Fig. X / 表 X / Table X 开头
_FIGURE_PATTERN = re.compile(
    r"^((figure|fig)\.?\s+\d+|表\s*\d+|table\s+\d+)",
    re.IGNORECASE,
)

# 句末标点：用于判断段落是否结束
_SENTENCE_END = set(".!?。！？：；")

# 页眉页脚判定阈值：短行长度上限
_HEADER_FOOTER_MAX_LEN = 80


# ---------- 解析辅助函数 ----------

def _extract_title(doc, first_page_lines: list[dict]) -> str:
    """从元数据或首页大字号文本提取论文标题"""
    meta = doc.metadata or {}
    meta_title = (meta.get("title") or "").strip()
    # 元数据标题有效且非占位符
    if meta_title and len(meta_title) > 5 and "untitled" not in meta_title.lower():
        return meta_title
    # 退化：取首页最大字号文本作为标题（标题可能跨多行）
    if first_page_lines:
        max_size = max(ln["size"] for ln in first_page_lines)
        title_lines = [
            ln["text"]
            for ln in first_page_lines
            if ln["size"] >= max_size * 0.9
        ]
        if title_lines:
            return " ".join(title_lines[:3]).strip()
    return ""


def _is_heading(line: dict, body_size: float) -> bool:
    """启发式判断是否为章节标题：字号较大或加粗的短行"""
    text = line["text"]
    size = line["size"]
    # 过长的不视为标题
    if len(text) > 120:
        return False
    # 字号明显大于正文 → 标题
    if size > body_size * 1.15:
        return True
    # 加粗且字号不小于正文 → 结合模式/大小写判定
    if line["bold"] and size >= body_size * 0.95:
        if _HEADING_PATTERN.match(text):
            return True
        if text.isupper() and len(text) < 80:
            return True
    return False


def _clean_lines_to_content(lines: list[dict]) -> tuple[str, list[str]]:
    """文本清洗：修复断句（行尾无标点则合并下一行）、合并跨页段落，提取图表标题。

    Returns:
        (正文, 图表标题列表)
    """
    figure_captions: list[str] = []
    paragraphs: list[str] = []
    buf = ""

    for ln in lines:
        text = ln["text"]
        # 图表标题独立提取，不并入正文
        if _FIGURE_PATTERN.match(text):
            figure_captions.append(text)
            # 图表标题前若有未结束段落，先落段
            if buf:
                paragraphs.append(buf)
                buf = ""
            continue

        if not buf:
            buf = text
        else:
            # 上一行以句末标点结尾 → 起新段；否则合并（修复断句、跨页段落）
            if buf[-1] in _SENTENCE_END:
                paragraphs.append(buf)
                buf = text
            else:
                # 英文之间补空格，中文直接连接
                if buf[-1].isascii() and text[:1].isascii():
                    buf = f"{buf} {text}"
                else:
                    buf = f"{buf}{text}"
    if buf:
        paragraphs.append(buf)

    content = "\n\n".join(paragraphs)
    return content, figure_captions


def _parse_pdf_sync(file_path: str) -> dict:
    """同步解析 PDF（在线程池中执行）"""
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    try:
        # 1. 收集所有行及其字体信息
        all_lines: list[dict] = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                # 只处理文本块（type 0）
                if block.get("type", 0) != 0:
                    continue
                for line in block.get("lines", []):
                    line_text = ""
                    max_size = 0.0
                    is_bold = False
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        max_size = max(max_size, span.get("size", 0.0))
                        # bold 标志位为 bit4（值 16）
                        if span.get("flags", 0) & 16:
                            is_bold = True
                    line_text = line_text.strip()
                    if line_text:
                        all_lines.append(
                            {
                                "text": line_text,
                                "size": max_size,
                                "bold": is_bold,
                                "page": page_idx,
                            }
                        )

        if not all_lines:
            return {"path": file_path, "title": "", "sections": []}

        page_count = max(ln["page"] for ln in all_lines) + 1

        # 2. 检测页眉页脚：跨页重复出现的短行
        short_line_counter = Counter()
        for ln in all_lines:
            if len(ln["text"]) <= _HEADER_FOOTER_MAX_LEN:
                short_line_counter[ln["text"]] += 1
        header_footer_set = {
            text
            for text, cnt in short_line_counter.items()
            if cnt >= max(3, page_count * 0.3)
        }

        # 过滤页眉页脚
        lines = [ln for ln in all_lines if ln["text"] not in header_footer_set]
        if not lines:
            lines = all_lines  # 退化：保留全部

        # 3. 计算正文字号（中位数）
        sizes = sorted(ln["size"] for ln in lines)
        body_size = sizes[len(sizes) // 2] if sizes else 12.0

        # 4. 提取标题
        first_page_lines = [ln for ln in lines if ln["page"] == 0]
        title = _extract_title(doc, first_page_lines)

        # 5. 按章节标题分组
        sections: list[dict] = []
        cur_heading = ""
        cur_lines: list[dict] = []

        for ln in lines:
            if _is_heading(ln, body_size):
                # 保存上一章节
                if cur_lines or cur_heading:
                    sections.append({"heading": cur_heading, "lines": cur_lines})
                cur_heading = ln["text"]
                cur_lines = []
            else:
                cur_lines.append(ln)
        # 末尾章节
        if cur_lines or cur_heading:
            sections.append({"heading": cur_heading, "lines": cur_lines})

        # 无标题识别到则整体作为一个默认章节
        if not sections:
            sections = [{"heading": "", "lines": lines}]

        # 6. 文本清洗 + 图表标题提取
        result_sections = []
        for sec in sections:
            content, figure_captions = _clean_lines_to_content(sec["lines"])
            result_sections.append(
                {
                    "heading": sec["heading"],
                    "content": content,
                    "figure_captions": figure_captions,
                }
            )

        return {
            "path": file_path,
            "title": title,
            "sections": result_sections,
        }
    finally:
        doc.close()


# ---------- 异步工具函数 ----------

async def parse_pdf(file_path: str) -> dict:
    """解析 PDF 文件，保留章节结构。

    用 PyMuPDF 解析，识别章节标题、清洗文本、提取图表标题。
    失败时返回 {"error": "..."} 不抛异常。
    """
    try:
        return await asyncio.to_thread(_parse_pdf_sync, file_path)
    except Exception as e:
        return {"error": f"PDF 解析失败: {e}", "path": file_path}


# ---------- 缓存函数 ----------

def _parsed_cache_path(paper_id: str) -> Path:
    """解析结果缓存路径：data/cache/parsed/{paper_id}.json"""
    parsed_dir = settings.CACHE_DIR / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    return parsed_dir / f"{paper_id}.json"


def save_parsed(paper_id: str, parsed: dict) -> Path:
    """保存解析结果到缓存

    Args:
        paper_id: 论文内容哈希
        parsed: parse_pdf 返回的解析结果 dict

    Returns:
        缓存文件路径
    """
    cache_path = _parsed_cache_path(paper_id)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2, default=str)
    logger.info("解析结果已缓存至 %s", cache_path)
    return cache_path


def load_parsed(paper_id: str) -> Optional[dict]:
    """从缓存加载解析结果，不存在返回 None"""
    cache_path = _parsed_cache_path(paper_id)
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("读取解析缓存 %s 失败: %s", cache_path, exc)
        return None


# ---------- Tool 定义 ----------

_PARAMETERS = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "PDF 文件绝对路径",
        }
    },
    "required": ["file_path"],
}

parse_pdf_tool = Tool(
    name="parse_pdf",
    description=(
        "步骤1：解析 PDF 论文，保留章节结构。"
        "输入 PDF 文件路径，输出 {path, title, sections: [{heading, content, figure_captions}]}。"
    ),
    parameters=_PARAMETERS,
    func=parse_pdf,
)
