"""项目路径。"""

from pathlib import Path


def project_root() -> Path:
    """返回 neil43lk-StudentConfideAgent 根目录。"""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return project_root() / "data"


def memory_dir() -> Path:
    path = data_dir() / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def outputs_dir() -> Path:
    path = project_root() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path
