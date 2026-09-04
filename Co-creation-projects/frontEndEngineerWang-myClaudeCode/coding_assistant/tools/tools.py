"""Filesystem, shell, and session todo tools."""

import atexit
import ast
import fnmatch
import hashlib
import inspect
import json
import locale
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path, PurePath, PurePosixPath

from ..core.config import WORKDIR
from ..core.workspace import current_workdir
from ..tasks.tasks import CURRENT_TODOS, assignment_cwd

# -- Search safety limits --
# A broad query over a large repo that contains build artifacts (dist/,
# node_modules/, ...) can return megabytes of matches and flood the context
# window. These limits keep every search result bounded no matter which
# backend runs, so the agent never freezes on a 24MB tool result.
SEARCH_MAX_COLUMNS = 500
SEARCH_MAX_OUTPUT_CHARS = 1_000_000
SEARCH_IGNORE_DIRS = frozenset({
    ".git", ".svn", ".hg", ".bzr",
    "node_modules", "dist", "build", "coverage", "out", "target",
    "__pycache__", ".venv", "venv", "env", ".tox", ".nox",
    ".idea", ".vscode", ".next", ".nuxt", ".output", ".svelte-kit",
    ".cache", ".parcel-cache", ".turbo", ".rollup.cache",
})
SEARCH_IGNORE_SUFFIXES = (".min.js", ".min.css", ".min.mjs", ".map")


def _gitignore_predicate(base: Path):
    """Best-effort .gitignore matcher for the Python search fallback.

    ripgrep honors .gitignore natively; the Python fallback must replicate it
    so broad searches skip build output and repo-specific ignored paths. Both
    root and nested .gitignore files are honored, with last-match-wins
    negation support.
    """
    gitignores: list[tuple[Path, list[tuple[str, bool]]]] = []
    for root_dir, dirs, files in os.walk(base):
        # Never descend into build artifacts while collecting gitignores.
        dirs[:] = [d for d in dirs if d not in SEARCH_IGNORE_DIRS]
        if ".gitignore" not in files:
            continue
        gi = Path(root_dir) / ".gitignore"
        try:
            raw_lines = gi.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        patterns: list[tuple[str, bool]] = []
        for raw in raw_lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            if negated:
                line = line[1:].strip()
            patterns.append((line, negated))
        if patterns:
            gitignores.append((gi.parent.resolve(), patterns))
    if not gitignores:
        return lambda rel_posix, is_dir: False

    base_resolved = base.resolve()

    def is_ignored(rel_posix: str, is_dir: bool) -> bool:
        try:
            full = (base_resolved / rel_posix).resolve()
        except OSError:
            return False
        ignored = False
        for gi_dir, patterns in gitignores:
            try:
                local = full.relative_to(gi_dir).as_posix()
            except ValueError:
                continue
            for pattern, negated in patterns:
                if _gitignore_path_matches(local, pattern):
                    ignored = not negated
        return ignored

    return is_ignored


def _gitignore_path_matches(local: str, pattern: str) -> bool:
    """Match a gitignore pattern (relative to its .gitignore dir) against a path."""
    p = pattern.rstrip("/")
    if fnmatch.fnmatch(local, p) or fnmatch.fnmatch(local, p + "/*"):
        return True
    if local == p or local.startswith(p + "/"):
        return True
    for part in local.split("/"):
        if fnmatch.fnmatch(part, p) or part == p:
            return True
    return False


# -- Basic Tools --


def safe_path(path: str, cwd: Path | None = None) -> Path:
    base = (cwd or WORKDIR).resolve()
    resolved = (base / path).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"Path escapes workspace: {path}")
    return resolved


