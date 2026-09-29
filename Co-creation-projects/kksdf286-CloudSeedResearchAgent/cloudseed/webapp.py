"""Local-only browser interface using Python's standard library."""

import base64
import json
import os
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .exporter import report, zip_bytes
from .pipeline import configure_env, config_available, run_pipeline
from .sources import ROOT, DEFAULT_TOPIC, DEFAULT_RESOURCES, load_sources, pdf_source, search_crossref


def serve(port=8765, env_file=None):
    if not 1024 <= port <= 65535:
        raise ValueError("端口应在1024—65535之间。")
    configure_env(env_file)
    jobs = {}
    lock = threading.Lock()
    active = threading.Lock()

    def run_job(job_id, body):
        def progress(index, name, state):
            with lock:
                jobs[job_id].update(stage=index, agent=name, stage_state=state)
        try:
            result = run_pipeline(body.get("sources", load_sources()), body.get("topic", DEFAULT_TOPIC),
                                  body.get("resources", DEFAULT_RESOURCES), body.get("mode", "demo"), progress)
            with lock:
                jobs[job_id].update(status="done", result=result)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}：分析失败，请检查模型配置和网络后重试。"
            with lock:
                jobs[job_id].update(status="error", error=message)
        finally:
            active.release()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, data, content_type="application/json; charset=utf-8", status=200, filename=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def allowed(self):
            # No CORS; reject cross-origin mutation of this local application.
            host = self.headers.get("Host", "")
            if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                return False
            origin = self.headers.get("Origin")
            return not origin or origin in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

        def do_GET(self):
            if not self.allowed():
                return self.send({"error": "请从本机地址打开。"}, status=403)
            path = urlsplit(self.path).path
            if path == "/":
                return self.send((ROOT / "ui/index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/api/config":
                return self.send({"live_available": config_available(), "topic": DEFAULT_TOPIC, "resources": DEFAULT_RESOURCES, "sources": load_sources()})
            if path == "/api/example":
                return self.send(run_pipeline(load_sources(), mode="demo"))
            if path.startswith("/api/jobs/"):
                parts = path.split("/")
                job_id = parts[3] if len(parts) > 3 else ""
                with lock:
                    job = dict(jobs.get(job_id, {}))
                if not job:
                    return self.send({"error": "分析记录不存在，请重新运行。"}, status=404)
                if len(parts) > 4 and job.get("status") == "done":
                    if parts[4] == "download":
                        return self.send(zip_bytes(job["result"]), "application/zip", filename="cloudseed-notes.zip")
                    if parts[4] == "report":
                        return self.send(report(job["result"]).encode("utf-8"), "text/markdown; charset=utf-8", filename="report.md")
                return self.send(job)
            return self.send({"error": "页面不存在。"}, status=404)

        def do_POST(self):
            if not self.allowed():
                return self.send({"error": "请求来源不匹配。"}, status=403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 24 * 1024 * 1024:
                    raise ValueError("请求为空或超过24MB，请缩小导入文件。")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("请求必须是JSON对象。")
                path = urlsplit(self.path).path
                if path == "/api/analyze":
                    if not active.acquire(blocking=False):
                        return self.send({"error": "已有分析正在运行，请等待当前任务完成。"}, status=409)
                    job_id = uuid.uuid4().hex
                    with lock:
                        if len(jobs) >= 12:
                            for key in list(jobs):
                                if jobs[key]["status"] != "running":
                                    del jobs[key]
                                    break
                        jobs[job_id] = {"status": "running", "stage": 0, "agent": "准备资料", "stage_state": "running"}
                    threading.Thread(target=run_job, args=(job_id, body), daemon=True).start()
                    return self.send({"job_id": job_id}, status=202)
                if path == "/api/import-pdf":
                    blob = base64.b64decode(body.get("data", ""), validate=True)
                    if not blob.startswith(b"%PDF") or len(blob) > 16 * 1024 * 1024:
                        raise ValueError("请导入16MB以内的有效PDF。")
                    with tempfile.TemporaryDirectory(prefix="cloudseed-") as directory:
                        tmp = Path(directory) / "paper.pdf"
                        tmp.write_bytes(blob)
                        source = pdf_source(tmp, body.get("id", "P1"), str(body.get("title", "导入论文")))
                    return self.send({"source": source})
                if path == "/api/search":
                    return self.send({"sources": search_crossref(str(body.get("query", "")))})
                return self.send({"error": "接口不存在。"}, status=404)
            except Exception as exc:
                message = str(exc) if isinstance(exc, ValueError) else "导入或检索失败，请检查文件和网络；可改用粘贴文本。"
                return self.send({"error": message}, status=400)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"本地网页：http://127.0.0.1:{port}", flush=True)
    print(f"模型配置：{'可用' if config_available() else '未配置，可运行离线示例'}。按Ctrl+C停止。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
