"""LLM服务"""

import json
import os
from pathlib import Path
from hello_agents import HelloAgentsLLM
from ..config import get_settings


_llm_instance = None
_llm_config_override = None
LLM_CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "llm_config.json"


def _load_llm_config():
    """从文件加载运行时LLM配置（优先于.env）"""
    global _llm_config_override
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
                _llm_config_override = json.load(f)
            print(f"[LLM] 加载运行时配置: {_llm_config_override.get('base_url', '')}")
        except Exception as e:
            print(f"[LLM] 加载运行时配置失败: {e}")
            _llm_config_override = None
    else:
        _llm_config_override = None


def _build_llm():
    """根据配置创建LLM实例（运行时配置优先，回退到.env）"""
    settings = get_settings()
    
    # 优先使用运行时配置，空字符串回退到.env
    if _llm_config_override:
        model = _llm_config_override.get("model_id") or settings.deepseek_model_id
        api_key = _llm_config_override.get("api_key") or settings.deepseek_api_key
        base_url = _llm_config_override.get("base_url") or settings.deepseek_base_url
    else:
        model = settings.deepseek_model_id
        api_key = settings.deepseek_api_key
        base_url = settings.deepseek_base_url
    
    return HelloAgentsLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )


def get_llm() -> HelloAgentsLLM:
    """获取LLM实例"""
    global _llm_instance
    if _llm_instance is None:
        _load_llm_config()
        _llm_instance = _build_llm()
        print(f"LLM服务初始化成功: {_llm_instance.model}")
    return _llm_instance


def reload_llm(config: dict = None) -> HelloAgentsLLM:
    """重新配置并刷新LLM实例"""
    global _llm_instance, _llm_config_override
    
    if config:
        # 清洗空值：去掉空字符串的字段，保留有效值
        clean = {}
        for key in ("base_url", "model_id", "api_key"):
            val = (config.get(key) or "").strip()
            if val:
                clean[key] = val
        # 保存运行时配置
        LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LLM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        _load_llm_config()
    
    # 重置实例
    _llm_instance = None
    new_llm = get_llm()
    print(f"LLM服务已重新配置: {new_llm.model}")
    return new_llm


def reset_llm_config() -> HelloAgentsLLM:
    """清除运行时配置，回退到.env默认值"""
    global _llm_instance, _llm_config_override
    
    _llm_config_override = None
    if LLM_CONFIG_FILE.exists():
        LLM_CONFIG_FILE.unlink()
        print("[LLM] 已清除运行时配置文件，回退到.env默认值")
    
    _llm_instance = None
    return get_llm()


def get_llm_config() -> dict:
    """获取当前LLM配置（API密钥脱敏）"""
    settings = get_settings()
    
    if _llm_config_override:
        config = _llm_config_override.copy()
    else:
        config = {
            "base_url": settings.deepseek_base_url,
            "model_id": settings.deepseek_model_id,
            "api_key": settings.deepseek_api_key,
        }
    
    # API密钥脱敏
    if config.get("api_key"):
        key = config["api_key"]
        config["api_key"] = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
    
    return config
