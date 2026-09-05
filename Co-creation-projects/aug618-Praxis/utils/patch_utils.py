"""补丁处理工具（与 CLI/TUI 共用）。"""

from __future__ import annotations

import re

# 匹配 Codex 风格补丁块（宽松，跨行，允许前导空白或代码围栏）
PATCH_RE = re.compile(r"\s*\*\*\* Begin Patch[\s\S]*?\*\*\* End Patch", re.MULTILINE)
# 备用：从 ```patch/```diff 围栏中提取补丁主体
PATCH_FENCE_RE = re.compile(
    r"```(?:patch|diff|text)?\s*(\*\*\* Begin Patch[\s\S]*?\*\*\* End Patch)\s*```",
    re.MULTILINE,
)


def extract_patch(text: str) -> str | None:
    """从文本中提取补丁块。"""
    m = PATCH_FENCE_RE.search(text)
    if m:
        return m.group(1)
    m = PATCH_RE.search(text)
    return m.group(0).strip() if m else None


def normalize_patch(patch_text: str) -> str:
    """规范化补丁格式（容错处理模型输出）。"""
    lines = patch_text.splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("Add File:", "Update File:", "Delete File:")) and not stripped.startswith("*** "):
            out.append("*** " + stripped)
            continue
        out.append(line)
    return "\n".join(out)


def patch_requires_confirmation(patch_text: str) -> bool:
    """判断补丁是否需要用户确认。"""
    if "*** Delete File:" in patch_text:
        return True
    file_ops = patch_text.count("*** Add File:") + patch_text.count("*** Update File:") + patch_text.count("*** Delete File:")
    if file_ops >= 6:
        return True
    changed_lines = 0
    for line in patch_text.splitlines():
        if line.startswith("+") or line.startswith("-"):
            changed_lines += 1
    return changed_lines >= 400
