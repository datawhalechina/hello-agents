"""
智能股票分析助手 — PyInstaller exe 入口

使用方式：
    # 开发模式（不打包）
    python run_exe.py

    # PyInstaller 打包后
    stock_analyzer.exe
    浏览器访问 http://127.0.0.1:5174/dashboard（端口可由 .env 中 BACKEND_PORT 修改）
"""

import sys
import os
from pathlib import Path

# PyInstaller 打包后的路径修正
if getattr(sys, 'frozen', False):
    # _MEIPASS 是 PyInstaller 的临时解压目录
    _bundle = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    _root = _bundle
else:
    _root = Path(__file__).parent

_backend = _root / "backend"
_agents = _root / "agents"
_hello = _root / "HelloAgents Optimized"

for p in [_backend, _root, _agents, _hello]:
    _s = str(p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import uvicorn
from app.config import settings, IS_FROZEN
from app.main import app

if __name__ == "__main__":
    host = settings.BACKEND_HOST
    port = settings.BACKEND_PORT

    print(f"============================================")
    print(f"  智能股票分析助手")
    print(f"  版本: 0.1.0")
    print(f"  模式: {'exe 独立运行' if IS_FROZEN else '开发模式'}")
    print(f"============================================")
    # 控制台提示：监听地址可为 0.0.0.0，本机浏览器统一用 127.0.0.1
    _ui_host = "127.0.0.1"
    print(f"  后端 API: http://{_ui_host}:{port}/docs")
    print(f"  前端界面: http://{_ui_host}:{port}/dashboard")
    print(f"============================================")

    if IS_FROZEN:
        import webbrowser
        import threading

        _no_browser = os.environ.get("NO_BROWSER", "").lower() in ("1", "true", "yes")

        def _open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{_ui_host}:{port}/dashboard")

        if not _no_browser:
            threading.Thread(target=_open_browser, daemon=True).start()
            print(f"  浏览器将自动打开，设置 NO_BROWSER=1 可禁用")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
