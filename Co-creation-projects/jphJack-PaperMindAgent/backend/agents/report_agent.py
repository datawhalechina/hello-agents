"""步骤7 整合输出 Agent：将前序步骤产物整合为结构化研究提案（Markdown 报告）

输入：pipeline_results 含 papers_records / gaps / innovations / experiment_plans
输出：{background_review, innovations, experiment_plans, references, markdown}
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from backend.llm.client import DeepSeekClient
from backend.llm.json_utils import parse_json_safe

logger = logging.getLogger(__name__)

# 模块级懒加载单例 DeepSeekClient
_client: Optional[DeepSeekClient] = None


def get_default_client() -> DeepSeekClient:
    """懒加载 DeepSeek 客户端单例，供未显式注入 client 时使用"""
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client


class ReportAgent:
    """步骤7 整合输出 Agent：调用 LLM 把前序产物整合为结构化研究提案

    职责：
    1. 基于 Gap 分析梳理领域背景综述；
    2. 对每个创新点论证 Gap 来源 + 创新思路 + 三维评分 + 论据支撑；
    3. 汇总每个创新点的完整实验方案；
    4. 整理参考文献溯源（含 source_sections，可追溯至具体章节）；
    5. 输出 Markdown 格式报告字符串与结构化 dict。
    """

    def __init__(self, client: Optional[DeepSeekClient] = None) -> None:
        # 未显式注入则使用模块级懒加载单例
        self.client = client or get_default_client()

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    async def generate_report(self, pipeline_results: dict) -> dict:
        """整合前序步骤产物，生成结构化研究提案

        输入 pipeline_results 字段：
        - papers_records：结构化记录列表（PaperRecord dict）
        - gaps：Gap 列表（Gap dict）
        - innovations：创新点列表（Innovation dict）
        - experiment_plans：实验方案列表（ExperimentPlan dict）

        返回 dict：
        - background_review：背景综述字符串
        - innovations：创新点列表（含论据支撑）
        - experiment_plans：实验方案列表
        - references：参考文献溯源列表 [{title, path, sections}]
        - markdown：完整 Markdown 报告字符串
        """
        import time as _time

        _t_total = _time.perf_counter()
        papers_records = pipeline_results.get("papers_records", []) or []
        gaps = pipeline_results.get("gaps", []) or []
        innovations = pipeline_results.get("innovations", []) or []
        experiment_plans = pipeline_results.get("experiment_plans", []) or []

        logger.info(
            "[ReportAgent] 输入规模: papers=%d gaps=%d innovations=%d plans=%d",
            len(papers_records), len(gaps), len(innovations), len(experiment_plans),
        )

        # 1. 构造整合提示词
        _t_prompt0 = _time.perf_counter()
        prompt = self._build_report_prompt(pipeline_results)
        logger.info("[ReportAgent timing] 构造 prompt: %.3fs", _time.perf_counter() - _t_prompt0)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是学术研究提案撰写专家，擅长把多篇论文的 Gap 分析、创新点与实验方案"
                    "整合为结构清晰、可追溯的研究提案。严格输出 JSON，不要输出任何额外说明文本。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # 2. 调用 LLM（ReportAgent 输出较长，显式放大 max_tokens 避免 JSON 被截断）
        try:
            _t_llm0 = _time.perf_counter()
            response = await self.client.chat(messages=messages, max_tokens=8192)
            content = response.choices[0].message.content or ""
            # 记录 finish_reason，length 表示被 max_tokens 截断
            finish_reason = response.choices[0].finish_reason
            usage = getattr(response, "usage", None)
            logger.info(
                "[ReportAgent timing] LLM 调用: %.2fs, 输出 %d 字符, finish_reason=%s, usage=%s",
                _time.perf_counter() - _t_llm0, len(content), finish_reason, usage,
            )
        except Exception as exc:
            logger.warning("ReportAgent LLM 调用失败，降级为本地格式化: %s", exc)
            content = ""

        # 3. 解析 LLM 返回的结构化数据
        _t_parse0 = _time.perf_counter()
        structured_from_llm: dict = {}
        if content:
            parsed = parse_json_safe(content)
            if isinstance(parsed, dict):
                structured_from_llm = parsed
            else:
                logger.warning(
                    "ReportAgent JSON 解析失败，原始内容前 200 字: %s",
                    content[:200],
                )

        # 4. 组装最终结构化结果（LLM 输出优先，缺失字段用原始输入补齐）
        background_review = (
            structured_from_llm.get("background_review")
            or self._build_default_background(gaps, papers_records)
        )

        # 创新点：保留原始输入，合并 LLM 补充的论据支撑
        merged_innovations = self._merge_innovations(
            innovations, structured_from_llm.get("innovations", [])
        )

        # 实验方案：优先用 LLM 输出，缺失则回退原始输入
        merged_plans = self._merge_experiment_plans(
            experiment_plans, structured_from_llm.get("experiment_plans", [])
        )

        # 参考文献溯源：从 papers_records 抽取，保证可追溯
        references = self._build_references(papers_records)

        # 5. 生成 Markdown 报告：LLM 已返回 markdown 则直接用，否则本地格式化
        markdown = structured_from_llm.get("markdown") or ""
        if not markdown.strip():
            markdown = self._format_markdown(
                {
                    "background_review": background_review,
                    "innovations": merged_innovations,
                    "experiment_plans": merged_plans,
                    "references": references,
                }
            )
        logger.info(
            "[ReportAgent timing] 解析+组装+markdown: %.3fs",
            _time.perf_counter() - _t_parse0,
        )

        logger.info(
            "[ReportAgent timing] 总耗时: %.2fs, markdown %d 字符",
            _time.perf_counter() - _t_total, len(markdown),
        )
        return {
            "background_review": background_review,
            "innovations": merged_innovations,
            "experiment_plans": merged_plans,
            "references": references,
            "markdown": markdown,
        }

    # ------------------------------------------------------------------
    # 提示词构造
    # ------------------------------------------------------------------
    def _build_report_prompt(self, pipeline_results: dict) -> str:
        """构造整合提示词（中文）

        把 papers_records / gaps / innovations / experiment_plans 序列化为
        可读文本，要求 LLM 输出严格 JSON。
        """
        papers_records = pipeline_results.get("papers_records", []) or []
        gaps = pipeline_results.get("gaps", []) or []
        innovations = pipeline_results.get("innovations", []) or []
        experiment_plans = pipeline_results.get("experiment_plans", []) or []

        # 论文记录精简版（含 source_sections 便于溯源）
        papers_block = self._serialize_papers(papers_records)
        gaps_block = self._serialize_gaps(gaps)
        innovations_block = self._serialize_innovations(innovations)
        plans_block = self._serialize_experiment_plans(experiment_plans)

        # 推断研究主题：取首个创新点标题或首个 Gap 描述
        topic = ""
        if innovations:
            topic = innovations[0].get("title", "")
        if not topic and gaps:
            topic = gaps[0].get("description", "")[:40]
        if not topic:
            topic = "未指定主题"

        return f"""请基于以下前序步骤产物，整合为一份结构化研究提案。