def _decode_bytes(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("gb18030")
    # Normalise to \n so callers (and the model) see one line ending style.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _detect_newline(data: bytes) -> str:
    """Return the dominant line ending of ``data`` ("\\r\\n", "\\n" or "\\r").

    A file is written back with the style it already used: rewriting a CRLF
    repository as LF (or the reverse) turns every line into a diff and hides
    the change that was actually requested.
    """
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    if crlf >= lf and crlf >= cr and crlf:
        return "\r\n"
    if cr > lf and cr:
        return "\r"
    return "\n"


def _write_text_file(path: Path, content: str) -> None:
    """Write text while preserving the file's existing line ending style.

    ``write_text`` defaults to ``newline=None``, which translates every "\\n"
    into ``os.linesep``. On Windows that silently converted LF repositories
    to CRLF and, combined with a byte-level reader that kept "\\r" intact,
    added one extra "\\r" per edit until lines became "\\r\\r\\r\\n" — shown
    as phantom blank lines and a whole-file diff.
    """
    newline = "\n"
    if path.is_file():
        try:
            newline = _detect_newline(path.read_bytes())
        except OSError:
            newline = "\n"
    body = content.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        body = body.replace("\n", newline)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(body)


def _read_text_file(path: Path) -> str:
    """Read repository text as UTF-8, with a Windows legacy fallback."""
    return _decode_bytes(path.read_bytes())


def _expand_braces(pattern: str) -> list[str]:
    """Expand ``{a,b}`` alternatives so fnmatch understands rg-style globs.

    The Python search fallback matches globs with fnmatch, which has no brace
    expansion. Without this, a perfectly reasonable query like
    ``src/**/*.{vue,ts}`` silently matches nothing and the agent concludes
    the symbol does not exist anywhere.
    """
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    head, tail = pattern[:match.start()], pattern[match.end():]
    expanded: list[str] = []
    for alternative in match.group(1).split(","):
        expanded.extend(_expand_braces(head + alternative + tail))
    return expanded or [pattern]


def _matches_glob(path: str, pattern: str | None) -> bool:
    if not pattern:
        return True
    normalized = path.replace("\\", "/")
    for candidate in _expand_braces(pattern):
        # '**' may match zero path segments (bash globstar / rg semantics);
        # fnmatch needs the zero-segment case spelled out explicitly, so
        # 'src/**/*.vue' also matches 'src/types.ts'.
        variants = {candidate, candidate.replace("**/", "")}
        for variant in variants:
            if (fnmatch.fnmatch(normalized, variant)
                    or Path(normalized).match(variant)
                    or (variant.startswith("**/")
                        and fnmatch.fnmatch(normalized, variant[3:]))):
                return True
    return False


def _search_with_rg(
    executable: str,
    query: str,
    base: Path,
    glob: str | None,
    case_sensitive: bool,
    max_results: int,
) -> tuple[list[str], bool]:
    run_cwd, search_target = base, "."
    if base.is_file():
        run_cwd, search_target = base.parent, base.name
    args = [
        executable,
        "--line-number",
        "--column",
        "--no-heading",
        "--color",
        "never",
        "--fixed-strings",
        "--max-columns",
        str(SEARCH_MAX_COLUMNS),
    ]
    if not case_sensitive:
        args.append("--ignore-case")
    # Belt-and-suspenders: never grep build artifacts even if a repo does not
    # gitignore them. ripgrep already skips .gitignore'd paths on its own.
    if not base.is_file():
        for ignored_dir in SEARCH_IGNORE_DIRS:
            args.extend(["--glob", f"!{ignored_dir}"])
    if glob:
        args.extend(["--glob", glob])
    args.extend(["--", query, search_target])

    process = subprocess.Popen(
        args,
        cwd=run_cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    matches: list[str] = []
    limit_reached = False
    try:
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip("\r\n")
            if line:
                matches.append(line.removeprefix(".\\").removeprefix("./"))
            if len(matches) >= max_results:
                limit_reached = True
                process.terminate()
                break
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)
        stderr = process.stderr.read().strip() if process.stderr else ""
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1)
    if process.returncode not in {0, 1, -15, 1} and not limit_reached:
        raise RuntimeError(stderr or f"rg exited with status {process.returncode}")
    return matches[:max_results], limit_reached


def _search_with_python(
    query: str,
    base: Path,
    glob: str | None,
    case_sensitive: bool,
    max_results: int,
) -> tuple[list[str], bool]:
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)
    is_ignored = _gitignore_predicate(base)
    matches: list[str] = []
    total_chars = 0
    # A single-file scope must not go through rglob (which only walks dirs).
    candidates: list[Path] = [base] if base.is_file() else []
    for path in candidates or base.rglob("*"):
        if not path.is_file():
            continue
        try:
            if not path.resolve().is_relative_to(base):
                continue
        except OSError:
            continue
        if base.is_file():
            relative = Path(path.name)
        else:
            relative = path.relative_to(base)
        # Skip build artifacts / dependency trees so a broad query never walks
        # into dist/ or node_modules/ and returns megabytes of matches.
        if any(part in SEARCH_IGNORE_DIRS for part in relative.parts):
            continue
        if relative.name.endswith(SEARCH_IGNORE_SUFFIXES):
            continue
        relative_text = relative.as_posix()
        if is_ignored(relative_text, is_dir=False):
            continue
        if not _matches_glob(relative_text, glob):
            continue
        try:
            data = path.read_bytes()
            if b"\0" in data[:8192]:
                continue
            text = _read_text_file(path)
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = pattern.search(line)
            if not match:
                continue
            # Cap each match line so a minified single-line bundle cannot
            # contribute megabytes on its own.
            if len(line) > SEARCH_MAX_COLUMNS:
                line = line[:SEARCH_MAX_COLUMNS] + "\u2026"
            entry = f"{relative_text}:{line_number}:{match.start() + 1}:{line}"
            if total_chars + len(entry) + 1 > SEARCH_MAX_OUTPUT_CHARS:
                return matches, True
            matches.append(entry)
            total_chars += len(entry) + 1
            if len(matches) >= max_results:
                return matches, True
    return matches, False


def _suggest_similar_paths(root: Path, missing: str,
                           max_suggestions: int = 5) -> str:
    """Find workspace files whose name matches the missing path's basename.

    A "search path not found" error with no hint once sent the agent into a
    glob-and-retry loop (it guessed src/pages/feedback/FeedbackPage.vue when
    the file lived at src/pages/FeedbackPage.vue). Suggesting real candidates
    up front turns the dead end into a one-step correction.
    """
    basename = PurePosixPath(missing.replace("\\", "/")).name
    if not basename:
        return ""
    matches: list[str] = []
    visited = 0
    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SEARCH_IGNORE_DIRS]
        visited += 1
        if visited > 20_000 or len(matches) >= max_suggestions:
            break
        for name in files:
            if name.lower() == basename.lower():
                candidate = (Path(root_dir) / name).relative_to(root).as_posix()
                matches.append(candidate)
                if len(matches) >= max_suggestions:
                    break
    if not matches:
        return ""
    return "\nDid you mean: " + ", ".join(matches)


