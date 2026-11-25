"""Small loopback-only HTTP application using Python's standard library."""
from __future__ import annotations

import copy
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import AppError, ROOT, Settings
from .services import HelloAgentsBackend, TavilySearch
from .workflow import Store, Workflow, string


def render_release_checklist(state: dict) -> str:
    requirements = (state.get("prd") or {}).get("requirements", [])
    reviews = state.get("prd_reviews") or {}
    lines = [f"# {state['title']} · 首版开发清单", ""]
    for index, requirement in enumerate(requirements):
        review = reviews.get(str(index), {})
        if review.get("decision") != "first_release":
            continue
        name = " ".join(requirement["name"].splitlines())
        description = "\n    ".join(requirement["description"].splitlines())
        acceptance = "\n    ".join(review["acceptance"].splitlines())
        lines.extend([f"- [ ] **F{index + 1:02d} {name}**",
                      f"  - **功能说明** {description}", f"  - **验收条件** {acceptance}", ""])
    if len(lines) == 2:
        raise AppError("请先在功能评审中将至少一项标为「首版做」。", 409)
    return "\n".join(lines)


class Application:
    def __init__(self, settings: Settings, db_path: Path, backend_factory=HelloAgentsBackend, search_factory=None):
        self.settings = settings
        self.store = Store(db_path)
        self.backend_factory = backend_factory
        self.search_factory = search_factory or (lambda cfg: TavilySearch(cfg.search_key))
        self.lock = threading.RLock()

    def workflow(self) -> Workflow:
        cfg = copy.copy(self.settings)
        return Workflow(self.store, self.backend_factory(cfg), self.search_factory(cfg))

    def launch(self, state, workflow, action, *args):
        state.update(busy=True, error="", retry_action=action)
        self.store.save(state)

        def work():
            try:
                getattr(workflow, action)(state, *args)
            except AppError as exc:
                state["error"] = str(exc)
            except Exception:
                state["error"] = "处理没有完成，请重试。若仍失败，请检查服务配置与模型输出格式。"
            finally:
                state["busy"] = False
                self.store.save(state)

        threading.Thread(target=work, daemon=True).start()
        return self.store.get(state["id"])

    def dispatch(self, path: str, body: dict) -> dict:
        with self.lock:
            if path == "/api/settings":
                if any(p.get("busy") for p in self.store.list()):
                    raise AppError("任务运行期间请稍后再修改连接设置。", 409)
                new = copy.copy(self.settings)
                new.model = string(body.get("model", new.model), 150)
                new.base_url = string(body.get("base_url", new.base_url), 1000).rstrip("/")
                # Blank input preserves the existing secret; keys never travel back to the browser.
                for key, attr in (("api_key", "api_key"), ("search_key", "search_key")):
                    value = string(body.get(key, ""), 2000)
                    if value:
                        setattr(new, attr, value)
                new.validate()
                self.settings = new
                return new.public()
            workflow = self.workflow()
            if path == "/api/projects":
                self.settings.validate()
                state = workflow.create(body.get("idea", ""))
                return self.launch(state, workflow, "interview")
            parts = path.strip("/").split("/")
            if len(parts) != 4 or parts[:2] != ["api", "projects"]:
                raise AppError("接口不存在。", 404)
            state, action = self.store.get(parts[2]), parts[3]
            if state["busy"]:
                raise AppError("这个项目正在处理中，请稍候。", 409)
            questions = body.get("pending_questions")
            if action == "answer":
                self.settings.validate()
                workflow.add_answer(state, body.get("answer", ""), body.get("edits"), questions)
                return self.launch(state, workflow, "interview")
            if action == "draft":
                workflow.save_draft(state, body.get("edits", {}), questions)
            elif action == "confirm":
                workflow.confirm(state, body.get("brief", {}), questions)
            elif action == "reopen":
                workflow.reopen(state)
            elif action == "review":
                workflow.review_requirement(state, body.get("index"), body.get("decision"),
                                            body.get("acceptance"), body.get("report_id"))
            elif action == "generate":
                self.settings.validate()
                if state["confirmed_brief"] is None:
                    raise AppError("请先确认需求。", 409)
                online = body.get("online", True)
                if not isinstance(online, bool):
                    raise AppError("联网选项必须是布尔值。")
                if online and not self.settings.search_key:
                    raise AppError("请先配置 Tavily 搜索密钥，或取消勾选联网竞品研究。", 503)
                return self.launch(state, workflow, "generate", online)
            elif action == "retry":
                self.settings.validate()
                if not state["error"]:
                    raise AppError("当前没有失败的任务。", 409)
                previous = state.get("retry_action", "interview")
                return self.launch(state, workflow, previous, *([state.get("online", True)] if previous == "generate" else []))
            else:
                raise AppError("接口不存在。", 404)
            return self.store.get(state["id"])


