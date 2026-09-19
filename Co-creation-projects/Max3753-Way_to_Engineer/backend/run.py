"""启动脚本"""

import os
import uvicorn
from app.config import get_settings

if __name__ == '__main__':
    settings = get_settings()
    
    # 若端口被 Windows 保留导致 WSAEACCES，设为 false 可绕过：$env:UVICORN_RELOAD='false'
    reload_enabled = os.getenv("UVICORN_RELOAD", "").lower() not in ("false", "0", "no")
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=reload_enabled,
        log_level="info",
    )
