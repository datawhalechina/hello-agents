"""CLI entry point for MoneyMirrorAgent."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from src.agents.coordinator import MoneyMirrorCoordinator
from src.agents.runtime import LLMCallError, RuntimeConfigurationError
from src.models import Goal

ROOT = Path(__file__).resolve().parent


def _parse_goal(specification: str) -> Goal:
    """Parse a repeatable CLI financial goal without inventing user data.

    Format: title|type|target_amount|current_amount|deadline
    For category_limit, append: |category|monthly_limit
    """
    fields = [field.strip() for field in specification.split("|")]
    if len(fields) not in {5, 7}:
        raise ValueError(
            "格式为 标题|类型|目标金额|当前金额|截止日期；类别限额目标追加 |类别|月限额"
        )
    title, goal_type, target_raw, current_raw, deadline = fields[:5]
    if not title:
        raise ValueError("目标标题不能为空")
    if goal_type not in {"savings", "travel", "category_limit"}:
        raise ValueError("目标类型必须是 savings、travel 或 category_limit")
    try:
        target_amount = float(target_raw)
        current_amount = float(current_raw)
        date.fromisoformat(deadline)
    except ValueError as exc:
        raise ValueError("目标金额必须是数字，截止日期必须为 YYYY-MM-DD") from exc
    if target_amount <= 0 or current_amount < 0:
        raise ValueError("目标金额必须大于 0，当前金额不能小于 0")

    category: str | None = None
    monthly_limit: float | None = None
    if goal_type == "category_limit":
        if len(fields) != 7 or not fields[5]:
            raise ValueError("category_limit 需要追加类别和月限额")
        category = fields[5]
        try:
            monthly_limit = float(fields[6])
        except ValueError as exc:
            raise ValueError("类别月限额必须是数字") from exc
        if monthly_limit <= 0:
            raise ValueError("类别月限额必须大于 0")
    elif len(fields) != 5:
        raise ValueError("只有 category_limit 可以追加类别和月限额")

    digest = hashlib.sha256(specification.encode("utf-8")).hexdigest()[:12]
    return Goal(
        goal_id=f"cli_{digest}",
        title=title,
        goal_type=goal_type,
        target_amount=target_amount,
        current_amount=current_amount,
        deadline=deadline,
        category=category,
        monthly_limit=monthly_limit,
    )

def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="MoneyMirrorAgent: 智能理财助手")
    command.add_argument("--interactive", action="store_true", help="分析账单后进入 LLM 引导对话，输入 /done 后生成最终 Markdown")
    command.add_argument("--csv", type=Path, required=True, metavar="账单CSV", help="要分析的 CSV 账单路径（必填）")
    command.add_argument("--month", help="指定分析月份，例如 2026-07")
    command.add_argument("--db", type=Path, default=ROOT / "outputs" / "moneymirror.db", help="SQLite Memory 路径")
    command.add_argument("--output-dir", type=Path, default=ROOT / "outputs", help="报告输出目录")
    command.add_argument("--reset", action="store_true", help="删除现有 SQLite Memory 后运行")
    command.add_argument("--correct", metavar="商户:类别", action="append", default=[], help="写入商户分类纠正，可重复指定")
    command.add_argument(
        "--goal",
        action="append",
        default=[],
        metavar="标题|类型|目标金额|当前金额|截止日期[|类别|月限额]",
        help="添加财务目标；可重复。类型为 savings、travel 或 category_limit",
    )
    return command


def _print_quest_board(report) -> None:
    """Show the RPG task board in terminals without a graphical UI."""
    print("\n🎮 当前 Money Quest：")
    for quest in report.quests:
        progress = f"{quest.progress:g}/{quest.target:g}{quest.unit}"
        status = "✅ 已完成" if quest.status == "completed" else "🔄 进行中"
        print(f"- [{quest.quest_id}] {quest.title} · {progress} · {status} · +{quest.exp_reward} EXP")
        print(f"  {quest.description}")
        print(f"  证据：{quest.evidence}")


def _interactive(coordinator: MoneyMirrorCoordinator, report, output_dir: Path, csv_path: Path) -> None:
    history: list[dict[str, str]] = []
    _print_quest_board(report)
    opening = coordinator.conversation_agent.opening(report)
    history.append({"role": "assistant", "content": opening})
    print("\n🧭 MoneyMirrorAgent 引导：")
    print(opening)
    print(
        "\n直接输入你的回答即可；/quests 查看任务；"
        "/complete <quest_id> [备注] 确认订阅检查等人工任务；"
        "/done、/quit 或 退出 结束对话并生成 Markdown 月报。"
    )
    while True:
        question = input("\n你> ").strip()
        lowered = question.lower()
        if lowered in {"/done", "/quit", "退出"}:
            break
        if not question:
            continue
        if lowered == "/quests":
            _print_quest_board(report)
            continue
        if lowered.startswith("/complete "):
            parts = question.split(maxsplit=2)
            if len(parts) < 2:
                print("用法：/complete <quest_id> [备注]")
                continue
            try:
                result = coordinator.complete_quest(report, parts[1], parts[2] if len(parts) > 2 else "")
                print(f"✅ 已确认 Quest，获得 {result['gained_exp']} EXP；当前 Lv.{result['level']} / EXP {result['total_exp']}。")
            except ValueError as exc:
                print(f"⚠️ {exc}")
            continue
        history.append({"role": "user", "content": question})
        print("\nMoneyMirrorAgent> ", end="", flush=True)
        chunks = coordinator.runtime.stream_user_guidance(
            question,
            coordinator.conversation_agent.payload(report),
            history,
        )
        answer_parts: list[str] = []
        for chunk in chunks:
            print(chunk, end="", flush=True)
            answer_parts.append(chunk)
        print()
        history.append({"role": "assistant", "content": "".join(answer_parts).strip()})
    json_path, markdown_path = coordinator.write_outputs(report, output_dir, history, source_csv=csv_path)
    print(f"\n✅ 对话结束，LLM Markdown 报告：{markdown_path}")
    print(f"📦 JSON 事实快照：{json_path}")


def main() -> int:
    load_dotenv(ROOT / ".env")
    logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    argument_parser = parser()
    args = argument_parser.parse_args()
    try:
        goals = [_parse_goal(specification) for specification in args.goal]
    except ValueError as exc:
        argument_parser.error(f"--goal {exc}")
    csv_path = args.csv
    print(f"账单文件: {csv_path}")
    if args.reset and args.db.exists():
        args.db.unlink()
    coordinator = None
    try:
        coordinator = MoneyMirrorCoordinator(args.db, os.getenv("MONEYMIRROR_USER_ID", "local_user"))
        for correction in args.correct:
            if ":" not in correction:
                argument_parser.error("--correct 格式必须为 商户:类别，例如 星巴克:餐饮")
            merchant, category = correction.split(":", 1)
            coordinator.correct_merchant_category(merchant, category)
        for goal in goals:
            coordinator.add_goal(goal)
        report = coordinator.analyze_csv(csv_path, args.month)
        if args.interactive:
            _interactive(coordinator, report, args.output_dir, csv_path)
        else:
            json_path, markdown_path = coordinator.write_outputs(report, args.output_dir, source_csv=csv_path)
            print("\nMoneyMirrorAgent 完整分析已完成")
            print(f"分析月份: {report.month}")
            print(f"收入 ¥{report.summary['income']:.2f} | 支出 ¥{report.summary['expense']:.2f} | 结余 ¥{report.summary['balance']:.2f} | 储蓄率 {report.summary['savings_rate']:.2f}%")
            print(f"消费人格: {report.persona['primary']}")
            print(f"异常消费: {len(report.anomalies)} 笔 | Quest: {len(report.quests)} 个 | 反思: 已生成")
            print(f"JSON 报告: {json_path}")
            print(f"Markdown 报告（LLM 生成）: {markdown_path}")
        return 0
    except (OSError, ValueError, RuntimeConfigurationError, LLMCallError) as exc:
        print(f"MoneyMirrorAgent 运行失败: {exc}", file=sys.stderr)
        return 2
    finally:
        if coordinator is not None:
            coordinator.close()


if __name__ == "__main__":
    raise SystemExit(main())
