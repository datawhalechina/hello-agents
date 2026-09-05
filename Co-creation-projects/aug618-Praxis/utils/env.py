"""环境变量读取工具。

统一处理布尔/字符串读取，确保全仓语义一致。
"""

from __future__ import annotations

import os

_TRUE_SET = {"1", "true", "yes", "y"}
_FALSE_SET = {"0", "false", "no", "n"}


def env_str(name: str, default: str = "") -> str:
    """读取环境变量字符串（保留原始空白）。"""
    return os.getenv(name, default)


def env_stripped(name: str, default: str = "") -> str:
    """读取环境变量并去除首尾空白。"""
    return os.getenv(name, default).strip()


def env_lower(name: str, default: str = "") -> str:
    """读取环境变量并转为小写（含去空白）。"""
    return os.getenv(name, default).strip().lower()


def env_flag(name: str, default: bool = False) -> bool:
    """读取布尔型环境变量（仅真值集合为 True）。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_SET


def env_flag_true(name: str, default: bool = True) -> bool:
    """读取布尔型环境变量（仅假值集合为 False）。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSE_SET
