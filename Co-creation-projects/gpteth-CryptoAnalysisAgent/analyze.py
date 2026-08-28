#!/usr/bin/env python3
"""
CryptoAnalysisAgent 命令行入口 - 脱离 Jupyter 的生产运行方式

用法:
    python analyze.py BTC                  # 分析 BTC: 报告 + 质量门禁 + 归档信号
    python analyze.py BTC ETH SOL          # 批量分析多个币种
    python analyze.py BTC --no-record      # 只分析，不归档信号
    python analyze.py --settle             # 不分析，只核算到期信号并打印胜率
    python analyze.py BTC --judge          # 额外执行 LLM Judge 语义评审

质量门禁: 报告必须通过结构合规 + 条件化检查才会归档为信号，
未通过的报告仍会保存但标记 NOT_PASSED，不污染对外的胜率记录。

定时运行 (每日报告 + 核算) 示例 crontab:
    0 9 * * *  cd /path/to/project && python analyze.py BTC ETH
    0 10 * * * cd /path/to/project && python analyze.py --settle
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "outputs" / "reports"

ANALYSIS_PROMPT = (
    "请对 {symbol} 进行全面的综合分析。"
    "分别从技术面、链上面、情绪面三个维度进行分析，"
    "然后综合三个维度的结论，给出交叉验证后的综合判断和条件化建议。"
)


def settle() -> int:
    """核算到期信号并打印历史胜率"""
    from src.evaluation import update_outcomes, summarize_signals, format_signal_summary

    n = update_outcomes()
    print(f"本次核算 {n} 条信号结果\n")
    print(format_signal_summary(summarize_signals()))
    return 0


def analyze(symbols, record: bool, use_judge: bool) -> int:
    from dotenv import load_dotenv
    load_dotenv()

    from hello_agents import HelloAgentsLLM
    from src.agents.coordinator import create_coordinator
    from src.evaluation import (
        ToolCallCounter, timed_run, format_metrics,
        evaluate_report, format_evaluation, record_signal,
    )

    llm = HelloAgentsLLM()
    counter = ToolCallCounter()
    coordinator = create_coordinator(llm=llm, tool_counter=counter)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for symbol in symbols:
        symbol = symbol.upper().replace("USDT", "")
        print(f"\n{'=' * 60}\n🎯 分析 {symbol}\n{'=' * 60}")

        counter.reset()
        report, metrics = timed_run(coordinator, ANALYSIS_PROMPT.format(symbol=symbol))

        # 质量门禁: 结构 + 条件化 + 数字溯源
        evaluation = evaluate_report(report, tool_outputs=counter.outputs)
        gate_passed = (evaluation["structure"]["passed"]
                       and evaluation["conditional"]["passed"])

        # 保存报告 (附带考核结果与性能指标，便于审计)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        status = "" if gate_passed else "_NOT_PASSED"
        path = OUTPUT_DIR / f"{symbol}_{stamp}{status}.md"
        path.write_text(
            f"{report}\n\n---\n\n{format_evaluation(evaluation)}\n\n"
            f"{format_metrics(metrics, counter)}\n",
            encoding="utf-8",
        )

        print(f"\n{format_evaluation(evaluation)}")
        print(f"\n{format_metrics(metrics, counter)}")
        print(f"\n📄 报告已保存: {path}")

        if not gate_passed:
            print("⛔ 质量门禁未通过，跳过信号归档")
            exit_code = 1
        elif record:
            entry = record_signal(symbol, report)
            print(f"✅ 信号已归档: {entry['bias']} @ ${entry['price_at_signal']:,.2f} "
                  f"(id={entry['id']})")

        if use_judge:
            from src.evaluation.judge import create_judge_agent, run_judge
            verdict = run_judge(create_judge_agent(llm), report)
            if verdict["parse_ok"]:
                print("\n## LLM Judge 评分")
                for k, v in verdict["scores"].items():
                    print(f"- {k}: {v}")
            else:
                print("\n⚠️ LLM Judge 评分解析失败")

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CryptoAnalysisAgent - 多 Agent 加密货币综合分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("用法:")[1],
    )
    parser.add_argument("symbols", nargs="*", help="币种符号，如 BTC ETH SOL")
    parser.add_argument("--settle", action="store_true",
                        help="只核算到期信号并打印胜率，不执行分析")
    parser.add_argument("--no-record", action="store_true",
                        help="只分析，不归档信号")
    parser.add_argument("--judge", action="store_true",
                        help="额外执行 LLM Judge 语义评审 (消耗额外 Token)")
    args = parser.parse_args()

    if args.settle:
        return settle()
    if not args.symbols:
        parser.error("请指定至少一个币种，或使用 --settle 模式")
    return analyze(args.symbols, record=not args.no_record, use_judge=args.judge)


if __name__ == "__main__":
    sys.exit(main())
