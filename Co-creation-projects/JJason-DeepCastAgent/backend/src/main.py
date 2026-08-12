"""通过 HTTP 暴露 DeepResearchAgent 的 FastAPI 入口点。"""

from __future__ import annotations

import asyncio
import concurrent.futures
import glob
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import Any

# Ensure src directory is in sys.path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

from agent import DeepResearchAgent
from config import Configuration

# 添加控制台日志处理程序
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <4}</level> | <cyan>using_function:{function}</cyan> | <cyan>{file}:{line}</cyan> | <level>{message}</level>",
    colorize=True,
)


class ResearchRequest(BaseModel):
    """触发研究运行的负载。"""

    topic: str = Field(..., description="用户提供的研究主题")

class PodcastScript(BaseModel):
    """播客脚本内容模型。"""
    script: str = Field(..., description="生成的播客脚本内容")


class ResearchResponse(BaseModel):
    """包含生成报告和结构化任务的 HTTP 响应。"""

    report_markdown: str = Field(
        ..., description="Markdown 格式的研究报告，包含各个部分"
    )
    todo_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="带有摘要和来源的结构化待办事项",
    )
    podcast_script: PodcastScript | None = Field(
        default=None,
        description="生成的播客脚本内容",
    )


def _mask_secret(value: str | None, visible: int = 4) -> str:
    """在保持前导和尾随字符的同时，掩盖敏感令牌。"""
    if not value:
        return "unset"

    if len(value) <= visible * 2:
        return "*" * len(value)

    return f"{value[:visible]}...{value[-visible:]}"


