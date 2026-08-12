"""全局异常处理：统一响应 {success, message, error_code}。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..exceptions import AppError
from ..utils.logger import get_logger

logger = get_logger("app.errors")


def _body(message: str, error_code: str) -> dict:
    return {"success": False, "message": message, "error_code": error_code}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("[%s] %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.message, exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        msg = "; ".join(
            f"{'.'.join(str(x) for x in err.get('loc', ()))}: {err.get('msg')}"
            for err in exc.errors()
        )
        logger.warning("validation: %s", msg)
        return JSONResponse(status_code=422, content=_body(msg, "VALIDATION_ERROR"))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(message, "HTTP_ERROR"),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_body("服务器内部错误", "INTERNAL_ERROR"),
        )