def run_search_text(
    query: str,
    glob: str | None = None,
    case_sensitive: bool = False,
    max_results: int = 100,
    cwd: Path | None = None,
    path: str | None = None,
) -> str:
    """Search workspace text with ripgrep, falling back to Python."""
    if not isinstance(query, str) or not query:
        return "Error: query must be a non-empty string"
    if glob is not None and (not isinstance(glob, str) or not glob):
        return "Error: glob must be a non-empty string when provided"
    try:
        limit = int(max_results)
    except (TypeError, ValueError):
        return "Error: max_results must be an integer"
    if limit < 1 or limit > 500:
        return "Error: max_results must be between 1 and 500"

    root = (cwd or WORKDIR).resolve()
    base = root
    if path is not None:
        if not isinstance(path, str) or not path:
            return "Error: path must be a non-empty string when provided"
        scoped = (root / path).resolve()
        try:
            inside = scoped.is_relative_to(root)
        except OSError:
            inside = False
        if not inside:
            return f"Error: search path escapes workspace: {path}"
        if not scoped.exists():
            return (f"Error: search path not found: {path}"
                    + _suggest_similar_paths(root, path))
        ignored = sorted({part for part in scoped.relative_to(root).parts
                          if part in SEARCH_IGNORE_DIRS})
        if ignored:
            # Silently returning "(no matches)" here once cost the agent a
            # long detour: it assumed the library had no combobox support and
            # kept probing node_modules internals by hand. The message must
            # redirect to the project's own usage, never back into the
            # dependency tree.
            return (
                f"Search scope '{path}' is inside an excluded directory "
                f"({', '.join(ignored)}). Dependency and build trees are "
                "excluded from search and from reading. For questions about "
                "a third-party library, the project's own source is the "
                "authoritative example of how it is used here: search the "
                "project source for the component name to find existing "
                "usages, check package.json for the installed version, and "
                "proceed with the edit."
            )
        base = scoped

    executable = shutil.which("rg")
    backend = "python"
    if executable:
        try:
            matches, truncated = _search_with_rg(
                executable, query, base, glob, case_sensitive, limit
            )
            backend = "rg"
        except (OSError, RuntimeError, subprocess.SubprocessError):
            matches, truncated = _search_with_python(
                query, base, glob, case_sensitive, limit
            )
    else:
        matches, truncated = _search_with_python(
            query, base, glob, case_sensitive, limit
        )

    header = f"Search backend: {backend}; matches: {len(matches)}"
    if truncated:
        header += f"; limit reached: {limit}"
    body = "\n".join(matches)
    full = header + ("\n" + body if matches else "\n(no matches)")
    if len(full) > SEARCH_MAX_OUTPUT_CHARS:
        keep = SEARCH_MAX_OUTPUT_CHARS
        full = (
            full[:keep]
            + f"\n... search output truncated to {keep} chars to protect the "
            f"context window; narrow the query or add a glob to see more"
        )
    return full


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _restore_newlines(content: str, newline: str) -> str:
    body = content.replace("\r\n", "\n").replace("\r", "\n")
    return body if newline == "\n" else body.replace("\n", newline)


def _write_patch_temp(path: Path, content: str, mode: int,
                      newline: str = "\n") -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{path.name}.",
        suffix=".patch.tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(_restore_newlines(content, newline))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(mode))
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _write_patch_bytes_temp(path: Path, content: bytes, mode: int) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{path.name}.",
        suffix=".rollback.tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(mode))
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def run_apply_patch(patches: list[dict], cwd: Path | None = None) -> str:
    """Validate and transactionally apply exact-context hunks to many files."""
    if not isinstance(patches, list) or not patches:
        return "Error: patches must be a non-empty list"

    base = (cwd or WORKDIR).resolve()
    staged: list[tuple[Path, bytes, str, int, int, str]] = []
    seen: set[Path] = set()
    total_hunks = 0

    try:
        for file_index, file_patch in enumerate(patches):
            if not isinstance(file_patch, dict):
                raise ValueError(f"patches[{file_index}] must be an object")
            raw_path = file_patch.get("path")
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f"patches[{file_index}].path must be non-empty")
            path = safe_path(raw_path, base)
            if path in seen:
                raise ValueError(f"duplicate patch path: {raw_path}")
            seen.add(path)
            if not path.is_file():
                raise ValueError(f"file not found: {raw_path}")

            original_bytes = path.read_bytes()
            expected_sha256 = file_patch.get("expected_sha256")
            if expected_sha256 is not None:
                if not isinstance(expected_sha256, str):
                    raise ValueError(
                        f"patches[{file_index}].expected_sha256 must be a string"
                    )
                actual_sha256 = _sha256(original_bytes)
                if actual_sha256.casefold() != expected_sha256.casefold():
                    raise ValueError(
                        f"stale file {raw_path}: SHA-256 is {actual_sha256}"
                    )

            text = _read_text_file(path)
            hunks = file_patch.get("hunks")
            if not isinstance(hunks, list) or not hunks:
                raise ValueError(f"patches[{file_index}].hunks must be non-empty")
            for hunk_index, hunk in enumerate(hunks):
                if not isinstance(hunk, dict):
                    raise ValueError(
                        f"patches[{file_index}].hunks[{hunk_index}] must be an object"
                    )
                old_text = hunk.get("old_text")
                new_text = hunk.get("new_text")
                if not isinstance(old_text, str) or not old_text:
                    raise ValueError(
                        f"patches[{file_index}].hunks[{hunk_index}].old_text "
                        "must be non-empty"
                    )
                if not isinstance(new_text, str):
                    raise ValueError(
                        f"patches[{file_index}].hunks[{hunk_index}].new_text "
                        "must be a string"
                    )
                if old_text == new_text:
                    raise ValueError(
                        f"patches[{file_index}].hunks[{hunk_index}] makes no change"
                    )
                expected = hunk.get("expected_occurrences", 1)
                if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
                    raise ValueError(
                        f"patches[{file_index}].hunks[{hunk_index}]."
                        "expected_occurrences must be a positive integer"
                    )
                # The model may paste CRLF fragments; the file is \n-based.
                old_text = old_text.replace("\r\n", "\n").replace("\r", "\n")
                new_text = new_text.replace("\r\n", "\n").replace("\r", "\n")
                actual = text.count(old_text)
                if actual != expected:
                    raise ValueError(
                        f"context mismatch in {raw_path} hunk {hunk_index}: "
                        f"expected {expected} occurrence(s), found {actual}"
                    )
                text = text.replace(old_text, new_text, expected)
                total_hunks += 1
            staged.append(
                (path, original_bytes, text, path.stat().st_mode, len(hunks),
                 _detect_newline(original_bytes))
            )
    except (OSError, UnicodeError, ValueError) as exc:
        return f"Error: patch validation failed: {exc}"

    temporary_files: dict[Path, Path] = {}
    replaced: list[tuple[Path, bytes, int]] = []
    try:
        for path, _, content, mode, _, newline in staged:
            temporary_files[path] = _write_patch_temp(path, content, mode,
                                                      newline)
        for path, original, _, mode, _, _ in staged:
            os.replace(temporary_files.pop(path), path)
            replaced.append((path, original, mode))
    except Exception as exc:
        rollback_errors = []
        for path, original, mode in reversed(replaced):
            try:
                rollback = _write_patch_bytes_temp(path, original, mode)
                os.replace(rollback, path)
            except Exception as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        detail = f"Error: patch commit failed: {type(exc).__name__}: {exc}"
        if rollback_errors:
            detail += "; rollback failed for " + ", ".join(rollback_errors)
        return detail
    finally:
        for temporary in temporary_files.values():
            temporary.unlink(missing_ok=True)

    files = ", ".join(path.relative_to(base).as_posix() for path, *_ in staged)
    return f"Patched {len(staged)} file(s), {total_hunks} hunk(s): {files}"


