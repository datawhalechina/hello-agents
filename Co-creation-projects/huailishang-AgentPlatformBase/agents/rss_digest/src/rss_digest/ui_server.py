from __future__ import annotations

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
import json
import sys

from rss_digest.config import build_config
from rss_digest.db import connect, get_recent_articles, init_db
from rss_digest.pipeline import run_pipeline


class UIState:
    def __init__(self, root_dir: Path, data_root: Path | None = None) -> None:
        self.root_dir = root_dir
        self.data_root = data_root
        self.lock = Lock()
        self.running = False
        self.last_started_at = None
        self.last_finished_at = None
        self.last_error = None
        self.last_digest_path = None

    def start_run(self) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.last_started_at = datetime.now().isoformat(timespec="seconds")
            self.last_error = None
            return True

    def finish_run(self, digest_path: str | None, error: str | None) -> None:
        with self.lock:
            self.running = False
            self.last_finished_at = datetime.now().isoformat(timespec="seconds")
            self.last_digest_path = digest_path
            self.last_error = error

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "last_started_at": self.last_started_at,
                "last_finished_at": self.last_finished_at,
                "last_error": self.last_error,
                "last_digest_path": self.last_digest_path,
            }


def _read_recent_articles(root_dir: Path, data_root: Path | None = None, limit: int = 12) -> list[dict]:
    cfg = build_config(root_dir, data_root)
    conn = connect(cfg.db_path)
    init_db(conn)
    return get_recent_articles(conn, limit=limit)


def _read_env_summary(root_dir: Path, data_root: Path | None = None) -> dict:
    cfg = build_config(root_dir, data_root)
    return {
        "summary_model": cfg.model_name,
        "translation_model": cfg.translation_model_name or cfg.model_name,
        "max_articles_per_run": cfg.max_articles_per_run,
        "llm_timeout_seconds": cfg.llm_timeout_seconds,
        "resummarize_existing": cfg.resummarize_existing,
        "fetch_full_translation": cfg.fetch_full_translation,
    }


