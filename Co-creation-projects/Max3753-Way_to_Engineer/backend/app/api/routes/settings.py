"""LLM配置API"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ...services.llm_service import get_llm_config, reload_llm, reset_llm_config

router = APIRouter(prefix="/settings", tags=["设置"])


class LLMConfigResponse(BaseModel):
    """LLM配置响应"""
    base_url: str
    model_id: str
    api_key: str  # 脱敏后返回


class LLMConfigUpdateRequest(BaseModel):
    """LLM配置更新请求"""
    base_url: str
    model_id: str
    api_key: str


class LLMConfigUpdateResponse(BaseModel):
    """LLM配置更新响应"""
    success: bool
    message: str
    config: LLMConfigResponse


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config_endpoint():
    """获取当前LLM配置"""
    config = get_llm_config()
    return LLMConfigResponse(**config)


@router.post("/llm", response_model=LLMConfigUpdateResponse)
async def update_llm_config_endpoint(request: LLMConfigUpdateRequest):
    """更新LLM配置并重新初始化"""
    try:
        reload_llm({
            "base_url": request.base_url.rstrip("/"),
            "model_id": request.model_id,
            "api_key": request.api_key,
        })
        config = get_llm_config()
        return LLMConfigUpdateResponse(
            success=True,
            message="LLM配置已更新",
            config=LLMConfigResponse(**config),
        )
    except Exception as e:
        return LLMConfigUpdateResponse(
            success=False,
            message=f"配置失败: {str(e)}",
            config=LLMConfigResponse(
                base_url="", model_id="", api_key=""
            ),
        )


@router.post("/llm/reset", response_model=LLMConfigUpdateResponse)
async def reset_llm_config_endpoint():
    """恢复LLM配置到.env默认值"""
    try:
        reset_llm_config()
        config = get_llm_config()
        return LLMConfigUpdateResponse(
            success=True,
            message="已恢复为默认配置",
            config=LLMConfigResponse(**config),
        )
    except Exception as e:
        return LLMConfigUpdateResponse(
            success=False,
            message=f"重置失败: {str(e)}",
            config=LLMConfigResponse(
                base_url="", model_id="", api_key=""
            ),
        )
