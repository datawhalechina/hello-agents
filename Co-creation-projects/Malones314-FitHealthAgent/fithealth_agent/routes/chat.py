"""Thin HTTP adapter for the chat workflow."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fithealth_agent.context_budget import ContextInputError
from fithealth_agent.runtime.responses import context_error_response
from fithealth_agent.workflows.chat_workflow import chat as run_chat_workflow


router = APIRouter()


async def read_chat_request(request: Request) -> dict:
    from fithealth_agent.context_budget import (
        CHAT_REQUEST_MAX_BYTES,
        decode_chat_payload,
        validate_chat_request_headers,
    )

    validate_chat_request_headers(
        request.headers.get("content-type"),
        request.headers.get("content-length"),
    )
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > CHAT_REQUEST_MAX_BYTES:
            raise ContextInputError(
                "REQUEST_TOO_LARGE",
                "聊天请求不能超过 256 KiB。",
                status_code=413,
            )
        chunks.append(chunk)
    return decode_chat_payload(b"".join(chunks))


@router.post("/chat")
async def chat(request: Request) -> JSONResponse:
    try:
        payload = await read_chat_request(request)
    except ContextInputError as exc:
        return context_error_response(exc)
    result = await run_chat_workflow(payload)
    return JSONResponse(result.body, status_code=result.status_code)
