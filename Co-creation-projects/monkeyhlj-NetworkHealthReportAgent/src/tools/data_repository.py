from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.date_utils import in_range


class DataRepository:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.data_dir = data_dir or (project_root / "data")

    def _load_json(self, filename: str) -> List[Dict[str, Any]]:
        path = self.data_dir / filename
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_sites(self) -> List[Dict[str, Any]]:
        return self._load_json("sites.json")

    def get_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        return next((s for s in self.list_sites() if s["site_id"] == site_id), None)

    def list_device_inventory(self, site_id: Optional[str] = None) -> List[Dict[str, Any]]:
        records = self._load_json("device_inventory.json")
        if site_id:
            records = [r for r in records if r["site_id"] == site_id]
        return records

    def list_device_status(self, site_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        records = self._load_json("device_status_timeseries.json")
        return [
            r
            for r in records
            if r["site_id"] == site_id and in_range(r["date"], start=start_date_obj(start_date), end=end_date_obj(end_date))
        ]

    def list_logs(self, site_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        records = self._load_json("network_logs.json")
        filtered = [r for r in records if r["site_id"] == site_id]
        return filtered[:limit]

    def latest_terminal_compliance(self, site_id: str) -> Optional[Dict[str, Any]]:
        records = self._load_json("terminal_compliance.json")
        by_site = [r for r in records if r["site_id"] == site_id]
        if not by_site:
            return None
        by_site.sort(key=lambda x: x["date"], reverse=True)
        return by_site[0]


def start_date_obj(value: str):
    from datetime import datetime

    return datetime.strptime(value, "%Y-%m-%d").date()


def end_date_obj(value: str):
    from datetime import datetime

    return datetime.strptime(value, "%Y-%m-%d").date()
