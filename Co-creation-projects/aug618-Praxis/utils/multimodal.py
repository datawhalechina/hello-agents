"""Multimodal helpers (image -> OpenAI-compatible message parts).

Keep it dependency-free (no Pillow) so it works in minimal environments.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional


def encode_image_to_data_url(path: str | Path, mime_type: Optional[str] = None) -> str:
    """Encode a local image file to a data URL (data:<mime>;base64,...)."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Image not found: {p}")

    mt = mime_type
    if not mt:
        mt, _ = mimetypes.guess_type(str(p))
    if not mt:
        # Safe default; most providers accept image/jpeg or image/png
        mt = "image/jpeg"

    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mt};base64,{b64}"


def image_part_from_path(path: str | Path, mime_type: Optional[str] = None) -> Dict[str, Any]:
    """Build an OpenAI-compatible image part from a local file path."""
    data_url = encode_image_to_data_url(path, mime_type=mime_type)
    return {"type": "image_url", "image_url": {"url": data_url}}


def build_user_content_with_images(text: str, image_paths: List[str | Path]) -> List[Dict[str, Any]]:
    """Build a user message content list: text + N image parts."""
    parts: List[Dict[str, Any]] = [{"type": "text", "text": text}]
    for p in image_paths:
        parts.append(image_part_from_path(p))
    return parts

