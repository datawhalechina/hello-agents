from pydantic import BaseModel, Field
from typing import Optional, List


class GenerationRequest(BaseModel):
    """生成请求模型"""
    generation_type: str = Field(..., description="生成类型：novel/poem/script")
    theme: str = Field(..., description="主题")
    style: Optional[str] = Field(None, description="风格")
    length: Optional[str] = Field(None, description="长度（仅小说）")
    form: Optional[str] = Field(None, description="形式（仅诗歌）")
    genre: Optional[str] = Field(None, description="类型（仅剧本）")
    scene_count: Optional[int] = Field(None, description="场景数量（仅剧本）")


class GenerationResponse(BaseModel):
    """生成响应模型"""
    success: bool = Field(..., description="是否成功")
    content: Optional[str] = Field(None, description="生成的内容")
    error: Optional[str] = Field(None, description="错误信息")
    generation_type: Optional[str] = Field(None, description="生成类型")
    tokens_used: Optional[int] = Field(None, description="使用的token数")


class SummaryRequest(BaseModel):
    """总结请求模型"""
    content: str = Field(..., description="需要总结的内容")


class SummaryResponse(BaseModel):
    """总结响应模型"""
    success: bool = Field(..., description="是否成功")
    summary: Optional[str] = Field(None, description="总结内容")
    error: Optional[str] = Field(None, description="错误信息")


class TranslationRequest(BaseModel):
    """翻译请求模型"""
    content: str = Field(..., description="需要翻译的内容")
    language: str = Field(..., description="目标语言")


class TranslationResponse(BaseModel):
    """翻译响应模型"""
    success: bool = Field(..., description="是否成功")
    translation: Optional[str] = Field(None, description="翻译内容")
    error: Optional[str] = Field(None, description="错误信息")


class ModelInfo(BaseModel):
    """模型信息"""
    model_name: str = Field(..., description="模型名称")
    temperature: float = Field(..., description="温度参数")
    max_tokens: int = Field(..., description="最大token数")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本信息")