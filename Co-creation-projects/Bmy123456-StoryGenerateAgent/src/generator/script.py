import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

from .base import BaseGenerator
# 导入提示词（带fallback）
try:
    from config.prompts import SCRIPT_PROMPT
except ImportError:
    # 使用默认提示词
    SCRIPT_PROMPT = "请创作一个关于{theme}的{style}剧本，类型为{genre}，包含{scene_count}个场景。"


class ScriptGenerator(BaseGenerator):
    """剧本生成器"""

    def generate(self, theme: str, style: str = None, **kwargs) -> str:
        """
        生成剧本

        Args:
            theme: 剧本主题
            style: 剧本风格
            **kwargs: 其他参数，包括：
                - genre: 剧本类型（喜剧/悲剧/科幻等）
                - scene_count: 场景数量

        Returns:
            生成的剧本内容
        """
        # 默认参数
        genre = kwargs.get('genre', '剧情')
        scene_count = kwargs.get('scene_count', 3)

        # 格式化提示词
        prompt = self._format_prompt(
            SCRIPT_PROMPT,
            theme=theme,
            style=style or '现代剧',
            genre=genre,
            scene_count=scene_count
        )

        # 生成内容
        return self.llm_client.generate(prompt, max_tokens=1500)