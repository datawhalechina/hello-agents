"""
Mock OpenAI 协议服务器（E2E 测试用）
=================================
提供 POST /v1/chat/completions，返回固定格式回复，并把每次请求写入 mock_log.jsonl。
启动：uv run uvicorn tests.mock_openai:app --host 127.0.0.1 --port 9000
"""
from fastapi import FastAPI, Request
import time
import json
import os

app = FastAPI()

LOG_PATH = os.path.join(os.path.dirname(__file__), "mock_log.jsonl")


def _log(entry: dict) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "unknown")
    messages = body.get("messages", [])
    last_user = ""
    for m in messages:
        if m.get("role") == "user":
            last_user = m.get("content", "")
    _log({"endpoint": "/v1/chat/completions", "model": model, "last_user": last_user[:200]})
    content = f"[mock:{model}] 收到: {last_user}"
    return {
        "id": "mock-1",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": "mock",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }
