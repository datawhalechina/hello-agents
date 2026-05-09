from fastapi import APIRouter, HTTPException, status
from ..agent import StoryGeneratorAgent
from .schemas import (
    GenerationRequest, GenerationResponse,
    SummaryRequest, SummaryResponse,
    TranslationRequest, TranslationResponse,
    HealthCheckResponse, ModelInfo
)
from ..utils.validation import validate_input
from ..config.settings import settings


router = APIRouter()
agent = StoryGeneratorAgent()


@router.post("/generate", response_model=GenerationResponse)
async def generate_content(request: GenerationRequest):
    """
    生成内容

    Args:
        request: 生成请求

    Returns:
        生成响应
    """
    try:
        # 验证输入
        validate_input(
            request.generation_type,
            request.theme,
            length=request.length,
            form=request.form,
            genre=request.genre,
            scene_count=request.scene_count
        )

        # 生成内容
        content = agent.generate(
            request.generation_type,
            request.theme,
            request.style,
            length=request.length,
            form=request.form,
            genre=request.genre,
            scene_count=request.scene_count
        )

        return GenerationResponse(
            success=True,
            content=content,
            generation_type=request.generation_type
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/summarize", response_model=SummaryResponse)
async def summarize_content(request: SummaryRequest):
    """
    总结内容

    Args:
        request: 总结请求

    Returns:
        总结响应
    """
    try:
        summary = agent.summarize(request.content)
        return SummaryResponse(success=True, summary=summary)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/translate", response_model=TranslationResponse)
async def translate_content(request: TranslationRequest):
    """
    翻译内容

    Args:
        request: 翻译请求

    Returns:
        翻译响应
    """
    try:
        translation = agent.translate(request.content, request.language)
        return TranslationResponse(success=True, translation=translation)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    健康检查

    Returns:
        健康检查响应
    """
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0"
    )


@router.get("/model/info", response_model=ModelInfo)
async def get_model_info():
    """
    获取模型信息

    Returns:
        模型信息
    """
    return ModelInfo(
        model_name=settings.model_name,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens
    )