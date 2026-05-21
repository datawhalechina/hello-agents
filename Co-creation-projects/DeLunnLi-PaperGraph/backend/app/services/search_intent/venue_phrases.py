
from __future__ import annotations

from ...utils.common import dedupe_strings_preserve_order

def sanitize_venue_tokens(raw: list[str | None]) -> list[str]:
    cleaned = [
        t
        for x in raw or []
        if (t := str(x).strip())
        and len(t) <= 120
        and not t.lower().startswith(("http://", "https://"))
        and any(c.isalnum() for c in t)
    ]
    return dedupe_strings_preserve_order(cleaned, max_n=8)
