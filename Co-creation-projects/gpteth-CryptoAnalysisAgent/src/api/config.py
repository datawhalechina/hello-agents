"""Identity and workspace config API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .deps import get_agent, get_workspace
from ..workspace.manager import CONFIG_FILES

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    content: str


@router.get("/list")
def list_configs():
    return {"configs": get_workspace().list_configs()}


@router.get("/agent/info")
def agent_info():
    return {"name": get_workspace().read_identity_name()}


@router.post("/reset")
def reset_workspace(reset_sessions: bool = False, reset_memory: bool = False):
    workspace = get_workspace()
    workspace.reset_to_templates(reset_sessions=reset_sessions, reset_memory=reset_memory)
    try:
        get_agent().reload_identity()
    except Exception:
        pass
    parts = ["配置文件已重置"]
    if reset_sessions:
        parts.append("会话已清除")
    if reset_memory:
        parts.append("每日记忆已清除")
    return {"status": "success", "message": "，".join(parts)}


@router.get("/{name}")
def get_config(name: str):
    content = get_workspace().load_config(name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"配置文件 {name} 不存在")
    return {"name": name, "content": content}


@router.put("/{name}")
def update_config(name: str, request: ConfigUpdateRequest):
    if name not in CONFIG_FILES:
        raise HTTPException(status_code=400, detail="不支持的配置文件")
    get_workspace().save_config(name, request.content)
    if name == "IDENTITY":
        try:
            get_agent().reload_identity()
        except Exception:
            pass
    return {"name": name, "status": "updated"}
