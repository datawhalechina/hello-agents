"""
配置管理 REST API

配置修改仅写入 YAML 文件，不影响已创建的 Agent 实例。
新配置在下次创建 Agent 时生效。
"""
import os
import yaml

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tool.config_handler import (
    Agent_Config, Chroma_Config, Rag_Config, FileManage_Config,
    Session_Config, get_abs_path,
)
from tool.logger_handler import logger

router = APIRouter()

# config 名称 → YAML 文件路径 + 运行时 dict 映射
CONFIG_MAP = {
    "agent":      ("config/AgentConfig.yml",      Agent_Config),
    "chroma":     ("config/ChromaConfig.yml",     Chroma_Config),
    "rag":        ("config/RagConfig.yml",        Rag_Config),
    "filemanage": ("config/FileManageConfig.yml", FileManage_Config),
    "session":    ("config/SessionConfig.yml",    Session_Config),
    "ui":         ("config/UIConfig.yml",         {}),
}


class ConfigUpdateRequest(BaseModel):
    values: dict


@router.get("/config/{name}")
async def api_get_config(name: str):
    """读取指定配置的当前值"""
    if name not in CONFIG_MAP:
        raise HTTPException(status_code=404, detail=f"未知配置 '{name}'。可选: {list(CONFIG_MAP.keys())}")

    yaml_path, runtime_dict = CONFIG_MAP[name]
    abs_path = get_abs_path(yaml_path)

    if os.path.exists(abs_path):
        with open(abs_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = dict(runtime_dict) if runtime_dict else {}

    return {"config": name, "values": data}


@router.put("/config/{name}")
async def api_update_config(name: str, req: ConfigUpdateRequest):
    """更新指定配置（写入 YAML 文件，不影响运行中 Agent）"""
    import yaml as yaml_lib

    if name not in CONFIG_MAP:
        raise HTTPException(status_code=404, detail=f"未知配置 '{name}'")

    yaml_path, runtime_dict = CONFIG_MAP[name]
    abs_path = get_abs_path(yaml_path)

    # 读取现有数据并合并
    if os.path.exists(abs_path):
        with open(abs_path, "r", encoding="utf-8") as f:
            current = yaml_lib.safe_load(f) or {}
    else:
        current = {}

    current.update(req.values)

    # 写回 YAML
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        yaml_lib.dump(current, f, allow_unicode=True, default_flow_style=False)

    # 同步更新运行时 dict（仅非敏感配置）
    if name != "ui":
        runtime_dict.clear()
        runtime_dict.update(current)

    logger.info(f"[config] 已更新配置 '{name}': {list(req.values.keys())}")
    return {"config": name, "updated": list(req.values.keys())}


@router.get("/config")
async def api_list_configs():
    """列出所有可用配置名称"""
    return {"configs": list(CONFIG_MAP.keys())}
