"""Wellness 工具基类：参数强校验、独立事务、自动 Trace。"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import trace_service

logger = logging.getLogger(__name__)

_TYPE_MAP = {
    "string": "string",
    "number": "number",
    "integer": "integer",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
}


def _resolve_type(prop: dict) -> str:
    declared = prop.get("type")
    if isinstance(declared, str):
        return _TYPE_MAP.get(declared, "string")
    for candidate in prop.get("anyOf", []) or []:
        if candidate.get("type") != "null":
            return _resolve_type(candidate)
    return "string"


def schema_to_parameters(model: type[BaseModel]) -> list[ToolParameter]:
    """从 Pydantic 模型生成 HelloAgents 工具参数定义。"""
    schema = model.model_json_schema()
    required = set(schema.get("required", []))
    return [
        ToolParameter(
            name=name,
            type=_resolve_type(prop),
            description=prop.get("description") or f"参数 {name}",
            required=name in required,
            default=prop.get("default"),
        )
        for name, prop in schema.get("properties", {}).items()
    ]


def json_safe(value: Any) -> Any:
    """把 datetime 等对象统一转为可 JSON 序列化的结构。"""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class WellnessTool(Tool):
    """所有业务工具的统一封装。

    handler 接收校验后的 Pydantic 模型和数据库会话，返回可序列化的 dict。
    """

    def __init__(
        self,
        name: str,
        description: str,
        param_model: type[BaseModel],
        handler: Callable[[BaseModel, Session], dict],
    ) -> None:
        super().__init__(name=name, description=description)
        self.param_model = param_model
        self.handler = handler
        self._parameters = schema_to_parameters(param_model)

    def get_parameters(self) -> list[ToolParameter]:
        return self._parameters

    def run(self, parameters: dict[str, Any]) -> ToolResponse:
        started = time.perf_counter()
        try:
            params = self.param_model.model_validate(parameters)
            with SessionLocal() as db:
                try:
                    result = self.handler(params, db)
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            payload = json_safe(result)
            self._record_trace(parameters, payload, None, started)
            return ToolResponse.success(
                text=json.dumps(payload, ensure_ascii=False),
                data=payload,
            )
        except ValidationError as exc:
            message = f"参数校验失败: {exc.errors(include_url=False)}"
            self._record_trace(parameters, None, message, started)
            return ToolResponse.error(code="INVALID_PARAM", message=message)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self._record_trace(parameters, None, message, started)
            return ToolResponse.error(code="EXECUTION_ERROR", message=message)

    def _record_trace(
        self,
        parameters: dict[str, Any],
        result: Any,
        error: str | None,
        started: float,
    ) -> None:
        trace_id = trace_service.current_trace_id.get()
        if not trace_id or not settings.trace_enabled:
            return
        try:
            with SessionLocal() as db:
                trace_service.add_step(
                    db,
                    trace_id,
                    "tool_error" if error else "tool_call",
                    tool_name=self.name,
                    tool_input=json_safe(parameters),
                    tool_output={"result": result} if result is not None else None,
                    error=error,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                db.commit()
        except Exception:
            logger.warning("写入工具 Trace 失败", exc_info=True)
