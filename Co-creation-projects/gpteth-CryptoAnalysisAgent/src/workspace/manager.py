"""Workspace files: identity, soul, user profile, long-term memory."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

CONFIG_FILES = ["IDENTITY", "SOUL", "USER", "MEMORY", "AGENTS"]
TEMPLATES_DIR = Path(__file__).parent / "templates"


class WorkspaceManager:
    def __init__(self, workspace_path: str | None = None):
        root = workspace_path or os.getenv("WORKSPACE_PATH") or "./workspace"
        self.workspace_path = os.path.abspath(os.path.expanduser(root))
        self.memory_path = os.path.join(self.workspace_path, "memory")
        self.sessions_path = os.path.join(self.workspace_path, "sessions")

    def ensure_workspace_exists(self) -> None:
        os.makedirs(self.workspace_path, exist_ok=True)
        os.makedirs(self.memory_path, exist_ok=True)
        os.makedirs(self.sessions_path, exist_ok=True)
        for name in CONFIG_FILES:
            if not os.path.exists(self.get_config_path(name)):
                self._create_default_config(name)

    def get_config_path(self, name: str) -> str:
        return os.path.join(self.workspace_path, f"{name}.md")

    def load_config(self, name: str) -> Optional[str]:
        path = self.get_config_path(name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        return None

    def save_config(self, name: str, content: str) -> None:
        os.makedirs(self.workspace_path, exist_ok=True)
        with open(self.get_config_path(name), "w", encoding="utf-8") as fh:
            fh.write(content)

    def list_configs(self) -> list[str]:
        names = []
        for name in CONFIG_FILES:
            if os.path.exists(self.get_config_path(name)):
                names.append(name)
        return names

    def read_identity_name(self, default: str = "Nova") -> str:
        identity = self.load_config("IDENTITY") or ""
        match = re.search(r"\*\*名称[：:]\*\*\s*(.+?)(?:\n|$)", identity)
        if not match:
            return default
        name = match.group(1).strip()
        if not name or name.startswith("_") or "选一个" in name or "（" in name:
            return default
        return name

    def build_system_prompt(self) -> str:
        parts = []
        for name, title in (
            ("AGENTS", "工作规则"),
            ("IDENTITY", "身份"),
            ("SOUL", "个性"),
            ("USER", "用户信息"),
            ("MEMORY", "长期记忆"),
        ):
            content = self.load_config(name)
            if content and content.strip():
                parts.append(f"## {title}\n\n{content.strip()}")
        return "\n\n".join(parts)

    def reset_to_templates(self, reset_sessions: bool = False, reset_memory: bool = False) -> None:
        for name in CONFIG_FILES:
            self._create_default_config(name)
        if reset_sessions:
            self._clear_dir(self.sessions_path, ".json")
        if reset_memory:
            self._clear_dir(self.memory_path, ".md")

    def _create_default_config(self, name: str) -> None:
        template = TEMPLATES_DIR / f"{name}.md"
        if template.exists():
            content = template.read_text(encoding="utf-8")
        else:
            content = f"# {name}\n\n（待配置）\n"
        content = content.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
        self.save_config(name, content)

    @staticmethod
    def _clear_dir(path: str, suffix: str) -> None:
        if not os.path.isdir(path):
            return
        for filename in os.listdir(path):
            if filename.endswith(suffix):
                os.remove(os.path.join(path, filename))


def load_llm_overrides(workspace: WorkspaceManager) -> dict:
    """Optional workspace/config.json overrides environment LLM settings."""
    path = os.path.join(os.path.dirname(workspace.workspace_path), "config.json")
    local = os.path.join(workspace.workspace_path, "config.json")
    for candidate in (local, path):
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return data.get("llm", {}) if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError):
                return {}
    return {}
