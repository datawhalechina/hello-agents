"""JSON 解析容错工具：从模型文本中稳健地提取与校验 JSON"""
import json
import re
from typing import Any, Optional


def parse_json_safe(text: str) -> Optional[Any]:
    """从模型文本中提取 JSON，解析失败返回 None

    依次处理以下情况：
    1. 纯 JSON 文本，直接解析；
    2. ```json ... ``` 或 ``` ... ``` 代码块包裹的 JSON；
    3. 前后含多余说明文本时，提取首个 {...} 或 [...] 片段。
    """
    if not text:
        return None

    raw = text.strip()

    # 1. 直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 或 ``` ... ``` 代码块
    fence_pattern = re.compile(
        r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE
    )
    match = fence_pattern.search(raw)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. 提取首个 {...} 或 [...] 片段（去除前后多余文本）
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start != -1 and end != -1 and end > start:
            snippet = raw[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    return None


def validate_required_fields(data: Any, required_fields: list[str]) -> list[str]:
    """校验必填字段，返回缺失字段列表（空列表表示全部齐全）"""
    if not isinstance(data, dict):
        # 非字典结构，视为全部缺失
        return list(required_fields)
    return [f for f in required_fields if f not in data]
