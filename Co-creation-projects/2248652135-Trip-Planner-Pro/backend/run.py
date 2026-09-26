"""启动脚本"""

import sys
sys.path.append(r"D:\learn-agent\hello-agents-1.0.2")
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    # SSL配置（路径自动基于 backend/ 目录解析）
    ssl_kwargs = {}
    if settings.ssl_enabled:
        ssl_kwargs["ssl_certfile"] = settings.get_ssl_certfile()
        ssl_kwargs["ssl_keyfile"] = settings.get_ssl_keyfile()

    protocol = "https" if settings.ssl_enabled else "http"
    print(f"\n🔒 协议: {protocol.upper()}")

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
        **ssl_kwargs
    )

