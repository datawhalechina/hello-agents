"""输出质量评估：基于 LLM 对创新点与最终报告进行质量评分"""
from __future__ import annotations

import logging
from typing import Optional

from backend.llm.client import DeepSeekClient
from backend.llm.json_utils import parse_json_safe

logger = logging.getLogger(__name__)

# 模块级懒加载单例
_client: Optional[DeepSeekClient] = None


def get_client() -> DeepSeekClient:
    """懒加载 DeepSeek 客户端单例"""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client


def _clamp_score(value: float) -> float:
    """将评分限制在 0-10 范围内，非法值降级为 0.0"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, v))


class QualityEvaluator:
    """输出质量评估器：调用 LLM 对创新点与报告做三维/多维评分"""

    def __init__(self, client: Optional[DeepSeekClient] = None) -> None:
        # 优先使用注入的 client，否则使用模块级懒加载单例
        self.client = client or get_client()

    async def evaluate_innovations(self, innovations: list[dict]) -> list[dict]:
        """对每个创新点用 LLM 评估三维评分（novelty/feasibility/significance 0-10）

        若创新点已有 score 则校验/调整，否则新生成。
        返回 [{innovation_title, score: {novelty, feasibility, significance}, reasoning}]
        """
        if not innovations:
            return []

        results: list[dict] = []
        for inv in innovations:
            if not isinstance(inv, dict):
                continue
            results.append(await self._evaluate_single_innovation(inv))
        return results

    async def _evaluate_single_innovation(self, inv: dict) -> dict:
        """评估单个创新点：构造提示词→调用 LLM→解析三维评分"""
        title = inv.get("title", "")
        idea = inv.get("idea", "")
        existing_score = inv.get("score")

        # 已有分数则校验/调整，否则新生成
        if isinstance(existing_score, dict) and existing_score:
            score_hint = (
                f"该创新点已有初步评分：novelty={existing_score.get('novelty', 0)}, "
                f"feasibility={existing_score.get('feasibility', 0)}, "
                f"significance={existing_score.get('significance', 0)}。"
                "请基于以上信息进行校验与调整。"
            )
        else:
            score_hint = "该创新点暂无评分，请生成新的三维评分。"

        prompt = f"""你是一位严谨的学术评审专家，请对以下创新点进行三维评分（0-10 分，保留一位小数）。

## 创新点信息
- 标题：{title}
- 思路：{idea}
- 论据支撑：{inv.get('supporting_evidence', '')}
- 新颖性检查：{inv.get('novelty_check', '') or '无'}

## 评分维度
- novelty（新颖性）：与现有工作的差异程度
- feasibility（可行性）：技术实现与资源获取的难度
- significance（显著性）：学术或应用价值

## 当前状态
{score_hint}

## 输出要求
严格输出 JSON，不要包含任何额外说明文本或代码块标记。格式如下：
{{
  "innovation_title": "{title}",
  "score": {{
    "novelty": 0.0到10.0,
    "feasibility": 0.0到10.0,
    "significance": 0.0到10.0
  }},
  "reasoning": "评分理由，简明扼要"
}}
"""
        messages = [
            {
                "role": "system",
                "content": "你是一位学术评审专家，擅长对创新点进行多维评分。只输出严格 JSON，不要输出任何其他内容。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat(messages=messages)
            content = response.choices[0].message.content or ""
            data = parse_json_safe(content)
            if isinstance(data, dict):
                score = data.get("score", {})
                if not isinstance(score, dict):
                    score = {}
                return {
                    "innovation_title": data.get("innovation_title", title),
                    "score": {
                        "novelty": _clamp_score(score.get("novelty", 0.0)),
                        "feasibility": _clamp_score(score.get("feasibility", 0.0)),
                        "significance": _clamp_score(score.get("significance", 0.0)),
                    },
                    "reasoning": data.get("reasoning", ""),
                }
            logger.warning("创新点评分 JSON 解析失败: %s", content[:200])
        except Exception as exc:
            logger.warning("创新点 '%s' 评分失败: %s", title, exc)

        # 降级：使用已有分数或全 0
        fallback = existing_score if isinstance(existing_score, dict) else {}
        return {
            "innovation_title": title,
            "score": {
                "novelty": _clamp_score(fallback.get("novelty", 0.0)),
                "feasibility": _clamp_score(fallback.get("feasibility", 0.0)),
                "significance": _clamp_score(fallback.get("significance", 0.0)),
            },
            "reasoning": "LLM 评分解析失败，使用降级分数",
        }

    async def evaluate_report(self, report: dict) -> dict:
        """对最终报告整体质量评估：结构完整性、论证严谨性、可执行性、可追溯性

        返回 {overall_score, dimensions: {...}, suggestions: [...]}
        """
        if not report:
            return {
                "overall_score": 0.0,
                "dimensions": {
                    "structural_completeness": 0.0,
                    "argument_rigor": 0.0,
                    "executability": 0.0,
                    "traceability": 0.0,
                },
                "suggestions": ["报告为空，无法评估"],
            }

        # 提取报告关键内容用于评估
        background = report.get("background_review", "")
        innovations = report.get("innovations", [])
        plans = report.get("experiment_plans", [])
        references = report.get("references", [])

        innovations_text = "\n".join(
            f"- {inv.get('title', '')}: {inv.get('idea', '')[:100]}"
            for inv in innovations
            if isinstance(inv, dict)
        )
        plans_text = "\n".join(
            f"- {p.get('innovation_title', '')}: 假设={p.get('hypothesis', '')[:80]}"
            for p in plans
            if isinstance(p, dict)
        )
        refs_count = len(references) if isinstance(references, list) else 0

        prompt = f"""你是一位学术报告评审专家，请对以下最终报告进行整体质量评估。