SEARCH_TEXT_TOOL = {
    "name": "search_text",
    "description": (
        "Search the workspace for a string and return matching lines with "
        "'file:line' prefixes. Use it to find where a symbol, prop or "
        "component is defined or used, and to see how this project already "
        "uses a third-party component.\n"
        "query: exact text — prefer a distinctive symbol. path: optional "
        "directory or single file to scope the search. glob: optional file "
        "filter such as '**/*.{vue,ts}'.\n"
        "dist, node_modules, build, coverage and other dependency/build "
        "trees are excluded and cannot be searched. Long lines and large "
        "results are truncated — narrow query, path or glob."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": ("Exact text to search for, e.g. a "
                                      "symbol or prop name.")},
            "path": {
                "type": "string",
                "description": ("Optional subdirectory or single file to "
                                "search within, relative to the workspace "
                                "root."),
            },
            "glob": {"type": "string",
                     "description": ("Optional file-name filter, e.g. "
                                     "'**/*.{vue,ts}'.")},
            "case_sensitive": {"type": "boolean", "default": False,
                               "description": ("True to match case "
                                               "exactly.")},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 500,
                            "default": 100,
                            "description": ("Maximum number of matching "
                                            "lines to return.")},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


APPLY_PATCH_TOOL = {
    "name": "apply_patch",
    "description": (
        "Apply several exact-text hunks to one or more files in a single "
        "transaction: all apply, or nothing changes. Use it for edits in "
        "several places or several files; edit_file is simpler for one.\n"
        "patches: one entry per file — {path, hunks: [{old_text, new_text, "
        "expected_occurrences}], expected_sha256?}. Copy old_text verbatim "
        "from the read_file output. expected_occurrences defaults to 1; set "
        "it to N to replace N identical fragments. expected_sha256 fails "
        "the patch if the file changed since you read it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "patches": {
                "type": "array",
                "description": "One entry per file to change.",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string",
                                 "description": ("File to patch, relative to "
                                                 "the workspace root.")},
                        "expected_sha256": {"type": "string",
                                            "description": ("Optional SHA-256 "
                                                            "of the file as "
                                                            "you read it; the "
                                                            "patch fails if "
                                                            "it changed.")},
                        "hunks": {
                            "type": "array",
                            "description": "The changes to apply to this file.",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "old_text": {"type": "string",
                                                 "description": ("Exact text "
                                                                 "to find, "
                                                                 "copied "
                                                                 "verbatim "
                                                                 "from the "
                                                                 "file.")},
                                    "new_text": {"type": "string",
                                                 "description": ("Replacement "
                                                                 "text.")},
                                    "expected_occurrences": {
                                        "type": "integer", "minimum": 1,
                                        "default": 1,
                                        "description": ("How many times "
                                                        "old_text should be "
                                                        "replaced; defaults "
                                                        "to 1."),
                                    },
                                },
                                "required": ["old_text", "new_text"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["path", "hunks"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["patches"],
        "additionalProperties": False,
    },
}


_shell_processes: set[subprocess.Popen] = set()
_shell_process_lock = threading.RLock()


def _stop_process_group(process: subprocess.Popen):
    """Stop processes that remain in the command's original process group.

    Cross-platform: ``os.killpg`` and ``signal.SIGKILL`` only exist on POSIX,
    so on Windows we fall back to terminating the process directly.
    """
    if hasattr(os, "killpg"):
        for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGKILL", None)):
            if sig is None:
                continue
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                return
            except OSError:
                return
            time.sleep(0.05)
    else:
        try:
            process.terminate()
        except OSError:
            pass
        time.sleep(0.05)
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass


def _stop_all_shell_processes():
    with _shell_process_lock:
        processes = list(_shell_processes)
    for process in processes:
        _stop_process_group(process)


def _handle_termination_signal(signum, _frame):
    _stop_all_shell_processes()
    raise SystemExit(128 + signum)


atexit.register(_stop_all_shell_processes)
signal.signal(signal.SIGTERM, _handle_termination_signal)


_CJK_RANGES = (
    (0x3000, 0x303F), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF), (0xFF00, 0xFFEF),
)


