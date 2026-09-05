from __future__ import annotations

from typing import Any

from mcp.server.mcpserver.server import MCPServer

from finance_agent.material_scanner import scan_material_folder


server = MCPServer(
    name="finance-material-folder-scanner",
    version="1.0.0",
    instructions=(
        "Read-only MCP server for scanning finance acceptance material file names "
        "under MATERIAL_ROOT. It must not read file contents or modify files."
    ),
)


@server.tool(
    name="scan_material_folder",
    description=(
        "Scan file names and metadata under the configured MATERIAL_ROOT. "
        "This tool is read-only and does not parse PDF/Word/Excel contents."
    ),
    structured_output=True,
)
def scan_material_folder_tool(relative_subdir: str = "", max_files: int = 1000) -> dict[str, Any]:
    return scan_material_folder(relative_subdir=relative_subdir, max_files=max_files)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
