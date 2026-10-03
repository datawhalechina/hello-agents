"""步骤4 跨论文 Gap 识别工具：聚合结构化字段，调用强推理模型识别四类研究空白"""
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


def _build_comparison_matrix(papers_records: list[dict]) -> str:
    """将多篇论文的结构化字段按维度聚合成对比矩阵文本

    每条记录是 PaperRecord dict，字段为 FieldSource 结构 {value, source_sections, confidence}
    """
    # 字段中文名映射
    field_labels = {
        "task_problem": "研究任务/问题",
        "method": "核心方法",
        "key_contributions": "主要贡献",
        "datasets": "数据集",
        "metrics": "评估指标",
        "results": "实验结果",
        "limitations": "局限性",
        "future_work": "未来工作",
    }

    lines: list[str] = []
    for idx, rec in enumerate(papers_records, 1):
        title = rec.get("title", f"论文{idx}")
        lines.append(f"===== 论文 {idx}: {title} =====")
        for field, label in field_labels.items():
            val = rec.get(field)
            if val is None:
                continue
            # FieldSource 结构：{value, source_sections, confidence}
            if isinstance(val, dict):
                text = val.get("value", "")
            else:
                text = str(val)
            if text:
                lines.append(f"[{label}] {text}")
        lines.append("")
    return "\n".join(lines)


async def _enrich_with_hybrid_search(gap: dict) -> str:
    """对单个 Gap 调用混合搜索检索原文细节，补充论证

    懒导入 hybrid_search，避免模块加载期依赖未就绪的模块。
    """
    query = gap.get("description", "")
    if not query:
        return gap.get("evidence", "")
    try:
        # 懒导入，避免模块加载期依赖
        from backend.tools.hybrid_search_tool import hybrid_search

        result = await hybrid_search(query)
        snippets: list[str] = []
        for r in result.get("results", [])[:3]:
            title = r.get("title", "")
            section = r.get("section", "")
            text = r.get("text", "")[:200]
            snippets.append(f"  - 《{title}》{section}: {text}")
        if snippets:
            extra = "\n[原文佐证]\n" + "\n".join(snippets)
            return gap.get("evidence", "") + extra
    except Exception as exc:
        logger.warning("hybrid_search 增强 Gap 论证失败: %s", exc)
    return gap.get("evidence", "")


async def analyze_gaps(papers_records: list[dict]) -> dict:
    """跨论文 Gap 识别

    输入：papers.jsonl 的记录列表（每条是 PaperRecord dict）
    输出：{"gaps": [{description, gap_type, source_papers, evidence, confidence}]}
    """
    if not papers_records:
        return {"gaps": []}

    # 1. 聚合对比矩阵
    matrix = _build_comparison_matrix(papers_records)

    # 2. 构造强推理提示词
    n_papers = len(papers_records)
    if n_papers == 1:
        single_paper_hint = (
            f"\n## 重要提示\n当前仅 1 篇论文。请基于该论文自身的 limitations（局限性）和 future_work（未来工作），"
            "识别可深化的研究空白。source_papers 只需包含这 1 篇论文即可。"
            "至少识别 2 个有价值的 Gap（基于论文内部字段证据，不要求跨论文对比）。"
        )
        source_constraint = "source_papers 至少包含 1 篇论文。"
    else:
        single_paper_hint = ""
        source_constraint = "每个 Gap 的 source_papers 至少包含 2 篇论文。"

    prompt = f"""你是一位资深学术研究者，需要从以下多篇论文的结构化对比中识别研究空白（Gap）。

## 论文对比矩阵
{matrix}
{single_paper_hint}
## 任务
请综合分析上述论文，识别以下四类 Gap 信号：
1. repeated_limitation（重复局限）：多篇论文提到同一局限性，但无人解决
2. method_gap（方法空白）：某类问题只有少数方法尝试且效果不佳
3. contradictory（矛盾结论）：不同论文对同一问题给出冲突结论
4. unfulfilled_future（未兑现的未来工作）：多篇论文指向同一未来方向但无人完成

对于单篇论文场景，重点关注该论文自身的 limitations 与 future_work 字段，
识别方法层面、数据层面、评估层面的可深化方向。

## 输出要求
严格输出 JSON，不要包含任何额外说明文本或代码块标记。格式如下：
{{
  "gaps": [
    {{
      "description": "Gap 的清晰描述",
      "gap_type": "repeated_limitation|method_gap|contradictory|unfulfilled_future",
      "source_papers": ["来源论文标题1"],
      "evidence": "论证依据，引用具体论文的具体字段",
      "confidence": 0.0到1.0之间的置信度
    }}
  ]
}}

只输出真正有证据支撑的 Gap，不要编造。{source_constraint}"""

    messages = [
        {
            "role": "system",
            "content": "你是一位严谨的学术研究分析专家，擅长跨论文综合推理与 Gap 识别。只输出严格 JSON，不要输出任何其他内容。",
        },
        {"role": "user", "content": prompt},
    ]

    client = get_client()
    response = await client.chat(messages=messages)
    content = response.choices[0].message.content or ""
    data = parse_json_safe(content)

    if not data or not isinstance(data, dict):
        logger.warning("Gap 识别 JSON 解析失败，原始内容: %s", content[:200])
        return {"gaps": []}

    gaps = data.get("gaps", [])
    if not isinstance(gaps, list):
        gaps = []

    logger.info(
        "[analyze_gaps] LLM 返回 %d gaps (papers=%d, content_len=%d)",
        len(gaps), len(papers_records), len(content),
    )
    if len(gaps) == 0:
        logger.warning("[analyze_gaps] Gap 数量为 0！原始内容前 500 字: %s", content[:500])

    # 3. 对每个 Gap 调用混合搜索补充原文佐证
    enriched: list[dict] = []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        # 规范化字段
        normalized = {
            "description": gap.get("description", ""),
            "gap_type": gap.get("gap_type", "method_gap"),
            "source_papers": gap.get("source_papers", []),
            "evidence": gap.get("evidence", ""),
            "confidence": float(gap.get("confidence", 0.5)),
        }
        # 调用混合搜索深化论证
        normalized["evidence"] = await _enrich_with_hybrid_search(normalized)
        enriched.append(normalized)

    return {"gaps": enriched}


# 工具参数 schema
analyze_gaps_parameters = {
    "type": "object",
    "properties": {
        "papers_records": {
            "type": "array",
            "items": {"type": "object"},
            "description": "papers.jsonl 的记录列表，每条是 PaperRecord dict",
        }
    },
    "required": ["papers_records"],
}

# 工具实例
analyze_gaps_tool = Tool(
    name="analyze_gaps",
    description=(
        "步骤4：跨论文 Gap 识别。将多篇论文结构化字段聚合成对比矩阵，"
        "调用强推理模型识别四类研究空白（重复局限/方法空白/矛盾结论/未兑现未来工作），"
        "需要时调用混合搜索检索原文细节佐证。"
    ),
    parameters=analyze_gaps_parameters,
    func=analyze_gaps,
)
