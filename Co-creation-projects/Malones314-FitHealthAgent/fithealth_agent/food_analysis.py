"""Vision-model based estimates for a photographed meal; images are never persisted."""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import requests


MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

PROMPT = """分析这张餐盘照片。你不是医疗或营养诊断工具；仅根据画面估算。
识别每种可见食物，估计份量、热量、蛋白质、碳水和脂肪。无法确认的调料、油脂、遮挡食物必须说明假设。
只返回 JSON：
{"items":[{"name":"食物","portion":"估计份量","calories_kcal":123,"protein_g":12.3,"carbs_g":20.4,"fat_g":5.6}],"total_kcal":123,"range_low_kcal":100,"range_high_kcal":150,"confidence":"low|medium|high","assumptions":["假设"],"disclaimer":"估算仅供记录参考"}
热量为非负整数，蛋白质、碳水、脂肪为非负数字，items 最多 12 项。"""


class FoodAnalysisError(ValueError):
    pass


def _extract_json(content: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise FoodAnalysisError("视觉模型未返回可用的餐食结果")
    cleaned = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise FoodAnalysisError("视觉模型返回的餐食结果格式无效") from exc
    if not isinstance(result, dict):
        raise FoodAnalysisError("视觉模型返回的餐食结果格式无效")
    _validate_result_schema(result)
    return result


def _validate_result_schema(result: dict[str, Any]) -> None:
    required = {
        "items", "total_kcal", "range_low_kcal", "range_high_kcal", "confidence",
        "assumptions", "disclaimer",
    }
    if not required.issubset(result):
        raise FoodAnalysisError("视觉模型返回的餐食结果字段不完整")
    if not isinstance(result["items"], list) or len(result["items"]) > 12:
        raise FoodAnalysisError("视觉模型返回的餐食项目格式无效")
    for item in result["items"]:
        if not isinstance(item, dict):
            raise FoodAnalysisError("视觉模型返回的餐食项目格式无效")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise FoodAnalysisError("视觉模型返回的餐食项目格式无效")
        if not isinstance(item.get("portion"), str):
            raise FoodAnalysisError("视觉模型返回的餐食项目格式无效")
        for field in ("calories_kcal", "protein_g", "carbs_g", "fat_g"):
            if not isinstance(item.get(field), (int, float)) or isinstance(item[field], bool):
                raise FoodAnalysisError("视觉模型返回的餐食项目格式无效")
    for field in ("total_kcal", "range_low_kcal", "range_high_kcal"):
        if not isinstance(result[field], (int, float)) or isinstance(result[field], bool):
            raise FoodAnalysisError("视觉模型返回的热量字段格式无效")
    if result["confidence"] not in {"low", "medium", "high"}:
        raise FoodAnalysisError("视觉模型返回的置信度格式无效")
    if not isinstance(result["assumptions"], list) or not all(
        isinstance(item, str) for item in result["assumptions"]
    ):
        raise FoodAnalysisError("视觉模型返回的假设字段格式无效")
    if not isinstance(result["disclaimer"], str):
        raise FoodAnalysisError("视觉模型返回的免责声明格式无效")


def _kcal(value: Any) -> int:
    try:
        return max(0, min(20_000, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _grams(value: Any) -> float:
    try:
        return round(max(0, min(1_000, float(value))), 1)
    except (TypeError, ValueError):
        return 0.0


def _normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return the stable, editable nutrition contract used by the check-in form."""
    items = result.get("items") if isinstance(result.get("items"), list) else []
    normalized = []
    for item in items[:12]:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        normalized.append({
            "name": str(item["name"]).strip()[:80],
            "portion": str(item.get("portion") or "份量不确定").strip()[:80],
            "calories_kcal": _kcal(item.get("calories_kcal")),
            "protein_g": _grams(item.get("protein_g")),
            "carbs_g": _grams(item.get("carbs_g")),
            "fat_g": _grams(item.get("fat_g")),
        })
    model_total = _kcal(result.get("total_kcal"))
    total = sum(item["calories_kcal"] for item in normalized)
    low, high = _kcal(result.get("range_low_kcal")), _kcal(result.get("range_high_kcal"))
    if not low or not high or not (low <= total <= high):
        low, high = round(total * 0.8), round(total * 1.2)
    low, high = min(low, high), max(low, high)
    confidence = str(result.get("confidence") or "low").lower()
    return {
        "items": normalized,
        "total_kcal": total,
        "model_total_kcal": model_total,
        "protein_g": round(sum(item["protein_g"] for item in normalized), 1),
        "carbs_g": round(sum(item["carbs_g"] for item in normalized), 1),
        "fat_g": round(sum(item["fat_g"] for item in normalized), 1),
        "range_low_kcal": low,
        "range_high_kcal": high,
        "confidence": confidence if confidence in {"low", "medium", "high"} else "low",
        "assumptions": [str(item)[:160] for item in result.get("assumptions", [])[:6]],
        "disclaimer": "照片营养为估算值；油、酱料、份量和烹饪方式会显著影响结果。",
    }


def analyze_food_image(content: bytes, media_type: str, context: str = "") -> dict[str, Any]:
    if media_type not in ALLOWED_IMAGE_TYPES:
        raise FoodAnalysisError("仅支持 JPG、PNG 或 WebP 餐盘照片")
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise FoodAnalysisError("餐盘照片不能为空且不能超过 10 MiB")
    api_key = os.getenv("VISION_API_KEY") or os.getenv("LLM_API_KEY")
    model = os.getenv("VISION_MODEL_ID")
    if not api_key or not model:
        raise FoodAnalysisError("未配置视觉模型。请在 .env 设置 VISION_API_KEY 和 VISION_MODEL_ID")
    base_url = (os.getenv("VISION_BASE_URL") or os.getenv("LLM_BASE_URL") or "").rstrip("/")
    if not base_url:
        raise FoodAnalysisError("未配置视觉模型地址 VISION_BASE_URL")
    context = context.strip()[:500]
    prompt = PROMPT + (f"\n用户补充说明（仅作估算参考）：{context}" if context else "")
    image_url = f"data:{media_type};base64,{base64.b64encode(content).decode('ascii')}"
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]}],
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, TypeError) as exc:
        raise FoodAnalysisError("餐盘图片分析失败，请稍后重试或检查视觉模型配置") from exc
    result = _extract_json(raw)
    return _normalize_result(result)
