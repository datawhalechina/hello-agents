"""批量评测脚本（FR-11）。

读取 ``data/sample.csv``（也兼容 ``data/samples.json``），逐条运行
“生成 → 审稿 → 修订”流水线，把汇总指标写入
``outputs/eval_summary.csv``，并绘制 ``outputs/demo_result.png``。

用法::

    python eval/run_eval.py                  # 跑全部样例
    python eval/run_eval.py --limit 3 --rounds 1
    python eval/run_eval.py --chart-only      # 仅根据已有汇总重新绘图

评测会真实调用 LLM，请先在 ``.env`` 中完成配置；串行执行以避免限流。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import Settings, get_settings  # noqa: E402
from src.errors import LLMNotConfiguredError  # noqa: E402
from src.models import Genre, RunStatus, StoryRequest  # noqa: E402
from src.pipeline import StoryPipeline  # noqa: E402

SUMMARY_FIELDS = [
    "case_id",
    "genre",
    "status",
    "rounds",
    "best_round",
    "final_score",
    "avg_score",
    "round_scores",
    "fatal_issues",
    "major_issues",
    "total_tokens",
    "latency_ms",
    "error",
    "note",
]

_STATUS_LABELS = {
    RunStatus.APPROVED.value: "已通过",
    RunStatus.MAX_ROUNDS_REACHED.value: "达到上限",
    RunStatus.DEGRADED.value: "审稿降级",
    RunStatus.FAILED.value: "生成失败",
    "error": "执行异常",
}


def _split_keywords(value: str | None) -> list[str]:
    """拆分 CSV 中用竖线/顿号/逗号分隔的关键词。"""
    if not value:
        return []
    normalized = value.replace("｜", "|").replace("、", "|").replace("，", ",")
    parts: list[str] = []
    for chunk in normalized.replace(",", "|").split("|"):
        item = chunk.strip()
        if item and item not in parts:
            parts.append(item)
    return parts[:5]


def _read_cases(path: Path) -> list[dict[str, Any]]:
    """读取 CSV 或 JSON 样例文件，统一返回字典列表。"""
    if not path.exists():
        raise FileNotFoundError(f"找不到评测样例：{path}")
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("JSON 样例文件必须是数组")
        return [item for item in payload if isinstance(item, dict)]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _build_request(case: dict[str, Any], rounds_override: int | None) -> StoryRequest:
    """把一行样例转换为经过校验的 StoryRequest。"""
    genre = str(case.get("genre") or "novel").strip()
    if genre not in {item.value for item in Genre}:
        raise ValueError(f"未知体裁：{genre}")
    raw_length = case.get("target_length") or 1200
    raw_rounds = case.get("max_rounds")
    return StoryRequest(
        prompt=str(case.get("prompt") or "").strip(),
        genre=genre,
        style=(str(case.get("style") or "").strip() or None),
        target_length=int(float(raw_length)),
        must_include=_split_keywords(case.get("must_include")),
        forbidden=_split_keywords(case.get("forbidden")),
        max_rounds=(
            rounds_override
            if rounds_override is not None
            else int(float(raw_rounds)) if str(raw_rounds or "").strip() else 2
        ),
    )


def _row_from_result(
    case_id: str,
    genre: str,
    result: Any,
    note: str,
) -> dict[str, Any]:
    """把一次 GenerationResult 压缩为汇总行。"""
    rounds = result.rounds or []
    scores = [int(record.overall_score or 0) for record in rounds]
    best = result.best_round
    final_score = 0
    if isinstance(best, int) and 0 < best <= len(rounds):
        final_score = scores[best - 1]
    elif scores:
        final_score = max(scores)
    best_record = rounds[best - 1] if isinstance(best, int) and 0 < best <= len(rounds) else None
    issues = best_record.merged_issues if best_record else []
    return {
        "case_id": case_id,
        "genre": genre,
        "status": result.status.value,
        "rounds": len(rounds),
        "best_round": best or "",
        "final_score": final_score,
        "avg_score": int(round(sum(scores) / len(scores))) if scores else 0,
        "round_scores": "|".join(str(score) for score in scores),
        "fatal_issues": sum(1 for item in issues if item.severity.value == "fatal"),
        "major_issues": sum(1 for item in issues if item.severity.value == "major"),
        "total_tokens": int(result.usage.total_tokens or 0),
        "latency_ms": sum(int(record.latency_ms or 0) for record in rounds),
        "error": (result.error or "").replace("\n", " ")[:300],
        "note": note[:200],
    }


def evaluate(
    cases: list[dict[str, Any]],
    settings: Settings,
    rounds_override: int | None = None,
) -> list[dict[str, Any]]:
    """逐条串行运行流水线，返回汇总行列表。"""
    pipeline = StoryPipeline.from_settings(settings)
    rows: list[dict[str, Any]] = []
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or case.get("id") or f"case-{index:03d}")
        note = str(case.get("note") or "")
        print(f"[{index}/{total}] {case_id} …", flush=True)
        try:
            request = _build_request(case, rounds_override)
            result = pipeline.run(request)
        except Exception as exc:  # noqa: BLE001 - 单条失败不阻断批量评测
            print(f"    失败：{exc}")
            rows.append(
                {
                    "case_id": case_id,
                    "genre": str(case.get("genre") or ""),
                    "status": "error",
                    "rounds": 0,
                    "best_round": "",
                    "final_score": 0,
                    "avg_score": 0,
                    "round_scores": "",
                    "fatal_issues": 0,
                    "major_issues": 0,
                    "total_tokens": 0,
                    "latency_ms": 0,
                    "error": str(exc).replace("\n", " ")[:300],
                    "note": note[:200],
                }
            )
            continue
        row = _row_from_result(case_id, request.genre.value, result, note)
        rows.append(row)
        print(
            f"    {_STATUS_LABELS.get(row['status'], row['status'])}，"
            f"最终 {row['final_score']} 分，{row['rounds']} 轮，"
            f"{row['total_tokens']} tokens"
        )
    return rows


def write_summary(rows: list[dict[str, Any]], path: Path) -> Path:
    """把汇总行写入 UTF-8 BOM CSV，便于 Excel 直接打开。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in SUMMARY_FIELDS})
    return path


