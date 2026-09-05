"""FastAPI 应用入口：挂载路由、配置 CORS、启动 uvicorn

启动方式：
    python run_backend.py
    或
    uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Paper Innovation Agent API",
    description="论文创新 Agent 异步接口：提交分析、SSE 进度推送、报告查询",
    version="1.0.0",
)

# 配置 CORS：允许前端 localhost:5173 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(router)


@app.on_event("startup")
async def on_startup() -> None:
    """应用启动日志 + 预加载重型模块

    预加载 torch/transformers/chromadb 等重型依赖，避免首次处理论文时
    才触发 import（实测 import torch 单独就要 100+ 秒）。
    """
    import time as _t

    _t0 = _t.perf_counter()
    logger.info("Paper Innovation Agent API 已启动，开始预加载重型模块...")

    # 顺序预加载：torch → transformers → chromadb → embedding（含模型加载）
    try:
        _t1 = _t.perf_counter()
        import torch  # noqa: F401
        logger.info("[预加载] import torch: %.2fs", _t.perf_counter() - _t1)

        _t2 = _t.perf_counter()
        from transformers import AutoModel, AutoTokenizer  # noqa: F401
        logger.info("[预加载] import transformers: %.2fs", _t.perf_counter() - _t2)

        _t3 = _t.perf_counter()
        import chromadb  # noqa: F401
        logger.info("[预加载] import chromadb: %.2fs", _t.perf_counter() - _t3)

        # 预加载 Embedder 单例（首次会触发模型加载 + CUDA 上下文初始化）
        _t4 = _t.perf_counter()
        from backend.rag.embedding import get_default_embedder
        _embedder = get_default_embedder()  # 注册为模块级单例
        # 触发模型加载 + 首次 forward（完成 CUDA 上下文初始化）
        _embedder.embed_texts(["预加载测试文本"])
        logger.info(
            "[预加载] Embedder 模型加载 + CUDA warmup: %.2fs (device=%s)",
            _t.perf_counter() - _t4,
            getattr(_embedder, "_device", "unknown"),
        )
    except Exception as exc:
        logger.warning("[预加载] 失败（不影响启动）: %s", exc)

    logger.info("[预加载] 全部完成: %.2fs", _t.perf_counter() - _t0)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
