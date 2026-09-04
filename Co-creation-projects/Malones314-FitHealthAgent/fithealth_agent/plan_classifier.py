"""plan_classifier.py

用于鉴定上传的 Markdown 文件是否为训练计划。
采用双层过滤架构：
1. Level 1 - 关键字快筛（正则表达式 / 词频）
2. Level 2 - LLM (Lite) 语义鉴定
"""

import os
import json
import re
from typing import Any

LLM_LITE_API_KEY: str | None = os.getenv("LLM_LITE_API_KEY") or os.getenv("LLM_API_KEY")
LLM_LITE_BASE_URL: str = (os.getenv("LLM_LITE_BASE_URL") or "https://api.deepseek.com").rstrip("/")
LLM_LITE_MODE: str = os.getenv("LLM_LITE_MODE_ID", "deepseek-chat")

# 关键词仅用于快速排除明显无关的文件；不得据此直接接收文件。
TRAINING_KEYWORDS = [
    "组间歇", "重量", "卧推", "硬拉", "深蹲", "划船", "哑铃", "杠铃", "RM", "组数",
    "力竭", "热身", "拉伸", "核心肌群", "训练", "计划", "运动", "健身", "锻炼", "动作",
    "次", "分钟",
]

def _level1_keyword_check(text: str) -> tuple[bool, str] | None:
    """仅拒绝不含任何训练内容的文件，其余全部交给语义鉴定。"""
    if not any(keyword.lower() in text.lower() for keyword in TRAINING_KEYWORDS):
        return False, "完全不包含任何运动、健身相关的常见词汇"
    return None

def _extract_json(text: str) -> dict[str, Any] | None:
    md_match = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r"\{[\s\S]+?\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return None

def _level2_llm_check(text: str) -> tuple[bool, str]:
    if not LLM_LITE_API_KEY:
        return False, "未配置 LLM API KEY 且无法通过规则验证"
        
    system_prompt = (
        "判断以下 Markdown 文本是否为一份可执行的健身/运动训练计划。\n"
        "仅仅提及动作名、重量、训练感受、健身知识、训练日志、复盘或文章，不是训练计划。\n"
        "只有包含面向未来执行的明确训练安排（例如动作、次数/时长/强度、顺序或频率）时才是训练计划。\n"
        "返回严格 JSON 格式：\n"
        "{\n"
        '  "is_plan": true 或 false,\n'
        '  "reason": "一句话说明理由"\n'
        "}"
    )
    
    try:
        import requests
        url = f"{LLM_LITE_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {LLM_LITE_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": LLM_LITE_MODE,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:2000]} # 截断防止超长
            ],
            "max_tokens": 200,
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        raw_text = resp.json()["choices"][0]["message"]["content"]
        parsed = _extract_json(raw_text)
        if parsed is None:
            return False, "LLM 返回无法解析"
        return bool(parsed.get("is_plan", False)), str(parsed.get("reason", ""))
    except Exception as exc:
        return False, f"LLM 调用异常: {exc}"

def validate_training_plan(
    text: str, *, allow_external_models: bool = True
) -> dict[str, Any]:
    """主入口
    返回: {"is_plan": bool, "reason": str, "stage": str}
    """
    res1 = _level1_keyword_check(text)
    if res1 is not None:
        return {"is_plan": res1[0], "reason": res1[1], "stage": "level1_keywords"}
    if not allow_external_models:
        return {
            "is_plan": False,
            "reason": "已关闭外部模型，无法对模糊的计划内容进行语义鉴定",
            "stage": "external_models_disabled",
        }

    res2 = _level2_llm_check(text)
    return {"is_plan": res2[0], "reason": res2[1], "stage": "level2_llm"}