def read_summary(path: Path) -> list[dict[str, Any]]:
    """读取已有的 eval_summary.csv。"""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]



def _has_cjk_font() -> bool:
    """检测系统是否安装了可用的中文字体。"""
    try:
        from matplotlib import font_manager
    except ImportError:  # pragma: no cover - 依赖缺失时按英文标签处理
        return False
    available = {item.name for item in font_manager.fontManager.ttflist}
    return bool({"Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC"} & available)


def render_chart(rows: list[dict[str, Any]], path: Path) -> bool:
    """绘制“用例得分 + 逐轮均分”双栏柱状图，失败时返回 False。"""
    if not rows:
        print("没有可绘制的评测数据。")
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover - matplotlib 为可选依赖
        print("未安装 matplotlib，跳过图表生成。")
        return False

    chinese = _has_cjk_font()
    if chinese:
        matplotlib.rcParams["font.sans-serif"] = [
            "Microsoft YaHei",
            "SimHei",
            "Noto Sans CJK SC",
            "PingFang SC",
            "DejaVu Sans",
        ]
    matplotlib.rcParams["axes.unicode_minus"] = False

    def label(cn: str, en: str) -> str:
        return cn if chinese else en

    labels = [str(row.get("case_id", "")) for row in rows]
    scores = [int(float(row.get("final_score") or 0)) for row in rows]
    statuses = [str(row.get("status", "")) for row in rows]
    palette = {
        "approved": "#2f6f4e",
        "max_rounds_reached": "#2b5876",
        "degraded": "#a16207",
        "failed": "#a12a2a",
        "error": "#7a7168",
    }
    colors = [palette.get(status, "#7a7168") for status in statuses]

    # 逐轮均分：把 "88|91" 拆开，按轮次位置求平均。
    buckets: dict[int, list[int]] = {}
    for row in rows:
        raw = str(row.get("round_scores") or "")
        for index, value in enumerate(raw.split("|"), start=1):
            try:
                buckets.setdefault(index, []).append(int(float(value)))
            except ValueError:
                continue
    round_labels = [label(f"第{index}轮", f"Round {index}") for index in sorted(buckets)]
    round_means = [
        round(sum(buckets[index]) / len(buckets[index]), 1) for index in sorted(buckets)
    ]

    fig, (left, right) = plt.subplots(1, 2, figsize=(12.6, 4.8))
    positions = list(range(len(rows)))
    left.bar(positions, scores, color=colors, width=0.68)
    left.set_xticks(positions)
    left.set_xticklabels(labels, rotation=32, ha="right", fontsize=8)
    left.set_ylim(0, 100)
    left.set_ylabel(label("最终得分", "Final score"))
    left.set_title(label("各用例最终得分", "Final score per case"), fontsize=12)
    left.grid(axis="y", alpha=0.25, linestyle="--")
    for position, score in zip(positions, scores):
        left.text(position, min(score + 2, 96), str(score), ha="center", fontsize=8)

    if round_means:
        right.bar(
            range(len(round_means)),
            round_means,
            color="#b45309",
            width=0.55,
        )
        right.set_xticks(range(len(round_means)))
        right.set_xticklabels(round_labels)
        right.set_ylim(0, 100)
        right.set_ylabel(label("平均分", "Average score"))
        right.set_title(label("逐轮平均得分", "Average score per round"), fontsize=12)
        right.grid(axis="y", alpha=0.25, linestyle="--")
        for position, value in enumerate(round_means):
            right.text(position, value + 2, f"{value:.1f}", ha="center", fontsize=8)
    else:
        right.text(0.5, 0.5, label("暂无轮次数据", "No round data"), ha="center", va="center")
        right.axis("off")

    fig.suptitle(
        label("智能故事生成器 · 批量评测结果", "Story Agent · Batch Evaluation"),
        fontsize=14,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


def _print_overview(rows: list[dict[str, Any]]) -> None:
    """在终端打印状态分布与均分。"""
    if not rows:
        return
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    scores = [int(float(row.get("final_score") or 0)) for row in rows]
    print("\n—— 评测汇总 ——")
    for status, count in sorted(counts.items(), key=lambda item: -item[1]):
        print(f"  {_STATUS_LABELS.get(status, status):<8} {count}")
    print(f"  平均最终得分：{sum(scores) / len(scores):.1f}")



def build_parser() -> argparse.ArgumentParser:
    """构造评测命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="story-eval",
        description="批量运行故事生成流水线，输出汇总 CSV 与评分图表。",
    )
    parser.add_argument(
        "--cases",
        default=str(ROOT / "data" / "sample.csv"),
        help="样例文件（CSV 或 JSON），默认 data/sample.csv",
    )
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument(
        "--rounds",
        type=int,
        choices=[0, 1, 2, 3],
        default=None,
        help="覆盖样例中的 max_rounds",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "outputs"),
        help="汇总与图表输出目录",
    )
    parser.add_argument(
        "--chart-only",
        action="store_true",
        help="不调用模型，仅根据已有 eval_summary.csv 重新绘图",
    )
    parser.add_argument("--no-chart", action="store_true", help="只写 CSV，不生成图表")
    return parser


def main(argv: list[str] | None = None) -> int:
    """批量评测入口，返回进程退出码。"""
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve()
    summary_path = output_dir / "eval_summary.csv"
    chart_path = output_dir / "demo_result.png"

    if args.chart_only:
        if not summary_path.exists():
            print(f"找不到汇总文件：{summary_path}，请先运行一次评测。", file=sys.stderr)
            return 2
        rows = read_summary(summary_path)
        if render_chart(rows, chart_path):
            print(f"图表已生成：{chart_path}")
            return 0
        return 1

    settings = get_settings()
    try:
        cases = _read_cases(Path(args.cases).expanduser().resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"读取样例失败：{exc}", file=sys.stderr)
        return 2
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]
    if not cases:
        print("没有可运行的样例。", file=sys.stderr)
        return 2

    try:
        rows = evaluate(cases, settings, rounds_override=args.rounds)
    except LLMNotConfiguredError as exc:
        print(f"{exc}\n请参考 .env.example 完成配置后重试。", file=sys.stderr)
        return 2

    write_summary(rows, summary_path)
    print(f"\n汇总已写入：{summary_path}")
    _print_overview(rows)
    if not args.no_chart:
        if render_chart(rows, chart_path):
            print(f"图表已生成：{chart_path}")
        else:
            print("图表生成失败，但不影响汇总 CSV。", file=sys.stderr)
    return 0 if any(row["status"] != "error" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

