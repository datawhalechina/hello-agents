"""HTTP 接口层（FR-11）。

提供生成、历史查询、定稿导出与健康检查接口，并托管 ``frontend/`` 单页应用。
接口只做参数校验、异常到 HTTP 状态码的映射，业务逻辑全部在
:class:`~src.pipeline.StoryPipeline` 中。

错误映射：
    - 请求体非法 → 422（FastAPI 默认校验）；
    - 未配置 LLM → 503；
    - 业务异常（Agent 初始化失败等）→ 502；
    - 运行结果为 ``failed`` → 502，响应体仍包含完整 ``result`` 便于排查；
    - 未知异常 → 500（不向调用方泄露内部细节）。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings, get_settings
from .errors import StoryAgentError, LLMNotConfiguredError
from .logging_utils import configure_logging, get_logger
from .models import GenerationResult, RunStatus, StoryRequest
from .pipeline import StoryPipeline
from .samples import load_samples
from .storage import RunStorage

logger = get_logger("api")

PipelineFactory = Callable[[Settings], StoryPipeline]
router = APIRouter(prefix="/api", tags=["story"])


def _settings(request: Request) -> Settings:
    """从应用状态中取出运行配置。"""
    return request.app.state.settings


def _result_payload(result: GenerationResult) -> dict:
    """把运行结果转换为带导出链接的 JSON 字典。"""
    payload = result.model_dump(mode="json")
    payload["final_markdown_url"] = f"/api/runs/{result.run_id}/final.md"
    payload["final_download_url"] = (
        f"/api/runs/{result.run_id}/final.md?download=true"
    )
    return payload


@router.get("/health")
def health(request: Request) -> dict:
    """健康检查：返回服务版本与 LLM 配置状态（不含密钥）。"""
    settings = _settings(request)
    return {
        "status": "ok",
        "version": __version__,
        "llm_configured": settings.llm_configured,
        "model": settings.llm_model_id or None,
        "approve_score": settings.approve_score,
        "min_relevance_score": settings.min_relevance_score,
        "max_rounds_default": settings.max_rounds_default,
    }


@router.get("/samples")
def samples(request: Request) -> dict:
    """返回内置示例请求，供前端一键填充。"""
    items = load_samples(_settings(request).data_dir / "samples.json")
    return {"samples": items, "count": len(items)}


@router.post("/generate")
def generate(payload: StoryRequest, request: Request):
    """执行一次完整的“生成 → 审稿 → 修订”流程。

    同步执行，耗时取决于轮次与模型速度；前端应展示加载状态。
    """
    settings = _settings(request)
    factory: PipelineFactory = request.app.state.pipeline_factory
    try:
        pipeline = factory(settings)
        result = pipeline.run(payload)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StoryAgentError as exc:
        logger.error("生成失败：%s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 兜底，避免泄露堆栈
        logger.exception("生成接口发生未预期错误")
        raise HTTPException(status_code=500, detail="生成服务暂时不可用。") from exc

    body = _result_payload(result)
    if result.status is RunStatus.FAILED:
        return JSONResponse(status_code=502, content=body)
    return body



@router.get("/runs")
def list_runs(
    request: Request, limit: int = Query(default=20, ge=1, le=100)
) -> dict:
    """按时间倒序返回历史运行摘要。"""
    storage = RunStorage(_settings(request).output_dir)
    items = storage.list_runs(limit=limit)
    return {"runs": items, "count": len(items)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict:
    """读取指定运行的完整结果（含逐轮草稿与审稿）。"""
    storage = RunStorage(_settings(request).output_dir)
    payload = storage.load_result(run_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"未找到运行记录：{run_id}")
    payload["final_markdown_url"] = f"/api/runs/{run_id}/final.md"
    payload["final_download_url"] = f"/api/runs/{run_id}/final.md?download=true"
    return payload


@router.get("/runs/{run_id}/final.md")
def get_final_markdown(
    run_id: str,
    request: Request,
    download: bool = Query(default=False),
) -> FileResponse:
    """返回 ``final.md``；``download=true`` 时作为附件下载。"""
    storage = RunStorage(_settings(request).output_dir)
    path = storage.final_markdown_path(run_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"未找到定稿文件：{run_id}")
    filename = f"story-{run_id}.md" if download else None
    return FileResponse(
        path=path,
        media_type="text/markdown; charset=utf-8",
        filename=filename,
    )


def create_app(
    settings: Settings | None = None,
    pipeline_factory: PipelineFactory | None = None,
) -> FastAPI:
    """创建 FastAPI 应用。

    Args:
        settings: 运行配置，缺省读取环境变量；便于测试注入临时目录。
        pipeline_factory: 流水线工厂，缺省使用
            :meth:`StoryPipeline.from_settings`；测试可注入 FakeLLM 流水线。

    Returns:
        配置完成、可直接交给 uvicorn 的应用实例。
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="智能故事生成器",
        description="写作 Agent + 独立审稿 Agent 的闭环故事生成服务。",
        version=__version__,
    )
    app.state.settings = settings
    app.state.pipeline_factory = pipeline_factory or StoryPipeline.from_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    frontend_dir = Path(settings.frontend_dir)
    index_file = frontend_dir / "index.html"
    if frontend_dir.is_dir():
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        """返回单页应用首页；文件缺失时给出可读提示。"""
        if index_file.exists():
            return FileResponse(index_file, media_type="text/html; charset=utf-8")
        return JSONResponse(
            status_code=200,
            content={
                "message": "智能故事生成器 API 已启动，但前端页面缺失。",
                "docs": "/docs",
                "health": "/api/health",
            },
        )

    return app


app = create_app()
