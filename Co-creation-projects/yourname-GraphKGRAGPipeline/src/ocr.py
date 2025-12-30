from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PIL import Image


@dataclass
class OCRSpan:
    text: str
    box: Optional[List[List[float]]] = None  # 4-point polygon
    score: Optional[float] = None


def extract_ocr_spans(image_path: str) -> List[OCRSpan]:
    """Best-effort OCR.

    Priority:
    1) paddleocr (box-level)
    2) pytesseract (text-only, no boxes)

    Returns list of OCRSpan.
    """

    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        result = ocr.ocr(image_path, cls=True)
        spans: List[OCRSpan] = []
        for page in result or []:
            for line in page or []:
                box, (txt, score) = line
                spans.append(OCRSpan(text=txt, box=box, score=float(score)))
        return spans
    except Exception:
        pass

    try:
        import pytesseract

        cmd = os.getenv("TESSERACT_CMD")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="chi_sim")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return [OCRSpan(text=ln) for ln in lines]
    except Exception as exc:
        raise RuntimeError(
            "No OCR backend available. Install one of: paddleocr+paddlepaddle OR pytesseract + Tesseract binary."
        ) from exc


def spans_to_text(spans: List[OCRSpan]) -> str:
    return "\n".join(s.text for s in spans if s.text.strip())


def spans_to_debug_json(spans: List[OCRSpan]) -> Dict[str, Any]:
    return {
        "spans": [
            {"text": s.text, "box": s.box, "score": s.score}
            for s in spans
        ]
    }
