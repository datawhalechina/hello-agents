"""Dataset metadata extraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DataContextSummary:
    data_path: Path
    absolute_path: Path
    columns: list[str]
    dtypes: str
    shape: tuple[int, int]
    head_markdown: str
    sample_size_warning: str
    small_sample_warning: bool
    context_text: str
    input_kind: str = "tabular"
    background_literature_context: str = ""
    parsed_document_path: Path | None = None
    pdf_small_table_mode: bool = False
    candidate_table_count: int = 0
    selected_table_id: str = ""
    pdf_multi_table_mode: bool = False
    candidate_table_summaries_text: str = ""


def _read_dataframe(data_path: Path) -> pd.DataFrame:
    suffix = data_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(data_path)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(data_path)
    raise ValueError(f"Unsupported data file format: {data_path.suffix}")


def _normalize_background_text(text: str, *, limit: int = 2000) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    return normalized[:limit]


def _load_parsed_document_context(parsed_document_path: Path | None) -> tuple[str, Path | None, dict[str, object]]:
    if parsed_document_path is None or not parsed_document_path.exists():
        return "", None, {}

    try:
        payload = json.loads(parsed_document_path.read_text(encoding="utf-8"))
    except Exception:
        return "", parsed_document_path, {}

    if not isinstance(payload, dict):
        return "", parsed_document_path, {}

    background = payload.get("background_literature_context", "")
    if not background:
        background = payload.get("abstract", "")
    if not background:
        background = payload.get("text_excerpt", "")
    return _normalize_background_text(str(background or "")), parsed_document_path, payload


def _extract_selected_table_metadata(
    parsed_payload: dict[str, object],
) -> tuple[int, str, tuple[int, int] | None, tuple[str, ...], tuple[str, ...], bool]:
    candidate_tables = parsed_payload.get("candidate_tables", [])
    selected_table_id = str(parsed_payload.get("selected_table_id", "") or "")
    pdf_multi_table_mode = bool(parsed_payload.get("pdf_multi_table_mode", False))
    if not isinstance(candidate_tables, list):
        return 0, selected_table_id, None, (), (), pdf_multi_table_mode

    selected_shape: tuple[int, int] | None = None
    selected_headers: tuple[str, ...] = ()
    selected_numeric_columns: tuple[str, ...] = ()
    for candidate in candidate_tables:
        if not isinstance(candidate, dict) or str(candidate.get("table_id", "") or "") != selected_table_id:
            continue
        shape = candidate.get("shape", [])
        if isinstance(shape, list) and len(shape) == 2:
            try:
                selected_shape = (int(shape[0]), int(shape[1]))
            except (TypeError, ValueError):
                selected_shape = None
        headers = candidate.get("headers", [])
        numeric_columns = candidate.get("numeric_columns", [])
        if isinstance(headers, list):
            selected_headers = tuple(str(item) for item in headers)
        if isinstance(numeric_columns, list):
            selected_numeric_columns = tuple(str(item) for item in numeric_columns)
        break
    return (
        len(candidate_tables),
        selected_table_id,
        selected_shape,
        selected_headers,
        selected_numeric_columns,
        pdf_multi_table_mode,
    )


def _format_candidate_table_summaries(parsed_payload: dict[str, object], *, limit: int = 5) -> str:
    candidate_tables = parsed_payload.get("candidate_table_summaries", parsed_payload.get("candidate_tables", []))
    if not isinstance(candidate_tables, list) or not candidate_tables:
        return ""

    lines: list[str] = []
    for candidate in candidate_tables[:limit]:
        if not isinstance(candidate, dict):
            continue
        table_id = str(candidate.get("table_id", "") or "unknown")
        page_number = candidate.get("page_number", "?")
        shape = candidate.get("shape", [])
        headers = candidate.get("headers", [])
        numeric_columns = candidate.get("numeric_columns", [])
        content_hint = str(candidate.get("content_hint", "") or "").strip()
        selected = bool(candidate.get("selected_as_primary", False))
        shape_text = (
            f"{shape[0]} x {shape[1]}"
            if isinstance(shape, list) and len(shape) == 2
            else "unknown"
        )
        header_text = ", ".join(str(item) for item in headers[:6]) if isinstance(headers, list) else ""
        numeric_text = ", ".join(str(item) for item in numeric_columns[:6]) if isinstance(numeric_columns, list) else ""
        line = (
            f"- {table_id} | page={page_number} | shape={shape_text} | "
            f"headers={header_text or 'none'} | numeric_columns={numeric_text or 'none'} | "
            f"selected_as_primary={selected}"
        )
        if content_hint:
            line += f" | content_hint={content_hint}"
        lines.append(line)
    return "\n".join(lines)


def _is_pdf_small_table(
    *,
    input_kind: str,
    selected_shape: tuple[int, int] | None,
    columns: list[str],
    selected_numeric_columns: tuple[str, ...],
) -> bool:
    if input_kind != "pdf" or selected_shape is None:
        return False
    rows, cols = selected_shape
    has_numeric = bool(selected_numeric_columns)
    has_text_label = len(columns) > len(selected_numeric_columns)
    return rows <= 30 and cols <= 10 and has_numeric and has_text_label


def build_data_context(
    data_path: str | Path,
    *,
    input_kind: str = "tabular",
    parsed_document_path: str | Path | None = None,
) -> DataContextSummary:
    """Build a compact metadata-first prompt context for a local dataset."""

    path = Path(data_path)
    try:
        normalized_path = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        normalized_path = path

    df = _read_dataframe(path)
    absolute_path = path.resolve()
    columns = df.columns.tolist()
    dtypes = df.dtypes.to_string()
    shape = df.shape
    head_markdown = df.head().to_markdown(index=False)

    sample_size_warning = ""
    small_sample_warning = shape[0] < 30
    if small_sample_warning:
        sample_size_warning = (
            "WARNING / 红色警告：当前样本量极小 (N<30)，强烈建议优先考虑非参数检验"
            "（如 Mann-Whitney U 检验），并对正态分布假设保持高度谨慎。"
        )

    literature_context, resolved_parsed_document, parsed_payload = _load_parsed_document_context(
        Path(parsed_document_path) if parsed_document_path is not None else None
    )
    (
        candidate_table_count,
        selected_table_id,
        selected_table_shape,
        _selected_table_headers,
        selected_table_numeric_columns,
        pdf_multi_table_mode,
    ) = _extract_selected_table_metadata(parsed_payload)
    candidate_table_summaries_text = _format_candidate_table_summaries(parsed_payload)
    pdf_small_table_mode = _is_pdf_small_table(
        input_kind=input_kind,
        selected_shape=selected_table_shape,
        columns=columns,
        selected_numeric_columns=selected_table_numeric_columns,
    )

    context_lines = [
        f"数据文件相对路径: {normalized_path.as_posix()}",
        f"数据文件绝对路径: {absolute_path.as_posix()}",
        f"输入类型: {input_kind}",
        f"数据列名: {columns}",
        f"数据类型:\n{dtypes}",
        f"数据规模: {shape}",
    ]
    if sample_size_warning:
        context_lines.append(sample_size_warning)
    if literature_context:
        context_lines.append(
            "<Background_Literature_Context>\n"
            f"{literature_context}\n"
            "</Background_Literature_Context>"
        )
    if candidate_table_summaries_text:
        context_lines.append(
            "<PDF_Candidate_Tables_Context>\n"
            f"candidate_table_count={candidate_table_count}\n"
            f"selected_table_id={selected_table_id or 'unknown'}\n"
            f"pdf_multi_table_mode={pdf_multi_table_mode}\n"
            f"{candidate_table_summaries_text}\n"
            "</PDF_Candidate_Tables_Context>"
        )
    if pdf_small_table_mode:
        context_lines.append(
            "<PDF_Small_Table_Mode>\n"
            "This is a PDF-derived small results table, often representing model comparison or compact experimental outcomes.\n"
            "Use a lightweight template: descriptive statistics, ranking, bootstrap confidence intervals, cautious correlation analysis, optional top-vs-bottom descriptive comparisons, and 2-4 light figures.\n"
            "The selected primary table is the only table for formal quantitative analysis. Other candidate tables are contextual evidence only and must not trigger extra significance testing by default.\n"
            "Do not run one-sample tests, do not treat distinct models as repeated observations from one population, and do not run group significance tests without repeated measurements or explicit experimental groups.\n"
            "</PDF_Small_Table_Mode>"
        )
    context_lines.append(f"前 5 行样本:\n{head_markdown}")
    context_text = "\n".join(context_lines).strip() + "\n"

    return DataContextSummary(
        data_path=normalized_path,
        absolute_path=absolute_path,
        columns=columns,
        dtypes=dtypes,
        shape=shape,
        head_markdown=head_markdown,
        sample_size_warning=sample_size_warning,
        small_sample_warning=small_sample_warning,
        context_text=context_text,
        input_kind=input_kind,
        background_literature_context=literature_context,
        parsed_document_path=resolved_parsed_document,
        pdf_small_table_mode=pdf_small_table_mode,
        candidate_table_count=candidate_table_count,
        selected_table_id=selected_table_id,
        pdf_multi_table_mode=pdf_multi_table_mode,
        candidate_table_summaries_text=candidate_table_summaries_text,
    )
