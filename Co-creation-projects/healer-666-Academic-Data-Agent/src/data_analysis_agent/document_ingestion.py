"""Input ingestion helpers for tabular files and PDF documents."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_TABULAR_SUFFIXES = frozenset({".csv", ".xls", ".xlsx"})
SUPPORTED_DOCUMENT_SUFFIXES = frozenset({".pdf"})


@dataclass(frozen=True)
class ExtractedTableRecord:
    table_id: str
    page_number: int
    csv_path: Path
    rows: int
    cols: int
    area: int
    headers: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    content_hint: str = ""
    selected_as_primary: bool = False


@dataclass(frozen=True)
class IngestionResult:
    input_kind: str
    status: str
    summary: str
    normalized_data_path: Path
    duration_ms: int
    log_path: Path | None = None
    parsed_document_path: Path | None = None
    extracted_table_paths: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()
    selected_table_id: str = ""
    background_literature_context: str = ""
    candidate_table_count: int = 0
    selected_table_shape: tuple[int, int] | None = None
    selected_table_headers: tuple[str, ...] = ()
    selected_table_numeric_columns: tuple[str, ...] = ()
    candidate_table_summaries: tuple[dict[str, Any], ...] = ()
    pdf_multi_table_mode: bool = False


@dataclass(frozen=True)
class PdfPreviewResult:
    source_pdf: Path
    background_literature_context: str
    candidate_tables: tuple[ExtractedTableRecord, ...]
    default_table_id: str = ""
    warnings: tuple[str, ...] = ()


def _elapsed_ms(start_time: float) -> int:
    return int(round((time.perf_counter() - start_time) * 1000))


def _normalize_header(header: Any, index: int) -> str:
    text = " ".join(str(header or "").split()).strip()
    if not text:
        return f"column_{index + 1}"
    return text


def _normalize_cell(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _extract_background_context(full_text: str, *, limit: int = 2000) -> str:
    normalized = re.sub(r"\s+", " ", str(full_text or "")).strip()
    if not normalized:
        return ""

    abstract_match = re.search(
        r"(?:^|\b)(abstract|摘要)\b[:：\s-]*(.+?)(?:\b(?:keywords|introduction|背景|方法|materials?|results?)\b|$)",
        normalized,
        flags=re.IGNORECASE,
    )
    if abstract_match:
        return abstract_match.group(2).strip()[:limit]
    return normalized[:limit]


def _coerce_numeric_columns(df: pd.DataFrame) -> tuple[str, ...]:
    numeric_columns: list[str] = []
    for column in df.columns:
        series = (
            df[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        converted = pd.to_numeric(series, errors="coerce")
        if converted.notna().any():
            numeric_columns.append(str(column))
    return tuple(numeric_columns)


def _build_content_hint(df: pd.DataFrame, *, max_columns: int = 4, max_rows: int = 2) -> str:
    preview_rows: list[str] = []
    limited_columns = list(df.columns[:max_columns])
    for _, row in df.head(max_rows).iterrows():
        values = []
        for column in limited_columns:
            value = " ".join(str(row[column] or "").split()).strip()
            if value:
                values.append(value)
        if values:
            preview_rows.append(" | ".join(values))
    return " || ".join(preview_rows)


def _table_to_dataframe(raw_table: list[list[Any]] | tuple[tuple[Any, ...], ...]) -> pd.DataFrame | None:
    rows = [list(row) for row in raw_table if any(str(cell or "").strip() for cell in row)]
    if len(rows) < 2:
        return None
    headers = [_normalize_header(value, index) for index, value in enumerate(rows[0])]
    data_rows = [
        [_normalize_cell(row[index] if index < len(row) else "") for index in range(len(headers))]
        for row in rows[1:]
    ]
    df = pd.DataFrame(data_rows, columns=headers)
    stripped = df.astype(str).apply(lambda column: column.str.strip())
    if df.empty or (stripped == "").all().all():
        return None
    return df


def _extract_pdf_payload(
    pdf_path: Path,
    *,
    max_pdf_pages: int,
    max_candidate_tables: int,
    extracted_tables_dir: Path,
    persist_csv: bool = True,
) -> tuple[str, list[ExtractedTableRecord]]:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError(
            "pdfplumber is not installed. Install project dependencies before using PDF ingestion."
        ) from exc

    extracted_tables_dir.mkdir(parents=True, exist_ok=True)
    page_texts: list[str] = []
    records: list[ExtractedTableRecord] = []
    table_counter = 1

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages[: max(1, max_pdf_pages)], start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_texts.append(page_text.strip())

            for raw_table in page.extract_tables() or []:
                if len(records) >= max(1, max_candidate_tables):
                    break
                df = _table_to_dataframe(raw_table)
                if df is None:
                    continue

                csv_path = extracted_tables_dir / f"table_{table_counter:02d}.csv"
                if persist_csv:
                    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                numeric_columns = _coerce_numeric_columns(df)
                records.append(
                    ExtractedTableRecord(
                        table_id=f"table_{table_counter:02d}",
                        page_number=page_index,
                        csv_path=csv_path.resolve() if persist_csv else csv_path,
                        rows=int(df.shape[0]),
                        cols=int(df.shape[1]),
                        area=int(df.shape[0] * df.shape[1]),
                        headers=tuple(str(column) for column in df.columns),
                        numeric_columns=numeric_columns,
                        content_hint=_build_content_hint(df),
                    )
                )
                table_counter += 1

            if len(records) >= max(1, max_candidate_tables):
                break

    return "\n\n".join(page_texts).strip(), records


def _select_primary_table(records: list[ExtractedTableRecord]) -> ExtractedTableRecord | None:
    eligible = [record for record in records if record.numeric_columns]
    if not eligible:
        return None
    return max(eligible, key=lambda record: (record.area, record.rows, record.cols, record.table_id))


def _serialize_candidate_tables(records: list[ExtractedTableRecord]) -> list[dict[str, Any]]:
    return [
        {
            "table_id": record.table_id,
            "page_number": record.page_number,
            "csv_path": record.csv_path.as_posix(),
            "shape": [record.rows, record.cols],
            "area": record.area,
            "headers": list(record.headers[:12]),
            "numeric_columns": list(record.numeric_columns),
            "content_hint": record.content_hint,
            "selected_as_primary": record.selected_as_primary,
        }
        for record in records
    ]


def _serialize_parsed_document(
    *,
    source_pdf: Path,
    background_literature_context: str,
    full_text_excerpt: str,
    selected_table_id: str,
    records: list[ExtractedTableRecord],
) -> dict[str, Any]:
    candidate_tables = _serialize_candidate_tables(records)
    return {
        "input_kind": "pdf",
        "pdf_multi_table_mode": True,
        "source_pdf": source_pdf.resolve().as_posix(),
        "background_literature_context": background_literature_context,
        "text_excerpt": full_text_excerpt,
        "selected_table_id": selected_table_id,
        "candidate_tables": candidate_tables,
        "candidate_table_summaries": candidate_tables,
    }


def preview_pdf_tables(
    data_path: str | Path,
    *,
    max_pdf_pages: int = 20,
    max_candidate_tables: int = 5,
) -> PdfPreviewResult:
    source_path = Path(data_path).resolve()
    if source_path.suffix.lower() not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise ValueError(f"Unsupported input file format: {source_path.suffix}")

    scratch_root = source_path.parent / ".pdf_preview_tmp"
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch_dir = Path(tempfile.mkdtemp(prefix="pdf_preview_", dir=scratch_root))
    try:
        full_text, records = _extract_pdf_payload(
            source_path,
            max_pdf_pages=max_pdf_pages,
            max_candidate_tables=max_candidate_tables,
            extracted_tables_dir=scratch_dir,
            persist_csv=False,
        )
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)

    default_record = _select_primary_table(records)
    warnings: list[str] = []
    if records:
        warnings.append("系统将以主表做定量分析，并结合其他候选表与文献背景生成综合报告。")
    else:
        warnings.append("当前 PDF 未提取到可用结构化表格。")

    return PdfPreviewResult(
        source_pdf=source_path,
        background_literature_context=_extract_background_context(full_text),
        candidate_tables=tuple(records),
        default_table_id=default_record.table_id if default_record is not None else "",
        warnings=tuple(warnings),
    )


def ingest_input_document(
    data_path: str | Path,
    *,
    run_dir: str | Path,
    data_dir: str | Path,
    logs_dir: str | Path,
    mode: str = "auto",
    max_pdf_pages: int = 20,
    max_candidate_tables: int = 5,
    selected_table_id: str | None = None,
) -> IngestionResult:
    started_at = time.perf_counter()
    source_path = Path(data_path).resolve()
    data_dir = Path(data_dir)
    logs_dir = Path(logs_dir)
    normalized_mode = str(mode or "auto").strip().lower()
    if normalized_mode not in {"auto", "text_only", "vision_fallback"}:
        raise ValueError(f"Unsupported document_ingestion_mode: {mode}")

    log_path = logs_dir / "document_ingestion.json"
    if source_path.suffix.lower() in SUPPORTED_TABULAR_SUFFIXES:
        result = IngestionResult(
            input_kind="tabular",
            status="not_needed",
            summary="输入文件已经是结构化表格，跳过文档解析阶段。",
            normalized_data_path=source_path,
            duration_ms=_elapsed_ms(started_at),
            log_path=log_path,
            candidate_table_count=0,
            pdf_multi_table_mode=False,
        )
        payload = {
            "input_kind": result.input_kind,
            "status": result.status,
            "summary": result.summary,
            "normalized_data_path": result.normalized_data_path.as_posix(),
            "duration_ms": result.duration_ms,
            "candidate_table_count": 0,
            "pdf_multi_table_mode": False,
            "mode": normalized_mode,
        }
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    if source_path.suffix.lower() not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise ValueError(f"Unsupported input file format: {source_path.suffix}")

    if normalized_mode == "vision_fallback":
        raise ValueError("V1 暂不支持 vision_fallback，请先使用文本型 PDF 或手动裁剪目标表格。")

    extracted_tables_dir = data_dir / "extracted_tables"
    cleaned_data_path = (data_dir / "cleaned_data.csv").resolve()
    parsed_document_path = (data_dir / "parsed_document.json").resolve()

    full_text, records = _extract_pdf_payload(
        source_path,
        max_pdf_pages=max_pdf_pages,
        max_candidate_tables=max_candidate_tables,
        extracted_tables_dir=extracted_tables_dir,
    )
    background_literature_context = _extract_background_context(full_text)
    requested_table_id = str(selected_table_id or "").strip()
    requested_record = None
    if requested_table_id:
        requested_record = next((record for record in records if record.table_id == requested_table_id), None)
        if requested_record is None:
            raise ValueError(
                f"Selected table_id '{requested_table_id}' was not found in the extracted candidate tables."
            )
        if not requested_record.numeric_columns:
            raise ValueError(
                f"Selected table_id '{requested_table_id}' does not contain any numeric columns and cannot be analyzed."
            )
    primary_record = requested_record or _select_primary_table(records)
    warnings: list[str] = []

    if primary_record is None:
        summary = (
            "PDF 解析失败：未提取到满足主表路由规则的结构化表格。"
            "V1 暂不支持复杂多表路由或扫描件恢复，请手动裁剪 PDF 或改上传目标表格。"
        )
        parsed_payload = _serialize_parsed_document(
            source_pdf=source_path,
            background_literature_context=background_literature_context,
            full_text_excerpt=full_text[:2000],
            selected_table_id="",
            records=records,
        )
        parsed_document_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_document_path.write_text(json.dumps(parsed_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        result = IngestionResult(
            input_kind="pdf",
            status="failed",
            summary=summary,
            normalized_data_path=cleaned_data_path,
            duration_ms=_elapsed_ms(started_at),
            log_path=log_path,
            parsed_document_path=parsed_document_path,
            extracted_table_paths=tuple(record.csv_path for record in records),
            warnings=tuple(warnings),
            background_literature_context=background_literature_context,
            candidate_table_count=len(records),
            candidate_table_summaries=tuple(parsed_payload["candidate_table_summaries"]),
            pdf_multi_table_mode=True,
        )
        payload = {
            "input_kind": result.input_kind,
            "status": result.status,
            "summary": result.summary,
            "normalized_data_path": result.normalized_data_path.as_posix(),
            "duration_ms": result.duration_ms,
            "parsed_document_path": parsed_document_path.as_posix(),
            "candidate_tables": parsed_payload["candidate_tables"],
            "candidate_table_summaries": parsed_payload["candidate_table_summaries"],
            "candidate_table_count": len(records),
            "selected_table_id": "",
            "selected_table_shape": None,
            "selected_table_headers": [],
            "selected_table_numeric_columns": [],
            "pdf_multi_table_mode": True,
            "warnings": list(result.warnings),
            "mode": normalized_mode,
        }
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    primary_df = pd.read_csv(primary_record.csv_path)
    cleaned_data_path.parent.mkdir(parents=True, exist_ok=True)
    primary_df.to_csv(cleaned_data_path, index=False, encoding="utf-8-sig")

    selected_records = [
        ExtractedTableRecord(
            table_id=record.table_id,
            page_number=record.page_number,
            csv_path=record.csv_path,
            rows=record.rows,
            cols=record.cols,
            area=record.area,
            headers=record.headers,
            numeric_columns=record.numeric_columns,
            content_hint=record.content_hint,
            selected_as_primary=(record.table_id == primary_record.table_id),
        )
        for record in records
    ]
    parsed_payload = _serialize_parsed_document(
        source_pdf=source_path,
        background_literature_context=background_literature_context,
        full_text_excerpt=full_text[:2000],
        selected_table_id=primary_record.table_id,
        records=selected_records,
    )
    parsed_document_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_document_path.write_text(json.dumps(parsed_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = (
        f"PDF 文档解析完成：共提取 {len(records)} 张候选表，"
        f"已选择 {primary_record.table_id} 作为主表写入 cleaned_data.csv，"
        "其余候选表会与文献背景一起作为综合解释上下文。"
    )
    warnings.append("V1 暂不支持多表联合定量分析；若主表选错，请手动裁剪 PDF 或在前端改选主表。")
    result = IngestionResult(
        input_kind="pdf",
        status="completed",
        summary=summary,
        normalized_data_path=primary_record.csv_path,
        duration_ms=_elapsed_ms(started_at),
        log_path=log_path,
        parsed_document_path=parsed_document_path,
        extracted_table_paths=tuple(record.csv_path for record in selected_records),
        warnings=tuple(warnings),
        selected_table_id=primary_record.table_id,
        background_literature_context=background_literature_context,
        candidate_table_count=len(selected_records),
        selected_table_shape=(primary_record.rows, primary_record.cols),
        selected_table_headers=primary_record.headers,
        selected_table_numeric_columns=primary_record.numeric_columns,
        candidate_table_summaries=tuple(parsed_payload["candidate_table_summaries"]),
        pdf_multi_table_mode=True,
    )
    payload = {
        "input_kind": result.input_kind,
        "status": result.status,
        "summary": result.summary,
        "normalized_data_path": result.normalized_data_path.as_posix(),
        "duration_ms": result.duration_ms,
        "parsed_document_path": parsed_document_path.as_posix(),
        "candidate_tables": parsed_payload["candidate_tables"],
        "candidate_table_summaries": parsed_payload["candidate_table_summaries"],
        "candidate_table_count": len(selected_records),
        "selected_table_id": primary_record.table_id,
        "selected_table_shape": list(result.selected_table_shape) if result.selected_table_shape else None,
        "selected_table_headers": list(result.selected_table_headers),
        "selected_table_numeric_columns": list(result.selected_table_numeric_columns),
        "pdf_multi_table_mode": True,
        "warnings": list(result.warnings),
        "mode": normalized_mode,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


__all__ = [
    "ExtractedTableRecord",
    "IngestionResult",
    "PdfPreviewResult",
    "SUPPORTED_DOCUMENT_SUFFIXES",
    "SUPPORTED_TABULAR_SUFFIXES",
    "ingest_input_document",
    "preview_pdf_tables",
]
