"""Bundled annotation instructions and static checks; never execute target code."""
from __future__ import annotations

import ast
import io
import re
import runpy
import tempfile
import tokenize
from functools import lru_cache
from pathlib import Path

from .analysis_documents import ANALYSIS_SKILL, ANALYSIS_INSTRUCTIONS

ANNOTATION_SKILL = "annotate-project-zh"
SKILL_DIRECTORY = Path(__file__).resolve().parent.parent / "skills" / ANNOTATION_SKILL
FILE_HEADER_FIELDS = ["代码用途", "输入文件", "输入说明", "输出文件", "输出说明"]
HEADER_FIELD = re.compile(r"#\s*(代码用途|输入文件|输入说明|输出文件|输出说明)\s*[:：]")


def _python_header_layout(source: str, tree: ast.Module) -> dict:
    """Inspect real leading comments around the preserved module docstring."""
    body = tree.body
    docstring_end = 0
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        docstring_end = body[0].end_lineno
        body = body[1:]
    # A decorator is executable code too: headers cannot be inserted between it
    # and its declaration. Docstring text is never treated as comment metadata.
    boundary = len(source.splitlines()) + 1
    if body:
        first = body[0]
        boundary = min([first.lineno, *(item.lineno for item in getattr(first, "decorator_list", []))])
    fields = []
    for item in tokenize.generate_tokens(io.StringIO(source).readline):
        if item.start[0] >= boundary:
            break
        if item.type != tokenize.COMMENT:
            continue
        if re.match(r"#\s*函数用途\s*[:：]", item.string):
            break
        match = HEADER_FIELD.match(item.string)
        if match:
            fields.append(match.group(1))
    return {"detected_fields": fields, "first_code_line": boundary,
            "module_docstring_end_line": docstring_end}


def annotation_read_hints(path: str, content: str) -> dict | None:
    if Path(path).suffix.lower() not in {".py", ".pyi"}:
        return None
    source = content.lstrip("\ufeff")
    try:
        tree = ast.parse(source, filename=path)
        layout = _python_header_layout(source, tree)
    except (SyntaxError, tokenize.TokenError):
        return {"note": "原文件存在语法或分词错误，不能以添加注释为由修改代码；请说明未覆盖范围。"}
    functions = []

    def collect(node, scope=""):
        next_scope = scope
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            next_scope = f"{scope}.{node.name}" if scope else node.name
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = [item.arg for item in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]]
            if node.args.vararg:
                parameters.append("*" + node.args.vararg.arg)
            if node.args.kwarg:
                parameters.append("**" + node.args.kwarg.arg)
            functions.append({"name": next_scope, "definition_line": node.lineno,
                              "comment_before_line": min([node.lineno, *(item.lineno for item in node.decorator_list)]),
                              "parameters": parameters})
        for child in ast.iter_child_nodes(node):
            collect(child, next_scope)

    collect(tree)
    return {**layout, "required_fields": FILE_HEADER_FIELDS, "function_comment_positions": functions,
            "function_rule": "每个具名函数各写一组“函数用途、输入说明、输出说明”，紧贴对应 def 或其第一条装饰器之前，缩进与 def 相同。不要把下一函数的说明放进前一函数的注释块；类声明和 if __name__ 入口块不是具名函数。",
            "note": "保留首行 shebang、前两行中的编码声明和原模块文档字符串。五项 # 文件头可放在模块文档字符串之前或之后，但必须在首条代码/装饰器之前；已有文件头应更新而非重复叠加。不要把文件头移到 shebang 之前。"}


def load_skill(skill: str | None) -> str:
    if skill is None:
        return ""
    if skill == ANALYSIS_SKILL:
        return ANALYSIS_INSTRUCTIONS
    if skill != ANNOTATION_SKILL:
        raise ValueError("不支持的技能。")
    return (SKILL_DIRECTORY / "SKILL.md").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def coverage_checker():
    # Load only our bundled, read-only checker, never a workspace script.
    return runpy.run_path(str(SKILL_DIRECTORY / "scripts/check_function_comments.py"))["check_file"]


