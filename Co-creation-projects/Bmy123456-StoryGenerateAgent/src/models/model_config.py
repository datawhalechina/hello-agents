from typing import Dict, Any
from ..config.settings import settings


class ModelConfig:
    """模型配置管理"""

    @staticmethod
    def get_model_config(model_name: str = None) -> Dict[str, Any]:
        """
        获取模型配置

        Args:
            model_name: 模型名称

        Returns:
            模型配置字典
        """
        model_name = model_name or settings.model_name
        return {
            "model": model_name,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens
        }

    @staticmethod
    def update_model_config(model_name: str, **kwargs) -> None:
        """
        更新模型配置

        Args:
            model_name: 模型名称
            **kwargs: 配置参数
        """
        # 这里可以添加配置更新逻辑
        pass

    @staticmethod
    def get_available_models() -> list:
        """
        获取可用模型列表

        Returns:
            可用模型列表
        """
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "text-davinci-003"
        ]