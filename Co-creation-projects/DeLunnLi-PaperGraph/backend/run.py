#!/usr/bin/env python3
"""PaperGraph Backend 启动脚本"""

import logging
import os
import sys

os.environ.setdefault("FZ_LOAD_SYSTEM_CMS", "0")  # 抑制 MuPDF/PyMuPDF ICC 颜色配置缺失警告

# PaperGraph 根目录（含 papergraph/ 包）：开发时可在该目录执行 pip install -e . 替代仅靠 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.settings import configure_logging, get_settings

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 启动 %s...", settings.app_name)

    # 说明：
    # - 开发模式 settings.debug=True 时，uvicorn 会开启 reload（WatchFiles）自动重启。
    # - 但流式接口（SSE）在重启窗口会触发前端报错：BodyStreamBuffer was aborted / ECONNRESET。
    # - 因此提供显式开关：PAPERGRAPH_UVICORN_RELOAD=0 可在 debug=True 时也关闭热重载，便于稳定测试。
    reload_flag = settings.debug
    env_reload = (os.getenv("PAPERGRAPH_UVICORN_RELOAD") or "").strip().lower()
    if env_reload in ("0", "false", "no", "off"):
        reload_flag = False
    elif env_reload in ("1", "true", "yes", "on"):
        reload_flag = True
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=reload_flag,
        log_level="info"
    )