## 研究主题
{topic}

## 一、论文结构化记录（含 source_sections，可追溯）
{papers_block}

## 二、识别到的 Gap 列表
{gaps_block}

## 三、创新点列表（含三维评分）
{innovations_block}

## 四、实验方案列表
{plans_block}

## 整合任务
1. 背景综述：基于 Gap 分析梳理领域现状与脉络，说明研究空白所在；
2. 创新点论证：对每个创新点补充 Gap 来源 + 创新思路 + 三维评分 + 论据支撑（论据须引用具体论文或 Gap 证据）；
3. 实验方案：保留每个创新点的完整实验方案要素；
4. 参考文献溯源：所有引用论文的来源标注，可追溯至具体章节（source_sections）；
5. Markdown 报告：按以下结构生成完整 Markdown 文本。

## Markdown 报告结构要求
```
# 研究提案：[主题]
## 一、背景综述
...
## 二、创新点论证
### 创新点 1：[标题]
- Gap 来源：...
- 创新思路：...
- 三维评分：新颖性 X / 可行性 X / 显著性 X
- 论据支撑：...
### 创新点 2：...
## 三、实验方案
### 创新点 1 实验方案
- 研究假设：...
- 数据集：...
- 基线方法：...
- 评估指标：...
- 消融实验：...
- 实验步骤：...
- 预期结果：...
- 风险：...
## 四、参考文献溯源
1. [论文标题] - 出处章节：...
```

