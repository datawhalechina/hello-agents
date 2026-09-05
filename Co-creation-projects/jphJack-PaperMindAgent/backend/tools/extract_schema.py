"""步骤2 结构化抽取 schema 定义：字段列表、Function Calling schema、提示词构造"""
from __future__ import annotations

from typing import Any


# 抽取的固定字段列表（顺序即重要性顺序，limitations 为重点字段）
EXTRACT_FIELDS: list[str] = [
    "title",
    "task_problem",
    "method",
    "key_contributions",
    "datasets",
    "metrics",
    "results",
    "limitations",
    "future_work",
]

# 各字段中文描述，用于 schema 与提示词
FIELD_DESCRIPTIONS: dict[str, str] = {
    "title": "论文标题",
    "task_problem": "研究任务/问题",
    "method": "核心方法",
    "key_contributions": "主要贡献",
    "datasets": "使用的数据集",
    "metrics": "评估指标",
    "results": "实验结果",
    "limitations": "局限性（重点字段，须论文明确承认或可从结果推断，严禁臆造）",
    "future_work": "未来工作",
}


def _field_source_schema(description: str) -> dict[str, Any]:
    """构造单个 FieldSource 字段的 JSON schema"""
    return {
        "type": "object",
        "description": description,
        "properties": {
            "value": {
                "type": "string",
                "description": "字段值",
            },
            "source_sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "原文出处章节标题列表，用于回溯核查",
            },
            "confidence": {
                "type": "number",
                "description": "置信度 0.0-1.0，信息明确且原文直述取高值，推断取中值，不足取低值",
            },
        },
        "required": ["value", "source_sections", "confidence"],
    }


# DeepSeek function calling schema：强制模型输出上述字段的 JSON
EXTRACT_FUNCTION_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "extract_paper_fields",
        "description": (
            "从论文中抽取结构化字段，每个字段含 value/source_sections/confidence。"
            "必须返回所有字段，limitations 须真实可溯源。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                field: _field_source_schema(desc)
                for field, desc in FIELD_DESCRIPTIONS.items()
            },
            "required": list(EXTRACT_FIELDS),
        },
    },
}


def build_extraction_prompt(parsed_paper: dict) -> str:
    """构造抽取提示词（中文）

    强调三点：
    1. source_sections 必须标注原文出处章节；
    2. limitations 须真实，论文未明确承认时不得臆造；
    3. 严格输出 JSON，不添加额外说明。
    """
    title = parsed_paper.get("title", "")
    sections = parsed_paper.get("sections", [])

    # 拼接章节正文，保留 heading 以便 source_sections 标注
    sections_text = ""
    for i, sec in enumerate(sections, 1):
        heading = sec.get("heading", f"章节{i}")
        content = sec.get("content", "")
        captions = sec.get("figure_captions", []) or []
        sections_text += f"\n\n## {heading}\n{content}"
        if captions:
            sections_text += "\n\n图表标题：\n" + "\n".join(f"- {c}" for c in captions)

    fields_list = "、".join(EXTRACT_FIELDS)

    return f"""请从以下论文中抽取结构化字段。

论文标题：{title}

论文正文：
{sections_text}

抽取要求：
1. 必须抽取以下字段：{fields_list}
2. 每个字段必须是 FieldSource 结构：
   {{
     "value": "字段值（字符串，尽量简洁完整）",
     "source_sections": ["原文出处章节标题列表"],
     "confidence": 0.0-1.0
   }}
3. source_sections 必须标注字段信息来源于上面哪个章节（用章节标题原文），便于回溯核查；可标注多个章节。
4. limitations 字段特别要求：必须是论文明确承认的局限，或可从实验结果直接推断的局限，严禁臆造或泛泛而谈。若论文未明确提及局限，value 填写"论文未明确陈述局限"，confidence 设为较低值（如 0.3）。
5. confidence 反映你对该字段抽取结果的可信度：
   - 信息明确且原文直述 → 0.9-1.0
   - 需要从原文推断 → 0.6-0.8
   - 信息不足或模糊 → 低于 0.6
6. 严格输出 JSON，不要添加任何额外说明文字或 markdown 代码块标记。
"""
