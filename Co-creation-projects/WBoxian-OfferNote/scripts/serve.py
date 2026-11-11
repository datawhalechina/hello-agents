"""从任意工作目录启动本地应用。"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)


def serve(port: int = 8765):
    import uvicorn
    from app.main import app
    from scripts.server_control import attach, release

    if not (ROOT / "frontend/dist/index.html").exists():
        print(
            "前端尚未构建，请先在 frontend 执行 npm ci && npm run build。API 仍可使用。"
        )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port))
    state = attach(app, server, port)
    try:
        server.run()
    finally:
        release(state)


if __name__ == "__main__":
    serve()
