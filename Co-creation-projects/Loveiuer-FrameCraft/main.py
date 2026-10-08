"""CLI entry point. Run `python main.py demo` without API credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="FrameCraft — Figma D2C 多智能体毕业设计")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("demo", "使用内置设计运行离线演示"), ("generate", "导入 JSON / Figma 并生成项目"), ("serve", "启动本地工作台")):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--env-file", type=Path, help="显式读取环境文件；默认只读取本项目 .env")
        if name == "serve":
            sub.add_argument("--port", type=int, default=7860)
        else:
            sub.add_argument("--output", type=Path, help="输出至新目录，拒绝覆盖已有目录")
            sub.add_argument("--brief", default="", help="补充页面语义或用途，不能代替业务规格")
            if name == "generate":
                source = sub.add_mutually_exclusive_group(required=True)
                source.add_argument("--input", type=Path, help="Figma REST 格式 JSON 文件")
                source.add_argument("--figma-url", help="带 node-id 的 Figma Frame 链接")
                sub.add_argument("--node-id", help="目标节点 ID")
                sub.add_argument("--mode", choices=("demo", "live"), default="demo")
    args = parser.parse_args()
    try:
        from dotenv import load_dotenv
        env_file = args.env_file or ROOT / ".env"
        if args.env_file and not env_file.is_file():
            raise ValueError("指定的 --env-file 不存在。")
        load_dotenv(env_file, override=False)
        if args.command == "serve":
            import uvicorn
            from d2c.server import app
            uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
            return 0
        from d2c.artifacts import write_result
        from d2c.pipeline import run_pipeline
        if args.output and args.output.exists():
            raise ValueError("输出目录已存在，请使用新的 --output 目录以保留原有代码。")
        selected = getattr(args, "node_id", None)
        if args.command == "generate" and args.figma_url:
            from d2c.figma import fetch_figma
            payload, selected = fetch_figma(args.figma_url, os.getenv("FIGMA_ACCESS_TOKEN", ""), selected)
        else:
            source = args.input if args.command == "generate" else ROOT / "data/sample-design.json"
            if source.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("JSON 文件超过 2 MB，请选择更小的 Frame。")
            payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("设计 JSON 的顶层必须是对象。")
        mode = getattr(args, "mode", "demo")
        if mode == "live":
            print("在线模式：设计节点与补充说明将发送到配置的模型端点。")
        result = run_pipeline(payload, node_id=selected, mode=mode, brief=args.brief,
                              on_event=lambda e: print(f"[{e['stage']}/{e['status']}] {e['message']}"))
        destination = args.output or ROOT / "outputs" / ("demo-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        path = write_result(result, destination)
        print(f"\n生成完成：{path}\n打开 preview.html 查看静态结果；完整 React 构建步骤见生成项目 README。")
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
