from typing import Dict, Any
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

# 尝试导入配置
try:
    from config.settings import settings
except ImportError:
    # 如果导入失败，使用默认设置
    class Settings:
        temperature = 0.7
        max_tokens = 1000
    settings = Settings()

def get_available_models() -> list:
    """获取可用模型列表"""
    return ["glm-4.5-air", "gpt-4", "gpt-3.5-turbo"]

def validate_input(generation_type: str, theme: str, **kwargs) -> None:
    """
    验证输入参数

    Args:
        generation_type: 生成类型
        theme: 主题
        **kwargs: 其他参数

    Raises:
        ValueError: 如果输入参数无效
    """
    # 验证生成类型
    valid_types = ['novel', 'poem', 'script']
    if generation_type not in valid_types:
        raise ValueError(f"不支持的生成类型: {generation_type}. 可用类型: {valid_types}")

    # 验证主题
    if not theme or not theme.strip():
        raise ValueError("主题不能为空")

    # 根据生成类型验证特定参数
    if generation_type == 'novel':
        length = kwargs.get('length', '中篇')
        if length not in ['短篇', '中篇', '长篇']:
            raise ValueError("小说长度必须是：短篇、中篇 或 长篇")

    elif generation_type == 'poem':
        form = kwargs.get('form', '自由诗')
        if form not in ['自由诗', '格律诗', '十四行诗', '俳句']:
            raise ValueError("诗歌形式无效")

    elif generation_type == 'script':
        genre = kwargs.get('genre', '剧情')
        if genre not in ['喜剧', '悲剧', '科幻', '悬疑', '剧情']:
            raise ValueError("剧本类型无效")


def validate_api_key(api_key: str) -> bool:
    """验证API密钥格式"""
    return bool(api_key and len(api_key) > 10)


def validate_model_name(model_name: str) -> bool:
    """验证模型名称"""
    valid_models = get_available_models()
    return model_name in valid_models


def validate_generation_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证生成参数

    Args:
        params: 生成参数

    Returns:
        验证后的参数
    """
    # 设置默认值
    params.setdefault('temperature', settings.temperature)
    params.setdefault('max_tokens', settings.max_tokens)

    # 验证参数范围
    if not (0 <= params['temperature'] <= 2):
        raise ValueError("温度参数必须在0-2之间")

    if params['max_tokens'] <= 0:
        raise ValueError("最大token数必须大于0")

    return params


class InputValidator:
    """输入验证器"""

    @staticmethod
    def validate_theme(theme: str) -> str:
        """验证主题"""
        if not theme or not theme.strip():
            raise ValueError("主题不能为空")
        return theme.strip()

    @staticmethod
    def validate_style(style: str) -> str:
        """验证风格"""
        if style and style.strip():
            return style.strip()
        return "默认风格"

    @staticmethod
    def validate_length(length: str) -> str:
        """验证长度"""
        valid_lengths = ['短篇', '中篇', '长篇']
        if length in valid_lengths:
            return length
        return "中篇"

    @staticmethod
    def validate_form(form: str) -> str:
        """验证形式"""
        valid_forms = ['自由诗', '格律诗', '十四行诗', '俳句']
        if form in valid_forms:
            return form
        return "自由诗"

    @staticmethod
    def validate_genre(genre: str) -> str:
        """验证类型"""
        valid_genres = ['喜剧', '悲剧', '科幻', '悬疑', '剧情']
        if genre in valid_genres:
            return genre
        return "剧情"