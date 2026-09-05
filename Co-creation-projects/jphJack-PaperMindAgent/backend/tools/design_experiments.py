"""步骤6 实验方案设计工具：为每个创新点输出可执行研究方案"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.llm.client import DeepSeekClient
from backend.llm.json_utils import parse_json_safe
from backend.tools.base import Tool

logger = logging.getLogger(__name__)

# 模块级懒加载单例
_client: Optional[DeepSeekClient] = None


def get_client() -> DeepSeekClient:
    """懒加载 DeepSeek 客户端单例"""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client


def _ensure_list(val: Any) -> list:
    """确保返回 list 类型"""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


async def design_experiments(innovations: list[dict]) -> dict:
    """为每个创新点输出可执行研究方案

    输入：创新点列表 [{title, idea, source, gap_origin, score, novelty_check, supporting_evidence}]
    输出：{"experiment_plans": [{innovation_title, hypothesis, datasets, baselines, metrics, ablation, steps, expected_results, risks}]}
    """
    if not innovations:
        return {"experiment_plans": []}

    # 1. 汇总创新点信息
    innovations_text = "\n".join(
        f"- {inv.get('title', '')}: {inv.get('idea', '')}"
        f"（来源: {inv.get('source', '')}，Gap: {inv.get('gap_origin', '')}）"
        for inv in innovations
    )

    # 2. 构造实验设计提示词
    prompt = f"""你是一位资深学术研究者，需要为以下创新点设计可执行的研究方案。

## 创新点列表
{innovations_text}

## 任务
为每个创新点设计完整、可执行的研究方案，包含：
- hypothesis（研究假设）：清晰可验证的假设
- datasets（数据集列表）：适合该研究的公开数据集
- baselines（基线方法列表）：需要对比的现有方法
- metrics（评估指标列表）：量化评估指标
- ablation（消融实验设计列表）：验证各组件贡献
- steps（实验步骤列表）：可复现的实验流程
- expected_results（预期结果）：预期达到的性能或发现
- risks（风险）：可能的失败点与应对

## 输出要求
严格输出 JSON，不要包含任何额外说明文本或代码块标记。格式如下：
{{
  "experiment_plans": [
    {{
      "innovation_title": "对应的创新点标题",
      "hypothesis": "研究假设",
      "datasets": ["数据集1", "数据集2"],
      "baselines": ["基线方法1", "基线方法2"],
      "metrics": ["指标1", "指标2"],
      "ablation": ["消融实验1", "消融实验2"],
      "steps": ["步骤1", "步骤2", "步骤3"],
      "expected_results": "预期结果描述",
      "risks": "风险与应对描述"
    }}
  ]
}}

每个创新点对应一条方案，方案须具体可执行。datasets/baselines/metrics/ablation/steps 均为字符串数组。"""

    messages = [
        {
            "role": "system",
            "content": "你是一位学术实验设计专家，擅长设计严谨可执行的研究方案。只输出严格 JSON，不要输出任何其他内容。",
        },
        {"role": "user", "content": prompt},
    ]

    client = get_client()
    response = await client.chat(messages=messages)
    content = response.choices[0].message.content or ""
    data = parse_json_safe(content)

    if not data or not isinstance(data, dict):
        logger.warning("实验方案 JSON 解析失败: %s", content[:200])
        return {"experiment_plans": []}

    plans = data.get("experiment_plans", [])
    if not isinstance(plans, list):
        plans = []

    # 3. 规范化字段，确保列表类型
    normalized: list[dict] = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        normalized.append(
            {
                "innovation_title": plan.get("innovation_title", ""),
                "hypothesis": plan.get("hypothesis", ""),
                "datasets": _ensure_list(plan.get("datasets", [])),
                "baselines": _ensure_list(plan.get("baselines", [])),
                "metrics": _ensure_list(plan.get("metrics", [])),
                "ablation": _ensure_list(plan.get("ablation", [])),
                "steps": _ensure_list(plan.get("steps", [])),
                "expected_results": plan.get("expected_results", ""),
                "risks": plan.get("risks", ""),
            }
        )

    return {"experiment_plans": normalized}


# 工具参数 schema
design_experiments_parameters = {
    "type": "object",
    "properties": {
        "innovations": {
            "type": "array",
            "items": {"type": "object"},
            "description": "创新点列表，每条含 title/idea/source/gap_origin/score/novelty_check/supporting_evidence",
        }
    },
    "required": ["innovations"],
}

# 工具实例
design_experiments_tool = Tool(
    name="design_experiments",
    description=(
        "步骤6：实验方案设计。为每个创新点输出可执行研究方案，"
        "包含研究假设、数据集、基线方法、评估指标、消融实验、实验步骤、预期结果与风险。"
    ),
    parameters=design_experiments_parameters,
    func=design_experiments,
)
