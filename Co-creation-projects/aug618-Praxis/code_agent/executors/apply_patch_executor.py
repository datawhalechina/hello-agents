from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class PatchApplyError(RuntimeError):
    """
    补丁应用过程中发生的异常类。
    用于封装补丁应用失败的原因，并提供额外的检查目标信息。
    
    参数:
        message: 错误消息，描述补丁应用失败的原因
        recheck_targets: 可选的重新检查目标列表，用于辅助调试和修复补丁问题
    """
    def __init__(self, message: str, recheck_targets: Optional[List[str]] = None):
        super().__init__(message)
        self.recheck_targets = recheck_targets or []


@dataclass
class ApplyResult:
    """
    补丁应用结果的数据类。
    用于返回补丁应用过程中产生的变更信息和备份信息。
    
    字段:
        files_changed: 被修改的文件路径列表（相对路径）
        backups: 创建的备份文件路径列表（绝对路径）
    """
    files_changed: List[str]
    backups: List[str]


class ApplyPatchExecutor:
    """
    应用 Codex 风格的 *** Begin Patch 格式补丁。

    安全特性 (MVP):
    - repo_root 路径限制 (防止路径逃逸)
    - 通过临时文件 + os.replace 实现原子写入
    - 备份到 <repo_root>/.helloagents/backups/<timestamp>/
    - 大小限制 (最大文件数, 最大总变更行数)
    - Update File 块的冲突检测 (精确匹配)
    """

    def __init__(
        self,
        repo_root: Path,
        max_files: int = 10,
        max_total_changed_lines: int = 800,
        allowed_write_suffixes: Optional[List[str]] = None,
    ):
        """
        初始化补丁应用执行器。
        
        参数:
            repo_root: 代码仓库根目录路径，所有补丁操作都限制在此目录内
            max_files: 单个补丁允许修改的最大文件数量，默认10个
            max_total_changed_lines: 单个补丁允许修改的最大总行数，默认800行
            allowed_write_suffixes: 允许修改的文件后缀列表，默认只允许常见文本文件
        """
        self.repo_root = repo_root
        self.max_files = max_files
        self.max_total_changed_lines = max_total_changed_lines
        
        # 默认允许写入的文件后缀，防止意外修改二进制文件或敏感文件
        self.allowed_write_suffixes = allowed_write_suffixes or [
            ".py",
            ".md",
            ".toml",
            ".json",
            ".yml",
            ".yaml",
            ".txt",
            ".html",
            ".htm",
            ".css",
            ".js",
        ]

        # 初始化工作目录和备份目录
        self.root_dir = repo_root / ".helloagents"
        self.backups_dir = self.root_dir / "backups"
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def apply(self, patch_text: str) -> ApplyResult:
        """
        解析并应用补丁文本。
        
        执行流程：
        1. 解析补丁操作 (Add/Update/Delete)
        2. 检查安全限制 (文件数量, 变更行数)
        3. 创建备份目录
        4. 逐个执行操作 (先备份再修改)
        
        参数:
            patch_text: 符合 Codex 风格的补丁文本，以 *** Begin Patch 开始，*** End Patch 结束
            
        返回:
            ApplyResult: 包含被修改文件和备份文件信息的结果对象
            
        异常:
            PatchApplyError: 当补丁不符合格式、超出限制或应用失败时抛出
        """
        # 解析补丁文本，提取操作列表
        ops = self._parse_patch(patch_text)
        
        # 统计受影响的文件数量，检查是否超过限制
        touched_files = [op[1] for op in ops if op[0] in {"add", "update", "delete"}]
        if len(set(touched_files)) > self.max_files:
            raise PatchApplyError(f"Too many files in patch: {len(set(touched_files))} > {self.max_files}")

        # 估算补丁修改的总行数，检查是否超过限制
        total_changed = self._estimate_changed_lines(ops)
        if total_changed > self.max_total_changed_lines:
            raise PatchApplyError(f"Patch too large: {total_changed} changed lines > {self.max_total_changed_lines}")

        # 创建本次补丁应用的专属备份目录（时间戳命名）
        backup_run_dir = self.backups_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_run_dir.mkdir(parents=True, exist_ok=True)

        # 初始化结果收集变量
        files_changed: List[str] = []  # 记录被修改的文件路径
        backups: List[str] = []  # 记录创建的备份文件路径

        # 遍历所有解析出的操作，逐个执行
        for kind, rel_path, payload in ops:
            # 安全检查：确保路径在仓库内，防止路径遍历攻击
            target = self._safe_path(rel_path)
            
            # 安全检查：确保文件后缀在允许的列表中
            self._enforce_suffix(target)

            if kind == "add":
                # 添加新文件操作
                if target.exists():
                    raise PatchApplyError(f"Add File target already exists: {rel_path}")
                # 创建父目录（如果不存在）
                target.parent.mkdir(parents=True, exist_ok=True)
                # 原子写入新文件内容
                self._atomic_write(target, payload)
                # 记录变更
                files_changed.append(rel_path)
                
            elif kind == "delete":
                # 删除文件操作
                if not target.exists():
                    raise PatchApplyError(f"Delete File target missing: {rel_path}")
                # 删除前先备份文件
                b = self._backup_file(target, backup_run_dir)
                backups.append(str(b))
                # 删除文件
                target.unlink()
                # 记录变更
                files_changed.append(rel_path)
                
            elif kind == "update":
                # 更新文件操作
                if not target.exists():
                    raise PatchApplyError(f"Update File target missing: {rel_path}")
                # 读取原始文件内容（保留换行符）
                original = target.read_text(encoding="utf-8").splitlines(keepends=True)
                # 修改前先备份文件
                b = self._backup_file(target, backup_run_dir)
                backups.append(str(b))
                # 应用更新补丁内容
                updated = self._apply_update_payload(original, payload, rel_path)
                # 原子写入更新后的内容
                self._atomic_write(target, "".join(updated))
                # 记录变更
                files_changed.append(rel_path)
                
            else:
                # 未知操作类型
                raise PatchApplyError(f"Unknown op kind: {kind}")

        # 返回最终的应用结果
        return ApplyResult(files_changed=files_changed, backups=backups)

    def _safe_path(self, rel_path: str) -> Path:
        """
        验证路径安全性，防止路径遍历攻击 (Path Traversal)。
        确保目标路径在 repo_root 目录下，防止访问仓库外的文件。
        
        参数:
            rel_path: 相对路径字符串
            
        返回:
            Path: 安全的绝对路径对象
            
        异常:
            PatchApplyError: 当路径是绝对路径、包含特殊字符或试图访问仓库外时抛出
        """
        if rel_path.startswith("/") or rel_path.startswith("~"):
            raise PatchApplyError(f"Absolute paths are not allowed: {rel_path}")
        target = (self.repo_root / rel_path).resolve()
        # 检查解析后的路径是否以 repo_root 开头
        if not str(target).startswith(str(self.repo_root.resolve()) + os.sep) and target != self.repo_root.resolve():
            raise PatchApplyError(f"Path escapes repo_root: {rel_path}")
        if target.exists() and target.is_symlink():
            raise PatchApplyError(f"Refusing to modify symlink: {rel_path}")
        return target

    def _enforce_suffix(self, target: Path) -> None:
        """
        检查目标文件的后缀是否在允许的列表中。
        防止意外修改二进制文件、配置文件或其他敏感文件。
        
        参数:
            target: 目标文件路径对象
            
        异常:
            PatchApplyError: 当文件后缀不在允许列表中时抛出
        """
        if target.suffix and target.suffix not in self.allowed_write_suffixes:
            raise PatchApplyError(f"Disallowed file suffix for write: {target.suffix}")

    def _backup_file(self, target: Path, backup_run_dir: Path) -> Path:
        """
        备份目标文件到指定的备份目录。
        备份文件保持与原文件相同的相对路径结构，后缀添加 .bak。
        
        参数:
            target: 要备份的目标文件路径
            backup_run_dir: 本次运行的备份目录
            
        返回:
            Path: 创建的备份文件路径
        """
        # 获取文件相对于仓库根目录的路径
        rel = target.relative_to(self.repo_root)
        # 构建备份文件路径
        backup_path = backup_run_dir / (str(rel) + ".bak")
        # 创建备份文件的父目录（如果不存在）
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        # 复制文件内容到备份文件
        backup_path.write_bytes(target.read_bytes())
        return backup_path

    def _atomic_write(self, target: Path, content: str) -> None:
        """
        原子写入文件内容。
        先写入临时文件，然后使用 os.replace 原子性替换目标文件，确保写入过程不会因为中断而导致文件损坏。
        
        参数:
            target: 目标文件路径
            content: 要写入的文件内容
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(target.parent), encoding="utf-8") as tf:
            tf.write(content)
            tf.flush()
            os.fsync(tf.fileno())
            tmp_name = tf.name
        os.replace(tmp_name, target)

    def _parse_patch(self, text: str) -> List[Tuple[str, str, str]]:
        """
        解析补丁文本，提取操作列表。
        支持的操作：
        - *** Add File: <path> - 添加新文件
        - *** Delete File: <path> - 删除文件
        - *** Update File: <path> - 更新文件内容
        
        参数:
            text: 补丁文本字符串
            
        返回:
            List[Tuple[str, str, str]]: 操作列表，每个操作包含(操作类型, 路径, 内容)
            
        异常:
            PatchApplyError: 当补丁格式不符合要求时抛出
        """
        lines = text.splitlines()
        # 宽容处理：跳过前置空行/代码块围栏，找到真正的开头
        while lines and lines[0].strip() in {"", "```", "```patch", "```diff", "```text"}:
            lines = lines[1:]
        # 如果仍未以标头开头，尝试向下寻找标头并截取
        if lines and lines[0].strip() != "*** Begin Patch":
            for idx, l in enumerate(lines):
                if l.strip() == "*** Begin Patch":
                    lines = lines[idx:]
                    break
        if not lines or lines[0].strip() != "*** Begin Patch":
            raise PatchApplyError("Patch must start with '*** Begin Patch'")
        # 同样跳过结尾的围栏/空行
        while lines and lines[-1].strip() in {"", "```"}:
            lines = lines[:-1]
        if not lines or lines[-1].strip() != "*** End Patch":
            # 如果末尾未对齐，尝试在中间找到最后一个 End 标记
            for idx in range(len(lines) - 1, -1, -1):
                if lines[idx].strip() == "*** End Patch":
                    lines = lines[: idx + 1]
                    break
        if not lines or lines[-1].strip() != "*** End Patch":
            raise PatchApplyError("Patch must end with '*** End Patch'")

        ops: List[Tuple[str, str, str]] = []
        i = 1
        while i < len(lines) - 1:
            line = lines[i]
            if line.startswith("*** Add File: "):
                path = line[len("*** Add File: ") :].strip()
                i += 1
                buf: List[str] = []
                while i < len(lines) - 1 and not lines[i].startswith("*** "):
                    # 兼容两种格式：
                    # 1) 规范形式：以 '+' 开头
                    # 2) 宽松形式：直接给出正文（模型有时会省略 '+')
                    if lines[i].startswith("+"):
                        buf.append(lines[i][1:] + "\n")
                    else:
                        buf.append(lines[i] + "\n")
                    i += 1
                ops.append(("add", path, "".join(buf)))
                continue
            if line.startswith("*** Delete File: "):
                path = line[len("*** Delete File: ") :].strip()
                ops.append(("delete", path, ""))
                i += 1
                continue
            if line.startswith("*** Update File: "):
                path = line[len("*** Update File: ") :].strip()
                i += 1
                buf: List[str] = []
                while i < len(lines) - 1 and not lines[i].startswith("*** "):
                    buf.append(lines[i])
                    i += 1
                ops.append(("update", path, "\n".join(buf)))
                continue
            if line.strip() == "":
                i += 1
                continue
            raise PatchApplyError(f"Unexpected patch line: {line}")

        return ops

    def _estimate_changed_lines(self, ops: List[Tuple[str, str, str]]) -> int:
        """
        估算补丁操作的总变更行数。
        用于检查补丁大小是否超过限制。
        
        参数:
            ops: 补丁操作列表
            
        返回:
            int: 估算的总变更行数
        """
        changed = 0
        for kind, _, payload in ops:
            if kind == "add":
                # 添加文件：按行数计算
                changed += payload.count("\n")
            elif kind == "delete":
                # 删除文件：按1行计算
                changed += 1
            elif kind == "update":
                # 更新文件：只计算+/-开头的变更行
                for l in payload.splitlines():
                    if l.startswith("+") or l.startswith("-"):
                        changed += 1
        return changed

    def _apply_update_payload(self, original: List[str], payload: str, rel_path: str) -> List[str]:
        """
        应用 Update File 的内容。
        将 payload 分割成多个 hunk (代码块)，然后逐个应用。
        """
        # 兼容宽松格式：如果 payload 没有任何 + / - / 前导空格行，视为“整文件替换”
        raw_lines = payload.splitlines(keepends=True)
        if raw_lines and all(not l.startswith(("+", "-", " ")) for l in raw_lines):
            return raw_lines

        hunks = self._split_hunks(payload)
        current = original
        try:
            for hunk in hunks:
                current = self._apply_hunk(current, hunk, rel_path)
            return current
        except PatchApplyError as e:
            # 宽松兜底：当上下文匹配失败时，尝试将 payload 视作“新的完整文件”生成 after 版本
            if "context not found" not in str(e).lower():
                raise
            fallback = self._hunks_to_after(hunks)
            if fallback:
                return fallback
            raise

    def _split_hunks(self, payload: str) -> List[List[str]]:
        """
        将 Update File 的 payload 分割成多个 hunk（代码块）。
        Hunk 通常由 @@ ... @@ 分隔符分隔，或者由空行分隔。
        每个 hunk 代表文件的一个修改区域。
        
        参数:
            payload: Update File 操作的内容
            
        返回:
            List[List[str]]: hunk 列表，每个 hunk 是多行字符串的列表
        """
        lines = payload.splitlines()
        hunks: List[List[str]] = []
        buf: List[str] = []
        for l in lines:
            if l.startswith("@@"):
                if buf:
                    hunks.append(buf)
                    buf = []
                continue
            if l.strip() == "" and buf:
                hunks.append(buf)
                buf = []
                continue
            buf.append(l)
        if buf:
            hunks.append(buf)
        return [h for h in hunks if any(x.startswith((" ", "+", "-")) for x in h)]

    def _apply_hunk(self, current: List[str], hunk_lines: List[str], rel_path: str) -> List[str]:
        """
        应用单个 hunk（代码块）到当前文件内容。
        
        原理：
        1. 解析 hunk，分离出 'before' (上下文 + 删除行) 和 'after' (上下文 + 新增行)
        2. 在当前文件中查找 'before' 块的精确位置
        3. 如果找到匹配的上下文，用 'after' 块替换 'before' 块
        4. 如果找不到匹配的上下文，抛出异常
        
        参数:
            current: 当前文件的内容行列表
            hunk_lines: hunk 的内容行列表
            rel_path: 文件的相对路径（用于错误提示）
            
        返回:
            List[str]: 应用 hunk 后的文件内容行列表
            
        异常:
            PatchApplyError: 当 hunk 格式错误或找不到匹配的上下文时抛出
        """
        before: List[str] = []
        after: List[str] = []
        for l in hunk_lines:
            if not l:
                continue
            tag = l[0]
            text = l[1:] + "\n"
            if tag == " ":
                before.append(text)
                after.append(text)
            elif tag == "-":
                before.append(text)
            elif tag == "+":
                after.append(text)

        if not before:
            raise PatchApplyError("Update hunk has no context/removals; refusing to apply")

        idx = self._find_subsequence(current, before)
        if idx is None:
            context_line = next((b.strip() for b in before if b.strip()), "")
            hint = f"{rel_path}:search:'{context_line[:80]}'"
            raise PatchApplyError("Patch hunk context not found; file changed?", recheck_targets=[hint])

        return current[:idx] + after + current[idx + len(before) :]

    def _find_subsequence(self, haystack: List[str], needle: List[str]) -> Optional[int]:
        """
        在文件内容中查找代码块的起始位置。
        使用简单的 O(N*M) 字符串匹配算法，在 haystack 中查找 needle 的精确匹配。
        
        参数:
            haystack: 文件内容行列表
            needle: 要查找的代码块行列表
            
        返回:
            Optional[int]: 匹配的起始行索引，如果未找到则返回 None
        """
        if len(needle) > len(haystack):
            return None
        for i in range(0, len(haystack) - len(needle) + 1):
            if haystack[i : i + len(needle)] == needle:
                return i
        # 宽松匹配：忽略行尾空白再尝试一次，缓解缩进/换行轻微偏差
        norm_hay = [h.rstrip() + "\n" for h in haystack]
        norm_need = [n.rstrip() + "\n" for n in needle]
        for i in range(0, len(norm_hay) - len(norm_need) + 1):
            if norm_hay[i : i + len(norm_need)] == norm_need:
                return i
        return None

    def _hunks_to_after(self, hunks: List[List[str]]) -> List[str]:
        """
        将多个 hunk 的“after”部分合成为一份完整文件内容。
        用于上下文匹配失败时的宽松回退：保留 + 和空格行，忽略 - 行。
        """
        out: List[str] = []
        for hunk in hunks:
            for l in hunk:
                if not l:
                    continue
                tag = l[0]
                text = l[1:] + "\n" if len(l) > 1 else "\n"
                if tag == "-" or tag == "@":
                    continue
                if tag in (" ", "+"):
                    out.append(text)
        return out