def _cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    hits = sum(1 for ch in text
               if any(low <= ord(ch) <= high for low, high in _CJK_RANGES))
    return hits / len(text)


def _decode_output(data: bytes) -> str:
    """Decode subprocess bytes, picking the codec that yields real CJK text.

    Ordering matters: some legacy-codepage byte pairs are also valid UTF-8
    (the GBK bytes for "目录" decode as "Ŀ¼"), so trying UTF-8 first silently
    mangles Chinese output. Score each candidate by how much CJK it produces
    instead of trusting the first codec that happens to decode.
    """
    if not data:
        return ""
    host = locale.getpreferredencoding(False)
    candidates = ["utf-8"]
    if host and host.lower().replace("-", "") != "utf8":
        candidates.append(host)
    candidates.append("gb18030")

    best_score, best_text = -1.0, ""
    for encoding in candidates:
        try:
            text = data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        score = _cjk_ratio(text)
        if score > best_score:
            best_score, best_text = score, text
        if score > 0:
            break
    if best_score < 0:
        return data.decode("utf-8", errors="replace")
    return best_text


def _run_bash_process(command: str, cwd: Path | None = None) -> tuple[str, int | None]:
    process = None
    try:
        process = subprocess.Popen(
            command, shell=True, cwd=cwd or WORKDIR,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        with _shell_process_lock:
            _shell_processes.add(process)
        raw_out, raw_err = process.communicate(timeout=120)
        out = _decode_output(raw_out + raw_err).strip()
        return (out[:50000] if out else "(no output)"), process.returncode
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)", None
    except OSError as exc:
        return f"Error: {type(exc).__name__}: {exc}", None
    finally:
        if process is not None:
            _stop_process_group(process)
            try:
                process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
            with _shell_process_lock:
                _shell_processes.discard(process)


def _format_bash_result(output: str, exit_code: int | None) -> str:
    if exit_code == 0:
        return output
    if exit_code is None:
        return output
    return f"Error: command exited with status {exit_code}\n{output}"


# Shell commands that dump file contents. Combined with a dependency/build
# path these are the hole in every guarded tool: the guards refuse
# read_file/glob/search_text, and the model simply reaches for `cat`
# (one session ran `dir node_modules\ant-design-vue\es\auto-complete` after
# the read guard fired). Refusing only content-dumping verbs keeps
# legitimate shell work — `npm run build`, `rm -rf dist`, `npx vue-tsc -b`
# — untouched.
_DEPENDENCY_PEEK_RE = re.compile(
    r"(?<![\w./-])(cat|type|head|tail|more|less|sed|awk|grep|egrep|fgrep|"
    r"rg|findstr|bat)(?![\w.-])", re.IGNORECASE)


def _bash_dependency_peek(command: str) -> str:
    """Refuse shell reads of dependency/build trees, and redirect."""
    if not _DEPENDENCY_PEEK_RE.search(command):
        return ""
    lowered = command.lower()
    hit = next((name for name in sorted(SEARCH_IGNORE_DIRS, key=len,
                                        reverse=True)
                if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])",
                             lowered)),
               None)
    if hit is None:
        return ""
    return (
        f"[bash refused: this command reads inside '{hit}'. Dependency and "
        f"build trees are off-limits through every tool, shell included. "
        f"For a third-party library question, this project's own source is "
        f"the authoritative example: use search_text on the project source "
        f"to see how the component is already used, check package.json for "
        f"the installed version, and proceed with the edit.]"
    )


def run_bash(command: str, cwd: Path | None = None,
             run_in_background: bool = False) -> str:
    refusal = _bash_dependency_peek(command)
    if refusal:
        return refusal
    # run_in_background is consumed by the dispatcher; direct execution ignores it.
    return _format_bash_result(*_run_bash_process(command, cwd))


# File-read cache + re-read guard. Serving unchanged files from cache avoids
# re-hitting disk, and (with compaction's working-set preservation) breaks the
# "compact -> re-read -> compact" death spiral that leaves an agent stuck
# re-reading the same file forever. The repeat counter is keyed by
# (path, offset, limit): counting per path alone once refused a legitimate
# follow-up read of the file's second half after a truncated first read.
_FILE_CACHE: dict[str, tuple[float, list[str]]] = {}
_READ_REPEAT: dict[tuple[str, int, int | None], int] = {}
MAX_READ_REPEATS = 3

# Served line ranges per unchanged file, plus a hard cap on dependency-tree
# reads. A weak model evaded the per-range re-read guard by paging through
# the same minified node_modules bundle with different offset/limit combos
# (15 calls in one session, zero edits). Range coverage refuses re-reads the
# context already contains; the dependency cap physically enforces the
# prompt's "rely on library knowledge" rule instead of hoping it is followed.
_READ_SERVED: dict[str, list[tuple[int, int]]] = {}
_DEPENDENCY_READS = 0

