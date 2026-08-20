"""CSV bill import and normalization."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Iterable, TextIO

from ..models import Transaction


class CSVImportTool:
    """Normalize common Chinese/English bank-export columns into transactions.

    Supported amount conventions:
    - positive amount + a direction/type column;
    - negative amount means expense and positive means income when direction is absent;
    - separate income/expense columns (the non-empty one wins).
    """

    aliases = {
        "date": ("date", "日期", "交易日期", "时间", "交易时间", "occurred_at"),
        "merchant": ("merchant", "商户", "商户名称", "交易对方", "description", "摘要", "备注"),
        "amount": ("amount", "金额", "交易金额", "price", "消费金额"),
        "direction": ("direction", "收支", "类型", "交易类型", "kind", "income_expense"),
        "income": ("income", "收入", "入账"),
        "expense": ("expense", "支出", "消费", "付款"),
        "category": ("category", "类别", "分类", "消费类别"),
        "note": ("note", "备注", "说明", "memo"),
    }

    date_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y年%m月%d日",
    )

    def __init__(self) -> None:
        # Exposed for the coordinator/UI so partially malformed exports are
        # visible instead of being silently mistaken for complete imports.
        self.last_errors: list[str] = []

    def load(self, source: str | Path | TextIO | BinaryIO) -> list[Transaction]:
        self.last_errors = []
        if hasattr(source, "read"):
            raw = source.read()
            source_name = getattr(source, "name", "uploaded.csv")
            text = self._decode(raw)
        else:
            path = Path(source)
            raw = path.read_bytes()
            source_name = str(path)
            text = self._decode(raw)
        if not text.strip():
            return []
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV 缺少表头")
        mapping = self._resolve_columns(reader.fieldnames)
        if not mapping.get("date") or not mapping.get("merchant"):
            raise ValueError("CSV 至少需要日期和商户列")
        transactions: list[Transaction] = []
        errors: list[str] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                transactions.append(self._row_to_transaction(row, mapping, source_name, row_number))
            except ValueError as exc:
                errors.append(f"第 {row_number} 行: {exc}")
        self.last_errors = errors
        if errors and not transactions:
            raise ValueError("CSV 没有可导入的交易: " + "; ".join(errors[:3]))
        return transactions

    @staticmethod
    def _decode(raw: str | bytes | bytearray) -> str:
        if isinstance(raw, str):
            return raw
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return bytes(raw).decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("CSV 编码无法识别，请另存为 UTF-8 或 GB18030")

    def _resolve_columns(self, fields: Iterable[str]) -> dict[str, str | None]:
        normalized = {self._norm(field): field for field in fields if field}
        result: dict[str, str | None] = {}
        for target, candidates in self.aliases.items():
            result[target] = next((normalized[self._norm(c)] for c in candidates if self._norm(c) in normalized), None)
        return result

    @staticmethod
    def _norm(value: str) -> str:
        return "".join(str(value).strip().lower().replace("_", "").replace("-", "").split())

    def _row_to_transaction(self, row: dict[str, str], mapping: dict[str, str | None], source: str, row_number: int) -> Transaction:
        raw_date = (row.get(mapping["date"] or "") or "").strip()
        occurred_at = self._parse_date(raw_date)
        merchant = (row.get(mapping["merchant"] or "") or "").strip() or "未知商户"
        amount, kind = self._parse_amount_and_kind(row, mapping)
        category = (row.get(mapping["category"] or "") or "").strip() or "Uncategorized"
        note = (row.get(mapping["note"] or "") or "").strip()
        digest = hashlib.sha1(f"{source}:{row_number}:{occurred_at}:{merchant}:{amount}:{kind}".encode()).hexdigest()[:16]
        return Transaction(digest, occurred_at, merchant, round(abs(amount), 2), kind, category, note, source)

    def _parse_date(self, raw: str) -> str:
        if not raw:
            raise ValueError("日期为空")
        candidate = raw.replace("T", " ").strip()
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.isoformat(timespec="minutes")
        except ValueError:
            pass
        for fmt in self.date_formats:
            try:
                return datetime.strptime(candidate, fmt).isoformat(timespec="minutes")
            except ValueError:
                continue
        raise ValueError(f"无法解析日期 {raw!r}")

    def _parse_amount_and_kind(self, row: dict[str, str], mapping: dict[str, str | None]) -> tuple[float, str]:
        income_raw = self._number(row.get(mapping["income"] or ""))
        expense_raw = self._number(row.get(mapping["expense"] or ""))
        if income_raw is not None and abs(income_raw) > 0:
            return abs(income_raw), "income"
        if expense_raw is not None and abs(expense_raw) > 0:
            return abs(expense_raw), "expense"
        raw = (row.get(mapping["amount"] or "") or "").strip()
        if not raw:
            raise ValueError("金额为空")
        amount = self._number(raw)
        if amount is None:
            raise ValueError(f"无法解析金额 {raw!r}")
        direction = (row.get(mapping["direction"] or "") or "").strip().lower()
        if any(token in direction for token in ("收入", "入账", "转入", "退款", "退货", "income", "credit", "deposit", "refund", "工资")):
            kind = "income"
        elif any(token in direction for token in ("支出", "消费", "expense", "debit", "payment", "付款")):
            kind = "expense"
        else:
            kind = "income" if amount > 0 else "expense"
        return abs(amount), kind

    @staticmethod
    def _number(raw: str | None) -> float | None:
        if raw is None or not str(raw).strip():
            return None
        cleaned = str(raw).strip().replace(",", "").replace("￥", "").replace("¥", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
