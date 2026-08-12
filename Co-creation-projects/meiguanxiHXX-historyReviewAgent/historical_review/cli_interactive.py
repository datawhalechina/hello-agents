"""命令行交互：议题、是否网络附录、运行前确认。"""

from __future__ import annotations

import sys


def prompt_yes_no(question: str, *, default: bool = True) -> bool:
    """
    询问 Y/n 或 y/N，回车采用 default。
    在非 TTY 环境下直接返回 default，避免管道挂住。
    """
    if not sys.stdin.isatty():
        return default

    hint = " [Y/n] " if default else " [y/N] "
    try:
        raw = input(question + hint).strip().lower()
    except EOFError:
        return default

    if raw == "":
        return default
    if raw in ("y", "yes", "是", "好", "确认", "1"):
        return True
    if raw in ("n", "no", "否", "不", "0"):
        return False
    return default


def prompt_topic(default_topic: str) -> str:
    if not sys.stdin.isatty():
        return default_topic

    try:
        raw = input(
            f"请输入历史议题（直接回车使用示例）：\n> ",
        ).strip()
    except EOFError:
        return default_topic

    return raw if raw else default_topic
