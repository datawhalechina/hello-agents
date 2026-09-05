import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

from .base import BaseGenerator
# 导入提示词（带fallback）
try:
    from config.prompts import POEM_PROMPT
except ImportError:
    # 使用默认提示词
    POEM_PROMPT = "请创作一首关于{theme}的{style}，形式为{form}。"


class PoemGenerator(BaseGenerator):
    """诗歌生成器"""

    def generate(self, theme: str, style: str = None, **kwargs) -> str:
        """
        生成诗歌

        Args:
            theme: 诗歌主题
            style: 诗歌风格
            **kwargs: 其他参数，包括：
                - form: 诗歌形式（自由诗/格律诗/十四行诗等）
                - emotion: 情绪基调

        Returns:
            生成的诗歌内容
        """
        # 默认参数
        form = kwargs.get('form', '自由诗')
        emotion = kwargs.get('emotion', '抒情')

        # 格式化提示词
        prompt = self._format_prompt(
            POEM_PROMPT,
            theme=theme,
            style=style or '现代诗',
            form=form,
            emotion=emotion
        )

        # 生成内容
        return self.llm_client.generate(prompt, max_tokens=500)