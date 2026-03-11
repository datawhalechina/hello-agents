"""辅助工具函数"""

import importlib
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

def format_time(timestamp: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间
    
    Args:
        timestamp: 时间戳，默认为当前时间
        format_str: 格式字符串
        
    Returns:
        格式化后的时间字符串
    """
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime(format_str)

def validate_config(config: Dict[str, Any], required_keys: list) -> bool:
    """
    验证配置是否包含必需的键
    
    Args:
        config: 配置字典
        required_keys: 必需的键列表
        
    Returns:
        是否验证通过
    """
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(f"配置缺少必需的键: {missing_keys}")
    return True

def safe_import(module_name: str, class_name: Optional[str] = None) -> Any:
    """
    安全导入模块或类
    
    Args:
        module_name: 模块名
        class_name: 类名（可选）
        
    Returns:
        导入的模块或类
    """
    try:
        module = importlib.import_module(module_name)
        if class_name:
            return getattr(module, class_name)
        return module
    except (ImportError, AttributeError) as e:
        raise ImportError(f"无法导入 {module_name}.{class_name or ''}: {e}")

def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """深度合并两个字典"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result