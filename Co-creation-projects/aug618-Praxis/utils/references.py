"""Reference parser for @ syntax.

Supports:
- @path/to/file.py - file reference (simplified syntax)
- @src/ - directory reference (trailing slash)
- @file(path) - legacy file syntax (still supported)
- @dir(path) - legacy dir syntax (still supported)
- Multiple references: @core/llm.py @utils/ 比较这两个

Image extensions are treated as multimodal attachments.
Text/code files are injected into context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .multimodal import image_part_from_path

# Image extensions that should be sent as multimodal attachments
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"}

# Text/code extensions we can safely read
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".cs",
    ".html", ".css", ".scss", ".less", ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg",
    ".md", ".txt", ".rst", ".tex", ".log",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".sql", ".graphql", ".proto",
    ".dockerfile", ".gitignore", ".env.example",
}

# Max file size to read (prevent huge files from blowing up context)
MAX_FILE_SIZE = 100 * 1024  # 100KB
MAX_DIR_FILES = 20  # Max files to include from a directory
MAX_DIR_DEPTH = 3   # Max depth for directory traversal


@dataclass
class ParsedReferences:
    """Result of parsing @file/@dir references from user input."""
    clean_query: str  # User query with references removed
    image_attachments: List[Dict[str, Any]] = field(default_factory=list)
    image_paths: List[Path] = field(default_factory=list)  # 原始图片路径（用于 OCR）
    context_blocks: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def parse_references(
    user_input: str,
    workspace: str | Path,
) -> ParsedReferences:
    """
    Parse @ references from user input.
    
    Supports two syntaxes:
    1. Simplified: @path/to/file.py or @src/ (directory with trailing /)
    2. Legacy: @file(path) or @dir(path)
    
    Args:
        user_input: Raw user input with potential @ references
        workspace: Base directory for resolving relative paths
        
    Returns:
        ParsedReferences with attachments, context blocks, and cleaned query
    """
    workspace = Path(workspace).resolve()
    result = ParsedReferences(clean_query=user_input)
    
    # Track all matched spans to remove later
    remove_spans: List[Tuple[int, int]] = []
    
    # Pattern 1: Legacy @file(paths) or @dir(paths)
    legacy_pattern = r'@(file|dir)\(([^)]+)\)'
    for match in re.finditer(legacy_pattern, user_input, re.IGNORECASE):
        remove_spans.append((match.start(), match.end()))
        ref_type = match.group(1).lower()
        paths_str = match.group(2).strip()
        paths = _split_paths(paths_str)
        
        for ref_path in paths:
            ref_path = ref_path.strip().strip("\"'")
            if not ref_path:
                continue
            full_path = (workspace / ref_path).resolve()
            try:
                full_path.relative_to(workspace)
            except ValueError:
                result.errors.append(f"路径不在工作目录内: {ref_path}")
                continue
            
            if ref_type == "file":
                _process_file(full_path, ref_path, result)
            else:
                _process_dir(full_path, ref_path, workspace, result)
    
    # Pattern 2: Simplified @path (not followed by file/dir parenthesis)
    # Match @followed by path characters until whitespace or end
    # Path can contain: letters, numbers, /, ., _, -, but not @
    simple_pattern = r'@(?!file\(|dir\()([a-zA-Z0-9_./-]+)'
    for match in re.finditer(simple_pattern, user_input):
        # Skip if this overlaps with a legacy match
        start, end = match.start(), match.end()
        if any(s <= start < e or s < end <= e for s, e in remove_spans):
            continue
        
        remove_spans.append((start, end))
        ref_path = match.group(1).strip()
        if not ref_path:
            continue
        
        full_path = (workspace / ref_path).resolve()
        try:
            full_path.relative_to(workspace)
        except ValueError:
            result.errors.append(f"路径不在工作目录内: {ref_path}")
            continue
        
        # Auto-detect: directory (ends with / or is a dir) vs file
        if ref_path.endswith("/") or full_path.is_dir():
            _process_dir(full_path, ref_path, workspace, result)
        else:
            _process_file(full_path, ref_path, result)
    
    # Remove all references from the query
    # Sort spans in reverse order to remove from end first
    remove_spans.sort(reverse=True)
    clean = user_input
    for start, end in remove_spans:
        clean = clean[:start] + clean[end:]
    
    # Clean up extra whitespace
    result.clean_query = " ".join(clean.split()).strip()
    
    # If query is empty after removing references, provide a default
    if not result.clean_query:
        if result.image_attachments:
            result.clean_query = "请描述这些图片的内容"
        elif result.context_blocks:
            result.clean_query = "请分析这些文件/目录的内容"
    
    return result


def _split_paths(paths_str: str) -> List[str]:
    """
    Split a paths string by comma, Chinese comma, or semicolon.
    Handles quoted paths with spaces.
    
    Examples:
        "a.py, b.py" -> ["a.py", "b.py"]
        "a.py、b.py" -> ["a.py", "b.py"]
        '"path with spaces/a.py", b.py' -> ["path with spaces/a.py", "b.py"]
    """
    # Separators: comma, Chinese comma, semicolon
    separators = [",", "、", ";", "；"]
    
    # Simple case: no quotes
    if '"' not in paths_str and "'" not in paths_str:
        for sep in separators:
            if sep in paths_str:
                return [p.strip() for p in paths_str.split(sep) if p.strip()]
        # No separator found, single path
        return [paths_str.strip()] if paths_str.strip() else []
    
    # Complex case: handle quotes
    paths: List[str] = []
    current = ""
    in_quote = None
    
    for char in paths_str:
        if char in ('"', "'") and in_quote is None:
            in_quote = char
        elif char == in_quote:
            in_quote = None
        elif char in separators and in_quote is None:
            if current.strip():
                paths.append(current.strip().strip("\"'"))
            current = ""
            continue
        current += char
    
    if current.strip():
        paths.append(current.strip().strip("\"'"))
    
    return paths


def _process_file(full_path: Path, display_path: str, result: ParsedReferences) -> None:
    """Process a single file reference."""
    if not full_path.exists():
        result.errors.append(f"文件不存在: {display_path}")
        return
    
    if not full_path.is_file():
        result.errors.append(f"不是文件: {display_path}")
        return
    
    suffix = full_path.suffix.lower()
    
    # Image file -> multimodal attachment + save path for OCR fallback
    if suffix in IMAGE_EXTENSIONS:
        try:
            attachment = image_part_from_path(full_path)
            result.image_attachments.append(attachment)
            result.image_paths.append(full_path)  # 保存原始路径，用于 OCR 降级
            result.context_blocks.append(f"[图片: {display_path}]")
        except Exception as e:
            result.errors.append(f"无法读取图片 {display_path}: {e}")
        return
    
    # Text/code file -> context block
    if suffix in TEXT_EXTENSIONS or suffix == "" or _is_likely_text(full_path):
        try:
            size = full_path.stat().st_size
            if size > MAX_FILE_SIZE:
                content = full_path.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_SIZE]
                content += f"\n\n... (文件过大，已截断，原始大小: {size} bytes)"
            else:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
            
            block = f"--- @file({display_path}) ---\n```{_get_language(suffix)}\n{content}\n```"
            result.context_blocks.append(block)
        except Exception as e:
            result.errors.append(f"无法读取文件 {display_path}: {e}")
        return
    
    # Unknown extension - try to read as text
    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        if len(content) > MAX_FILE_SIZE:
            content = content[:MAX_FILE_SIZE] + "\n\n... (已截断)"
        block = f"--- @file({display_path}) ---\n```\n{content}\n```"
        result.context_blocks.append(block)
    except Exception:
        result.errors.append(f"无法读取文件（可能是二进制）: {display_path}")


def _process_dir(
    full_path: Path,
    display_path: str,
    workspace: Path,
    result: ParsedReferences,
) -> None:
    """Process a directory reference."""
    if not full_path.exists():
        result.errors.append(f"目录不存在: {display_path}")
        return
    
    if not full_path.is_dir():
        result.errors.append(f"不是目录: {display_path}")
        return
    
    # Build directory tree
    tree_lines = [f"--- @dir({display_path}) ---", "目录结构:"]
    tree_lines.extend(_build_tree(full_path, prefix="", depth=0, max_depth=MAX_DIR_DEPTH))
    
    # Collect key files to include content
    key_files: List[Path] = []
    for f in _iter_files(full_path, max_depth=MAX_DIR_DEPTH):
        if len(key_files) >= MAX_DIR_FILES:
            break
        suffix = f.suffix.lower()
        if suffix in TEXT_EXTENSIONS or f.name in {"Makefile", "Dockerfile", "README", "LICENSE"}:
            key_files.append(f)
    
    # Add file contents
    file_blocks: List[str] = []
    for f in key_files[:MAX_DIR_FILES]:
        try:
            rel = f.relative_to(full_path)
            size = f.stat().st_size
            if size > MAX_FILE_SIZE // 2:  # Smaller limit for dir files
                content = f.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_SIZE // 2]
                content += "\n... (已截断)"
            else:
                content = f.read_text(encoding="utf-8", errors="ignore")
            
            lang = _get_language(f.suffix.lower())
            file_blocks.append(f"## {rel}\n```{lang}\n{content}\n```")
        except Exception:
            continue
    
    # Combine tree + files
    block = "\n".join(tree_lines)
    if file_blocks:
        block += "\n\n关键文件内容:\n" + "\n\n".join(file_blocks)
    
    result.context_blocks.append(block)


def _build_tree(path: Path, prefix: str, depth: int, max_depth: int) -> List[str]:
    """Build a tree representation of a directory."""
    if depth >= max_depth:
        return [f"{prefix}... (deeper levels omitted)"]
    
    lines: List[str] = []
    try:
        entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except PermissionError:
        return [f"{prefix}(permission denied)"]
    
    # Filter out hidden and common ignored dirs
    ignored = {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}
    entries = [e for e in entries if not e.name.startswith(".") or e.name in {".gitignore", ".env.example"}]
    entries = [e for e in entries if e.name not in ignored]
    
    for i, entry in enumerate(entries[:30]):  # Limit entries per level
        is_last = i == len(entries) - 1 or i == 29
        connector = "└── " if is_last else "├── "
        
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if is_last else "│   "
            lines.extend(_build_tree(entry, prefix + extension, depth + 1, max_depth))
        else:
            lines.append(f"{prefix}{connector}{entry.name}")
    
    if len(entries) > 30:
        lines.append(f"{prefix}... ({len(entries) - 30} more items)")
    
    return lines


def _iter_files(path: Path, max_depth: int, current_depth: int = 0) -> List[Path]:
    """Iterate files in a directory up to max_depth."""
    if current_depth >= max_depth:
        return []
    
    files: List[Path] = []
    try:
        for entry in path.iterdir():
            if entry.name.startswith(".") and entry.name not in {".gitignore", ".env.example"}:
                continue
            if entry.name in {"node_modules", "__pycache__", ".git", "venv", ".venv"}:
                continue
            if entry.is_file():
                files.append(entry)
            elif entry.is_dir():
                files.extend(_iter_files(entry, max_depth, current_depth + 1))
    except PermissionError:
        pass
    return files


def _is_likely_text(path: Path) -> bool:
    """Heuristic: check if file is likely text by reading first bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
        # If it contains null bytes, probably binary
        return b"\x00" not in chunk
    except Exception:
        return False


def _get_language(suffix: str) -> str:
    """Map file suffix to markdown code block language."""
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".cs": "csharp",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".vue": "vue",
        ".svelte": "svelte",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".md": "markdown",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".sql": "sql",
        ".graphql": "graphql",
        ".proto": "protobuf",
    }
    return mapping.get(suffix, "")