## 输出要求
严格输出 JSON，不要包含任何额外说明文本或代码块标记。格式如下：
{{
  "background_review": "背景综述文本（可含换行）",
  "innovations": [
    {{
      "title": "创新点标题",
      "idea": "创新思路",
      "gap_origin": "Gap 来源描述",
      "score": {{"novelty": 8.0, "feasibility": 7.5, "significance": 8.0}},
      "supporting_evidence": "论据支撑，引用具体论文或 Gap 证据"
    }}
  ],
  "experiment_plans": [
    {{
      "innovation_title": "对应创新点标题",
      "hypothesis": "研究假设",
      "datasets": ["数据集1"],
      "baselines": ["基线方法1"],
      "metrics": ["评估指标1"],
      "ablation": ["消融实验1"],
      "steps": ["实验步骤1"],
      "expected_results": "预期结果",
      "risks": "风险"
    }}
  ],
  "references": [
    {{"title": "论文标题", "path": "论文路径", "sections": ["出处章节1", "出处章节2"]}}
  ],
  "markdown": "完整 Markdown 报告字符串"
}}

注意：
- references 必须可追溯至具体章节（source_sections）；
- 不得编造论文或证据，所有引用须来自上述论文记录；
- 若某字段在输入中缺失，对应位置写"暂无"而非编造。"""

    # ------------------------------------------------------------------
    # Markdown 格式化（降级路径）
    # ------------------------------------------------------------------
    def _format_markdown(self, structured: dict) -> str:
        """把结构化数据格式化为清晰 Markdown（LLM 未返回 markdown 时使用）"""
        background_review = structured.get("background_review", "") or "暂无"
        innovations = structured.get("innovations", []) or []
        experiment_plans = structured.get("experiment_plans", []) or []
        references = structured.get("references", []) or []

        # 主题推断
        topic = ""
        if innovations:
            topic = innovations[0].get("title", "")
        if not topic:
            topic = "未指定主题"

        lines: list[str] = []
        lines.append(f"# 研究提案：{topic}")
        lines.append("")

        # 一、背景综述
        lines.append("## 一、背景综述")
        lines.append(background_review.strip() or "暂无")
        lines.append("")

        # 二、创新点论证
        lines.append("## 二、创新点论证")
        if innovations:
            for idx, inn in enumerate(innovations, 1):
                title = inn.get("title", f"创新点{idx}")
                idea = inn.get("idea", "暂无")
                gap_origin = inn.get("gap_origin", "暂无")
                score = inn.get("score", {}) or {}
                novelty = score.get("novelty", "-")
                feasibility = score.get("feasibility", "-")
                significance = score.get("significance", "-")
                evidence = inn.get("supporting_evidence", "暂无")

                lines.append(f"### 创新点 {idx}：{title}")
                lines.append(f"- Gap 来源：{gap_origin}")
                lines.append(f"- 创新思路：{idea}")
                lines.append(
                    f"- 三维评分：新颖性 {novelty} / 可行性 {feasibility} / 显著性 {significance}"
                )
                lines.append(f"- 论据支撑：{evidence}")
                lines.append("")
        else:
            lines.append("暂无创新点")
            lines.append("")

        # 三、实验方案
        lines.append("## 三、实验方案")
        if experiment_plans:
            for idx, plan in enumerate(experiment_plans, 1):
                inn_title = plan.get("innovation_title", f"创新点{idx}")
                hypothesis = plan.get("hypothesis", "暂无")
                datasets = plan.get("datasets", []) or []
                baselines = plan.get("baselines", []) or []
                metrics = plan.get("metrics", []) or []
                ablation = plan.get("ablation", []) or []
                steps = plan.get("steps", []) or []
                expected = plan.get("expected_results", "暂无")
                risks = plan.get("risks", "暂无")

                lines.append(f"### 创新点 {idx} 实验方案（{inn_title}）")
                lines.append(f"- 研究假设：{hypothesis}")
                lines.append(f"- 数据集：{', '.join(datasets) if datasets else '暂无'}")
                lines.append(
                    f"- 基线方法：{', '.join(baselines) if baselines else '暂无'}"
                )
                lines.append(
                    f"- 评估指标：{', '.join(metrics) if metrics else '暂无'}"
                )
                lines.append(
                    f"- 消融实验：{'; '.join(ablation) if ablation else '暂无'}"
                )
                if steps:
                    steps_text = "; ".join(steps)
                else:
                    steps_text = "暂无"
                lines.append(f"- 实验步骤：{steps_text}")
                lines.append(f"- 预期结果：{expected}")
                lines.append(f"- 风险：{risks}")
                lines.append("")
        else:
            lines.append("暂无实验方案")
            lines.append("")

        # 四、参考文献溯源
        lines.append("## 四、参考文献溯源")
        if references:
            for idx, ref in enumerate(references, 1):
                title = ref.get("title", "未知标题")
                sections = ref.get("sections", []) or []
                if sections:
                    sections_text = "; ".join(sections)
                else:
                    sections_text = "未标注"
                lines.append(f"{idx}. [{title}] - 出处章节：{sections_text}")
        else:
            lines.append("暂无参考文献")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 私有辅助方法
    # ------------------------------------------------------------------
    def _serialize_papers(self, papers_records: list[dict]) -> str:
        """把论文记录序列化为可读文本（含 source_sections）"""
        if not papers_records:
            return "（无论文记录）"

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
            path = rec.get("path", "")
            lines.append(f"----- 论文 {idx}: {title} (path={path}) -----")
            for field, label in field_labels.items():
                val = rec.get(field)
                if val is None:
                    continue
                # FieldSource 结构：{value, source_sections, confidence}
                if isinstance(val, dict):
                    text = val.get("value", "")
                    src = val.get("source_sections", []) or []
                    src_text = "; ".join(src) if src else "未标注"
                    lines.append(f"  [{label}] {text}  (出处章节: {src_text})")
                else:
                    lines.append(f"  [{label}] {val}")
            lines.append("")
        return "\n".join(lines)

    def _serialize_gaps(self, gaps: list[dict]) -> str:
        """把 Gap 列表序列化为可读文本"""
        if not gaps:
            return "（无 Gap）"

        lines: list[str] = []
        for idx, gap in enumerate(gaps, 1):
            desc = gap.get("description", "")
            gtype = gap.get("gap_type", "")
            src = gap.get("source_papers", []) or []
            evidence = gap.get("evidence", "")
            conf = gap.get("confidence", "")
            src_text = "; ".join(src) if src else "未标注"
            lines.append(
                f"Gap {idx} [{gtype}] (置信度={conf}): {desc}\n"
                f"  来源论文: {src_text}\n"
                f"  论证: {evidence}"
            )
        return "\n".join(lines)

    def _serialize_innovations(self, innovations: list[dict]) -> str:
        """把创新点列表序列化为可读文本"""
        if not innovations:
            return "（无创新点）"

        lines: list[str] = []
        for idx, inn in enumerate(innovations, 1):
            title = inn.get("title", f"创新点{idx}")
            idea = inn.get("idea", "")
            source = inn.get("source", "")
            gap_origin = inn.get("gap_origin", "")
            score = inn.get("score", {}) or {}
            novelty = score.get("novelty", "-")
            feasibility = score.get("feasibility", "-")
            significance = score.get("significance", "-")
            novelty_check = inn.get("novelty_check", "")
            evidence = inn.get("supporting_evidence", "")

            lines.append(
                f"创新点 {idx}: {title} (来源={source})\n"
                f"  创新思路: {idea}\n"
                f"  Gap 来源: {gap_origin}\n"
                f"  三维评分: 新颖性 {novelty} / 可行性 {feasibility} / 显著性 {significance}\n"
                f"  新颖性验证: {novelty_check}\n"
                f"  论据支撑: {evidence}"
            )
        return "\n".join(lines)

    def _serialize_experiment_plans(self, plans: list[dict]) -> str:
        """把实验方案列表序列化为可读文本"""
        if not plans:
            return "（无实验方案）"

        lines: list[str] = []
        for idx, plan in enumerate(plans, 1):
            inn_title = plan.get("innovation_title", f"创新点{idx}")
            hypothesis = plan.get("hypothesis", "")
            datasets = plan.get("datasets", []) or []
            baselines = plan.get("baselines", []) or []
            metrics = plan.get("metrics", []) or []
            ablation = plan.get("ablation", []) or []
            steps = plan.get("steps", []) or []
            expected = plan.get("expected_results", "")
            risks = plan.get("risks", "")

            lines.append(
                f"方案 {idx} (对应: {inn_title})\n"
                f"  研究假设: {hypothesis}\n"
                f"  数据集: {', '.join(datasets)}\n"
                f"  基线方法: {', '.join(baselines)}\n"
                f"  评估指标: {', '.join(metrics)}\n"
                f"  消融实验: {'; '.join(ablation)}\n"
                f"  实验步骤: {'; '.join(steps)}\n"
                f"  预期结果: {expected}\n"
                f"  风险: {risks}"
            )
        return "\n".join(lines)

    def _build_default_background(self, gaps: list[dict], papers_records: list[dict]) -> str:
        """LLM 未返回背景综述时，基于 Gap 与论文记录生成默认综述"""
        if not gaps:
            return (
                f"本次分析共覆盖 {len(papers_records)} 篇论文，"
                "未识别到显著跨论文 Gap，建议结合具体场景进一步分析。"
            )

        lines: list[str] = []
        lines.append(
            f"本次分析共覆盖 {len(papers_records)} 篇论文，识别到 {len(gaps)} 个研究空白："
        )
        for idx, gap in enumerate(gaps, 1):
            desc = gap.get("description", "")
            gtype = gap.get("gap_type", "")
            lines.append(f"{idx}. [{gtype}] {desc}")
        return "\n".join(lines)

    def _merge_innovations(
        self, original: list[dict], from_llm: list[dict]
    ) -> list[dict]:
        """合并原始创新点与 LLM 补充的论据支撑

        以原始输入为基准，按 title 匹配 LLM 输出，补充 supporting_evidence。
        """
        if not original:
            return from_llm if isinstance(from_llm, list) else []

        # 以 title 为键建立 LLM 输出索引
        llm_index: dict[str, dict] = {}
        for item in from_llm:
            if isinstance(item, dict):
                title = item.get("title", "")
                if title:
                    llm_index[title] = item

        merged: list[dict] = []
        for inn in original:
            if not isinstance(inn, dict):
                continue
            title = inn.get("title", "")
            llm_item = llm_index.get(title, {})
            # LLM 补充的论据支撑优先，否则保留原始
            evidence = llm_item.get("supporting_evidence") or inn.get(
                "supporting_evidence", ""
            )
            merged_item = dict(inn)
            if evidence:
                merged_item["supporting_evidence"] = evidence
            merged.append(merged_item)
        return merged

    def _merge_experiment_plans(
        self, original: list[dict], from_llm: list[dict]
    ) -> list[dict]:
        """合并原始实验方案与 LLM 输出

        优先使用 LLM 输出（若存在且非空），否则回退原始输入。
        """
        if isinstance(from_llm, list) and from_llm:
            return from_llm
        return original

    def _build_references(self, papers_records: list[dict]) -> list[dict]:
        """从 papers_records 抽取参考文献溯源列表

        每条含 {title, path, sections}，sections 汇总该论文所有字段的 source_sections，
        保证可追溯至具体章节。
        """
        references: list[dict] = []
        for rec in papers_records:
            if not isinstance(rec, dict):
                continue
            title = rec.get("title", "未知标题")
            path = rec.get("path", "")
            sections: list[str] = []
            # 遍历所有 FieldSource 字段，收集 source_sections
            for key, val in rec.items():
                if isinstance(val, dict) and "source_sections" in val:
                    src = val.get("source_sections", []) or []
                    for s in src:
                        if s and s not in sections:
                            sections.append(s)
            references.append(
                {"title": title, "path": path, "sections": sections}
            )
        return references
