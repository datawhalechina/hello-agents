"""序列化工具"""

import json
import pickle
from typing import Any, Union
from pathlib import Path

def serialize_object(obj: Any, format: str = "json") -> Union[str, bytes]:
    """
    序列化对象
    
    Args:
        obj: 要序列化的对象
        format: 序列化格式 ("json" 或 "pickle")
        
    Returns:
        序列化后的数据
    """
    if format == "json":
        return json.dumps(obj, ensure_ascii=False, indent=2)
    elif format == "pickle":
        return pickle.dumps(obj)
    else:
        raise ValueError(f"不支持的序列化格式: {format}")

def deserialize_object(data: Union[str, bytes], format: str = "json") -> Any:
    """
    反序列化对象
    
    Args:
        data: 序列化的数据
        format: 序列化格式
        
    Returns:
        反序列化后的对象
    """
    if format == "json":
        return json.loads(data)
    elif format == "pickle":
        return pickle.loads(data)
    else:
        raise ValueError(f"不支持的反序列化格式: {format}")

def save_to_file(obj: Any, filepath: Union[str, Path], format: str = "json") -> None:
    """保存对象到文件"""
    filepath = Path(filepath)
    data = serialize_object(obj, format)
    
    mode = "w" if format == "json" else "wb"
    with open(filepath, mode) as f:
        f.write(data)

def load_from_file(filepath: Union[str, Path], format: str = "json") -> Any:
    """从文件加载对象"""
    filepath = Path(filepath)
    mode = "r" if format == "json" else "rb"
    
    with open(filepath, mode) as f:
        data = f.read()
    
    return deserialize_object(data, format)