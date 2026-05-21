from __future__ import annotations

from typing import Any

from .method_acronym import is_method_acronym_token

RANKER_SYSTEM_PROMPT = (
    "你是学术文献评估专家。根据候选论文列表评估与排序；不得虚构论文。\n\n"
    "排序原则：\n"
    "1. 优先选择与用户查询语义最相关的论文\n"
    "2. 识别经典/里程碑论文：引用量极高(>500)且发表≥5年的开创性工作应排在前面\n"
    "3. 顶会/顶刊论文(Nature/Science/NeurIPS/CVPR/ICML/ICLR等)优先\n"
    "4. 在相关性接近时，被广泛引用的论文优先于新发论文\n"
    "5. 平衡新颖性：若用户明显在找最新方法，可适当降低经典论文权重\n\n"
    "请严格按照要求的JSON格式输出。"
)

RANKER_SYSTEM_PROMPT_RETRY = (
    "你是学术文献评估专家。根据候选论文列表评估与排序；不得虚构论文。\n\n"
    "排序原则：优先语义相关，识别经典/里程碑论文，顶会论文优先，被广泛引用的论文优先。\n"
    "请严格按照要求的JSON格式输出。"
)


def ranker_short_focus_query(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    if is_method_acronym_token(q):
        return True
    return len(q.split()) <= 2 and len(q) <= 24


def build_retrieval_constraints_block(
    *,
    target_titles: list[str] | None,
    authors: list[str] | None,
    venues: list[str] | None,
    year_from: int | None,
    year_to: int | None,
    method_acronym: str | None = None,
) -> str:
    parts: list[str] = []
    ma = (method_acronym or "").strip()
    if ma:
        parts.append(
            f"- 方法缩写 **{ma}**：优先标题/摘要含「{ma}」的原始论文；"
            f"若用户指某会议上的该方法，应匹配该方法的正式论文（锚定标题优先）"
        )
    tt = [str(t).strip() for t in (target_titles or []) if str(t).strip()][:4]
    if tt:
        parts.append(f"- 目标论文标题（优先精确匹配）：{'; '.join(tt)}")
    au = [str(a).strip() for a in (authors or []) if str(a).strip()][:6]
    if au:
        parts.append(f"- 目标作者：{', '.join(au)}")
    vv = [str(v).strip() for v in (venues or []) if str(v).strip()][:4]
    if vv:
        parts.append(f"- 会议/期刊约束：{', '.join(vv)}")
    if year_from is not None or year_to is not None:
        yf = year_from if year_from is not None else "?"
        yt = year_to if year_to is not None else yf
        parts.append(f"- 年份范围：{yf}–{yt}")
    if not parts:
        return ""
    return "\n## 检索约束（必须遵守）\n" + "\n".join(parts) + "\n"


def _profile_task_and_dims(
    profile: str,
    *,
    n_papers: int,
    top_k: int,
    target_venue: str | None,
) -> tuple[str, str]:
    if profile == "novelty":
        return (
            f"从 {n_papers} 篇中选出 top {top_k}（「近期进展 / 新工作」），"
            "按「新且与查询相关」降序排列；相关度接近时优先更新、更前瞻的工作。",
            """## 评估维度（novelty）
1. **时效与趋势**（35%）：年份更新；反映该方向最新设定或基准
2. **主题相关性**（30%）：与查询任务一致（可略宽于 accuracy）
3. **新意与贡献**（25%）：架构/目标/数据/结论上相比既有方法有明确新点
4. **可信度底线**（10%）：实验充分；无关或空壳工作后排""",
        )
    if profile == "classic":
        return (
            f"从 {n_papers} 篇中选出 top {top_k}（「原始奠基 / 里程碑式经典工作」），"
            "优先**开创性论文**（查询所指方法/架构的原始提出）；近年引用/综述后排，除非用户明确要综述。",
            """## 评估维度（classic）
1. **开创性与匹配**（40%）：是否为查询所指方法/架构的**原始提出论文**或公认首作
2. **引用与影响力**（35%）：总引用与领域地位；仅讨论该方法的 survey 后排
3. **权威出处**（15%）：顶会/期刊正式收录
4. **时效**（10%）：开创性相近时优先更早的奠基论文""",
        )
    dims = """## 评估维度（accuracy）
1. **主题相关性**（40%）：论文主题与查询匹配程度
2. **方法创新性**（25%）：方法新颖与创新点
3. **结果质量**（20%）：实验充分性、结果可靠性
4. **权威与可引用性**（15%）：顶会/期刊与引用表现；经典工作可优先于纯新文"""
    if target_venue:
        dims = """## 评估维度（accuracy · 会议检索）
1. **主题相关性**（35%）：论文主题与查询匹配程度
2. **届次与年份**（25%）：相关度接近时**优先最近一届**（年份更大者优先）
3. **方法创新性**（20%）：方法新颖与创新点
4. **结果质量**（10%）：实验充分性、结果可靠性
5. **权威与可引用性**（10%）：正式 proceedings 与引用表现"""
    return (
        f"从 {n_papers} 篇中选出最相关的 top {top_k}，按与检索意图匹配程度降序排列。",
        dims,
    )


def build_ranking_prompt(
    papers: list[Any],
    query: str,
    top_k: int,
    ranking_profile: str = "accuracy",
    *,
    abstract_max_chars: int = 500,
    target_venue: str | None = None,
    main_conference_proceedings_only: bool = False,
    intent_source_message: str | None = None,
    target_titles: list[str] | None = None,
    authors: list[str] | None = None,
    venues: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    method_acronym: str | None = None,
) -> str:
    max_abs = max(120, int(abstract_max_chars or 500))
    papers_desc: list[str] = []
    for i, rp in enumerate(papers, 1):
        paper = rp.paper
        title = getattr(paper, "title", "N/A")
        abstract = getattr(paper, "abstract", "") or ""
        if len(abstract) > max_abs:
            abstract = abstract[:max_abs] + "..."
        year = getattr(paper, "year", "N/A")
        venue = getattr(paper, "venue", "") or getattr(paper, "journal", "N/A")
        citations = getattr(paper, "citations", 0) or 0
        papers_desc.append(
            f"\n【论文 {i}】\n标题：{title}\n年份：{year}\n会议/期刊：{venue}\n"
            f"引用数：{citations}\n摘要：{abstract}\n"
        )

    constraint_hint = build_retrieval_constraints_block(
        target_titles=target_titles,
        authors=authors,
        venues=venues or ([target_venue] if target_venue else None),
        year_from=year_from,
        year_to=year_to,
        method_acronym=method_acronym,
    )

    venue_hint = ""
    if target_venue:
        venue_hint = f"""
## 会场约束
用户限定了 **{target_venue}** 会议。按以下优先级判断：
1. **优先**：会议/期刊字段明确标注 {target_venue} 或其 proceedings 全称
2. **降级**：仅标题/摘要提及 {target_venue} 但会议字段不明（arXiv预印本）
3. **末位**：会议字段明确为其他会议
4. 同相关度时**发表年份更近**优先；主会优先于 workshop/symposium。
每条 reason 注明关联判断依据。

"""

    main_track_hint = ""
    if main_conference_proceedings_only and target_venue:
        um = (intent_source_message or "").strip()
        um_block = f"\n### 用户原始表述\n{um[:700]}\n" if um else ""
        main_track_hint = f"""
## 主会议录用
仅保留 **{target_venue}** 主会正式论文；排除 workshop、卫星会等。{um_block}
依据「会议/期刊」字段判断，**非主会论文不得进入前 {top_k}**（不足则少填）。
每条 reason 说明认定为主会的依据。

"""

    profile = (ranking_profile or "accuracy").strip().lower()
    if profile not in ("accuracy", "novelty", "classic"):
        profile = "accuracy"

    short_disambig = ""
    if ranker_short_focus_query(query):
        short_disambig = """
## 短查询消歧
同名缩写论文：优先副标题更匹配 ML 顶会主流问题且会议为高等级 proceedings 的论文；
下调任务/数据形态与用户意图明显不符的论文。每条 reason 说明区分依据。

"""

    task_line, dims = _profile_task_and_dims(
        profile, n_papers=len(papers), top_k=top_k, target_venue=target_venue
    )
    papers_block = "\n---\n".join(papers_desc)

    return f"""你是一位学术文献评估专家，请根据用户检索需求对以下论文精排序。

## 用户检索需求
{query}
{constraint_hint}{short_disambig}{venue_hint}{main_track_hint}
## 候选论文列表
{papers_block}

## 排序任务
{task_line}

{dims}

## 输出格式
JSON 格式：
```json
{{"rankings": [
  {{"rank": 1, "paper_index": 1, "fine_score": 9.2, "reason": "排序理由：..."}},
  ...
]}}
```

要求（必须遵守）：
1. paper_index 对应序号 1-{len(papers)}，不得虚构论文
2. fine_score 范围 0-10，保留一位小数
3. reason 用中文 2-3 句话简洁说明
4. 只输出 JSON，无其他内容
5. 仅依据上方列表判断，不得编造不存在的论文、会议或结果
"""
