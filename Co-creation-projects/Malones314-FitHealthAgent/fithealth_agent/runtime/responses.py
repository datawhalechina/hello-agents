"""跨路由复用的 HTTP 响应构造器（main.py 拆分：阶段 2）。"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from fithealth_agent.context_budget import ContextInputError


def context_error_response(exc: ContextInputError) -> JSONResponse:
    return JSONResponse(
        {
            "reply": exc.message,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field or None,
            },
        },
        status_code=exc.status_code,
    )