## 报告概览
- 背景综述长度：{len(background) if isinstance(background, str) else 0} 字符
- 创新点数量：{len(innovations) if isinstance(innovations, list) else 0}
- 实验方案数量：{len(plans) if isinstance(plans, list) else 0}
- 参考文献数量：{refs_count}

## 创新点列表
{innovations_text or '无'}

## 实验方案列表
{plans_text or '无'}

## 评估维度（0-10 分，保留一位小数）
- structural_completeness（结构完整性）：背景/创新/方案/参考是否齐全
- argument_rigor（论证严谨性）：论据是否充分、逻辑是否自洽
- executability（可执行性）：实验方案是否可落地
- traceability（可追溯性）：是否标注来源、可回溯原文

## 输出要求
严格输出 JSON，不要包含任何额外说明文本或代码块标记。格式如下：
{{
  "overall_score": 0.0到10.0,
  "dimensions": {{
    "structural_completeness": 0.0到10.0,
    "argument_rigor": 0.0到10.0,
    "executability": 0.0到10.0,
    "traceability": 0.0到10.0
  }},
  "suggestions": ["改进建议1", "改进建议2"]
}}
"""
        messages = [
            {
                "role": "system",
                "content": "你是一位学术报告评审专家，擅长整体质量评估。只输出严格 JSON，不要输出任何其他内容。",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat(messages=messages)
            content = response.choices[0].message.content or ""
            data = parse_json_safe(content)
            if isinstance(data, dict):
                dimensions = data.get("dimensions", {})
                if not isinstance(dimensions, dict):
                    dimensions = {}
                suggestions = data.get("suggestions", [])
                if not isinstance(suggestions, list):
                    suggestions = []
                return {
                    "overall_score": _clamp_score(data.get("overall_score", 0.0)),
                    "dimensions": {
                        "structural_completeness": _clamp_score(
                            dimensions.get("structural_completeness", 0.0)
                        ),
                        "argument_rigor": _clamp_score(
                            dimensions.get("argument_rigor", 0.0)
                        ),
                        "executability": _clamp_score(
                            dimensions.get("executability", 0.0)
                        ),
                        "traceability": _clamp_score(
                            dimensions.get("traceability", 0.0)
                        ),
                    },
                    "suggestions": [str(s) for s in suggestions],
                }
            logger.warning("报告评估 JSON 解析失败: %s", content[:200])
        except Exception as exc:
            logger.warning("报告评估失败: %s", exc)

        # 降级返回
        return {
            "overall_score": 0.0,
            "dimensions": {
                "structural_completeness": 0.0,
                "argument_rigor": 0.0,
                "executability": 0.0,
                "traceability": 0.0,
            },
            "suggestions": ["评估调用失败，请检查 LLM 服务"],
        }