# Dependency-tree reads are limited to declaration/doc files only: minified
# implementation code taught the model nothing and burned the context. One
# capped read satisfies the legitimate "verify this prop exists" case while
# making the node_modules rabbit hole physically short.
MAX_DEPENDENCY_READS = 1
DEPENDENCY_READ_LIMIT = 150


def _is_dependency_doc(file_path: Path) -> bool:
    return (file_path.name.endswith(".d.ts")
            or file_path.suffix in {".md", ".json", ".txt"})


def _dependency_refusal(path: str, reason: str) -> str:
    # The refusal must redirect, never invite: an earlier version suggested
    # "read one specific file with read_file", and the model immediately
    # walked that escape hatch into node_modules.
    return (
        f"[read_file refused: {path} — {reason} Dependency and build trees "
        "are off-limits. For questions about a third-party library, this "
        "project's own source is the authoritative example: use search_text "
        "in the project source to see how the component is already used, "
        "check package.json for the installed version, and proceed with "
        "the edit. Do NOT retry this file with different offset/limit or "
        "another file under the same directory.]"
    )


def reset_read_repeat_counters() -> None:
    """Clear re-read guards.

    Called after a full compaction: the compacted summary replaces the older
    file contents, so a re-read is legitimate again and must not be refused
    with "already in your context".
    """
    global _DEPENDENCY_READS
    _READ_REPEAT.clear()
    _READ_SERVED.clear()
    _DEPENDENCY_READS = 0


def _range_covered(served: list[tuple[int, int]], start: int, end: int) -> bool:
    """True when [start, end) is fully covered by previously served ranges."""
    covered_upto = start
    for low, high in sorted(served):
        if low > covered_upto:
            break
        covered_upto = max(covered_upto, high)
    return covered_upto >= end


def _invalidate_file_cache(file_path: Path) -> None:
    key = str(file_path)
    _FILE_CACHE.pop(key, None)
    _READ_SERVED.pop(key, None)
    for range_key in [k for k in _READ_REPEAT if k[0] == key]:
        _READ_REPEAT.pop(range_key, None)


def run_read(path: str, limit: int | None = None,
             offset: int = 0, cwd: Path | None = None) -> str:
    global _DEPENDENCY_READS
    try:
        file_path = safe_path(path, cwd)
        # stat first: a guessed dependency path that does not exist must not
        # consume the budget (one session spent its single allowed .d.ts read
        # on a non-existent file, so the real declaration file was refused).
        mtime = file_path.stat().st_mtime_ns
        if any(part in SEARCH_IGNORE_DIRS for part in file_path.parts):
            if not _is_dependency_doc(file_path):
                return _dependency_refusal(
                    path, "only declaration/doc files (.d.ts, .md, .json, "
                    ".txt) inside dependency trees are ever readable, and "
                    "this is not one.")
            _DEPENDENCY_READS += 1
            if _DEPENDENCY_READS > MAX_DEPENDENCY_READS:
                return _dependency_refusal(
                    path, f"you have already read "
                    f"{MAX_DEPENDENCY_READS} dependency declaration file(s) "
                    f"this session.")
            # Force a line cap so even the one allowed read stays small.
            limit = DEPENDENCY_READ_LIMIT
        cache_key = str(file_path)
        offset = max(int(offset or 0), 0)
        limit_value = None if limit is None else int(limit)
        range_key = (cache_key, offset, limit_value)
        cached = _FILE_CACHE.get(cache_key)
        if cached is not None and cached[0] == mtime:
            lines = cached[1]
            _READ_REPEAT[range_key] = _READ_REPEAT.get(range_key, 0) + 1
        else:
            lines = _read_text_file(file_path).splitlines()
            _FILE_CACHE[cache_key] = (mtime, lines)
            _READ_REPEAT[range_key] = 1
            # The file changed on disk; earlier served ranges describe stale
            # content and must not suppress the fresh read.
            _READ_SERVED.pop(cache_key, None)
        repeat = _READ_REPEAT[range_key]
        if repeat > MAX_READ_REPEATS:
            # The file is unchanged and this exact range has been read enough
            # times already; its contents are in context. Refuse the re-read
            # so the loop stops.
            return (
                f"[read_file {path}: this exact range (offset={offset}, "
                f"limit={limit_value}) has already been read {repeat} times "
                f"and the file is unchanged (mtime stable). Its contents are "
                f"already in your context from the earlier read — do NOT call "
                f"read_file on it again; proceed to edit directly. "
                f"Path: {path}]"
            )
        if repeat > 1:
            # Identical-range re-read of an unchanged file: the earlier copy
            # is already in context (working-set reads survive micro-compact
            # and exact duplicates are collapsed by dedup). Re-sending the
            # content here would double the context cost and defeat that
            # message-level dedup, so serve only the note.
            return (
                f"[read_file cache hit: {path} (offset={offset}, "
                f"limit={limit_value}) unchanged since your earlier read of "
                f"this exact range; that content is already in your context — "
                f"do not re-read; edit directly if needed.]"
            )
        req_end = len(lines) if limit_value is None else min(
            offset + limit_value, len(lines))
        served = _READ_SERVED.get(cache_key)
        if served and _range_covered(served, offset, req_end):
            # A different offset/limit combo whose lines were all served
            # before: re-sending them only buys the model another loop of
            # exploration. Point it back at the content it already has.
            return (
                f"[read_file {path}: lines {offset}-{req_end} are fully "
                f"covered by your earlier reads of this unchanged file; that "
                f"content is already in your context — do not re-read it with "
                f"different offset/limit; proceed to edit directly.]"
            )
        _READ_SERVED.setdefault(cache_key, []).append((offset, req_end))
        segment = lines[offset:]
        if limit_value is not None and limit_value < len(segment):
            segment = segment[:limit_value] + [f"... ({len(segment) - limit_value} more lines)"]
        return "\n".join(segment)
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str, cwd: Path | None = None) -> str:
    try:
        fp = safe_path(path, cwd)
        fp.parent.mkdir(parents=True, exist_ok=True)
        _write_text_file(fp, content)
        _invalidate_file_cache(fp)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str,
             cwd: Path | None = None) -> str:
    try:
        fp = safe_path(path, cwd)
        text = _read_text_file(fp)
        # The model may paste CRLF fragments; the file is normalised to \n.
        needle = old_text.replace("\r\n", "\n").replace("\r", "\n")
        replacement = new_text.replace("\r\n", "\n").replace("\r", "\n")
        if needle not in text:
            hint = _fuzzy_match_hint(text, needle)
            return (f"Error: text not found in {path}. Re-read the file and "
                    f"copy old_text verbatim, including indentation and "
                    f"quotes.{hint}")
        updated = text.replace(needle, replacement, 1)
        _write_text_file(fp, updated)
        _invalidate_file_cache(fp)
        return f"Edited {path}{_remaining_hint(updated, needle, replacement)}"
    except Exception as e:
        return f"Error: {e}"


