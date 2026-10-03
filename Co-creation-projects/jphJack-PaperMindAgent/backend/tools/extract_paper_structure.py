"""步骤2 单篇论文结构化抽取工具：核心主干

职责：
- 调用 DeepSeek 通过 function calling 强制 JSON 输出，抽取固定 schema 字段；
- 长论文按章节分块抽取后合并去重；
- 字段完整性校验 + 针对性补抽（只补缺失字段，不重跑整篇）；
- limitations 字段单独强调须真实可溯源；
- 自校验输出各字段置信度，低于阈值标记需复核；
- 结果独立缓存（每篇一个 JSON + 追加 papers.jsonl），失败可单独重跑。
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

from backend.config import settings
from backend.llm.client import DeepSeekClient
from backend.llm.json_utils import parse_json_safe, validate_required_fields
from backend.tools.base import Tool
from backend.tools.extract_schema import (
    EXTRACT_FIELDS,
    EXTRACT_FUNCTION_SCHEMA,
    build_extraction_prompt,
)

logger = logging.getLogger(__name__)

# 长论文分块阈值（章节总字符数超过此值则分块抽取）
CHUNK_CHAR_THRESHOLD = 20000

# 模块级懒加载单例客户端
_client: Optional[DeepSeekClient] = None


def _get_client() -> DeepSeekClient:
    """懒加载 DeepSeekClient 单例，首次调用时创建"""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client


# --------------------------------------------------------------------------- #
# 内部辅助函数
# --------------------------------------------------------------------------- #

def _normalize_field_source(val: Any) -> Optional[dict]:
    """将任意值归一化为 FieldSource dict {value, source_sections, confidence}

    支持三种输入：
    - 字符串：包装为低置信度 FieldSource；
    - dict：补全缺失键、裁剪 confidence 到 [0,1]；
    - 其他：返回 None。
    """
    if val is None:
        return None
    if isinstance(val, str):
        if not val.strip():
            return None
        return {"value": val, "source_sections": [], "confidence": 0.5}
    if isinstance(val, dict):
        value = val.get("value", "")
        if value is None:
            value = ""
        value = str(value).strip()
        if not value:
            return None
        source = val.get("source_sections", [])
        if isinstance(source, str):
            source = [source]
        elif not isinstance(source, list):
            source = []
        else:
            source = [str(s) for s in source]
        try:
            conf = float(val.get("confidence", 0.8))
        except (TypeError, ValueError):
            conf = 0.8
        conf = max(0.0, min(1.0, conf))
        return {"value": value, "source_sections": source, "confidence": conf}
    return None


def _normalize_record(data: Any) -> dict:
    """将模型输出的 dict 归一化为标准 record（所有字段为 FieldSource dict）"""
    if not isinstance(data, dict):
        return {}
    record: dict[str, Any] = {}
    for field in EXTRACT_FIELDS:
        fs = _normalize_field_source(data.get(field))
        if fs is not None:
            record[field] = fs
    return record


def _chunk_sections(
    sections: list[dict], max_chars: int = CHUNK_CHAR_THRESHOLD
) -> list[list[dict]]:
    """按章节分块，每块总字符数不超过 max_chars（不拆分单个章节）"""
    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0
    for sec in sections:
        sec_chars = len(sec.get("content", ""))
        # 当前块非空且加入后会超限 → 先落盘当前块
        if current and current_chars + sec_chars > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(sec)
        current_chars += sec_chars
    if current:
        chunks.append(current)
    return chunks


def _merge_records(records: list[dict]) -> dict:
    """合并多次抽取结果：每字段取置信度最高的 value，source_sections 去重合并"""
    merged: dict[str, Any] = {}
    for field in EXTRACT_FIELDS:
        candidates: list[dict] = []
        for r in records:
            fs = r.get(field)
            if fs and isinstance(fs, dict) and fs.get("value"):
                candidates.append(fs)
        if not candidates:
            continue
        # 取置信度最高的候选作为 value
        best = max(candidates, key=lambda x: x.get("confidence", 0.0))
        # 合并所有 source_sections 并去重（保序）
        all_sources: list[str] = []
        seen: set[str] = set()
        for c in candidates:
            for s in c.get("source_sections", []):
                if s not in seen:
                    seen.add(s)
                    all_sources.append(s)
        merged[field] = {
            "value": best["value"],
            "source_sections": all_sources,
            "confidence": best.get("confidence", 0.8),
        }
    return merged


async def _call_extract(
    client: DeepSeekClient, parsed_paper: dict, focus_fields: Optional[list[str]] = None
) -> dict:
    """单次调用模型抽取字段，返回归一化后的 record dict

    Args:
        client: DeepSeek 客户端
        parsed_paper: 已解析论文 dict
        focus_fields: 若指定，则只补抽这些缺失字段（针对性补抽）
    """
    prompt = build_extraction_prompt(parsed_paper)
    if focus_fields:
        prompt = (
            f"前一次抽取缺失了以下字段：{', '.join(focus_fields)}。\n"
            f"请重点从原文中补抽这些字段，其他字段可留空。\n\n{prompt}"
        )

    messages = [
        {
            "role": "system",
            "content": (
                "你是论文结构化抽取助手。严格通过函数调用输出 JSON，"
                "每个字段含 value/source_sections/confidence。"
                "limitations 必须真实可溯源，严禁臆造。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    # 强制调用指定函数以获得结构化 JSON 输出
    response = await client.chat(
        messages=messages,
        tools=[EXTRACT_FUNCTION_SCHEMA],
        tool_choice={
            "type": "function",
            "function": {"name": "extract_paper_fields"},
        },
    )

    msg = response.choices[0].message
    data: Any = None

    # 优先从 tool_calls 提取参数
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        try:
            data = parse_json_safe(tool_calls[0].function.arguments)
        except Exception:
            data = None

    # 降级：从 content 解析
    if data is None and msg.content:
        data = parse_json_safe(msg.content)

    if data is None:
        logger.warning("模型未返回可解析的 JSON，返回空 record")
        return {}

    return _normalize_record(data)


# --------------------------------------------------------------------------- #
# 核心抽取函数
# --------------------------------------------------------------------------- #

async def extract_paper_structure(paper_path: str, parsed_paper: dict) -> dict:
    """从已解析论文中抽取结构化字段

    Args:
        paper_path: 论文文件路径
        parsed_paper: 已解析论文 dict，含 path/title/sections:[{heading,content,figure_captions}]

    Returns:
        dict，可序列化为 PaperRecord。所有 EXTRACT_FIELDS 字段为 FieldSource dict。
    """
    client = _get_client()
    sections = parsed_paper.get("sections", [])
    total_chars = sum(len(s.get("content", "")) for s in sections)

    if total_chars > CHUNK_CHAR_THRESHOLD:
        # 长论文：按章节分块抽取后合并去重
        logger.info(
            "论文 %s 总字符数 %d 超过阈值 %d，按章节分块抽取",
            paper_path,
            total_chars,
            CHUNK_CHAR_THRESHOLD,
        )
        chunks = _chunk_sections(sections, CHUNK_CHAR_THRESHOLD)
        chunk_records: list[dict] = []
        for idx, chunk in enumerate(chunks):
            chunk_paper = {**parsed_paper, "sections": chunk}
            logger.debug("抽取分块 %d/%d（%d 章节）", idx + 1, len(chunks), len(chunk))
            rec = await _call_extract(client, chunk_paper)
            if rec:
                chunk_records.append(rec)
        record = _merge_records(chunk_records) if chunk_records else {}
    else:
        # 短论文：一次性抽取
        record = await _call_extract(client, parsed_paper)

    # 字段完整性校验：检查必填字段是否齐全
    missing = validate_required_fields(record, EXTRACT_FIELDS)
    if missing:
        logger.info("首次抽取缺失字段 %s，触发针对性补抽", missing)
        supplement = await _call_extract(client, parsed_paper, focus_fields=missing)
        for field in missing:
            fs = supplement.get(field)
            if fs:
                record[field] = fs

    # 确保 path 字段（PaperRecord 顶层字段，非 FieldSource）
    record["path"] = paper_path
    # 若 title 缺失，用 parsed_paper 的 title 兜底
    if "title" not in record or not record["title"].get("value"):
        fallback_title = parsed_paper.get("title", "")
        if fallback_title:
            record["title"] = {
                "value": fallback_title,
                "source_sections": [],
                "confidence": 0.6,
            }

    return record


# --------------------------------------------------------------------------- #
# 自校验函数
# --------------------------------------------------------------------------- #

async def self_check(
    record: dict, parsed_paper: dict, client: DeepSeekClient
) -> dict:
    """让模型对照原文检查各字段，输出每字段置信度

    Args:
        record: 抽取结果 dict
        parsed_paper: 已解析论文 dict
        client: DeepSeek 客户端（由调用方传入）

    Returns:
        {
            "record": record,
            "field_confidences": {字段名: 置信度},
            "overall_confidence": float,
            "needs_review": [低于阈值的字段名]
        }
    """
    # 拼接原文节选（截断避免超长）
    sections = parsed_paper.get("sections", [])
    sections_text = "\n\n".join(
        f"## {s.get('heading', '')}\n{s.get('content', '')[:3000]}"
        for s in sections
    )[:15000]

    record_text = json.dumps(record, ensure_ascii=False, indent=2, default=str)
    fields_list = "、".join(EXTRACT_FIELDS)

    prompt = f"""请对照论文原文，检查以下结构化抽取记录的每个字段是否准确。