def _latest_digest_path(root_dir: Path, data_root: Path | None = None) -> str | None:
    if data_root is None:
        data_root = root_dir / "data"
    digest_dir = data_root / "runs" / "digests"
    files = sorted(digest_dir.glob("digest_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files[0]) if files else None


def _run_pipeline_background(state: UIState) -> None:
    digest_path = None
    error = None
    try:
        run_pipeline(state.root_dir, state.data_root)
        digest_path = _latest_digest_path(state.root_dir, state.data_root)
    except Exception as exc:
        error = str(exc)
    finally:
        state.finish_run(digest_path, error)


def build_handler(root_dir: Path, state: UIState):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _html(self, body: str, status: int = 200) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                snapshot = state.snapshot()
                env_summary = _read_env_summary(root_dir, state.data_root)
                body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RSS Digest UI</title>
  <style>
    body {{ font-family: "Segoe UI","Microsoft YaHei",sans-serif; margin: 0; background: #f3eee3; color: #201c18; }}
    .page {{ max-width: 1100px; margin: 0 auto; padding: 24px 18px 40px; }}
    .hero, .panel {{ background: #fffdf8; border: 1px solid #dccfbc; border-radius: 18px; padding: 18px 20px; box-shadow: 0 10px 20px rgba(0,0,0,.03); }}
    .hero h1 {{ margin: 0 0 8px; }}
    .grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 16px; margin-top: 16px; }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }}
    button, a.btn {{ background: #9a4f2b; color: #fff; border: 0; border-radius: 999px; padding: 10px 16px; text-decoration: none; cursor: pointer; }}
    a.btn.secondary, button.secondary {{ background: #efe3d5; color: #6a4a34; }}
    .meta {{ color: #655c52; line-height: 1.8; }}
    .articles {{ margin-top: 16px; display: grid; gap: 12px; }}
    .card {{ background: #fffaf2; border: 1px solid #e1d4c1; border-radius: 16px; padding: 14px 16px; }}
    .muted {{ color: #6f665c; }}
    .score {{ float: right; font-weight: 700; color: #2f6b4f; }}
    iframe {{ width: 100%; height: 620px; border: 1px solid #dccfbc; border-radius: 16px; background: white; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} iframe {{ height: 420px; }} }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>RSS Digest 控制台</h1>
      <div class="meta">
        <div>摘要模型：{env_summary["summary_model"] or "未配置"}</div>
        <div>翻译模型：{env_summary["translation_model"] or "未配置"}</div>
        <div>每轮文章数：{env_summary["max_articles_per_run"]} | 重做旧摘要：{env_summary["resummarize_existing"]} | 全文翻译：{env_summary["fetch_full_translation"]}</div>
        <div>运行状态：{"运行中" if snapshot["running"] else "空闲"}</div>
        <div>最近启动：{snapshot["last_started_at"] or "暂无"} | 最近完成：{snapshot["last_finished_at"] or "暂无"}</div>
        <div>最近错误：{snapshot["last_error"] or "无"}</div>
      </div>
      <div class="row">
        <button onclick="runDigest()">运行一次</button>
        <button class="secondary" onclick="refreshStatus()">刷新状态</button>
        <a class="btn secondary" href="/digest" target="_blank">打开最新 HTML</a>
      </div>
    </section>
    <section class="grid">
      <section class="panel">
        <h2>最近文章</h2>
        <div id="articles" class="articles"></div>
      </section>
      <section class="panel">
        <h2>最新日报预览</h2>
        <iframe src="/digest"></iframe>
      </section>
    </section>
  </main>
  <script>
    async function refreshStatus() {{
      const res = await fetch('/api/status');
      const data = await res.json();
      console.log(data);
    }}
    async function loadArticles() {{
      const res = await fetch('/api/articles');
      const data = await res.json();
      const root = document.getElementById('articles');
      root.innerHTML = '';
      for (const article of data.articles) {{
        const div = document.createElement('div');
        div.className = 'card';
        div.innerHTML = `
          <div><strong>${{article.title}}</strong><span class="score">${{article.article_score ?? '-'}} 分</span></div>
          <div class="muted">${{article.source_name}} · ${{article.category}} · ${{article.worth_reading ?? '未评级'}}</div>
          <div style="margin-top:8px;">${{article.one_line ?? article.summary_cn ?? '暂无摘要'}}</div>
          <div style="margin-top:8px;"><a href="${{article.link}}" target="_blank">原文</a></div>
        `;
        root.appendChild(div);
      }}
    }}
    async function runDigest() {{
      const res = await fetch('/api/run', {{method: 'POST'}});
      const data = await res.json();
      alert(data.message);
      await loadArticles();
    }}
    loadArticles();
  </script>
</body>
</html>"""
                self._html(body)
                return

            if parsed.path == "/api/status":
                payload = state.snapshot()
                payload["latest_digest_path"] = _latest_digest_path(root_dir, state.data_root)
                payload["env"] = _read_env_summary(root_dir, state.data_root)
                self._json(payload)
                return

            if parsed.path == "/api/articles":
                articles = _read_recent_articles(root_dir, state.data_root, limit=12)
                self._json({"articles": articles})
                return

            if parsed.path == "/digest":
                digest_path = _latest_digest_path(root_dir, state.data_root)
                if not digest_path:
                    self._html("<p>暂无日报，请先运行一次任务。</p>", status=200)
                    return
                data = Path(digest_path).read_text(encoding="utf-8")
                self._html(data)
                return

            self._html("<p>Not found</p>", status=404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/run":
                if not state.start_run():
                    self._json({"ok": False, "message": "任务已经在运行中。"}, status=409)
                    return
                Thread(target=_run_pipeline_background, args=(state,), daemon=True).start()
                self._json({"ok": True, "message": "后台任务已启动。"})
                return
            self._json({"ok": False, "message": "Not found"}, status=404)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def serve_ui(root_dir: Path, data_root: Path | None = None, host: str = "127.0.0.1", port: int = 8765) -> None:
    state = UIState(root_dir, data_root)
    server = ThreadingHTTPServer((host, port), build_handler(root_dir, state))
    print(f"UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