_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _changed_fragment(old_text: str, new_text: str) -> tuple[str, str]:
    """Return the single identifier that this edit renames, if any.

    A common-prefix/suffix diff is useless for the most common edit of all:
    ``internal_model`` -> ``like_internal_model`` is a pure insertion, so the
    shared ``: string`` suffix swallows the whole fragment and leaves
    nothing to count. Comparing identifier sets names the renamed symbol
    directly.
    """
    old_trimmed, new_trimmed = old_text.strip(), new_text.strip()
    if not old_trimmed or not new_trimmed or old_trimmed == new_trimmed:
        return "", ""
    old_ids = dict.fromkeys(_IDENTIFIER_RE.findall(old_trimmed))
    new_ids = dict.fromkeys(_IDENTIFIER_RE.findall(new_trimmed))
    removed = [name for name in old_ids if name not in new_ids]
    added = [name for name in new_ids if name not in old_ids]
    if len(removed) != 1 or len(added) != 1:
        # Not a plain rename (structural rewrite, or several names at once).
        return "", ""
    return removed[0], added[0]


def _remaining_hint(text: str, old_text: str, new_text: str) -> str:
    """Report untouched occurrences of the fragment that was just renamed.

    A rename usually has to happen everywhere. Without this note the model
    discovers the remaining call sites one edit at a time: one session
    edited, reverted and re-edited the same field across eight turns.
    """
    old_core, new_core = _changed_fragment(old_text, new_text)
    if len(old_core) < 3 or old_core == new_core:
        return ""
    new_spans = []
    cursor = text.find(new_core)
    while cursor >= 0:
        new_spans.append((cursor, cursor + len(new_core)))
        cursor = text.find(new_core, cursor + 1)
    remaining = 0
    cursor = text.find(old_core)
    while cursor >= 0:
        if not any(start <= cursor < stop for start, stop in new_spans):
            remaining += 1
        cursor = text.find(old_core, cursor + 1)
    if not remaining or remaining > 20:
        return ""
    return (f" — note: '{old_core}' still occurs {remaining} more time(s) in "
            f"this file. Update them in the same way, or use apply_patch with "
            f"expected_occurrences to change every occurrence at once.")


def _fuzzy_match_hint(text: str, needle: str) -> str:
    """Explain *why* old_text missed, so the model retries correctly.

    A bare "text not found" made the model re-read the whole file and retry
    with a guess, burning turns. Naming the cause (whitespace-only drift,
    a near-miss that already exists, or a different file) makes the next
    call count.
    """
    lines = text.splitlines()
    needle_lines = needle.splitlines()
    if len(needle_lines) == 1:
        stripped = needle.strip()
        for index, line in enumerate(lines, start=1):
            if line.strip() == stripped:
                return (f" A line with the same content exists at line "
                        f"{index} but with different leading whitespace — "
                        f"copy it exactly as read, indentation included.")
        compact_needle = "".join(needle.split())
        for index, line in enumerate(lines, start=1):
            if "".join(line.split()) == compact_needle:
                return (f" Line {index} matches after ignoring whitespace "
                        f"differences — copy it verbatim from the file.")
        return ""
    first = needle_lines[0].strip()
    for index, line in enumerate(lines, start=1):
        if line.strip() == first:
            window = "\n".join(lines[index - 1:index - 1 + len(needle_lines)])
            if window != needle:
                return (f" Line {index} matches the first line of old_text, "
                        f"but the following lines differ — re-read the file "
                        f"and copy the whole block verbatim.")
            break
    return ""


