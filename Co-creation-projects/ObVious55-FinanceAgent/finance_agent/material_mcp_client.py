from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def scan_material_folder_via_mcp(
    *,
    relative_subdir: str = "",
    max_files: int = 1000,
) -> dict[str, Any]:
    return anyio.run(_scan_material_folder_via_mcp, relative_subdir, max_files)


async def _scan_material_folder_via_mcp(relative_subdir: str, max_files: int) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[1]
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "finance_agent.material_mcp_server"],
        env=os.environ.copy(),
        cwd=project_root,
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "scan_material_folder",
                {
                    "relative_subdir": relative_subdir,
                    "max_files": max_files,
                },
            )
            return parse_tool_result(result)


def parse_tool_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured

    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return {
        "schema": "MaterialFolderScanResult",
        "schema_version": "1.0",
        "available": False,
        "read_only": True,
        "reason": "MCP tool returned no structured material scan result.",
        "files": [],
    }
