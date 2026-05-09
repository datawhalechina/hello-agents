import os
from typing import Dict, Any, Optional
from .models.llm_client import LLMClient
from .generator.base import BaseGenerator
from .generator.novel import NovelGenerator
from .generator.poem import PoemGenerator
from .generator.script import ScriptGenerator
from .utils.validation import validate_input

# 导入提示词
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

try:
    from config.settings import settings
    from config.prompts import (
        NOVEL_PROMPT, POEM_PROMPT, SCRIPT_PROMPT,
        SUMMARY_PROMPT, TRANSLATION_PROMPT
    )
except ImportError:
    # 如果导入失败，使用环境变量和默认提示词
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    class Settings:
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        base_url = os.getenv('BASE_URL', None)
        model_name = os.getenv('MODEL_NAME', 'qwen3-max')
        temperature = float(os.getenv('TEMPERATURE', 0.7))
        max_tokens = int(os.getenv('MAX_TOKENS', 1000))

    settings = Settings()

    # 默认提示词
    NOVEL_PROMPT = """请创作一个关于{theme}的故事，风格为{style}，长度为{length}。"""
    POEM_PROMPT = """请创作一首关于{theme}的{style}，形式为{form}。"""
    SCRIPT_PROMPT = """请创作一个关于{theme}的{style}剧本，类型为{genre}，包含{scene_count}个场景。"""
    SUMMARY_PROMPT = """请总结以下内容：{content}"""
    TRANSLATION_PROMPT = """请将以下内容翻译成{language}：{content}"""


class StoryGeneratorAgent:
    def __init__(self, api_key: str = None, model_name: str = None):
        # 如果没有提供API密钥，尝试从环境获取
        if api_key is None:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('OPENAI_API_KEY', '')

        # 如果没有提供模型名称，尝试从环境获取
        if model_name is None:
            model_name = os.getenv('MODEL_NAME', 'qwen3-max')

        self.llm_client = LLMClient(api_key, model_name)
        self.generators = {
            'novel': NovelGenerator(self.llm_client),
            'poem': PoemGenerator(self.llm_client),
            'script': ScriptGenerator(self.llm_client)
        }

    def generate(self,
                generation_type: str,
                theme: str,
                style: Optional[str] = None,
                length:Optional[str] = None,
                **kwargs) -> str:
        """
        根据指定类型生成故事内容

        Args:
            generation_type: 生成类型 (novel/poem/script)
            theme: 主题
            style: 风格
            length:长度
            **kwargs: 其他参数

        Returns:
            生成的文本内容
        """
        # 验证输入
        validate_input(generation_type, theme)

        # 获取对应的生成器
        generator = self.generators.get(generation_type)
        if not generator:
            raise ValueError(f"不支持的生成类型: {generation_type}")

        # 生成内容
        return generator.generate(theme, style, **kwargs)

    def generate_novel(self, theme: str, style: Optional[str] = None,length:Optional[str] = None, **kwargs) -> str:
        """生成小说"""
        return self.generate('novel', theme, style, length, **kwargs)

    def generate_poem(self, theme: str, style: Optional[str] = None, length:Optional[str] = None,**kwargs) -> str:
        """生成诗歌"""
        return self.generate('poem', theme, style, **kwargs)

    def generate_script(self, theme: str, style: Optional[str] = None, length:Optional[str] = None,**kwargs) -> str:
        """生成剧本"""
        return self.generate('script', theme, style, **kwargs)

    def summarize(self, content: str, **kwargs) -> str:
        """总结内容"""
        prompt = SUMMARY_PROMPT.format(content=content)
        return self.llm_client.generate(prompt, **kwargs)

    def translate(self, content: str, language: str, **kwargs) -> str:
        """翻译内容"""
        prompt = TRANSLATION_PROMPT.format(content=content, language=language)
        return self.llm_client.generate(prompt, **kwargs)