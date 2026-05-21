
from __future__ import annotations

import logging
import sys

def _normalize_level(level: str | int | None) -> int:
    if level is None:
        return logging.INFO
    if isinstance(level, int):
        return level
    s = str(level).strip().upper()
    return getattr(logging, s, logging.INFO)

def configure_logging(level: str | int | None = None) -> None:
    lvl = _normalize_level(level)

    app_root = logging.getLogger("app")
    app_root.setLevel(lvl)

    if not app_root.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setLevel(lvl)
        h.setFormatter(
            logging.Formatter("%(levelname)s:     %(name)s: %(message)s")
        )
        app_root.addHandler(h)

        app_root.propagate = False

    logging.getLogger(__name__).setLevel(lvl)
