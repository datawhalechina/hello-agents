"""Workspace-bounded text access; never follows a link outside the selected root."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

MAX_FILE = 256_000
EXCLUDED = {".git", "node_modules", ".venv", "venv", "__pycache__", ".idea", ".pytest_cache",
            ".test-artifacts", ".runtime", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints", "dist", "build"}
PRIVATE_SUFFIXES = {".pem", ".key", ".pfx", ".p12", ".sqlite", ".sqlite3", ".db"}


def digest(content: str | None) -> str:
    return "missing" if content is None else hashlib.sha256(content.encode("utf-8")).hexdigest()


class Conflict(ValueError):
    pass


class Workspace:
    def __init__(self, root: str, include_build_sources: bool = False):
        self.root = Path(root).expanduser().resolve(strict=True)
        # Annotation must inspect content before calling build/dist generated.
        self.excluded = EXCLUDED - {"build", "dist"} if include_build_sources else EXCLUDED
        if not self.root.is_dir():
            raise ValueError("请选择有效的项目文件夹。")

    def path(self, relative: str) -> Path:
        if not relative or Path(relative).is_absolute() or "\x00" in relative or ":" in relative:
            raise ValueError("文件路径必须相对于工作区。")
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("路径超出工作区。")
        parts = path.relative_to(self.root).parts
        if any(part.casefold() in self.excluded for part in parts):
            raise ValueError("该目录不在可访问范围内。")
        name = path.name.casefold()
        if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
            raise ValueError("本地密钥配置不提供给模型或编辑器。")
        if path.suffix.lower() in PRIVATE_SUFFIXES:
            raise ValueError("该文件类型不在文本工具的访问范围内。")
        return path

    def read(self, relative: str) -> dict:
        path = self.path(relative)
        if not path.is_file():
            raise ValueError("文件不存在。")
        if path.stat().st_size > MAX_FILE:
            raise ValueError("文件超过 256 KB，请选择较小的文本文件。")
        raw = path.read_bytes()
        if b"\x00" in raw:
            raise ValueError("暂不支持二进制文件。")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("当前仅支持 UTF-8 文本文件。") from exc
        return {"path": path.relative_to(self.root).as_posix(), "hash": digest(content), "content": content}

    def tree(self, relative: str = "") -> list[dict]:
        if not isinstance(relative, str):
            raise ValueError("目录路径必须是字符串；列出项目根目录请使用空字符串或点号。")
        # Listing the root is valid; file reads and writes still use path(),
        # which deliberately rejects the workspace directory itself.
        parent = self.root if relative in {"", ".", "./", ".\\"} else self.path(relative)
        if not parent.is_dir():
            raise ValueError("目录不存在。")
        entries = []
        for item in sorted(parent.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold())):
            if item.name.casefold() in self.excluded or item.is_symlink():
                continue
            rel = item.relative_to(self.root).as_posix()
            try:
                self.path(rel)
            except ValueError:
                continue
            entries.append({"path": rel, "name": item.name, "directory": item.is_dir()})
            if len(entries) >= 500:
                break
        return entries

    def files(self, limit: int | None = 800):
        count = 0
        for directory, names, files in os.walk(self.root, followlinks=False):
            names[:] = sorted(n for n in names if n.casefold() not in self.excluded and not (Path(directory) / n).is_symlink())
            for name in sorted(files):
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                relative = path.relative_to(self.root).as_posix()
                try:
                    self.path(relative)
                except ValueError:
                    continue
                yield relative
                count += 1
                if limit is not None and count >= limit:
                    return

    def search(self, query: str) -> list[dict]:
        if not query or len(query) > 250:
            raise ValueError("搜索内容应为 1–250 个字符。")
        results = []
        executable = shutil.which("rg")
        if executable:
            # Explicit files preserve our exclusions even for hidden or untracked files.
            files = list(self.files())
            if not files:
                return []
            for start in range(0, len(files), 50):
                batch = subprocess.run(
                    [executable, "--json", "--fixed-strings", "--ignore-case", "--max-count", "60",
                     "--max-filesize", str(MAX_FILE), "--", query, *files[start:start + 50]],
                    cwd=self.root, capture_output=True, timeout=10,
                )
                if batch.returncode not in {0, 1}:
                    raise ValueError("rg 搜索失败：" + batch.stderr.decode("utf-8", errors="replace")[:300])
                for line in batch.stdout.splitlines():
                    item = json.loads(line)
                    if item["type"] == "match":
                        data = item["data"]
                        relative = data["path"].get("text", "").replace("\\", "/")
                        self.path(relative)
                        results.append({"path": relative, "line": data["line_number"], "text": data["lines"].get("text", "").rstrip()[:350]})
                        if len(results) >= 60:
                            return results
            return results
        # Bounded UTF-8 reads provide the same access policy without rg installed.
        for relative in self.files():
            try:
                file = self.read(relative)
            except (ValueError, OSError):
                continue
            for number, line in enumerate(file["content"].splitlines(), 1):
                if query.casefold() in line.casefold():
                    results.append({"path": relative, "line": number, "text": line[:350]})
                    if len(results) >= 60:
                        return results
        return results

    def git_diff(self) -> str:
        executable = shutil.which("git")
        if not executable:
            return "未安装 Git。"
        changed = subprocess.run(
            [executable, "diff", "--relative", "--name-only", "--no-ext-diff", "-z"],
            cwd=self.root, capture_output=True, timeout=10,
        )
        if changed.returncode:
            return "当前工作区没有可读取的 Git 差异。"
        paths = []
        for raw in changed.stdout.split(b"\x00"):
            if not raw:
                continue
            relative = raw.decode("utf-8", errors="replace")
            try:
                self.path(relative)
            except ValueError:
                continue
            paths.append(relative)
            if len(paths) >= 100:
                break
        if not paths:
            return "没有访问范围内的未暂存文本差异。"
        result = subprocess.run(
            [executable, "--literal-pathspecs", "--no-pager", "diff", "--relative", "--no-ext-diff", "--no-textconv", "--", *paths],
            cwd=self.root, capture_output=True, timeout=10,
        )
        return result.stdout.decode("utf-8", errors="replace")[:24000] or "没有未暂存的文本差异。"
