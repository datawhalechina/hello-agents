"""Local privacy settings for features that send data to external services."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any
from fithealth_agent.atomic_json import atomic_write_json
from fithealth_agent.json_file_lock import JsonFileLock
from fithealth_agent.settings import data_path


DEFAULT_SETTINGS = {"external_models_enabled": True}


class ExternalModelSettingsStore:
    """Persist the user's opt-in for all external AI model requests."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_path("external_model_settings.json")
        self._lock = RLock()
        self._degraded_reason: str | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, JsonFileLock(self.path):
            if not self.path.exists():
                self._write(DEFAULT_SETTINGS)

    def _read(self) -> dict[str, bool]:
        try:
            data: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return dict(DEFAULT_SETTINGS)
        except (OSError, json.JSONDecodeError) as exc:
            self._degraded_reason = str(exc)
            return {"external_models_enabled": False}
        if not isinstance(data, dict) or not isinstance(data.get("external_models_enabled"), bool):
            self._degraded_reason = "隐私设置格式无效"
            return {"external_models_enabled": False}
        self._degraded_reason = None
        return {"external_models_enabled": data["external_models_enabled"]}

    def _write(self, settings: dict[str, bool]) -> None:
        # DATA-06：这里存的是"要不要把数据发给外部模型"的隐私开关。断电后
        # 读到 0 字节文件会静默回落到 DEFAULT_SETTINGS（也就是**开启**），
        # 把用户显式关掉的开关又打开——所以同样必须 fsync 后再 replace。
        atomic_write_json(self.path, settings)

    def get(self) -> dict[str, bool]:
        with self._lock, JsonFileLock(self.path):
            return self._read()

    def storage_status(self) -> dict[str, object]:
        with self._lock, JsonFileLock(self.path):
            settings = self._read()
            return {
                "available": self._degraded_reason is None,
                "degraded_reason": self._degraded_reason,
                **settings,
            }

    def set_external_models_enabled(self, enabled: bool) -> dict[str, bool]:
        if not isinstance(enabled, bool):
            raise ValueError("external_models_enabled 必须是布尔值")
        with self._lock, JsonFileLock(self.path):
            settings = {"external_models_enabled": enabled}
            self._write(settings)
            self._degraded_reason = None
            return settings

