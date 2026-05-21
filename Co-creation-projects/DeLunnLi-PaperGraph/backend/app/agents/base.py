from __future__ import annotations

import logging
from typing import Any

from ..services.llm.llm_service import get_llm
from ..settings import get_settings

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self) -> None:
        self._settings = get_settings()
        self.llm = self._init_llm()

    def _init_llm(self) -> Any:
        try:
            return get_llm()
        except Exception as e:
            logger.exception("[%s] LLM 初始化失败", type(self).__name__)
            raise RuntimeError(f"{type(self).__name__}_llm_init_failed") from e

    def _cfg(self, name: str, default: Any = None) -> Any:
        return getattr(self._settings, name, default)

    def _cfg_int(self, name: str, default: int = 0) -> int:
        try:
            return int(self._cfg(name, default))
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _clip(value: Any, limit: int) -> str:
        return str(value or "").strip()[:limit]