def run_glob(pattern: str, cwd: Path | None = None) -> str:
    import glob as g
    try:
        base = (cwd or WORKDIR).resolve()
        # A literal (non-wildcard) path part pointing into an excluded dir
        # must return the guard even when nothing matched: a bare
        # "(no matches)" once read as "this file doesn't exist", and the
        # model just probed another node_modules path.
        for part in re.split(r"[\\/]", pattern):
            if ("*" not in part and "?" not in part and "[" not in part
                    and part in SEARCH_IGNORE_DIRS):
                return (
                    "This glob pattern targets an excluded dependency/build "
                    "directory. Dependency trees are not searchable or "
                    "readable. To see how a third-party library is used "
                    "here, search the project source for the component "
                    "name instead."
                )
        kept = []
        excluded = 0
        for match in g.glob(pattern, root_dir=base, recursive=True):
            if not (base / match).resolve().is_relative_to(base):
                continue
            # Build/dependency trees only inject noise: an early `**/foo*`
            # glob once surfaced dist bundle paths, and an explicit
            # node_modules glob handed the model a readable file list that
            # defeated the read guards. Hide them by default.
            if any(part in SEARCH_IGNORE_DIRS for part in PurePath(match).parts):
                excluded += 1
                continue
            kept.append(match)
        if not kept:
            if excluded:
                return (
                    f"All {excluded} matches for this pattern are inside "
                    "excluded dependency/build directories (node_modules, "
                    "dist, build, ...). Dependency trees are not searchable "
                    "or readable. To see how a third-party library is used "
                    "here, search the project source for the component "
                    "name instead."
                )
            return "(no matches)"
        lines = "\n".join(kept)
        if excluded:
            lines += (f"\n({excluded} matches under excluded dependency/build"
                      " directories hidden)")
        return lines
    except Exception as e:
        return f"Error: {e}"


def run_list_dir(path: str = ".", cwd: Path | None = None,
                 max_entries: int = 200) -> str:
    """List directory entries in-process, without going through a shell.

    `ls` is the single most common cross-platform failure: it exists on macOS
    and on Windows only when Git for Windows happens to be on PATH. A built-in
    removes the guess entirely.
    """
    try:
        base = safe_path(path or ".", cwd)
        if not base.exists():
            return f"Error: no such directory: {path}"
        if not base.is_dir():
            return f"Error: not a directory: {path}"
        entries = sorted(base.iterdir(),
                         key=lambda p: (not p.is_dir(), p.name.lower()))
        if not entries:
            return "(empty directory)"
        lines = []
        for entry in entries[:max_entries]:
            if entry.is_dir():
                lines.append(f"{entry.name}/")
            elif entry.is_symlink():
                lines.append(f"{entry.name}@")
            else:
                lines.append(entry.name)
        if len(entries) > max_entries:
            lines.append(f"... ({len(entries) - max_entries} more entries)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def _agent_cwd() -> tuple[Path | None, str | None]:
    # Web conversations select a context-local workspace; CLI/task worktrees
    # continue to use the durable assignment registry as a fallback.
    active = current_workdir()
    if active != WORKDIR:
        return active, None
    try:
        return assignment_cwd("agent"), None
    except (FileNotFoundError, ValueError) as exc:
        return None, f"Error: Invalid task assignment: {exc}"


def run_agent_bash(command: str, run_in_background: bool = False) -> str:
    cwd, error = _agent_cwd()
    return error or run_bash(command, cwd, run_in_background)


def run_agent_read(path: str, limit: int | None = None,
                   offset: int = 0) -> str:
    cwd, error = _agent_cwd()
    return error or run_read(path, limit, offset, cwd)


def run_agent_write(path: str, content: str) -> str:
    cwd, error = _agent_cwd()
    return error or run_write(path, content, cwd)


def run_agent_edit(path: str, old_text: str, new_text: str) -> str:
    cwd, error = _agent_cwd()
    return error or run_edit(path, old_text, new_text, cwd)


def run_agent_glob(pattern: str) -> str:
    cwd, error = _agent_cwd()
    return error or run_glob(pattern, cwd)


def run_agent_list_dir(path: str = ".", max_entries: int = 200) -> str:
    cwd, error = _agent_cwd()
    return error or run_list_dir(path, cwd, max_entries)


def run_agent_search_text(query: str, glob: str | None = None,
                          case_sensitive: bool = False,
                          max_results: int = 100,
                          path: str | None = None) -> str:
    cwd, error = _agent_cwd()
    return error or run_search_text(
        query, glob, case_sensitive, max_results, cwd, path
    )


def run_agent_apply_patch(patches: list[dict]) -> str:
    cwd, error = _agent_cwd()
    return error or run_apply_patch(patches, cwd)


def call_tool_handler(handler, args: dict, name: str) -> str:
    if not handler:
        return f"Unknown tool: {name}"
    if isinstance(args, str):
        # Models or replayed sessions may emit the tool input as a serialized
        # JSON string. Coerce it before dispatch so we don't raise TypeError.
        from ..core.hooks import _coerce_input_value
        args = _coerce_input_value(args)
    kwargs = dict(args or {})
    try:
        params = inspect.signature(handler).parameters
        accepts_kwargs = any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        if not accepts_kwargs:
            # Drop fields the model invented; a TypeError here wastes the round.
            kwargs = {key: value for key, value in kwargs.items()
                      if key in params}
    except (TypeError, ValueError):
        pass
    try:
        return str(handler(**kwargs))
    except Exception as exc:
        return f"Error: {type(exc).__name__}: {exc}"


def _normalize_todos(todos):
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos, list):
        return None, "Error: todos must be a list"
    for i, todo in enumerate(todos):
        if not isinstance(todo, dict):
            return None, f"Error: todos[{i}] must be an object"
        if "content" not in todo or "status" not in todo:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        if todo["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{todo['status']}'"
    return todos, None

def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    print(f"  \033[33m[todo] updated {len(CURRENT_TODOS)} item(s)\033[0m")
    return f"Updated {len(CURRENT_TODOS)} todos"


# -- MessageBus and Team Protocols --
