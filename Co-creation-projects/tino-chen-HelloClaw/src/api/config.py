"""配置 API 路由"""
import json
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ..workspace.manager import WorkspaceManager, get_default_global_config

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    content: str


class AgentInfo(BaseModel):
    """助手信息"""
    name: str


# 全局 workspace 实例（由 main.py 在启动时设置）
_workspace: Optional[WorkspaceManager] = None


def set_workspace(ws: WorkspaceManager):
    """设置全局 workspace 实例"""
    global _workspace
    _workspace = ws


def get_workspace() -> WorkspaceManager:
    """获取 workspace 实例"""
    if _workspace is None:
        ws = WorkspaceManager(os.getenv("WORKSPACE_PATH", "~/.helloclaw/workspace"))
        ws.ensure_workspace_exists()
        set_workspace(ws)
    return _workspace


def get_config_json_path() -> str:
    """获取全局 config.json 路径"""
    return os.path.expanduser("~/.helloclaw/config.json")


def ensure_config_json_exists():
    """确保 config.json 存在"""
    config_path = get_config_json_path()
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(get_default_global_config(), f, indent=2, ensure_ascii=False)


@router.get("/list")
async def list_configs(ws: WorkspaceManager = Depends(get_workspace)):
    """获取配置文件列表"""
    configs = ws.list_configs()

    # 添加 config.json 到列表开头
    configs.insert(0, "CONFIG")
    return {"configs": configs}


@router.get("/{name}")
async def get_config(name: str, ws: WorkspaceManager = Depends(get_workspace)):
    """获取指定配置文件内容"""
    # 特殊处理 CONFIG (config.json)
    if name == "CONFIG":
        ensure_config_json_exists()
        config_path = get_config_json_path()
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"name": name, "content": content}

    # 处理 .md 配置文件
    content = ws.load_config(name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"配置文件 {name} 不存在")
    return {"name": name, "content": content}


@router.put("/{name}")
async def update_config(name: str, request: ConfigUpdateRequest, ws: WorkspaceManager = Depends(get_workspace)):
    """更新配置文件"""
    # 特殊处理 CONFIG (config.json)
    if name == "CONFIG":
        ensure_config_json_exists()
        # 严格校验 JSON 格式
        try:
            config_data = json.loads(request.content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"无效的 JSON 格式: {str(e)}")

        # 校验必需字段
        if not isinstance(config_data, dict):
            raise HTTPException(status_code=400, detail="配置必须是 JSON 对象")

        if "llm" not in config_data:
            raise HTTPException(status_code=400, detail="缺少必需字段: llm")

        llm_config = config_data.get("llm", {})
        required_fields = ["model_id", "api_key", "base_url"]
        missing_fields = [f for f in required_fields if f not in llm_config]
        if missing_fields:
            raise HTTPException(status_code=400, detail=f"llm 配置缺少必需字段: {', '.join(missing_fields)}")

        config_path = get_config_json_path()
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        return {"name": name, "status": "updated"}

    # 处理 .md 配置文件
    if name not in ws.list_configs():
        raise HTTPException(status_code=404, detail=f"配置文件 {name} 不存在")

    ws.save_config(name, request.content)
    return {"name": name, "status": "updated"}


def get_agent():
    """获取全局 Agent 实例"""
    from ..main import get_agent as _get_agent
    return _get_agent()


@router.post("/reset")
async def reset_workspace(
    reset_sessions: bool = False,
    reset_memory: bool = False,
    reset_global_config: bool = False,
    ws: WorkspaceManager = Depends(get_workspace)
):
    """重置工作空间到初始模板

    Args:
        reset_sessions: 是否清除会话
        reset_memory: 是否清除每日记忆
        reset_global_config: 是否重置全局配置

    警告：这将覆盖所有配置文件！
    """
    try:
        ws.reset_to_templates(
            reset_sessions=reset_sessions,
            reset_memory=reset_memory,
            reset_global_config=reset_global_config
        )

        # 如果清除了会话，也要清除 Agent 内存中的历史记录
        if reset_sessions:
            agent = get_agent()
            if agent:
                agent.clear_all_history()

        messages = ["配置文件已重置"]
        if reset_sessions:
            messages.append("会话已清除")
        if reset_memory:
            messages.append("每日记忆已清除")
        if reset_global_config:
            messages.append("全局配置已重置")

        return {"status": "success", "message": "，".join(messages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.get("/agent/info", response_model=AgentInfo)
async def get_agent_info(ws: WorkspaceManager = Depends(get_workspace)):
    """获取助手信息（包括名字）

    每次都重新读取 IDENTITY.md 以获取最新的名字
    """
    # 从 IDENTITY.md 读取最新的名字
    identity = ws.load_config("IDENTITY")
    name = "HelloClaw"  # 默认名字

    if identity:
        import re
        # 匹配格式: - **名称：** xxx 或 - **名称:** xxx
        match = re.search(r'\*\*名称[：:]\*\*\s*(.+?)(?:\n|$)', identity)
        if match:
            name = match.group(1).strip()
            # 检查是否是占位符
            if name.startswith('_') or '选一个' in name or '（' in name:
                name = "HelloClaw"

    return AgentInfo(name=name)
