"""CLI entry point for FeastPlanAgent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from src.agent import BanquetPlannerAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 Markdown 宴席策划方案")
    parser.add_argument("--input", default="data/cases/shenzhen_wedding.json", help="宴席需求 JSON 文件")
    parser.add_argument("--output", default="outputs/banquet_plan.md", help="输出 Markdown 文件")
    args = parser.parse_args()

    load_dotenv()
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"找不到输入文件：{input_path}")
    request_data = json.loads(input_path.read_text(encoding="utf-8"))
    output_path = BanquetPlannerAgent().plan(request_data, Path(args.output))
    print(f"✅ 已生成宴席方案：{output_path}")


if __name__ == "__main__":
    main()
