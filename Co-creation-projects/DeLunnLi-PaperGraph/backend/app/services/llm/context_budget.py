"""Offline input bounds, measured in UTF-8 bytes rather than guessed token ratios.

For byte-backed model tokenizers, one byte is a conservative upper bound of one
content token. The 9,000-byte ceiling leaves headroom below 10K tokens; callers
should still review evidence-bearing items above the 1K-token review threshold.
No tokenizer vocabulary download is needed to enforce this bound.
"""
from __future__ import annotations

MODEL_ITEM_BYTES = 9000
TOOL_ITEM_BYTES = 6000


def clip_utf8(value: object, max_bytes: int = MODEL_ITEM_BYTES, *, tail: bool = False) -> str:
    text = str(value or "")
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return data.decode("utf-8")
    if max_bytes <= 0:
        return ""
    return (data[-max_bytes:] if tail else data[:max_bytes]).decode("utf-8", errors="ignore")
