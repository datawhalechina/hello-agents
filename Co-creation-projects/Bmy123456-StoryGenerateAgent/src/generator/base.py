from abc import ABC, abstractmethod
from typing import Dict, Any
from ..models.llm_client import LLMClient


class BaseGenerator(ABC):
    """生成器基类"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    @abstractmethod
    def generate(self, theme: str, style: str = None, **kwargs) -> str:
        """
        生成内容

        Args:
            theme: 主题
            style: 风格
            **kwargs: 其他参数

        Returns:
            生成的文本内容
        """
        pass

    def _format_prompt(self, prompt_template: str, **kwargs) -> str:
        """格式化提示词"""
        return prompt_template.format(**kwargs)

    def _validate_input(self, theme: str, style: str = None) -> None:
        """验证输入参数"""
        if not theme or not theme.strip():
            raise ValueError("主题不能为空")
        if style and not style.strip():
            raise ValueError("风格不能为空")