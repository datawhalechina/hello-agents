"""Late-bound MCP clients and host authorization metadata."""

import re

# -- MCP System --

# MCP is modeled as late-bound tools: connect first, then discovered server
# tools are merged into the normal tool pool with mcp__server__tool names.
class MCPClient:
    """Small in-process stand-in for MCP tools/list and tools/call."""

    def __init__(self, name: str):
        self.name = name
        self.tools: list[dict] = []
        self._handlers: dict[str, callable] = {}

    def register(self, tool_defs: list[dict],
                 handlers: dict[str, callable]):
        names = [tool.get("name") for tool in tool_defs]
        if any(not isinstance(name, str) or not name for name in names):
            raise ValueError("Every MCP tool needs a non-empty name")
        if len(set(names)) != len(names):
            raise ValueError(f"Duplicate MCP tool name on server {self.name!r}")
        missing = [name for name in names if name not in handlers]
        if missing:
            raise ValueError(f"Missing MCP handlers: {', '.join(missing)}")
        self.tools = list(tool_defs)
        self._handlers = dict(handlers)

    def call_tool(self, tool_name: str, args: dict) -> str:
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"MCP error: unknown tool '{tool_name}'"
        try:
            return str(handler(**args))
        except Exception as exc:
            return f"MCP error: {type(exc).__name__}: {exc}"


mcp_clients: dict[str, MCPClient] = {}
_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")

# Authorization comes from host configuration, never server descriptions.
MCP_HOST_POLICY = {
    ("docs", "search"): "allow",
    ("docs", "get_version"): "allow",
    ("deploy", "status"): "allow",
    ("deploy", "trigger"): "confirm",
}


def normalize_mcp_name(name: str) -> str:
    """Replace characters outside the model tool-name alphabet."""
    normalized = _DISALLOWED_CHARS.sub("_", name)
    if not normalized:
        raise ValueError("MCP names cannot normalize to an empty string")
    return normalized


def _mock_server_docs() -> MCPClient:
    client = MCPClient("docs")
    client.register(
        tool_defs=[
            {"name": "search", "description": "Search the documentation.",
             "inputSchema": {"type": "object",
                             "properties": {"query": {"type": "string"}},
                             "required": ["query"]},
             "annotations": {"readOnlyHint": True}},
            {"name": "get_version",
             "description": "Get the documentation API version.",
             "inputSchema": {"type": "object", "properties": {},
                             "required": []},
             "annotations": {"readOnlyHint": True}},
        ],
        handlers={
            "search": lambda query: f"[docs] Found 3 results for '{query}'",
            "get_version": lambda: "[docs] API v2.1.0",
        })
    return client


def _mock_server_deploy() -> MCPClient:
    client = MCPClient("deploy")
    client.register(
        tool_defs=[
            {"name": "trigger",
             "description": "Trigger a deployment.",
             "inputSchema": {"type": "object",
                             "properties": {"service": {"type": "string"}},
                             "required": ["service"]},
             "annotations": {"destructiveHint": True}},
            {"name": "status", "description": "Check deployment status.",
             "inputSchema": {"type": "object",
                             "properties": {"service": {"type": "string"}},
                             "required": ["service"]},
             "annotations": {"readOnlyHint": True}},
        ],
        handlers={
            "trigger": lambda service: f"[deploy] Triggered: {service}",
            "status": lambda service: f"[deploy] {service}: running (v1.4.2)",
        })
    return client


MOCK_SERVERS = {
    "docs": _mock_server_docs,
    "deploy": _mock_server_deploy,
}


def connect_mcp(name: str) -> str:
    if name in mcp_clients:
        return f"MCP server '{name}' already connected"
    factory = MOCK_SERVERS.get(name)
    if not factory:
        available = ", ".join(MOCK_SERVERS)
        return f"Unknown server '{name}'. Available: {available}"
    mcp_client = factory()
    mcp_clients[name] = mcp_client
    tool_names = [tool["name"] for tool in mcp_client.tools]
    print(f"  \033[31m[mcp] connected: {name} -> {tool_names}\033[0m")
    return (f"Connected to MCP server '{name}'. "
            f"Discovered {len(mcp_client.tools)} tools: {', '.join(tool_names)}")
