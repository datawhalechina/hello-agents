#!/usr/bin/env python3
"""CLI entry point; `serve` opens the same pipeline in a local browser."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from cloudseed.sources import DEFAULT_TOPIC, DEFAULT_RESOURCES, load_sources, pdf_source, search_crossref


def main():
    parser = argparse.ArgumentParser(description="人工增雨科研选题助手：证据提取、跨论文比较、实验规划。")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="分析资料并导出报告")
    analyze.add_argument("--mode", choices=["live", "demo"], default="demo")
    analyze.add_argument("--sources", help="资料JSON，默认使用内置核实资料")
    analyze.add_argument("--topic", default=DEFAULT_TOPIC)
    analyze.add_argument("--resources", default=DEFAULT_RESOURCES)
    analyze.add_argument("--env-file", help="外部.env路径，不会复制到项目")
    analyze.add_argument("--out", help="新的输出目录，已有目录不会覆盖")
    analyze.add_argument("--vault", help="可选：知识库目录，只向00_Inbox新增本次笔记")
    serve = sub.add_parser("serve", help="启动本地网页")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--env-file")
    search = sub.add_parser("search", help="通过Crossref检索元数据与可用摘要")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--out", default="outputs/search.json")
    pdf = sub.add_parser("import-pdf", help="将本地PDF提取为可分析的资料JSON")
    pdf.add_argument("paths", nargs="+")
    pdf.add_argument("--out", default="outputs/imported_sources.json")
    args = parser.parse_args()
    try:
        if args.command == "analyze":
            from cloudseed.pipeline import configure_env, run_pipeline
            from cloudseed.exporter import save_result
            if args.mode == "live":
                configure_env(args.env_file)
            result = run_pipeline(load_sources(args.sources), args.topic, args.resources, args.mode,
                                  lambda i, n, state: print(f"[{i + 1}/4] {n}: {state}", flush=True))
            out = args.out or "outputs/" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            destination, batch = save_result(result, out, args.vault)
            print(f"完成：{destination}")
            if batch:
                print(f"Obsidian新增笔记：{batch}")
        elif args.command == "serve":
            from cloudseed.webapp import serve
            serve(args.port, args.env_file)
        else:
            if args.command == "search":
                payload = {"sources": search_crossref(args.query, args.limit)}
            else:
                payload = {"sources": [pdf_source(p, f"P{i}") for i, p in enumerate(args.paths, 1)]}
            out = Path(args.out)
            if out.exists():
                raise ValueError("输出文件已存在，请指定新的--out，避免覆盖资料。")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"已保存：{out.resolve()}。请核对标题、作者、年份；缺少摘要的记录需补充文本。")
        return 0
    except Exception as exc:
        # Do not print configuration values or HTTP request headers on failure.
        if isinstance(exc, (ValueError, FileNotFoundError, FileExistsError, ImportError)):
            message = str(exc)
        else:
            message = f"{type(exc).__name__}：操作失败，请检查网络、模型配置或资料格式后重试。"
        print(f"失败：{message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
