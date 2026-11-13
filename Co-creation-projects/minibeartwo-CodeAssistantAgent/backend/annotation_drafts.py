"""Durable per-function comment drafts, assembled and checked before any write."""
from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import tokenize
from pathlib import Path

from .skills import FILE_HEADER_FIELDS, validate_annotation_change
from .store import identifier
from .workspace import Conflict, MAX_FILE


UNIT_CHARS = 22_000
HEADER_KEYS = ("purpose", "input_files", "inputs", "output_files", "outputs")
FUNCTION_KEYS = ("purpose", "inputs", "outputs")
FUNCTION_LABELS = ("函数用途", "输入说明", "输出说明")
METADATA = re.compile(r"#\s*(代码用途|输入文件|输入说明|输出文件|输出说明|函数用途)\s*[:：]")
PROTECTED = re.compile(r"copyright|版权|SPDX-License-Identifier|#\s*(?:type\s*:|noqa\b|"
                       r"noinspection\b|pragma\b|pylint\b|pyright\b|mypy\b|ruff\b|fmt\s*:|"
                       r"isort\s*:|yapf\s*:|doctest\s*:|nosec\b)", re.I)


def encoded_size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False))


class AnnotationDrafts:
    def __init__(self, store, task_id: str, workspace):
        self.store, self.task_id, self.workspace = store, task_id, workspace
        self.owner = identifier()
        with store.connect() as db:
            if db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                db.execute("INSERT INTO annotation_draft_owners(task_id,owner) VALUES(?,?) "
                           "ON CONFLICT(task_id) DO UPDATE SET owner=excluded.owner", (task_id, self.owner))

    def _save(self, path: str, hash_value: str, state: dict):
        with self.store.connect() as db:
            owner = db.execute("SELECT owner FROM annotation_draft_owners WHERE task_id=?", (self.task_id,)).fetchone()
            if not owner or owner["owner"] != self.owner or not db.execute(
                    "SELECT 1 FROM tasks WHERE id=?", (self.task_id,)).fetchone():
                raise Conflict("旧执行轮次或已删除任务不能保存注释草稿，请重新选择任务。")
            db.execute("INSERT INTO annotation_drafts(task_id,path,base_hash,state) VALUES(?,?,?,?) "
                       "ON CONFLICT(task_id,path) DO UPDATE SET base_hash=excluded.base_hash,state=excluded.state",
                       (self.task_id, path, hash_value, json.dumps(state, ensure_ascii=False)))

    def _file(self, path: str) -> dict:
        file = self.workspace.read(path)
        if Path(file["path"]).suffix.lower() not in {".py", ".pyi"}:
            raise ValueError("分函数注释草稿仅支持现有 Python 源文件。")
        return file

    def _load(self, file: dict, *, reset: bool) -> tuple[dict, bool]:
        rows = self.store.rows("SELECT base_hash,state FROM annotation_drafts WHERE task_id=? AND path=?",
                               (self.task_id, file["path"]))
        state = json.loads(rows[0]["state"]) if rows else {"documents": {}}
        changed = bool(rows and rows[0]["base_hash"] != file["hash"])
        if changed and not reset:
            raise Conflict("注释草稿基线已变化，尚未写入；请重新准备当前文件。")
        if changed or state.get("consumed"):
            state = {"documents": {}}
        # A hard stop between apply and finish must not replay drafts after undo.
        if reset:
            reverted = {row["id"] for row in self.store.rows(
                "SELECT id,changes FROM patches WHERE task_id=? AND status='reverted'", (self.task_id,))
                if any(change.get("path") == file["path"] and change.get("before_hash") == file["hash"]
                       for change in json.loads(row["changes"]))}
            if reverted - set(state.get("reverted_seen", [])):
                state = {"documents": {}, "reverted_seen": sorted(reverted)}
                changed = True
        return state, changed

    def _plan(self, file: dict) -> tuple[list[dict], list[str], dict]:
        text = file["content"]
        source = text[1:] if text.startswith("\ufeff") else text
        try:
            tree = ast.parse(source, filename=file["path"])
            tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        except (SyntaxError, tokenize.TokenError) as exc:
            raise ValueError("原文件存在语法或分词错误，不能安全构建分函数注释草稿。") from exc
        lines = source.splitlines(keepends=True)
        comments = {item.start[0] - 1: item for item in tokens if item.type == tokenize.COMMENT
                    and not lines[item.start[0] - 1][:item.start[1]].strip()}
        functions = []

        def visit(node, scope=""):
            current_scope = scope
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                current_scope = f"{scope}.{node.name}" if scope else node.name
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)]) - 1
                parameters = [p.arg for p in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]]
                if node.args.vararg:
                    parameters.append("*" + node.args.vararg.arg)
                if node.args.kwarg:
                    parameters.append("**" + node.args.kwarg.arg)
                functions.append({"kind": "function", "name": current_scope, "parameters": parameters,
                                  "line": start, "end_line": node.end_lineno,
                                  "definition_line": node.lineno,
                                  "indent": re.match(r"[ \t]*", lines[start]).group()})
            for child in ast.iter_child_nodes(node):
                visit(child, current_scope)

        visit(tree)
        functions.sort(key=lambda unit: (unit["line"], unit["definition_line"]))
        header = {"kind": "header", "name": "文件头", "parameters": [], "line": 0}
        # Insert after the exact original shebang/coding lines, before the
        # existing module docstring. No original strings are changed.
        if lines and lines[0].startswith("#!"):
            header["line"] = 1
        for index, line in enumerate(lines[:2]):
            if re.match(r"\s*#.*coding[:=]\s*[-\w.]+", line):
                header["line"] = max(header["line"], index + 1)
        units = [header, *functions]
        for unit in units:
            seed = f"{file['path']}\0{file['hash']}\0{unit['kind']}\0{unit['name']}\0{unit['line']}"
            unit["target_id"] = hashlib.sha256(seed.encode()).hexdigest()[:24]
        context_parts = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                context_parts.append("".join(lines[node.lineno - 1:node.end_lineno]))
        context = ""
        for part in context_parts:
            if len(context + part) <= 1800:
                context += part
        return units, lines, {"tree": tree, "comments": comments, "module_context": context}

    @staticmethod
    def _progress(units, state):
        return {"done": sum(unit["target_id"] in state["documents"] for unit in units), "total": len(units)}

    def _overview(self, units, lines, extra):
        sections = []
        # An overview is explicitly an excerpt: complete top-level statements
        # that fit plus function signatures, never a fabricated full file.
        for node in extra["tree"].body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                text = lines[node.lineno - 1]
                end = node.lineno
            else:
                text = "".join(lines[node.lineno - 1:node.end_lineno])
                end = node.end_lineno
            value = {"start_line": node.lineno, "end_line": end, "text": text}
            if encoded_size(sections + [value]) <= 10000:
                sections.append(value)
        return {"source": "".join(item["text"] for item in sections), "source_sections": sections,
                "source_is_overview": True,
                "overview_note": "文件头概览：只包含上述真实行范围中的顶层语句及声明行，未提供整个文件正文。",
                "function_names": [unit["name"] for unit in units if unit["kind"] == "function"][:100],
                "function_names_omitted": max(0, len(units) - 101)}

    def prepare(self, path: str) -> dict:
        file = self._file(path)
        units, lines, extra = self._plan(file)
        state, reset = self._load(file, reset=True)
        self._save(file["path"], file["hash"], state)
        progress = self._progress(units, state)
        result = {"path": file["path"], "base_hash": file["hash"], "progress": progress,
                  "ready": progress["done"] == progress["total"], "reset": reset}
        if result["ready"]:
            return result
        unit = next(unit for unit in units if unit["target_id"] not in state["documents"])
        result.update({key: unit[key] for key in ("target_id", "kind", "name", "parameters")})
        if unit["kind"] == "header":
            result.update(self._overview(units, lines, extra))
        else:
            result.update(source="".join(lines[unit["line"]:unit["end_line"]]),
                          start_line=unit["line"] + 1, end_line=unit["end_line"],
                          source_is_overview=False, module_context=extra["module_context"],
                          module_context_note="仅列出可容纳的完整 import 语句，函数 source 则为该定义及装饰器的完整真实原文。")
        if encoded_size(result) > UNIT_CHARS:
            raise ValueError(f"{file['path']} 的 {unit['name']} 单函数上下文超过 {UNIT_CHARS} 字符；"
                             "尚未写入，需分段分析该函数，不能假称已完整读取。")
        return result

    def stage(self, path: str, base_hash: str, target_id: str, documentation: dict) -> dict:
        file = self._file(path)
        if file["hash"] != base_hash:
            raise Conflict("草稿基线已变化，请重新准备当前文件；旧草稿不会覆盖用户修改。")
        units, _, _ = self._plan(file)
        state, _ = self._load(file, reset=False)
        remaining = [unit for unit in units if unit["target_id"] not in state["documents"]]
        if not remaining or remaining[0]["target_id"] != target_id:
            raise ValueError("target_id 不是当前待处理项，不能跳过函数或重复提交旧草稿。")
        unit = remaining[0]
        keys = HEADER_KEYS if unit["kind"] == "header" else FUNCTION_KEYS
        if not isinstance(documentation, dict) or set(documentation) != set(keys):
            raise ValueError("注释字段必须完整且仅包含：" + "、".join(keys))
        for key, text in documentation.items():
            if not isinstance(text, str) or not text.strip() or len(text) > 5000 or "\x00" in text:
                raise ValueError(f"{key} 必须为 1–5000 字符的说明文本。")
            if any(METADATA.match("# " + line.strip().lstrip("# ")) or PROTECTED.search("# " + line.strip().lstrip("# "))
                   for line in text.splitlines()):
                raise ValueError("说明文本不能注入格式字段、许可声明或工具控制指令。")
        if unit["kind"] == "function":
            inputs = documentation["inputs"]
            for parameter in unit["parameters"]:
                name = parameter.lstrip("*")
                if not re.search(r"(?<![\w])\*{0,2}" + re.escape(name) + r"\s*[:：]", inputs):
                    raise ValueError(f"函数输入说明缺少参数：{name}。")
            if not unit["parameters"] and "无" not in inputs:
                raise ValueError("无参数函数的输入说明须注明“无”。")
        state["documents"][target_id] = {key: text.strip() for key, text in documentation.items()}
        self._save(file["path"], file["hash"], state)
        progress = self._progress(units, state)
        return {"path": file["path"], "base_hash": file["hash"], "ready": progress["done"] == progress["total"],
                "progress": progress, "target_id": target_id, "message": "注释草稿已保存，尚未写入项目文件。"}

    def candidate(self, path: str) -> dict:
        file = self._file(path)
        units, lines, extra = self._plan(file)
        state, _ = self._load(file, reset=False)
        if self._progress(units, state)["done"] != len(units):
            raise ValueError("注释草稿尚未覆盖文件头与所有函数，不能生成或写入不完整候选。")
        removed, insertions = set(), {}
        comments = extra["comments"]
        newline = "\r\n" if "\r\n" in file["content"] else "\n"
        # File metadata ends at executable code or the first function comment;
        # token positions ensure # labels inside strings are never touched.
        body = extra["tree"].body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        boundary = min([body[0].lineno, *(d.lineno for d in getattr(body[0], "decorator_list", []))]) - 1 if body else len(lines)
        for index in sorted(comments):
            if index >= boundary:
                break
            token = comments[index]
            if re.match(r"#\s*函数用途\s*[:：]", token.string):
                break
            match = METADATA.match(token.string)
            if match and match.group(1) in FILE_HEADER_FIELDS:
                if PROTECTED.search(token.string):
                    raise ValueError("许可或工具控制注释与文件头字段位于同一行，不能安全自动替换。")
                removed.add(index)
        for unit in units:
            document = state["documents"][unit["target_id"]]
            if unit["kind"] == "header":
                keys, labels, indent = HEADER_KEYS, FILE_HEADER_FIELDS, ""
            else:
                keys, labels, indent = FUNCTION_KEYS, FUNCTION_LABELS, unit["indent"]
                cursor = unit["line"] - 1
                while cursor >= 0 and cursor in comments:
                    token = comments[cursor]
                    if lines[cursor][:token.start[1]] != indent:
                        break
                    match = METADATA.match(token.string)
                    if match and match.group(1) in FUNCTION_LABELS:
                        if PROTECTED.search(token.string):
                            raise ValueError("许可或控制指令与函数注释字段混合，不能安全自动替换。")
                        removed.add(cursor)
                    cursor -= 1
            block = []
            for key, label in zip(keys, labels):
                parts = document[key].splitlines()
                block.append(f"{indent}# {label}：{parts[0]}{newline}")
                block.extend(f"{indent}# {part}{newline}" for part in parts[1:])
            insertions.setdefault(unit["line"], []).extend(block)
        result = []
        for index in range(len(lines) + 1):
            result.extend(insertions.get(index, []))
            if index < len(lines) and index not in removed:
                result.append(lines[index])
        after = ("\ufeff" if file["content"].startswith("\ufeff") else "") + "".join(result)
        if len(after.encode("utf-8")) > MAX_FILE:
            raise ValueError("注释候选超过 256 KB，草稿保留但不能写入。")
        validate_annotation_change(file["path"], file["content"], after)
        return {"path": file["path"], "base_hash": file["hash"], "before": file["content"], "after": after}

    def summary(self, path: str) -> dict:
        file = self._file(path)
        units, _, _ = self._plan(file)
        state, _ = self._load(file, reset=False)
        return {"path": file["path"], "base_hash": file["hash"], "progress": self._progress(units, state)}

    def finish(self, path: str) -> None:
        resolved = self.workspace.path(path).relative_to(self.workspace.root).as_posix()
        rows = self.store.rows("SELECT base_hash,state FROM annotation_drafts WHERE task_id=? AND path=?",
                               (self.task_id, resolved))
        if rows:
            state = json.loads(rows[0]["state"])
            state["consumed"] = True
            self._save(resolved, rows[0]["base_hash"], state)
