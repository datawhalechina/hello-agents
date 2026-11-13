# -*- coding: utf-8 -*-
"""只读检查 Python 函数三项中文注释及参数覆盖，不导入或执行项目。"""

import argparse
import ast
from pathlib import Path
import re
import tokenize


LABELS = ('函数用途', '输入说明', '输出说明')
SKIP_DIRS = {'.git', '.hg', '.svn', '.idea', '.vscode', '.venv', 'venv',
             '__pycache__', 'site-packages', 'node_modules'}


def iter_functions(node, parents=()):
    """遍历普通、异步、方法和嵌套函数，同时给出所属作用域。"""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = parents + (child.name,)
            yield child, '.'.join(scope)
            yield from iter_functions(child, scope)
        elif isinstance(child, ast.ClassDef):
            yield from iter_functions(child, parents + (child.name,))
        else:
            yield from iter_functions(child, parents)


def preceding_comments(lines, node):
    """读取定义或第一条装饰器之前的连续注释块。"""
    start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
    cursor = start - 1
    while cursor >= 0 and lines[cursor].lstrip().startswith('#'):
        cursor -= 1
    block = '\n'.join(lines[cursor + 1:start])
    first_function = re.search(r'#\s*函数用途\s*[:：]', block)
    return block[first_function.start():] if first_function else block


def parameter_names(node):
    """列出全部显式参数，包含仅限位置、仅限关键字和可变参数。"""
    names = [arg.arg for arg in node.args.posonlyargs + node.args.args
             + node.args.kwonlyargs]
    if node.args.vararg:
        names.append(node.args.vararg.arg)
    if node.args.kwarg:
        names.append(node.args.kwarg.arg)
    return names


def check_file(path):
    """检查单个源码文件，返回函数数量、匿名函数数量和缺漏列表。"""
    with tokenize.open(str(path)) as source:
        text = source.read()
    tree = ast.parse(text, filename=str(path))
    lines = text.splitlines()
    issues = []
    count = 0
    for node, scope in iter_functions(tree):
        count += 1
        block = preceding_comments(lines, node)
        positions = []
        for label in LABELS:
            matches = list(re.finditer(r'#\s*' + label + r'\s*[:：]', block))
            if len(matches) != 1:
                issues.append((node.lineno, scope, label + '缺失或重复'))
            positions.append(matches[0].start() if len(matches) == 1 else -1)
        if -1 in positions:
            continue
        if positions != sorted(positions):
            issues.append((node.lineno, scope, '三项顺序不正确'))
            continue
        inputs = block[positions[1]:positions[2]]
        for name in parameter_names(node):
            if not re.search(r'(?<![\w])\*{0,2}' + re.escape(name)
                             + r'\s*[:：]', inputs):
                issues.append((node.lineno, scope, '参数未说明：' + name))
        if not parameter_names(node) and '无' not in inputs:
            issues.append((node.lineno, scope, '无参数函数应注明“无”'))
    anonymous = sum(isinstance(n, ast.Lambda) for n in ast.walk(tree))
    return count, anonymous, issues


def main():
    """检查指定目录中的自有 Python 源码，仅向终端显示检查结果。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path, help='项目目录或单个 Python 文件')
    parser.add_argument('--exclude', action='append', default=[],
                        help='需要额外跳过的目录名，可重复指定')
    args = parser.parse_args()
    root = args.project.resolve()
    if not root.exists():
        parser.error('指定的项目路径不存在')
    files = [root] if root.is_file() else sorted(root.rglob('*.py'))
    skip = SKIP_DIRS | set(args.exclude)
    files = [p for p in files if p.suffix.lower() == '.py'
             and not any(part in skip for part in p.relative_to(root.parent if root.is_file() else root).parts[:-1])]
    total = anonymous = failures = 0
    for path in files:
        try:
            count, lambdas, issues = check_file(path)
        except (SyntaxError, UnicodeError, OSError) as error:
            print(f'{path}：无法静态检查（{type(error).__name__}）')
            failures += 1
            continue
        total += count
        anonymous += lambdas
        for line, scope, message in issues:
            print(f'{path}:{line} {scope}：{message}')
            failures += 1
    print(f'检查 {len(files)} 个 Python 文件、{total} 个具名函数；缺漏 {failures} 项。')
    print(f'另有 {anonymous} 个匿名函数，需人工核对相邻说明；其他语言按各自语法核对。')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
