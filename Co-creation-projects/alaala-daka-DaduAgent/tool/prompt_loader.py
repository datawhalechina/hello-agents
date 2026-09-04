from tool.logger_handler import logger
from tool.config_handler import Prompt_Config
from tool.path_tool import get_abs_path

def _resolve_prompt_path(config_key: str) -> str:
    """将 PromptConfig 中的路径解析为绝对路径（兼容相对路径和绝对路径）"""
    raw_path = Prompt_Config[config_key]
    if not raw_path:
        raise FileNotFoundError(f"PromptConfig 中缺少键 '{config_key}'")
    resolved = get_abs_path(raw_path)
    return resolved

def system_prompt_load():
    try:
        path = _resolve_prompt_path("system_prompt_path")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"[system_prompt_load()]出现{str(e)}")
        raise e

def rag_prompt_load():
    try:
        path = _resolve_prompt_path("rag_prompt_path")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"[rag_prompt_load()]出现{str(e)}")
        raise e

def report_prompt_load():
    try:
        path = _resolve_prompt_path("report_prompt_path")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"[report_prompt_load()]出现{str(e)}")
        raise e
