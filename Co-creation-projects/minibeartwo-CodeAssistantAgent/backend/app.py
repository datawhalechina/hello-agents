"""Authenticated loopback HTTP API and persisted server-sent events."""
from __future__ import annotations

import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .patches import Patches
from .models import discover_models, test_connection
from .runtime import Runtime, TERMINAL
from .settings import DEFAULT_MAX_STEPS, Settings
from .store import Store, identifier
from .workspace import Conflict, MAX_FILE, Workspace


class OpenWorkspace(BaseModel):
    path: str = Field(min_length=1, max_length=2000)


class SaveFile(BaseModel):
    path: str = Field(min_length=1, max_length=2000)
    content: str = Field(max_length=256_000)
    base_hash: str = Field(min_length=1, max_length=100)


class NewTask(BaseModel):
    workspace_id: str
    session_id: str | None = None
    prompt: str = Field(min_length=1, max_length=12000)
    selected_file: str | None = None
    test_argv: list[str] = Field(default_factory=list, max_length=30)
    skill: Literal["annotate-project-zh", "analyze-project-zh"] | None = None


class ModelSettings(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    base_url: str = Field(min_length=1, max_length=2000)
    api_key: str = Field(default="", max_length=2000)
    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1)


class ModelDiscovery(BaseModel):
    base_url: str = Field(min_length=1, max_length=2000)
    api_key: str = Field(default="", max_length=2000)
    connection_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    use_saved_key: bool = True


class SavedConnection(ModelSettings):
    id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    name: str = Field(default="", max_length=100)


class Review(BaseModel):
    accept: bool


