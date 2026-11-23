"""Start the local app: python main.py [--port 8765]."""
from __future__ import annotations

import argparse
from src.config import ROOT, Settings
from src.server import Application, make_server


def main():
    parser = argparse.ArgumentParser(description="AI 产品经理 · 本地工作台")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    settings = Settings.from_env()
    server = make_server(Application(settings, ROOT / "runtime" / "projects.sqlite3"), args.port)
    print(f"AI Product Manager: http://127.0.0.1:{server.server_port}", flush=True)
    if not settings.public()["ready"]:
        print("界面可以打开；开始 AI 访谈前请安装 requirements.txt 并配置模型连接。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
