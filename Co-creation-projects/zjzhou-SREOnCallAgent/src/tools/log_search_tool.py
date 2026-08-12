import re
from typing import Dict, Any, List


class LogSearchTool:
    """
    Searches incident log entries by keyword or regex pattern.

    Input to run(): a keyword or regex string
    Returns: matching log lines as a formatted string
    """

    name = "log_search"
    description = (
        "Search incident logs by keyword or regex pattern. "
        "Input: a keyword or regex string (e.g. 'pool exhausted', 'ERROR', '429'). "
        "Returns matching log entries with timestamps and severity levels."
    )

    def __init__(self, incident_data: Dict[str, Any]):
        self.logs: List[Dict] = incident_data.get("logs", [])
        self.service: str = incident_data.get("service", "unknown")

    def run(self, query: str) -> str:
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            # Fall back to plain substring match if regex is invalid
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        matches = [
            f"[{e['timestamp']}] [{e['level']:8s}] {e['message']}"
            for e in self.logs
            if pattern.search(e.get("message", "")) or pattern.search(e.get("level", ""))
        ]

        if not matches:
            return f"No log entries found matching '{query}' in {self.service} logs."
        return (
            f"Found {len(matches)} log entries matching '{query}':\n"
            + "\n".join(matches)
        )