论文原文（节选）：
{sections_text}

抽取记录：
{record_text}

检查要求：
1. 对以下每个字段输出 0-1 的置信度：{fields_list}
2. 输出整体置信度 overall_confidence（所有字段的加权平均，limitations 权重更高）。
3. 严格以 JSON 输出，格式如下：
{{
  "field_confidences": {{
    "title": 0.95,
    "task_problem": 0.9,
    "method": 0.85,
    "key_contributions": 0.8,
    "datasets": 0.9,
    "metrics": 0.85,
    "results": 0.8,
    "limitations": 0.7,
    "future_work": 0.6
  }},
  "overall_confidence": 0.82,
  "issues": ["limitations 字段描述过于模糊，原文未明确提及"]
}}
"""

    messages = [
        {"role": "system", "content": "你是论文抽取质量审核员，负责对照原文核查字段准确性。"},
        {"role": "user", "content": prompt},
    ]

    response = await client.chat(messages=messages)
    content = response.choices[0].message.content or ""
    result = parse_json_safe(content)

    if not isinstance(result, dict):
        logger.warning("自校验未返回有效 JSON，降级为空结果")
        result = {}

    field_confidences: dict[str, float] = {}
    raw_confidences = result.get("field_confidences", {})
    if isinstance(raw_confidences, dict):
        for f in EXTRACT_FIELDS:
            try:
                field_confidences[f] = float(raw_confidences.get(f, 0.0))
            except (TypeError, ValueError):
                field_confidences[f] = 0.0

    try:
        overall = float(result.get("overall_confidence", 0.0))
    except (TypeError, ValueError):
        overall = 0.0
    overall = max(0.0, min(1.0, overall))

    # 低于阈值的字段标记需复核
    threshold = settings.CONFIDENCE_THRESHOLD
    needs_review = [
        f for f in EXTRACT_FIELDS if field_confidences.get(f, 0.0) < threshold
    ]

    return {
        "record": record,
        "field_confidences": field_confidences,
        "overall_confidence": overall,
        "needs_review": needs_review,
        "issues": result.get("issues", []),
    }


# --------------------------------------------------------------------------- #
# 缓存函数
# --------------------------------------------------------------------------- #

def _resolve_cache_dir(cache_dir: Optional[str] = None) -> Path:
    """解析缓存目录，默认使用 settings.CACHE_DIR"""
    if cache_dir:
        p = Path(cache_dir)
    else:
        p = settings.CACHE_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _paper_hash(paper_path: str) -> str:
    """以论文路径生成 hash，作为缓存文件名（向后兼容旧缓存）"""
    return hashlib.md5(paper_path.encode("utf-8")).hexdigest()[:16]


def _cache_file_path(paper_id: Optional[str], paper_path: str, cache_dir: Optional[Path] = None) -> Path:
    """解析缓存文件路径，优先用 paper_id，否则回退到路径哈希"""
    base = cache_dir or _resolve_cache_dir()
    papers_dir = base / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    key = paper_id if paper_id else _paper_hash(paper_path)
    return papers_dir / f"{key}.json"


def save_record(record: dict, cache_dir: Optional[str] = None, paper_id: Optional[str] = None) -> Path:
    """保存单篇抽取结果到独立 JSON 文件，并追加写入 papers.jsonl

    Args:
        record: 抽取结果 dict
        cache_dir: 缓存目录，默认 settings.CACHE_DIR
        paper_id: 论文内容哈希，优先用作缓存键

    Returns:
        独立 JSON 文件路径
    """
    base = _resolve_cache_dir(cache_dir)
    paper_path = record.get("path", "")
    file_path = _cache_file_path(paper_id, paper_path, base)

    # 独立 JSON 文件（可单独重跑）
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)

    # 追加写入 papers.jsonl（一行一篇）
    jsonl_path = base / "papers.jsonl"
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    logger.info("抽取结果已缓存至 %s", file_path)
    return file_path


def load_record(paper_path: str, cache_dir: Optional[str] = None, paper_id: Optional[str] = None) -> Optional[dict]:
    """从缓存加载单篇抽取结果，不存在返回 None

    Args:
        paper_path: 论文文件路径
        cache_dir: 缓存目录，默认 settings.CACHE_DIR
        paper_id: 论文内容哈希，优先用作缓存键

    Returns:
        抽取结果 dict，或 None
    """
    base = _resolve_cache_dir(cache_dir)
    file_path = _cache_file_path(paper_id, paper_path, base)
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("读取缓存 %s 失败: %s", file_path, exc)
        return None


# --------------------------------------------------------------------------- #
# 工具定义
# --------------------------------------------------------------------------- #

_PARAMETERS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "paper_path": {"type": "string"},
        "parsed_paper": {
            "type": "object",
            "description": "已解析论文，含 path/title/sections",
        },
    },
    "required": ["paper_path", "parsed_paper"],
}

extract_paper_structure_tool = Tool(
    name="extract_paper_structure",
    description=(
        "从已解析论文中抽取结构化字段"
        "（title/task_problem/method/key_contributions/datasets/metrics/"
        "results/limitations/future_work），"
        "每个字段含来源章节与置信度。长论文自动分块抽取后合并。"
    ),
    parameters=_PARAMETERS_SCHEMA,
    func=extract_paper_structure,
)
