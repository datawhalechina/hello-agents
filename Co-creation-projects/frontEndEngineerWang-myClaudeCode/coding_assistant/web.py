"""Local browser UI for the coding assistant.

Run with ``python -m coding_assistant.web`` and open http://127.0.0.1:8787.
The server deliberately uses only Python's standard library so the CLI's
runtime dependencies remain unchanged.
"""

from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .agent.agent import agent_loop, update_context
from .core.config import WORKDIR
from .core.hooks import trigger_hooks
from .core.storage import ConversationStore, json_safe
from .core.workspace import use_workdir

STATIC_DIR = Path(__file__).with_name("web_static")


class ConversationManager:
    def __init__(self, store: ConversationStore):
        self.store = store
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def lock_for(self, conversation_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(conversation_id, threading.Lock())

    def submit(self, conversation_id: str, content: str) -> None:
        content = content.strip()
        if not content:
            raise ValueError("消息不能为空")
        lock = self.lock_for(conversation_id)
        if not lock.acquire(blocking=False):
            raise RuntimeError("该对话正在处理中")
        try:
            record = self.store.get(conversation_id)
            if record.get("status") == "running":
                raise RuntimeError("该对话正在处理中")
            messages = list(record.get("messages", []))
            if not record.get("title") or record.get("title") == "新对话":
                record["title"] = content.replace("\n", " ")[:40]
            messages.append({"role": "user", "content": content})
            self.store.update(conversation_id, title=record["title"], messages=messages, status="running", error="")
            thread = threading.Thread(
                target=self._run,
                args=(conversation_id, messages, content, record["workdir"], lock),
                daemon=True,
                name=f"conversation-{conversation_id[:8]}",
            )
            thread.start()
        except Exception:
            lock.release()
            raise

    def _run(self, conversation_id: str, messages: list, active_request: str, workdir: str, lock: threading.Lock):
        def trace(event_type: str, payload: dict):
            self.store.append_debug(conversation_id, event_type, payload)

        try:
            with use_workdir(workdir):
                trigger_hooks("UserPromptSubmit", active_request)
                context = update_context({}, messages)
                agent_loop(messages, context, active_request, trace_callback=trace,
                           session_id=conversation_id)
            self.store.update(conversation_id, messages=json_safe(messages), status="idle", error="")
            self.store.append_debug(conversation_id, "turn_finished", {"message_count": len(messages)})
        except Exception as exc:
            self.store.update(
                conversation_id,
                messages=json_safe(messages),
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )
            self.store.append_debug(conversation_id, "turn_error", {"error": f"{type(exc).__name__}: {exc}"})
        finally:
            lock.release()


class WebHandler(BaseHTTPRequestHandler):
    server_version = "CodingAssistantWeb/0.1"

    @property
    def app(self):
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args):
        # Keep the terminal readable while the CLI is not involved.
        print(f"[web] {self.address_string()} - {fmt % args}")

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(json_safe(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, body: str, content_type: str, status=HTTPStatus.OK):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2_000_000:
            raise ValueError("请求体过大")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8") or "{}")

    def _error(self, message: str, status=HTTPStatus.BAD_REQUEST):
        self._send_json({"error": message}, status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/":
                self._send_text((STATIC_DIR / "index.html").read_text(encoding="utf-8"), "text/html")
            elif path == "/app.css":
                self._send_text((STATIC_DIR / "app.css").read_text(encoding="utf-8"), "text/css")
            elif path == "/app.js":
                self._send_text((STATIC_DIR / "app.js").read_text(encoding="utf-8"), "application/javascript")
            elif path == "/api/conversations":
                self._send_json({"conversations": self.app.store.list()})
            elif path.startswith("/api/conversations/"):
                conversation_id = unquote(path.split("/", 3)[3])
                self._send_json(self.app.store.get(conversation_id))
            else:
                self._error("Not found", HTTPStatus.NOT_FOUND)
        except FileNotFoundError:
            self._error("对话不存在", HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._error(f"{type(exc).__name__}: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        try:
            body = self._body()
            if path == "/api/conversations":
                record = self.app.store.create(body.get("title", ""), body.get("workdir") or str(WORKDIR))
                self._send_json(record, HTTPStatus.CREATED)
                return
            if path.endswith("/messages") and path.startswith("/api/conversations/"):
                conversation_id = unquote(path.split("/", 4)[3])
                self.app.manager.submit(conversation_id, str(body.get("content", "")))
                self._send_json(self.app.store.get(conversation_id), HTTPStatus.ACCEPTED)
                return
            self._error("Not found", HTTPStatus.NOT_FOUND)
        except FileNotFoundError:
            self._error("对话不存在", HTTPStatus.NOT_FOUND)
        except RuntimeError as exc:
            self._error(str(exc), HTTPStatus.CONFLICT)
        except ValueError as exc:
            self._error(str(exc))
        except Exception as exc:
            self._error(f"{type(exc).__name__}: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path.startswith("/api/conversations/"):
            self._error("Not found", HTTPStatus.NOT_FOUND)
            return
        try:
            conversation_id = unquote(path.split("/")[3])
            body = self._body()
            changes = {}
            if "title" in body:
                changes["title"] = str(body["title"]).strip()[:120] or "新对话"
            if "workdir" in body:
                workdir = Path(str(body["workdir"])).expanduser().resolve()
                if not workdir.is_dir():
                    raise ValueError(f"工作目录不存在: {workdir}")
                changes["workdir"] = str(workdir)
            self._send_json(self.app.store.update(conversation_id, **changes))
        except FileNotFoundError:
            self._error("对话不存在", HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._error(str(exc))
        except Exception as exc:
            self._error(f"{type(exc).__name__}: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)


def create_server(host: str = "127.0.0.1", port: int = 8787, store: ConversationStore | None = None):
    app = type("App", (), {})()
    app.store = store or ConversationStore()
    app.manager = ConversationManager(app.store)
    server = ThreadingHTTPServer((host, port), WebHandler)
    server.app = app  # type: ignore[attr-defined]
    return server


def main():
    parser = argparse.ArgumentParser(description="Coding assistant browser UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Coding assistant web UI: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
