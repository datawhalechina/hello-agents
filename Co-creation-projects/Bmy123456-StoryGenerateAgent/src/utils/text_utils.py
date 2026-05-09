from typing import List, Dict, Any
import re
from ..config.settings import settings


class TextUtils:
    """文本处理工具类"""

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本，去除多余空白和特殊字符"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    @staticmethod
    def split_text(text: str, max_length: int = 4000) -> List[str]:
        """将长文本分割成多个片段"""
        return [text[i:i + max_length] for i in range(0, len(text), max_length)]

    @staticmethod
    def extract_keywords(text: str, num_keywords: int = 5) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取实现
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = {}
        for word in words:
            if len(word) > 3:  # 忽略短词
                word_freq[word] = word_freq.get(word, 0) + 1

        # 按频率排序并返回前N个关键词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:num_keywords]]

    @staticmethod
    def count_tokens(text: str) -> int:
        """估算文本的token数量"""
        # 简单的token估算（实际应用中应使用更准确的估算方法）
        words = text.split()
        return len(words) * 1.3  # 平均每个单词约1.3个token

    @staticmethod
    def format_output(text: str, output_format: str = "text") -> str:
        """格式化输出"""
        if output_format == "markdown":
            return f"```\n{text}\n```"
        return text

    @staticmethod
    def validate_content(content: str, min_length: int = 10) -> bool:
        """验证生成的内容是否有效"""
        return len(content.strip()) >= min_length


class PromptFormatter:
    """提示词格式化工具"""

    @staticmethod
    def format_novel_prompt(theme: str, style: str = "现实主义", length: str = "中篇") -> str:
        """格式化小说提示词"""
        return f"请以{style}风格创作一部{length}小说，主题为：{theme}"

    @staticmethod
    def format_poem_prompt(theme: str, style: str = "现代诗", form: str = "自由诗") -> str:
        """格式化诗歌提示词"""
        return f"请以{style}风格创作一首{form}，主题为：{theme}"

    @staticmethod
    def format_script_prompt(theme: str, style: str = "现代剧", genre: str = "剧情") -> str:
        """格式化剧本提示词"""
        return f"请以{style}风格创作一个{genre}剧本，主题为：{theme}"