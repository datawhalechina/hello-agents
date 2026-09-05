"""Reflexion 自校验机制：关键步骤后自检质量，低于阈值触发针对性补抽/重试

核心职责：
- self_check：让模型对照上下文检查结果质量，输出置信度与问题
- reflect_and_retry：自校验 + 针对性重试（非整篇重跑），最多重试 2 次
- 记录所有自校验置信度，提供统计接口
"""
from __future__ import annotations

import json
import logging
from typing import Callable

from backend.config import settings
from backend.llm.client import DeepSeekClient
from backend.llm.json_utils import parse_json_safe

logger = logging.getLogger(__name__)

# 最多重试次数
MAX_RETRIES = 2


class Reflexion:
    """Reflexion 自校验机制

    在关键步骤（抽取/Gap/创新）后启用：
    1. 对照上下文自检结果质量，输出置信度；
    2. 置信度低于阈值时触发针对性补抽/重试（retry_func），非整篇重跑；
    3. 最多重试 MAX_RETRIES 次，仍不达标则标记 needs_human_review。
    """

    def __init__(self, client: DeepSeekClient) -> None:
        self.client = client
        # 记录所有自校验的置信度
        self.confidences: list[float] = []

    async def self_check(
        self,
        step_name: str,
        result: dict,
        context: str = "",
    ) -> dict:
        """让模型对照上下文检查结果质量

        Args:
            step_name: 步骤名称（如 Extractor / GapAnalyzer / InnovationGenerator）
            result: 步骤执行结果 dict
            context: 校验上下文（依赖步骤的结果或原文摘要）

        Returns:
            {
                "confidence": float,        # 0-1 置信度
                "issues": list[str],        # 发现的问题
                "needs_retry": bool,        # 是否需要重试
                "retry_fields": list[str],  # 需重试的字段或方面
            }
        """
        # 序列化结果，截断避免超长
        if isinstance(result, dict):
            result_str = json.dumps(result, ensure_ascii=False, default=str)[:6000]
        else:
            result_str = str(result)[:6000]

        context_str = context[:4000] if context else "（无额外上下文）"

        prompt = (
            f"请对照上下文检查以下步骤的结果质量。\n\n"
            f"步骤：{step_name}\n"
            f"上下文：\n{context_str}\n\n"
            f"结果：\n{result_str}\n\n"
            f"检查要求：\n"
            f"1. 评估结果是否准确、完整、无臆造；\n"
            f"2. 输出 0-1 的置信度（confidence）；\n"
            f"3. 列出发现的问题（issues）；\n"
            f"4. 置信度低于 {settings.CONFIDENCE_THRESHOLD} 时 needs_retry=true；\n"
            f"5. 指出需重试的字段或方面（retry_fields）。\n\n"
            f"严格以 JSON 输出，格式：\n"
            f'{{"confidence": 0.85, "issues": ["问题1"], '
            f'"needs_retry": false, "retry_fields": []}}'
        )

        messages = [
            {
                "role": "system",
                "content": "你是质量审核员，负责对照上下文检查 Agent 输出质量。只输出 JSON。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat(messages=messages)
            content = response.choices[0].message.content or ""
            data = parse_json_safe(content)
            if not isinstance(data, dict):
                data = {}
        except Exception as exc:
            logger.warning("自校验 LLM 调用失败: %s", exc)
            data = {}

        # 解析置信度
        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        # 解析是否需要重试
        needs_retry = data.get("needs_retry", False)
        if not isinstance(needs_retry, bool):
            needs_retry = bool(needs_retry)
        # 置信度低于阈值强制标记重试
        if confidence < settings.CONFIDENCE_THRESHOLD:
            needs_retry = True

        # 解析问题列表
        issues = data.get("issues", [])
        if not isinstance(issues, list):
            issues = [str(issues)] if issues else []

        # 解析重试字段
        retry_fields = data.get("retry_fields", [])
        if not isinstance(retry_fields, list):
            retry_fields = [str(retry_fields)] if retry_fields else []

        # 记录置信度
        self.confidences.append(confidence)

        check_result = {
            "confidence": confidence,
            "issues": issues,
            "needs_retry": needs_retry,
            "retry_fields": retry_fields,
        }

        logger.info(
            "步骤 %s 自校验: confidence=%.2f, needs_retry=%s",
            step_name,
            confidence,
            needs_retry,
        )

        return check_result

    async def reflect_and_retry(
        self,
        step_name: str,
        result: dict,
        context: str,
        retry_func: Callable,
    ) -> dict:
        """自校验 + 针对性重试

        流程：
        1. 调用 self_check 检查结果质量；
        2. 若 needs_retry，调用 retry_func 进行针对性补抽/重试（非整篇重跑）；
        3. 最多重试 MAX_RETRIES 次；
        4. 仍不达标则标记 needs_human_review 并返回当前结果。

        Args:
            step_name: 步骤名称
            result: 原始结果
            context: 校验上下文
            retry_func: 重试函数（async，无参，返回新的 result dict）

        Returns:
            更新后的 result dict，附加 reflexion 字段与可能的 needs_human_review
        """
        current = result
        check = await self.self_check(step_name, current, context)

        retries = 0
        while check["needs_retry"] and retries < MAX_RETRIES:
            retries += 1
            logger.info(
                "步骤 %s 自校验未达标 (confidence=%.2f)，触发针对性重试 %d/%d",
                step_name,
                check["confidence"],
                retries,
                MAX_RETRIES,
            )
            try:
                current = await retry_func()
                # 重试后重新自校验
                check = await self.self_check(step_name, current, context)
            except Exception as exc:
                logger.warning("步骤 %s 重试失败: %s", step_name, exc)
                break

        # 仍不达标，标记需人工复核
        needs_human_review = check["needs_retry"]
        if needs_human_review:
            logger.warning(
                "步骤 %s 经 %d 次重试仍未达标 (confidence=%.2f)，标记需人工复核",
                step_name,
                retries,
                check["confidence"],
            )

        # 将自校验结果附加到 result
        if isinstance(current, dict):
            current["reflexion"] = check
            if needs_human_review:
                current["needs_human_review"] = True
            return current
        return {
            "result": current,
            "reflexion": check,
            "needs_human_review": needs_human_review,
        }

    def get_confidence_stats(self) -> dict:
        """返回置信度统计

        Returns:
            {avg_confidence, min_confidence, count}
        """
        if not self.confidences:
            return {"avg_confidence": 0.0, "min_confidence": 0.0, "count": 0}
        return {
            "avg_confidence": round(sum(self.confidences) / len(self.confidences), 4),
            "min_confidence": round(min(self.confidences), 4),
            "count": len(self.confidences),
        }