def _build_config(payload: ResearchRequest) -> Configuration:
    return Configuration.from_env()


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""

    # 当前活跃的研究 agent 引用，用于支持取消操作
    _active_agent: dict[str, DeepResearchAgent | None] = {"current": None}

    # 确保输出目录存在（使用绝对路径，基于 backend 根目录）
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(backend_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理：启动时记录配置，关闭时清理资源。"""
        config = Configuration.from_env()
        logger.info(
            "DeepResearch configuration loaded: provider=%s model=%s base_url=%s search_api=%s "
            "max_loops=%s fetch_full_page=%s tool_calling=%s strip_thinking=%s api_key=%s",
            config.llm_provider,
            config.resolved_model() or "unset",
            config.llm_base_url or "unset",
            config.search_api.value,
            config.max_web_research_loops,
            config.fetch_full_page,
            config.use_tool_calling,
            config.strip_thinking_tokens,
            _mask_secret(config.llm_api_key),
        )
        yield  # 应用运行中
        # 关闭时清理
        _active_agent["current"] = None

    app = FastAPI(title="DeepCast - 自动播客生成智能体", lifespan=lifespan)

    # 从配置读取 CORS 允许的源，避免生产环境使用通配符
    _startup_config = Configuration.from_env()
    _allowed_origins = [
        origin.strip()
        for origin in _startup_config.cors_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载静态文件目录，用于访问生成的音频文件
    app.mount("/output", StaticFiles(directory=output_dir), name="output")

    @app.get("/healthz")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/audio/latest")
    def get_latest_audio() -> dict[str, Any]:
        """获取最新生成的音频文件。"""
        audio_dir = os.path.join(output_dir, "audio")
        if not os.path.exists(audio_dir):
            return {"file": None, "error": "音频目录不存在"}
        
        # 查找所有 podcast_*.mp3 文件
        pattern = os.path.join(audio_dir, "podcast_*.mp3")
        files = glob.glob(pattern)
        
        if not files:
            return {"file": None, "error": "没有找到音频文件"}
        
        # 按修改时间排序，获取最新的
        latest_file = max(files, key=os.path.getmtime)
        filename = os.path.basename(latest_file)
        return {"file": filename, "url": f"/output/audio/{filename}"}

    @app.post("/research", response_model=ResearchResponse)
    def run_research(payload: ResearchRequest) -> ResearchResponse:
        """
        触发同步研究任务。
        
        执行完整的研究流程，并在 HTTP 响应中一次性返回所有结果。
        """
        try:
            config = _build_config(payload)
            agent = DeepResearchAgent(config=config)
            result = agent.run(payload.topic)
        except ValueError as exc:  # Likely due to unsupported configuration
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guardrail
            raise HTTPException(status_code=500, detail="Research failed") from exc

        todo_payload = [
            {
                "id": item.id,
                "title": item.title,
                "intent": item.intent,
                "query": item.query,
                "status": item.status,
                "summary": item.summary,
                "sources_summary": item.sources_summary,
                "note_id": item.note_id,
                "note_path": item.note_path,
            }
            for item in result.todo_items
        ]

        # 确保 podcast_script 类型正确，Pydantic 模型需要 PodcastScript 实例
        script_content = ""
        if result.podcast_script:
            if isinstance(result.podcast_script, (list, dict)):
                script_content = json.dumps(result.podcast_script, ensure_ascii=False)
            else:
                script_content = str(result.podcast_script)
        
        podcast_resp = PodcastScript(script=script_content)

        return ResearchResponse(
            report_markdown=(result.report_markdown or result.running_summary or ""),
            todo_items=todo_payload,
            podcast_script=podcast_resp,
        )

    @app.post("/research/cancel")
    async def cancel_research() -> dict[str, str]:
        """
        主动取消当前正在执行的研究任务。
        
        前端可以通过此端点显式通知后端停止处理。
        """
        agent = _active_agent.get("current")
        if agent and not agent.is_cancelled():
            logger.info("Cancel requested via /research/cancel endpoint")
            agent.cancel()
            return {"status": "cancelled", "message": "取消请求已发送"}
        return {"status": "no_task", "message": "当前没有正在运行的任务"}

    @app.post("/research/stream")
    async def stream_research(payload: ResearchRequest, request: Request) -> StreamingResponse:
        """
        触发流式研究任务。
        
        通过 Server-Sent Events (SSE) 实时返回研究进度、日志和部分结果。
        支持客户端断开连接时自动取消后端任务。
        """
        try:
            config = _build_config(payload)
            agent = DeepResearchAgent(config=config)
            _active_agent["current"] = agent  # 注册活跃 agent 以支持取消
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        async def event_iterator():
            loop = asyncio.get_event_loop()
            # 用 asyncio.Queue 桥接同步生成器和异步循环
            # 生成器在单一后台线程中完整运行，避免并发调用 next() 破坏生成器状态
            event_queue: asyncio.Queue = asyncio.Queue()
            _SENTINEL = object()  # 生成器结束的哨兵值

            def run_generator():
                """在后台线程中完整运行生成器，将事件逐一推入异步队列。"""
                try:
                    for event in agent.run_stream(payload.topic):
                        if agent.is_cancelled():
                            logger.info("Generator stopped: cancel detected")
                            break
                        loop.call_soon_threadsafe(event_queue.put_nowait, event)
                except Exception as exc:
                    logger.exception("Generator raised exception")
                    loop.call_soon_threadsafe(
                        event_queue.put_nowait,
                        {"type": "error", "detail": str(exc)},
                    )
                finally:
                    loop.call_soon_threadsafe(event_queue.put_nowait, _SENTINEL)

            # 启动断开连接监控任务
            async def monitor_disconnect():
                while True:
                    if await request.is_disconnected():
                        logger.info("Client disconnected detected by monitor")
                        agent.cancel()
                        return
                    await asyncio.sleep(0.5)

            monitor_task = asyncio.create_task(monitor_disconnect())
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            loop.run_in_executor(executor, run_generator)

            try:
                while True:
                    try:
                        # 带超时等待，以便能及时响应取消
                        item = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # 超时时检查是否已取消（用于客户端断开但生成器还未感知的情况）
                        if agent.is_cancelled():
                            logger.info("✅ 本次任务已取消（超时检测）")
                            yield 'data: {"type": "cancelled", "message": "研究任务已被用户取消"}\n\n'
                            break
                        continue

                    # 哨兵：生成器已结束
                    if item is _SENTINEL:
                        break

                    event = item
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    if event.get("type") in ("done", "cancelled", "error"):
                        break
            finally:
                # 确保取消信号被设置 —— 这是取消机制的核心：
                # 前端 abort SSE 后 monitor_task 可能还未检测到断连就被 cancel，
                # 而 /research/cancel API 到达时 _active_agent 可能已被置 None。
                # 因此必须在此处显式调用 cancel() 确保后台线程能感知取消。
                agent.cancel()
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                executor.shutdown(wait=False)
                _active_agent["current"] = None

        return StreamingResponse(
            event_iterator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    _config = Configuration.from_env()
    uvicorn.run(
        "main:app",
        host=_config.host,
        port=_config.port,
        reload=True,
        log_level=_config.log_level.lower(),
    )
