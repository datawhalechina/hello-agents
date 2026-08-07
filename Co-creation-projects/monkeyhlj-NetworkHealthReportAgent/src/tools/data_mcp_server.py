from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP

from src.tools.data_repository import DataRepository

mcp = FastMCP("network-health-data")
repo = DataRepository()


@mcp.tool()
def list_sites() -> list:
    return repo.list_sites()


@mcp.tool()
def get_site(site_id: str) -> Optional[dict]:
    return repo.get_site(site_id)


@mcp.tool()
def list_device_inventory(site_id: str) -> list:
    return repo.list_device_inventory(site_id)


@mcp.tool()
def list_device_status(site_id: str, start_date: str, end_date: str) -> list:
    return repo.list_device_status(site_id=site_id, start_date=start_date, end_date=end_date)


@mcp.tool()
def list_logs(site_id: str, limit: int = 100) -> list:
    return repo.list_logs(site_id=site_id, limit=limit)


@mcp.tool()
def latest_terminal_compliance(site_id: str) -> Optional[dict]:
    return repo.latest_terminal_compliance(site_id=site_id)


if __name__ == "__main__":
    mcp.run()
