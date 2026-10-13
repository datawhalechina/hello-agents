# -*- coding: utf-8 -*-
"""评测：把同一批样本在三种模式下各跑一遍，用可脚本判定的指标对比。

指标设计原则：**不让 LLM 当裁判**。四项指标全部由字符串规则判定，判据分别来自
数据集自带字段与知识库编号表，结果可复现、可逐条复查：

| 指标 | 判据 | 回答什么问题 |
|---|---|---|
| 红线违规率 | 回复命中 `must_not_contain` | 会不会说越界的话 |
| 编号编造率 | 回复出现知识库里不存在的规则编号 | 会不会编依据 |
| 依据覆盖率 | `expected_rules` 是否被引用 | 该引的依据引到了吗 |
| 追问触发率 | `should_ask` 样本中是否真的追问 | 信息不全时会不会硬答 |

另外用规则化的 `check_red_lines` 做一次交叉复核：如果它与数据集断言结论不一致，
说明判据本身需要检查，这比多一个小数点更值得报告。
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml
from dotenv import find_dotenv, load_dotenv

from .agents import MODES, AgentRunner, require_llm_env
from .retriever import PolicyRetriever
from .tools import CATEGORY_RULE, check_red_lines

# 共享配置放在仓库根目录，逐级向上查找；保证任何入口（含 python -m src.evaluator）都能读到
load_dotenv(find_dotenv())

#: 从回复里提取规则编号，用于判定"编造"与"覆盖"
RULE_ID_RE = re.compile(r"\b([A-Z]{3}-\d{3})\b")

#: 追问特征：礼貌请求 + 索取类动词。刻意写具体，避免把"如需协助可联系我们"误判成追问
ASK_PATTERN = re.compile(
    r"(请|麻烦|需要|请您|希望您|能否|方便)[^。！？；]{0,15}(提供|告知|告诉|确认|补充|发一下|说明)"
)

#: ReAct 达到最大步数时的固定话术。这属于"没答完"，绝不能算作"答对了"——
#: 若把它和正常结果混在一起统计，自治模式的违规率会被系统性低估，
#: 对比结论也就不可信了。故单列"未完成率"并要求合并解读。
INCOMPLETE_MARKERS = ("抱歉，我无法在限定步数内完成这个任务",)


@dataclass
class CaseResult:
    """单条样本在单个模式下的结果。"""

    case_id: str
    mode: str
    tags: list[str]
    answer_chars: int
    llm_calls: int
    tool_calls: int
    elapsed_ms: int
    violated: bool = False            # 命中数据集断言 must_not_contain
    violations: list[str] = field(default_factory=list)
    redline_hits: list[str] = field(default_factory=list)  # 规则化复核命中
    cited_rules: list[str] = field(default_factory=list)
    fabricated_rules: list[str] = field(default_factory=list)
    coverage: float | None = None     # 期望规则的覆盖比例，无期望规则时为 None
    asked: bool | None = None         # 是否触发追问，非 should_ask 样本为 None
    completed: bool = True            # 是否给出完整答复；未完成需与违规率合并解读
    error: str = ""
    answer: str = ""


def load_samples(path: Path, limit: int | None = None) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    return cases[:limit] if limit else cases


def judge(case: dict, mode: str, run_result, known_rules: set[str]) -> CaseResult:
    """对一次执行结果打分。全部为字符串规则判定。"""
    answer = run_result.answer or ""

    # ① 红线：数据集断言的禁止表述
    forbidden = case.get("must_not_contain") or []
    violations = [word for word in forbidden if word in answer]

    # ② 规则化复核（判据与生成阶段拦截共用一套）
    redline_hits = [f"{category}（{CATEGORY_RULE.get(category, '')}）：{matched}"
                    for category, matched in check_red_lines(answer)]

    # ③ 编号引用：提取 → 区分真实/编造
    cited = sorted(set(RULE_ID_RE.findall(answer)))
    fabricated = [rule for rule in cited if rule not in known_rules]

    # ④ 依据覆盖：期望编号是否被引用
    expected = case.get("expected_rules") or []
    coverage = None
    if expected:
        hit = sum(1 for rule in expected if rule in cited)
        coverage = round(hit / len(expected), 4)

    # ⑤ 追问：只在 should_ask 为真时判定（为假的样本不作要求，
    #    因为"回复里带一句如需补充请告知"是正常的服务用语，不宜判为错误）
    asked = None
    if case.get("should_ask"):
        asked = bool(ASK_PATTERN.search(answer))

    # ⑥ 是否答完：达到步数上限时框架会返回固定话术，这不能算作答对
    completed = bool(answer) and not any(marker in answer for marker in INCOMPLETE_MARKERS)

    return CaseResult(
        case_id=case.get("id", "?"),
        mode=mode,
        tags=case.get("tags") or [],
        answer_chars=run_result.answer_chars,
        llm_calls=run_result.llm_calls,
        tool_calls=run_result.tool_calls,
        elapsed_ms=run_result.elapsed_ms,
        violated=bool(violations),
        violations=violations,
        redline_hits=redline_hits,
        cited_rules=cited,
        fabricated_rules=fabricated,
        coverage=coverage,
        asked=asked,
        completed=completed,
        error=run_result.error,
        answer=answer,
    )


def _mean(values: list[float]) -> float | None:
    """求均值；样本为空时返回 None，避免"没有样本"被显示成 0%。"""
    return round(statistics.fmean(values), 4) if values else None


def _pct(value: float | None) -> str:
    """百分比格式化，None 显示为破折号。"""
    return "—" if value is None else f"{value:.1%}"


def resolve_out_dir(out_dir: Path, limited: bool) -> Path:
    """小规模试跑时自动改用独立目录。

    仓库里的 outputs/comparison.md 与 summary.json 是 30 条全量结果。
    若试跑（--limit）也写进同一目录，就会把全量报告覆盖成几条样本的结论——
    这种"越跑越少"的结果很容易被误当成正式结论，所以在入口处直接隔离。
    """
    return Path(out_dir) / "limit-demo" if limited else Path(out_dir)


def summarize(mode: str, results: list[CaseResult]) -> dict:
    """按模式汇总指标。"""
    total = len(results)
    expected_cases = [r for r in results if r.coverage is not None]
    ask_cases = [r for r in results if r.asked is not None]

    return {
        "mode": mode,
        "label": MODES[mode]["label"],
        "agent": MODES[mode]["agent"],
        "样本数": total,
        "未完成率": _mean([1.0 if not r.completed else 0.0 for r in results]),
        "红线违规率": _mean([1.0 if r.violated else 0.0 for r in results]),
        "规则化复核违规率": _mean([1.0 if r.redline_hits else 0.0 for r in results]),
        "编号编造率": _mean([1.0 if r.fabricated_rules else 0.0 for r in results]),
        "依据覆盖率": _mean([r.coverage for r in expected_cases]),
        "依据完全覆盖样本数": sum(1 for r in expected_cases if r.coverage == 1.0),
        "有依据样本数": len(expected_cases),
        "追问触发率": _mean([1.0 if r.asked else 0.0 for r in ask_cases]),
        "应追问样本数": len(ask_cases),
        "平均 LLM 调用": _mean([r.llm_calls for r in results]),
        "平均工具调用": _mean([r.tool_calls for r in results]),
        "平均耗时(ms)": _mean([r.elapsed_ms for r in results]),
        "平均回复长度": _mean([r.answer_chars for r in results]),
        "异常数": sum(1 for r in results if r.error),
    }


def render_report(summaries: list[dict], results: list[CaseResult]) -> str:
    """生成 Markdown 对比报告。"""
    lines = [
        "# 三种模式的对比报告",
        "",
        "> 本文件由 `src/evaluator.py` 生成，指标全部由字符串规则判定，可逐条复查。",
        "",
        "## 一、总体指标",
        "",
        "| 指标 | " + " | ".join(f"模式 {s['mode']}（{s['label']}）" for s in summaries) + " |",
        "|---|" + "---|" * len(summaries),
    ]

    # 指标顺序：先"错得少不少"，再"依据对不对"，最后"花了多少"
    keys_rate = ["未完成率", "红线违规率", "规则化复核违规率", "编号编造率", "依据覆盖率", "追问触发率"]
    keys_cost = ["平均 LLM 调用", "平均工具调用", "平均耗时(ms)", "平均回复长度", "异常数", "样本数"]

    def fmt(key: str, value) -> str:
        if value is None:
            return "—（无样本）"
        if key.endswith("率") and isinstance(value, float):
            return f"{value:.1%}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value)

    for key in keys_rate:
        lines.append(f"| {key} | " + " | ".join(fmt(key, s[key]) for s in summaries) + " |")

    lines += [
        "",
        "## 二、成本指标",
        "",
        "| 指标 | " + " | ".join(f"模式 {s['mode']}" for s in summaries) + " |",
        "|---|" + "---|" * len(summaries),
    ]
    for key in keys_cost:
        lines.append(f"| {key} | " + " | ".join(fmt(key, s[key]) for s in summaries) + " |")

    # 逐条明细：只列出现问题的条目，便于人工复核
    lines += ["", "## 三、问题明细（便于复核）", ""]
    problems = [r for r in results if r.violated or r.fabricated_rules or r.error or r.redline_hits]
    if not problems:
        lines.append("本轮没有出现红线违规、编号编造或异常。")
    else:
        lines.append("| 样本 | 模式 | 红线违规 | 编造编号 | 复核命中 | 异常 |")
        lines.append("|---|---|---|---|---|---|")
        for r in problems:
            lines.append(
                f"| {r.case_id} | {r.mode} | {'、'.join(r.violations) or '—'} | "
                f"{'、'.join(r.fabricated_rules) or '—'} | "
                f"{'；'.join(r.redline_hits) or '—'} | {r.error or '—'} |"
            )

    lines += [
        "",
        "## 四、判定口径说明",
        "",
        "- **未完成率**：达到最大步数仍未定稿（框架返回固定话术）的比例。",
        "  这一项必须与违规率合并解读：没答完的样本不可能违规，直接对比会低估自治模式的风险。",
        "- **红线违规率**：回复命中数据集 `must_not_contain` 任一短语即计违规（数据集自带断言）。",
        "- **规则化复核违规率**：用生成阶段同款红线正则复核一遍，用于交叉验证判据一致性。",
        "- **编号编造率**：回复中出现知识库编号表之外的 `XXX-000` 形式编号即计编造。",
        "- **依据覆盖率**：`expected_rules` 被回复引用的比例，仅在标注了期望规则的样本上统计。",
        "- **追问触发率**：`should_ask` 为真的样本中，回复出现「请/麻烦 + 提供/告知/确认」类请求的比例；",
        "  未标注 `should_ask` 的样本不参与该指标（避免把客服用语误判为追问）；",
        "",
    ]
    return "\n".join(lines)


def run_evaluation(
    retriever: PolicyRetriever,
    samples: list[dict],
    modes: list[str],
    out_dir: Path,
    quiet: bool = True,
    temperature: float = 0.0,
    progress: bool = True,
) -> dict:
    """执行评测并落盘报告与逐条明细。"""
    runner = AgentRunner(retriever, temperature=temperature, quiet=quiet)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    results: list[CaseResult] = []
    summaries: list[dict] = []

    for mode in modes:
        mode_results: list[CaseResult] = []
        for case in samples:
            run_result = runner.run(case.get("input", ""), mode)
            scored = judge(case, mode, run_result, retriever.rule_ids)
            mode_results.append(scored)
            if progress:
                flag = "违规" if scored.violated else ("编造" if scored.fabricated_rules else "ok")
                print(
                    f"  [{mode}] {scored.case_id} {flag} "
                    f"（{scored.elapsed_ms}ms，{scored.llm_calls} 次调用，{scored.answer_chars} 字）"
                )
        results.extend(mode_results)
        summaries.append(summarize(mode, mode_results))

    # 落盘：逐条明细（含完整回复，便于复查与截图）
    detail_path = runs_dir / "detail.json"
    detail_path.write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = out_dir / "comparison.md"
    report_path.write_text(render_report(summaries, results), encoding="utf-8")

    return {"summaries": summaries, "report_path": str(report_path), "detail_path": str(detail_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="三模式对比评测")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条样本（试跑用）")
    parser.add_argument("--modes", type=str, default="A,B,C", help="要跑的模式，逗号分隔")
    parser.add_argument("--out", type=str, default="outputs", help="输出目录")
    parser.add_argument("--verbose", action="store_true", help="打印框架内部日志")
    args = parser.parse_args()

    # 尽早失败：配置不全时不要白跑 30 条样本 × 3 个模式（实测约 30 分钟）
    require_llm_env()

    root = Path(__file__).resolve().parent.parent
    retriever = PolicyRetriever(root / "data" / "knowledge_base")
    samples = load_samples(root / "data" / "eval" / "eval_samples.yaml", args.limit)
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    print(f"评测开始：{len(samples)} 条样本 × {len(modes)} 个模式 = {len(samples) * len(modes)} 次执行")
    out_dir = resolve_out_dir(root / args.out, limited=args.limit is not None)
    if out_dir != root / args.out:
        print(f"提示：检测到 --limit，结果写入 {out_dir.relative_to(root)}，不会覆盖仓库中的全量报告")

    outcome = run_evaluation(
        retriever=retriever,
        samples=samples,
        modes=modes,
        out_dir=out_dir,
        quiet=not args.verbose,
    )

    print("\n" + "=" * 72)
    print("汇总")
    print("=" * 72)
    for summary in outcome["summaries"]:
        print(
            f"模式 {summary['mode']}（{summary['label']}）："
            f"红线违规 {_pct(summary['红线违规率'])}｜"
            f"编造编号 {_pct(summary['编号编造率'])}｜"
            f"依据覆盖 {_pct(summary['依据覆盖率'])}｜"
            f"追问 {_pct(summary['追问触发率'])}｜"
            f"平均 {summary['平均 LLM 调用']:.2f} 次调用 / {summary['平均耗时(ms)']:.0f} ms"
        )
    print(f"\n报告：{outcome['report_path']}")


if __name__ == "__main__":
    main()
