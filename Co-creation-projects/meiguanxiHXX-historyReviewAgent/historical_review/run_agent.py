#!/usr/bin/env python3
"""
多角色历史辩论：观点碰撞 → 终局综合。

默认**交互**：会询问议题、是否网络附录、是否确认开始。
一键非交互：加 -y（或 --yes），可配合命令行议题。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from historical_review.cli_interactive import prompt_topic, prompt_yes_no
from historical_review.debate_orchestrator import run_historical_debate

DEFAULT_TOPIC = (
    "玄武门之变：官修叙事如何书写？若结合当时宫廷权力与文官修史环境，"
    "有哪些记载显得蹊跷？野史与域外材料能否照出缝隙？"
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="多角色历史辩论（官修/野史/政治语境/域外/蹊跷辨析 → 综合）",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="历史议题；省略则在交互模式下询问",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="非交互：不询问，直接使用参数与默认值（适合脚本/自动化）",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        help="不抓取维基/检索附录（若在交互模式且未指定本项，仍会询问是否启用）",
    )
    parser.add_argument(
        "--debate-temp",
        type=float,
        default=0.72,
        help="辩论轮温度",
    )
    parser.add_argument(
        "--synth-temp",
        type=float,
        default=0.22,
        help="终局综合温度",
    )
    args = parser.parse_args()

    topic = args.topic
    use_evidence = not args.no_evidence

    if args.yes:
        if topic is None or not str(topic).strip():
            topic = DEFAULT_TOPIC
        use_evidence = not args.no_evidence
    else:
        print("=" * 56)
        print(" 多角色历史辩论 — 请先确认选项（加 -y 可跳过本流程）")
        print("=" * 56)
        if topic is None or not str(topic).strip():
            topic = prompt_topic(DEFAULT_TOPIC)
        else:
            print(f"\n议题（来自命令行）：{topic}\n")

        if args.no_evidence:
            use_evidence = False
            print("已指定 --no-evidence：不抓取维基/检索附录。\n")
        else:
            use_evidence = prompt_yes_no("是否启用维基与检索作为考据附录？", default=True)
            print()

        if not prompt_yes_no(
            "即将依次调用：5 角色第一轮 + 1 次秘书摘要 + 5 角色第二轮 + 1 次终局综合（约 12 次 LLM 请求），确认开始？",
            default=True,
        ):
            print("已取消。")
            sys.exit(0)
        print()

    report = run_historical_debate(
        str(topic).strip(),
        use_evidence_bundle=use_evidence,
        debate_temperature=args.debate_temp,
        synthesizer_temperature=args.synth_temp,
    )
    print(report)


if __name__ == "__main__":
    main()
