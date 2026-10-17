"""A local, dependency-free demo of the MCP Tasks request lifecycle.

It models a small subset of the 2026-07-28 Tasks extension:
tools/call, resultType="task", tasks/get, polling, and synchronous fallback.
It is not a complete MCP implementation or a conformance test.
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


TASKS: dict[str, dict[str, Any]] = {}
CANCEL_EVENTS: dict[str, threading.Event] = {}
LOCK = threading.Lock()
POLL_MS = 120


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def rpc_response(request_id: int, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def start_report(task_id: str, topic: str) -> None:
    cancel = CANCEL_EVENTS[task_id]
    for step in range(1, 4):
        time.sleep(0.18)
        with LOCK:
            task = TASKS.get(task_id)
            if task is None:
                return
            if cancel.is_set():
                task.update(status="cancelled", lastUpdatedAt=utc_now())
                return
            task["statusMessage"] = f"Preparing report ({step}/3)"
            task["lastUpdatedAt"] = utc_now()

    with LOCK:
        task = TASKS.get(task_id)
        if task is not None:
            task.update(
                status="completed",
                lastUpdatedAt=utc_now(),
                result={
                    "content": [
                        {"type": "text", "text": f"Report ready for: {topic}"}
                    ],
                    "isError": False,
                },
            )


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the demo output focused on the JSON-RPC lifecycle.
        return

    def reply(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            size = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(size))
            request_id = int(request["id"])
            method = request["method"]
            params = request.get("params", {})

            if self.headers.get("MCP-Protocol-Version") != "2026-07-28":
                raise ValueError("MCP-Protocol-Version must be 2026-07-28")
            if self.headers.get("Mcp-Method") != method:
                raise ValueError("Mcp-Method header must match the JSON-RPC method")

            if method == "tools/call":
                name = params.get("name", "")
                if self.headers.get("Mcp-Name") != name:
                    raise ValueError("Mcp-Name header must match the tool name")
                topic = params.get("arguments", {}).get("topic", "untitled")
                metadata = params.get("_meta", {})
                extensions = (
                    metadata.get("io.modelcontextprotocol/clientCapabilities", {})
                    .get("extensions", {})
                )
                supports_tasks = "io.modelcontextprotocol/tasks" in extensions

                if not supports_tasks:
                    self.reply(
                        rpc_response(
                            request_id,
                            {
                                "resultType": "complete",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Report ready for: {topic}",
                                    }
                                ],
                                "isError": False,
                            },
                        )
                    )
                    return

                task_id = uuid.uuid4().hex
                now = utc_now()
                task: dict[str, Any] = {
                    "resultType": "task",
                    "taskId": task_id,
                    "status": "working",
                    "statusMessage": "Task accepted",
                    "createdAt": now,
                    "lastUpdatedAt": now,
                    "ttlMs": 60_000,
                    "pollIntervalMs": POLL_MS,
                }
                with LOCK:
                    TASKS[task_id] = task
                    CANCEL_EVENTS[task_id] = threading.Event()

                worker = threading.Thread(
                    target=start_report, args=(task_id, topic), daemon=True
                )
                worker.start()
                self.reply(rpc_response(request_id, dict(task)))
                return

            if method == "tasks/get":
                task_id = params["taskId"]
                if self.headers.get("Mcp-Name") != task_id:
                    raise ValueError("For tasks/get, Mcp-Name must be the taskId")
                with LOCK:
                    task = TASKS.get(task_id)
                    snapshot = dict(task) if task is not None else None
                if snapshot is None:
                    self.reply(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32602, "message": "Task not found"},
                        }
                    )
                    return
                self.reply(rpc_response(request_id, snapshot))
                return

            if method == "tasks/cancel":
                task_id = params["taskId"]
                if self.headers.get("Mcp-Name") != task_id:
                    raise ValueError("For tasks/cancel, Mcp-Name must be the taskId")
                with LOCK:
                    cancel = CANCEL_EVENTS.get(task_id)
                    if cancel is None:
                        self.reply(
                            {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -32602, "message": "Task not found"},
                            }
                        )
                        return
                    cancel.set()
                self.reply(rpc_response(request_id, {"resultType": "complete"}))
                return

            self.reply(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"},
                }
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            request_id = locals().get("request_id", 0)
            self.reply(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32600, "message": str(error)},
                }
            )


def call_rpc(
    url: str, method: str, params: dict[str, Any], resource_name: str, request_id: int
) -> dict[str, Any]:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2026-07-28",
            "Mcp-Method": method,
            "Mcp-Name": resource_name,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except urllib.error.URLError as error:
        raise RuntimeError(f"Local MCP toy request failed: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local MCP Tasks lifecycle demo.")
    parser.add_argument(
        "--no-extension",
        action="store_true",
        help="omit the Tasks capability and observe a synchronous result",
    )
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{server.server_port}/mcp"
    print(f"local JSON-RPC endpoint: {url}")

    try:
        metadata: dict[str, Any] = {}
        if not args.no_extension:
            metadata = {
                "io.modelcontextprotocol/clientCapabilities": {
                    "extensions": {"io.modelcontextprotocol/tasks": {}}
                }
            }
        call = call_rpc(
            url,
            "tools/call",
            {
                "name": "build_report",
                "arguments": {"topic": "protocol migration"},
                "_meta": metadata,
            },
            resource_name="build_report",
            request_id=1,
        )
        result = call["result"]
        if result.get("resultType") != "task":
            text = result["content"][0]["text"]
            print("server returned a synchronous result")
            print(f"result={text}")
            return

        task_id = result["taskId"]
        print(
            "server returned "
            f"resultType=task taskId={task_id} "
            f"pollIntervalMs={result['pollIntervalMs']}"
        )
        request_id = 2
        while True:
            time.sleep(result.get("pollIntervalMs", POLL_MS) / 1000)
            status_response = call_rpc(
                url,
                "tasks/get",
                {"taskId": task_id},
                resource_name=task_id,
                request_id=request_id,
            )
            request_id += 1
            result = status_response["result"]
            print(f"task status={result['status']}")
            if result["status"] in {"completed", "failed", "cancelled"}:
                break

        if result["status"] == "completed":
            print(f"result={result['result']['content'][0]['text']}")
        elif result["status"] == "failed":
            print(f"error={result['error']}")
        else:
            print("task cancelled")
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)


if __name__ == "__main__":
    main()