def data_directory() -> Path:
    configured = os.getenv("CODE_ASSISTANT_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    base = Path(os.getenv("LOCALAPPDATA", Path.home() / ".local/share"))
    return base / "CodeAssistantAgent"


def create_app(data_dir: Path | None = None, token: str | None = None, model_factory=None, persist_secrets: bool = True) -> FastAPI:
    store = Store((data_dir or data_directory()) / "state.sqlite3")
    settings = Settings(store, persist_secrets=persist_secrets)
    runtime = Runtime(store, settings, model_factory)
    bearer = token or os.getenv("CODE_ASSISTANT_TOKEN") or identifier()

    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        await runtime.resume_annotation_reviews()
        yield
        await runtime.close()

    app = FastAPI(title="CodeAssistantAgent", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.runtime, app.state.settings = store, runtime, settings

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path != "/health":
            supplied = request.headers.get("authorization", "")
            if not hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + bearer).encode("utf-8")):
                return JSONResponse({"detail": "本地服务认证失败。"}, status_code=401)
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409 if isinstance(exc, Conflict) else 400)

    @app.exception_handler(LookupError)
    async def missing_record(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(OSError)
    async def filesystem_error(request, exc):
        return JSONResponse({"detail": "文件操作失败：" + str(exc)}, status_code=400)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "CodeAssistantAgent", "version": "0.1.0"}

    @app.get("/api/settings")
    async def get_settings():
        return settings.public()

    @app.put("/api/settings")
    async def save_settings(values: ModelSettings):
        return settings.save(values.model_dump())

    @app.get("/api/connections")
    async def list_connections():
        return settings.connections()

    @app.post("/api/connections")
    async def save_connection(values: SavedConnection):
        return settings.save_connection(values.model_dump())

    @app.delete("/api/connections/{connection_id}")
    async def delete_connection(connection_id: str):
        return settings.delete_connection(connection_id)

    @app.post("/api/connections/{connection_id}/activate")
    async def activate_connection(connection_id: str):
        return settings.activate(connection_id)

    @app.post("/api/models")
    async def list_models(values: ModelDiscovery):
        return {"models": await discover_models(values.base_url, values.api_key, settings,
            values.connection_id, values.use_saved_key)}

    @app.post("/api/connection-test")
    async def check_connection(values: ModelDiscovery):
        return await test_connection(values.base_url, values.api_key, settings,
            values.connection_id, values.use_saved_key)

    @app.get("/api/workspaces")
    async def list_workspaces():
        return store.rows("SELECT * FROM workspaces ORDER BY name")

    @app.post("/api/workspaces")
    async def open_workspace(values: OpenWorkspace):
        workspace = Workspace(values.path)
        existing = store.rows("SELECT * FROM workspaces WHERE root=?", (str(workspace.root),))
        if existing:
            return existing[0]
        workspace_id = identifier()
        store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(workspace.root), workspace.root.name))
        return store.one("workspaces", workspace_id)

    def workspace_for(workspace_id: str) -> Workspace:
        return Workspace(store.one("workspaces", workspace_id)["root"])

    @app.get("/api/workspaces/{workspace_id}/tree")
    async def tree(workspace_id: str, path: str = ""):
        return await asyncio.to_thread(workspace_for(workspace_id).tree, path)

    @app.get("/api/workspaces/{workspace_id}/file")
    async def read_file(workspace_id: str, path: str):
        return workspace_for(workspace_id).read(path)

    @app.put("/api/workspaces/{workspace_id}/file")
    async def save_file(workspace_id: str, values: SaveFile):
        if len(values.content.encode("utf-8")) > MAX_FILE or "\x00" in values.content:
            raise ValueError("仅支持 256 KB 以内的 UTF-8 文本。")
        workspace = workspace_for(workspace_id)
        async with runtime.workspace_locks[workspace_id]:
            file = workspace.read(values.path)
            if file["hash"] != values.base_hash:
                raise Conflict("文件已在外部变化，请重新打开后合并修改。")
            Patches.write(workspace.path(values.path), values.content)
            return workspace.read(values.path)

    @app.get("/api/workspaces/{workspace_id}/search")
    async def search(workspace_id: str, query: str):
        return await asyncio.to_thread(workspace_for(workspace_id).search, query)

    @app.get("/api/sessions")
    async def sessions(workspace_id: str):
        workspace_for(workspace_id)
        return store.rows("SELECT * FROM sessions WHERE workspace_id=? ORDER BY created_at DESC LIMIT 200", (workspace_id,))

    @app.get("/api/sessions/{session_id}/tasks")
    async def session_tasks(session_id: str):
        store.one("sessions", session_id)
        tasks = store.rows("SELECT * FROM tasks WHERE session_id=? ORDER BY created_at", (session_id,))
        return [public_task(task) for task in tasks]

    def public_task(task):
        return {key: json.loads(value) if key == "test_argv" else value for key, value in task.items()
                if key not in {"messages", "skill_instructions"}}

    @app.post("/api/tasks", status_code=202)
    async def create_task(values: NewTask):
        if not values.prompt.strip():
            raise ValueError("请输入任务内容。")
        return public_task(runtime.create(values.model_dump()))

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str):
        task = public_task(store.one("tasks", task_id))
        task["patches"] = [runtime.patches.get(row["id"]) for row in store.rows("SELECT id FROM patches WHERE task_id=? ORDER BY created_at", (task_id,))]
        return task

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        return public_task(await runtime.cancel(task_id))

    @app.post("/api/tasks/{task_id}/resume", status_code=202)
    async def resume_task(task_id: str):
        return public_task(await runtime.resume(task_id))

    @app.delete("/api/tasks/{task_id}")
    async def delete_task(task_id: str):
        return await runtime.delete(task_id)

    @app.get("/api/tasks/{task_id}/events")
    async def events(task_id: str, request: Request, after: int = 0):
        store.one("tasks", task_id)
        try:
            cursor = max(0, after, int(request.headers.get("last-event-id", "0")))
        except ValueError as exc:
            raise ValueError("事件游标必须为整数。") from exc

        async def generate():
            nonlocal cursor
            idle = 0
            while not await request.is_disconnected():
                batch = store.events(task_id, cursor)
                for event in batch:
                    cursor = event["id"]
                    yield f"id: {cursor}\nevent: update\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                current = store.rows("SELECT status FROM tasks WHERE id=?", (task_id,))
                if not current or (not batch and current[0]["status"] in TERMINAL):
                    return
                idle += 1
                if idle % 40 == 0:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.2)

        return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/patches/{patch_id}/review")
    async def review_patch(patch_id: str, values: Review):
        return public_task(await runtime.review(patch_id, values.accept))

    @app.post("/api/patches/{patch_id}/undo")
    async def undo_patch(patch_id: str):
        patch = runtime.patches.get(patch_id)
        async with runtime.operation_locks[patch["task_id"]]:
            task = store.one("tasks", patch["task_id"])
            if task["status"] not in TERMINAL:
                raise Conflict("请先结束或取消任务，再撤销修改。")
            async with runtime.workspace_locks[patch["workspace_id"]]:
                updated = runtime.patches.apply(patch_id, undo=True)
            await runtime.emit(patch["task_id"], "patch.reverted", {"patch_id": patch_id, "message": "补丁已撤销。"})
            return updated

    return app
