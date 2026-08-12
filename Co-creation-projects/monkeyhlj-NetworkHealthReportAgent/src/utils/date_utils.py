from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Tuple


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def default_date_window(start_date: Optional[str], end_date: Optional[str], days: int = 7) -> Tuple[date, date]:
    parsed_start = parse_date(start_date)
    parsed_end = parse_date(end_date)

    if parsed_end is None:
        parsed_end = date.today()
    if parsed_start is None:
        parsed_start = parsed_end - timedelta(days=days - 1)

    if parsed_start > parsed_end:
        parsed_start, parsed_end = parsed_end, parsed_start

    return parsed_start, parsed_end


def in_range(date_str: str, start: date, end: date) -> bool:
    current = datetime.strptime(date_str, "%Y-%m-%d").date()
    return start <= current <= end
