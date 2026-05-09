import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

from .base import BaseGenerator
# 导入提示词（带fallback）
try:
    from config.prompts import NOVEL_PROMPT
except ImportError:
    # 使用默认提示词
    NOVEL_PROMPT = "请创作一个关于{theme}的故事，风格为{style}，长度为{length}。"


class NovelGenerator(BaseGenerator):
    """小说生成器"""

    def generate(self, theme: str, style: str = None, **kwargs) -> str:
        """
        生成小说

        Args:
            theme: 小说主题
            style: 写作风格
            **kwargs: 其他参数，包括：
                - length: 长度（短篇/中篇/长篇）
                - target_audience: 目标读者

        Returns:
            生成的小说内容
        """
        # 默认参数
        length = kwargs.get('length', '中篇')
        target_audience = kwargs.get('target_audience', '普通读者')

        # 格式化提示词
        prompt = self._format_prompt(
            NOVEL_PROMPT,
            theme=theme,
            style=style or '现实主义',
            length=length,
            target_audience=target_audience
        )

        # 生成内容
        return self.llm_client.generate(prompt, max_tokens=2000)