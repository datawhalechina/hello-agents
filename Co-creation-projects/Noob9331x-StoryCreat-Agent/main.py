"""命令行入口（FR-09）。

用法示例::

    python main.py "写一个雨夜便利店的故事" --genre novel --length 1200
    python main.py --serve --port 8000
    python main.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from src import __version__
from src.config import Settings, get_settings
from src.errors import LLMNotConfiguredError
from src.logging_utils import configure_logging, get_logger
from src.models import GenerationResult, Genre, RunStatus, StoryRequest
from src.pipeline import StoryPipeline
from src.storage import RunStorage

logger = get_logger("cli")

_STATUS_LABELS = {
    RunStatus.APPROVED: "已通过",
    RunStatus.MAX_ROUNDS_REACHED: "达到最大轮次",
    RunStatus.DEGRADED: "审稿降级",
    RunStatus.FAILED: "生成失败",
}


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="story-agent",
        description="智能故事生成器：写作 Agent + 独立审稿 Agent 的闭环生成。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            '  python main.py "写一个雨夜便利店的故事" --genre novel --length 1200\n'
            "  python main.py --serve --port 8000\n"
            "  python main.py --list"
        ),
    )
    parser.add_argument("prompt", nargs="?", help="创作需求（10–2000 字）")
    parser.add_argument(
        "--genre", choices=[item.value for item in Genre], default="novel", help="体裁"
    )
    parser.add_argument("--style", default=None, help="文风，例如“温暖克制”")
    parser.add_argument("--length", type=int, default=1200, help="目标字数（200–5000）")
    parser.add_argument("--must", default="", help="必须包含的元素，逗号分隔，最多 5 个")
    parser.add_argument("--forbid", default="", help="禁止出现的元素，逗号分隔，最多 5 个")
    parser.add_argument("--rounds", type=int, default=None, help="最大修订轮次（0–3）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出完整结果")
    parser.add_argument("--quiet", action="store_true", help="不输出逐轮摘要")
    parser.add_argument("--list", action="store_true", help="列出历史运行")
    parser.add_argument("--serve", action="store_true", help="启动 Web 服务（含前端）")
    parser.add_argument("--host", default=None, help="服务监听地址")
    parser.add_argument("--port", type=int, default=None, help="服务端口")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _split_keywords(raw: str) -> list[str]:
    """把逗号分隔的关键词字符串拆分为列表。"""
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]



def _print_history(settings: Settings) -> int:
    """打印历史运行摘要。"""
    storage = RunStorage(settings.output_dir)
    runs = storage.list_runs(limit=20)
    if not runs:
        print("暂无历史运行记录。")
        return 0
    print(f"{'运行 ID':<22} {'状态':<20} {'分数':>4} {'轮次':>4}  需求")
    for item in runs:
        status = _STATUS_LABELS.get(
            RunStatus(item.get("status", "")), item.get("status", "")
        )
        print(
            f"{item['run_id']:<22} {status:<20} "
            f"{item.get('overall_score', 0):>4} {item.get('rounds', 0):>4}  "
            f"{(item.get('prompt') or '')[:36]}"
        )
    return 0


def _print_result(result: GenerationResult, settings: Settings) -> None:
    """以人类可读格式打印运行结果。"""
    status_label = _STATUS_LABELS.get(result.status, result.status.value)
    print(f"\n运行 ID：{result.run_id}")
    print(f"状态：{result.status.value}（{status_label}）")
    if result.best_round is not None:
        print(f"采用轮次：{result.best_round}/{len(result.rounds)}")
    if result.rounds:
        best = result.rounds[result.best_round - 1] if result.best_round else None
        score = best.overall_score if best else result.rounds[-1].overall_score
        print(f"最终评分：{score}")
    print(
        f"Token：{result.usage.total_tokens} "
        f"(prompt {result.usage.prompt_tokens} / completion "
        f"{result.usage.completion_tokens})"
    )
    if result.error:
        print(f"提示：{result.error}")

    if not result.rounds:
        return
    print("\n逐轮摘要：")
    for record in result.rounds:
        fatal = sum(
            1 for issue in record.merged_issues if issue.severity.value == "fatal"
        )
        major = sum(
            1 for issue in record.merged_issues if issue.severity.value == "major"
        )
        flag = "通过" if record.approved else ("降级" if record.degraded else "未通过")
        print(
            f"  第 {record.round} 轮 | {record.overall_score:>3} 分 | {flag} | "
            f"fatal {fatal} / major {major} | {record.latency_ms} ms"
        )

    print("\n" + "=" * 60)
    print(result.final_text or "（无正文）")
    print("=" * 60)

    path = RunStorage(settings.output_dir).final_markdown_path(result.run_id)
    if path:
        try:
            display = path.relative_to(Path.cwd())
        except ValueError:
            display = path
        print(f"定稿文件：{display}")


def _run_generation(args: argparse.Namespace, settings: Settings) -> int:
    """执行一次生成并输出结果。"""
    max_rounds = settings.max_rounds_default if args.rounds is None else args.rounds
    try:
        request = StoryRequest(
            prompt=args.prompt,
            genre=args.genre,
            style=args.style,
            target_length=args.length,
            must_include=_split_keywords(args.must),
            forbidden=_split_keywords(args.forbid),
            max_rounds=max_rounds,
        )
    except ValidationError as exc:
        print("请求参数不合法：", file=sys.stderr)
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            print(f"  - {location}: {error['msg']}", file=sys.stderr)
        return 2

    rounds = max(1, request.max_rounds)
    print(f"正在生成（体裁：{request.genre.label}，最多 {rounds} 轮）…")
    try:
        pipeline = StoryPipeline.from_settings(settings)
    except LLMNotConfiguredError as exc:
        print(f"{exc}\n请参考 .env.example 完成配置后重试。", file=sys.stderr)
        return 2

    result = pipeline.run(request)
    if args.json:
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    elif args.quiet:
        status_label = _STATUS_LABELS.get(result.status, result.status.value)
        print(f"状态：{status_label}；采用轮次：{result.best_round or '-'}")
        print("\n" + (result.final_text or "（无正文）"))
    else:
        _print_result(result, settings)
    return 1 if result.status is RunStatus.FAILED else 0


def main(argv: list[str] | None = None) -> int:
    """命令行主函数，返回进程退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging("WARNING")
    settings = get_settings()

    if args.serve:
        import uvicorn

        host = args.host or settings.host
        port = args.port or settings.port
        print(f"启动服务：http://{host}:{port}  （Ctrl+C 停止）")
        uvicorn.run("src.api:app", host=host, port=port, log_level="info")
        return 0

    if args.list:
        return _print_history(settings)

    if not args.prompt:
        parser.error("请提供创作需求，或使用 --serve / --list。")

    try:
        return _run_generation(args, settings)
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI 兜底
        logger.exception("命令行执行失败")
        print(f"执行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
