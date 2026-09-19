import json
import time
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings


class StepSearchMCPClient:
    """Small synchronous Streamable HTTP MCP client for StepSearch."""

    def __init__(self, timeout: float = 45.0):
        self.endpoint = settings.final_base_url.rstrip("/") + "/mcp/web_search/mcp"
        self.timeout = timeout
        self._next_id = 1

    def _call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {settings.final_api_key}",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError("StepSearch MCP request failed")
        return payload.get("result") or {}

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._call("tools/call", {"name": name, "arguments": arguments})

    @staticmethod
    def text(result: Dict[str, Any]) -> str:
        chunks = []
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
        return "\n".join(chunks)


class StepSearchPersonaTool:
    def __init__(self, client: Optional[StepSearchMCPClient] = None):
        self.client = client or StepSearchMCPClient()

    def search(self, query: str, n: int = 5) -> str:
        result = self.client.call_tool("web_search", {"query": query, "n": n, "use_common_search": True})
        return self.client.text(result) or "未找到可用搜索结果"

    def fetch(self, url: str) -> str:
        result = self.client.call_tool("web_fetch", {"url": url})
        return self.client.text(result) or "未找到网页内容"