def validate_annotation_change(path: str, before: str | None, after: str | None):
    if before is None or after is None:
        raise ValueError("注释技能仅修改已有源码，不能新增或删除文件。")
    suffix = Path(path).suffix.lower()
    if suffix in {".json", ".jsonl", ".md", ".rst", ".txt"}:
        raise ValueError("注释技能不修改文档或严格 JSON 文件，也不生成额外交付文件。")
    if suffix not in {".py", ".pyi"}:
        return  # Other languages follow the skill without Python-equivalent checks.
    if before.startswith("\ufeff") != after.startswith("\ufeff"):
        raise ValueError(f"{path} 必须保留原有 BOM 编码标记。")
    original, annotated = before.lstrip("\ufeff"), after.lstrip("\ufeff")
    if original.startswith("#!") and original.partition("\n")[0] != annotated.partition("\n")[0]:
        raise ValueError(f"{path} 必须在首行保留原有 shebang。请把五项文件头放在 shebang/编码声明之后，可放在原模块文档字符串之后、首条代码之前。")
    encoding_lines = [line for line in original.splitlines()[:2]
                      if re.match(r"\s*#.*coding[:=]\s*[-\w.]+", line)]
    if any(line not in annotated.splitlines()[:2] for line in encoding_lines):
        raise ValueError(f"{path} 必须保留编码声明的内容及合法位置。")
    try:
        old_tree = ast.parse(original, filename=path)
    except SyntaxError as exc:
        raise ValueError(f"{path} 原有语法错误，无法自动确认注释修改，请先人工核对。") from exc
    try:
        new_tree = ast.parse(annotated, filename=path)
        compile(new_tree, path, "exec")  # Compile in memory; do not import or execute.
    except SyntaxError as exc:
        raise ValueError(f"{path} 注释后存在语法错误。") from exc
    if ast.dump(old_tree, include_attributes=False) != ast.dump(new_tree, include_attributes=False):
        raise ValueError(f"{path} 修改了代码或文档字符串，注释技能仅允许原生注释。")

    def code_tokens(text):
        ignored = {tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER}
        return [(item.type, item.string) for item in tokenize.generate_tokens(io.StringIO(text).readline)
                if item.type not in ignored]

    if code_tokens(original) != code_tokens(annotated):
        raise ValueError(f"{path} 修改了原始代码、字符串或排版，请仅添加或更新注释。")
    directive = re.compile(r"#\s*(?:type\s*:|noqa\b|noinspection\b|pragma\b|pylint\b|pyright\b|"
                           r"mypy\b|ruff\b|fmt\s*:|isort\s*:|yapf\s*:|doctest\s*:|nosec\b)", re.I)

    def controls(text):
        position, result = 0, []
        for item in tokenize.generate_tokens(io.StringIO(text).readline):
            if item.type == tokenize.COMMENT and directive.match(item.string):
                result.append((position, item.string))
            elif item.type not in {tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER}:
                position += 1
        return result

    if controls(original) != controls(annotated):
        raise ValueError(f"{path} 必须保留原有类型指令和工具控制注释，不能移动或新增此类指令。")
    for line in original.splitlines():
        if re.match(r"\s*#.*(?:copyright|版权|SPDX-License-Identifier)", line, re.I) and line not in annotated.splitlines():
            raise ValueError(f"{path} 必须保留原有版权和许可声明。")
    layout = _python_header_layout(annotated, new_tree)
    labels = layout["detected_fields"]
    if labels != FILE_HEADER_FIELDS:
        raise ValueError(f"{path} 五项文件头检查未通过：检测字段为 {labels}；"
                         f"期望依次为 {FILE_HEADER_FIELDS}，各出现一次。"
                         f"文件头须位于首条代码/装饰器（当前第 {layout['first_code_line']} 行）之前，"
                         "允许放在原模块文档字符串之后；保留原文档字符串及首行 shebang，不要移动它们。")
    with tempfile.TemporaryDirectory(prefix="code-assistant-annotation-") as temporary:
        candidate = Path(temporary) / "candidate.py"
        candidate.write_text(after, encoding="utf-8", newline="")
        count, anonymous, issues = coverage_checker()(candidate)
    if issues:
        details = "；".join(f"{scope}：{message}" for _, scope, message in issues[:8])
        raise ValueError(f"{path} 函数注释检查未通过：{details}。"
                         "每个函数必须有独立的三项注释，放在对应 def 或其第一条装饰器之前；"
                         "不能把下一函数的注释挤在前一函数上方。请按 read 返回的 function_comment_positions 修正。")
    return {"functions": count, "anonymous_functions": anonymous}
