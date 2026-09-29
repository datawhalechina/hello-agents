# -*- coding: utf-8 -*-
"""VulnAuditAgent 桌面应用入口（双击即用，原生窗口，无浏览器地址栏）"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
import webview
from web_ui import app as fastapi_app


def start_server():
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8501, log_level="error")


if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    time.sleep(1.5)  # 等后端服务就绪
    webview.create_window(
        "VulnAuditAgent · 智能代码漏洞审计",
        "http://127.0.0.1:8501",
        width=1180, height=800, min_size=(960, 640),
    )
    webview.start()
