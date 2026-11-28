"""项目根入口：python main.py 启动后端服务。"""

import uvicorn

from app.core.config import settings
from app.main import app

__all__ = ["app"]


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