def make_server(app: Application, port: int = 8765) -> ThreadingHTTPServer:
    static = ROOT / "web"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, content, content_type="application/json; charset=utf-8", filename=None):
            data = json.dumps(content, ensure_ascii=False).encode() if content_type.startswith("application/json") else content
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                if path == "/api/health":
                    self.respond(200, app.settings.public())
                elif path == "/api/projects":
                    self.respond(200, app.store.list())
                elif path.startswith("/api/projects/"):
                    parts = path.strip("/").split("/")
                    state = app.store.get(parts[2])
                    if len(parts) == 3:
                        self.respond(200, state)
                    elif len(parts) == 4 and parts[3] in ("export", "release-checklist"):
                        if not state["report"] or state["busy"]:
                            raise AppError("请等待文档生成完成后再导出。", 409)
                        if parts[3] == "export":
                            content, filename = state["report"], "product-requirements.md"
                        else:
                            content, filename = render_release_checklist(state), "first-release-checklist.md"
                        self.respond(200, content.encode("utf-8"), "text/markdown; charset=utf-8", filename)
                    else:
                        raise AppError("接口不存在。", 404)
                elif path in ("/", "/index.html", "/app.js", "/style.css", "/favicon.svg", "/tokens.css", "/font.woff2"):
                    file = static / ("index.html" if path == "/" else path[1:])
                    if not file.is_file():
                        raise AppError("文件不存在。", 404)
                    kind = mimetypes.guess_type(str(file))[0] or "application/octet-stream"
                    self.respond(200, file.read_bytes(), kind + ("; charset=utf-8" if kind.startswith("text/") else ""))
                else:
                    raise AppError("页面不存在。", 404)
            except AppError as exc:
                self.respond(exc.status, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            try:
                path = urlparse(self.path).path
                origin = self.headers.get("Origin")
                if origin and urlparse(origin).netloc != self.headers.get("Host"):
                    raise AppError("不接受来自其他网站的操作请求。", 403)
                if self.headers.get("X-Requested-With") != "AIProductManager":
                    raise AppError("缺少请求标记。", 403)
                if self.headers.get_content_type() != "application/json":
                    raise AppError("请求格式应为 JSON。", 415)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    raise AppError("请求长度无效。") from None
                # A full brief plus its pending questions can exceed the regular request limit.
                edits_project = path.startswith("/api/projects/") and path.rsplit("/", 1)[-1] in ("draft", "answer", "confirm")
                limit = 1_600_000 if edits_project else 100_000
                if not 0 < length <= limit:
                    raise AppError("请求内容过大或为空。", 413)
                try:
                    body = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeError):
                    raise AppError("请求不是有效的 JSON。") from None
                if not isinstance(body, dict):
                    raise AppError("请求内容应为对象。")
                self.respond(200, app.dispatch(path, body))
            except AppError as exc:
                self.respond(exc.status, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.respond(500, {"error": "服务处理失败，请稍后重试。"})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
