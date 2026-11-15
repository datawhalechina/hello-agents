"""真实 HelloAgents + 本机模拟模型服务：验证协议，不评估模型效果。"""

import os
import threading
from http.server import ThreadingHTTPServer

from mock_provider import Handler, verify


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    os.environ.update(
        OFFERNOTE_API_KEY="local-test-key",
        OFFERNOTE_MODEL="local-check",
        OFFERNOTE_BASE_URL=f"http://127.0.0.1:{server.server_port}/v1",
    )
    try:
        verify()
    finally:
        server.shutdown()
        server.server_close()
