from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal environments.
    load_dotenv = None


MATERIAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "contract": ("合同", "采购", "协议", "contract", "agreement"),
    "invoice": ("发票", "invoice", "票据"),
    "bank_receipt": ("银行回单", "回单", "付款凭证", "支付凭证", "receipt", "bank"),
    "acceptance": ("验收", "入库", "签收", "acceptance"),
    "meeting_notice": ("会议通知", "通知", "notice"),
    "meeting_sign_in": ("签到", "签名", "sign"),
    "meeting_minutes": ("纪要", "议程", "minutes", "agenda"),
    "expense_detail": ("明细", "清单", "detail", "list"),
    "approval": ("审批", "批复", "approval"),
}


def load_material_env() -> None:
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    for candidate in [project_root / ".env", Path.cwd() / ".env"]:
        if candidate.exists():
            load_dotenv(candidate, override=False)


def material_root_from_env() -> Path | None:
    load_material_env()
    raw = os.getenv("MATERIAL_ROOT")
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def scan_material_folder(
    *,
    relative_subdir: str = "",
    max_files: int = 1000,
) -> dict[str, Any]:
    root = material_root_from_env()
    if root is None:
        return unavailable_result("MATERIAL_ROOT is not configured.")
    if not root.exists() or not root.is_dir():
        return unavailable_result(f"MATERIAL_ROOT does not exist or is not a directory: {root}")

    scan_dir = resolve_scan_dir(root, relative_subdir)
    files: list[dict[str, Any]] = []
    for path in sorted(scan_dir.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        relative_path = path.relative_to(root).as_posix()
        files.append(
            {
                "file_name": path.name,
                "relative_path": relative_path,
                "suffix": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "material_keyword_hits": material_keyword_hits(path.name),
            }
        )
        if len(files) >= max_files:
            break

    return {
        "schema": "MaterialFolderScanResult",
        "schema_version": "1.0",
        "available": True,
        "read_only": True,
        "material_root": str(root),
        "relative_subdir": relative_subdir,
        "scan_dir": str(scan_dir),
        "file_count": len(files),
        "max_files": max_files,
        "files": files,
        "policy": {
            "scope": "File-name and metadata scan only.",
            "does_not_parse_file_content": True,
            "does_not_validate_authenticity_or_compliance": True,
            "allowed_operations": ["list_files"],
            "blocked_operations": ["delete", "move", "modify", "content_parse"],
        },
    }


def unavailable_result(reason: str) -> dict[str, Any]:
    return {
        "schema": "MaterialFolderScanResult",
        "schema_version": "1.0",
        "available": False,
        "read_only": True,
        "reason": reason,
        "files": [],
        "policy": {
            "scope": "File-name and metadata scan only.",
            "does_not_parse_file_content": True,
            "does_not_validate_authenticity_or_compliance": True,
        },
    }


def resolve_scan_dir(root: Path, relative_subdir: str) -> Path:
    scan_dir = (root / relative_subdir).resolve() if relative_subdir else root
    if not scan_dir.is_relative_to(root):
        raise ValueError("relative_subdir must stay within MATERIAL_ROOT.")
    if not scan_dir.exists() or not scan_dir.is_dir():
        raise FileNotFoundError(scan_dir)
    return scan_dir


def material_keyword_hits(file_name: str) -> list[str]:
    lower_name = file_name.lower()
    hits = [
        material_type
        for material_type, keywords in MATERIAL_KEYWORDS.items()
        if any(keyword.lower() in lower_name for keyword in keywords)
    ]
    return sorted(hits)
