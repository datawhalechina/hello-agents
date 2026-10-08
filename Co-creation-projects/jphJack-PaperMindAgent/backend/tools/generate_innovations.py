"""步骤5 创新生成与筛选工具：针对 Gap 生成候选创新方向，三维评分筛选，联网新颖性去重"""
from __future__ import annotations

import logging
from typing import Optional

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


async def _novelty_check(title: str, idea: str) -> str:
    """调用联网搜索做新颖性去重，检索近 1-2 年相关工作

    懒导入 web_search，避免模块加载期依赖未就绪的模块。
    """
    query = f"{title} {idea[:100]}"
    try:
        # 懒导入
        from backend.tools.web_search import web_search

        result = await web_search(query)
        items = result.get("results", [])[:5]
        if not items:
            return "未检索到高度相关工作，新颖性较高"
        lines: list[str] = []
        for r in items:
            t = r.get("title", "")
            snippet = r.get("snippet", "")[:120]
            url = r.get("url", "")
            lines.append(f"  - {t}: {snippet} ({url})")
        return "近 1-2 年相关工作：\n" + "\n".join(lines)
    except Exception as exc:
        logger.warning("web_search 新颖性检查失败: %s", exc)
        return "新颖性检查失败（联网搜索不可用）"


async def generate_innovations(
    gaps: list[dict],
    research_direction: Optional[str] = None,
) -> dict:
    """针对 Gap 生成候选创新方向，三维评分筛选，取综合得分最高的 2-3 个

    输入：Gap 列表 [{description, gap_type, source_papers, evidence, confidence}]
    输出：{"innovations": [{title, idea, source, gap_origin, score, novelty_check, supporting_evidence}]}
    """
    if not gaps:
        return {"innovations": []}

    # 1. 汇总 Gap 信息
    gaps_text = "\n".join(
        f"- [{g.get('gap_type', 'unknown')}] {g.get('description', '')}"
        f"（来源: {', '.join(g.get('source_papers', []))}）"
        for g in gaps
    )

    # 1.1 研究方向约束文本
    direction_text = ""
    if research_direction and research_direction.strip():
        direction_text = (
            f"\n## 用户研究方向约束\n"
            f"用户的研究方向为：{research_direction.strip()}\n"
            f"生成的创新点应尽量与该方向相关，"
            f"并在 supporting_evidence 中说明创新点与该方向的关联。\n"
        )

    # 2. 构造创新生成提示词
    prompt = f"""你是一位富有创造力的学术研究者，需要基于以下研究空白（Gap）生成候选创新方向。
{direction_text}
## 研究空白列表
{gaps_text}

## 任务
针对每个 Gap，从以下四类来源生成候选创新方向：
1. method_combination（方法组合）：把 A 论文方法迁移到 B 论文问题
2. limitation_fix（局限改进）：直接解决被反复提及的局限
3. cross_domain（跨域迁移）：引入其他领域方法
4. new_scenario（新场景应用）：把现有方法用到未被覆盖的数据/场景

对每个候选创新方向，用三维评分（0-10 分）：
- novelty（新颖性）
- feasibility（可行性）
- significance（显著性）

## 输出要求
严格输出 JSON，不要包含任何额外说明文本或代码块标记。格式如下：
{{
  "innovations": [
    {{
      "title": "创新点标题",
      "idea": "创新思路详细描述",
      "source": "method_combination|limitation_fix|cross_domain|new_scenario",
      "gap_origin": "对应的 Gap 描述",
      "score": {{
        "novelty": 0.0到10.0,
        "feasibility": 0.0到10.0,
        "significance": 0.0到10.0
      }},
      "supporting_evidence": "论据支撑"
    }}
  ]
}}

生成多个候选（每个 Gap 至少 1-2 个），按综合得分（三项之和）从高到低排序。"""

    messages = [
        {
            "role": "system",
            "content": "你是一位学术创新生成专家，擅长从研究空白中挖掘可执行的创新方向。只输出严格 JSON，不要输出任何其他内容。",
        },
        {"role": "user", "content": prompt},
    ]

    client = get_client()
    response = await client.chat(messages=messages)
    content = response.choices[0].message.content or ""
    data = parse_json_safe(content)

    if not data or not isinstance(data, dict):
        logger.warning("创新生成 JSON 解析失败: %s", content[:200])
        return {"innovations": []}

    innovations = data.get("innovations", [])
    if not isinstance(innovations, list):
        innovations = []

    # 3. 规范化 + 计算综合得分排序
    normalized: list[dict] = []
    for inv in innovations:
        if not isinstance(inv, dict):
            continue
        score = inv.get("score", {})
        if not isinstance(score, dict):
            score = {}
        novelty = float(score.get("novelty", 0.0))
        feasibility = float(score.get("feasibility", 0.0))
        significance = float(score.get("significance", 0.0))
        normalized.append(
            {
                "title": inv.get("title", ""),
                "idea": inv.get("idea", ""),
                "source": inv.get("source", "limitation_fix"),
                "gap_origin": inv.get("gap_origin", ""),
                "score": {
                    "novelty": novelty,
                    "feasibility": feasibility,
                    "significance": significance,
                },
                "_total": novelty + feasibility + significance,
                "novelty_check": None,
                "supporting_evidence": inv.get("supporting_evidence", ""),
            }
        )

    # 4. 按综合得分降序，取前 2-3 个
    normalized.sort(key=lambda x: x["_total"], reverse=True)
    top_count = 3 if len(normalized) >= 3 else len(normalized)
    top = normalized[:top_count]

    # 5. 对每个创新点做联网新颖性去重
    for inv in top:
        inv["novelty_check"] = await _novelty_check(inv["title"], inv["idea"])
        inv.pop("_total", None)

    return {"innovations": top}


# 工具参数 schema
generate_innovations_parameters = {
    "type": "object",
    "properties": {
        "gaps": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Gap 列表，每条含 description/gap_type/source_papers/evidence/confidence",
        },
        "research_direction": {
            "type": "string",
            "description": "用户的研究方向（可选），生成的创新点应尽量与该方向相关",
        },
    },
    "required": ["gaps"],
}

# 工具实例
generate_innovations_tool = Tool(
    name="generate_innovations",
    description=(
        "步骤5：创新生成与筛选。针对每个 Gap 从四类来源（方法组合/局限改进/跨域迁移/新场景应用）"
        "生成候选创新方向，三维评分筛选取综合得分最高的 2-3 个，"
        "并联网检索近 1-2 年相关工作做新颖性去重。"
    ),
    parameters=generate_innovations_parameters,
    func=generate_innovations,
)
