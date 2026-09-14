#!/usr/bin/env python3
"""
CryptoAnalysisAgent 命令行入口 - 脱离 Jupyter 的生产运行方式

用法:
    python analyze.py BTC                  # 分析 BTC: 报告 + 质量门禁 + 归档信号
    python analyze.py BTC ETH SOL          # 批量分析多个币种
    python analyze.py BTC --no-record      # 只分析，不归档信号
    python analyze.py --settle             # 不分析，只核算到期信号并打印胜率
    python analyze.py BTC --judge          # 额外执行 LLM Judge 语义评审
    python web.py                          # 启动本地 Web 界面

质量门禁: 报告必须通过结构合规 + 条件化检查才会归档为信号，
未通过的报告仍会保存但标记 NOT_PASSED，不污染对外的胜率记录。

定时运行 (每日报告 + 核算) 示例 crontab:
    0 9 * * *  cd /path/to/project && python analyze.py BTC ETH
    0 10 * * * cd /path/to/project && python analyze.py --settle
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

OUTPUT_DIR = Path(__file__).parent / "outputs" / "reports"
SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,12}$")

ANALYSIS_PROMPT = (
    "请对 {symbol} 进行全面的综合分析。"
    "分别从技术面、链上面、情绪面三个维度进行分析，"
    "然后综合三个维度的结论，给出交叉验证后的综合判断和条件化建议。"
)


def load_runtime_env() -> None:
    """Load .env, then fall back to a local DeepSeek key if LLM_API_KEY is unset."""
    from dotenv import load_dotenv
    load_dotenv()

    key = (os.getenv("LLM_API_KEY") or "").strip()
    placeholders = {
        "",
        "your_api_key_here",
        "your_deepseek_api_key",
        "your_openai_api_key",
    }
    if key not in placeholders:
        return

    hermes = Path.home() / ".hermes" / ".env"
    if not hermes.is_file():
        return
    deepseek = None
    for line in hermes.read_text(encoding="utf-8").splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            deepseek = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    if not deepseek:
        return
    # Placeholder ModelScope settings in .env must not keep the DeepSeek key
    # pointed at api-inference.modelscope.cn (that yields 401 token errors).
    os.environ["LLM_API_KEY"] = deepseek
    os.environ["LLM_MODEL_ID"] = "deepseek-flash"
    os.environ["LLM_BASE_URL"] = "https://api.deepseek.com/v1/"
    os.environ["LLM_TIMEOUT"] = "180"


def normalize_symbol(symbol: str) -> str:
    symbol = (symbol or "").strip().upper().replace("USDT", "").replace("/", "")
    if not SYMBOL_RE.fullmatch(symbol):
        raise ValueError("币种符号无效，请使用如 BTC、ETH、SOL")
    return symbol


def settle() -> int:
    """核算到期信号并打印历史胜率"""
    from src.evaluation import update_outcomes, summarize_signals, format_signal_summary

    n = update_outcomes()
    print(f"本次核算 {n} 条信号结果\n")
    print(format_signal_summary(summarize_signals()))
    return 0


def run_one(
    symbol: str,
    record: bool = True,
    use_judge: bool = False,
    *,
    llm=None,
    counter=None,
    coordinator=None,
) -> Dict[str, Any]:
    """Run a full analysis for one symbol and return structured results."""
    from hello_agents import HelloAgentsLLM
    from src.agents.coordinator import create_coordinator
    from src.evaluation import (
        ToolCallCounter, timed_run, evaluate_report, record_signal,
    )

    symbol = normalize_symbol(symbol)
    load_runtime_env()

    if llm is None:
        llm = HelloAgentsLLM()
    if counter is None:
        counter = ToolCallCounter()
    if coordinator is None:
        coordinator = create_coordinator(llm=llm, tool_counter=counter)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    counter.reset()
    report, metrics = timed_run(coordinator, ANALYSIS_PROMPT.format(symbol=symbol))

    evaluation = evaluate_report(report, tool_outputs=counter.outputs)
    gate_passed = (
        evaluation["structure"]["passed"]
        and evaluation["conditional"]["passed"]
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    status = "" if gate_passed else "_NOT_PASSED"
    filename = f"{symbol}_{stamp}{status}.md"
    path = OUTPUT_DIR / filename
    from src.evaluation import format_evaluation, format_metrics
    path.write_text(
        f"{report}\n\n---\n\n{format_evaluation(evaluation)}\n\n"
        f"{format_metrics(metrics, counter)}\n",
        encoding="utf-8",
    )

    signal = None
    if gate_passed and record:
        signal = record_signal(symbol, report)

    judge = None
    if use_judge:
        from src.evaluation.judge import create_judge_agent, run_judge
        judge = run_judge(create_judge_agent(llm), report)

    return {
        "symbol": symbol,
        "report": report,
        "evaluation": evaluation,
        "metrics": metrics,
        "tool_counts": dict(counter.counts),
        "gate_passed": gate_passed,
        "filename": filename,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "signal": signal,
        "judge": judge,
    }


def analyze(symbols, record: bool, use_judge: bool) -> int:
    load_runtime_env()

    from hello_agents import HelloAgentsLLM
    from src.agents.coordinator import create_coordinator
    from src.evaluation import (
        ToolCallCounter, format_metrics, format_evaluation,
    )

    llm = HelloAgentsLLM()
    counter = ToolCallCounter()
    coordinator = create_coordinator(llm=llm, tool_counter=counter)

    exit_code = 0
    for raw in symbols:
        symbol = normalize_symbol(raw)
        print(f"\n{'=' * 60}\n🎯 分析 {symbol}\n{'=' * 60}")
        result = run_one(
            symbol,
            record=record,
            use_judge=use_judge,
            llm=llm,
            counter=counter,
            coordinator=coordinator,
        )
        print(f"\n{format_evaluation(result['evaluation'])}")
        print(f"\n{format_metrics(result['metrics'], counter)}")
        print(f"\n📄 报告已保存: {OUTPUT_DIR / result['filename']}")

        if not result["gate_passed"]:
            print("⛔ 质量门禁未通过，跳过信号归档")
            exit_code = 1
        elif result.get("signal"):
            entry = result["signal"]
            print(f"✅ 信号已归档: {entry['bias']} @ ${entry['price_at_signal']:,.2f} "
                  f"(id={entry['id']})")

        if use_judge:
            verdict = result.get("judge") or {}
            if verdict.get("parse_ok"):
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
