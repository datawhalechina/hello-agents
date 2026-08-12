#!/usr/bin/env python3
"""
将妙想接口返回的原始 JSON 保存到 backend/fixtures/mx_raw/，
后续设置 MX_REPLAY_FIXTURES=1 即可本地回放同一 query，不再消耗额度。

在项目根目录执行（需已配置 MX_APIKEY）:

  set PYTHONPATH=backend
  py backend/scripts/capture_mx_fixture.py mx_data "600519 最新价 涨跌幅"
  py backend/scripts/capture_mx_fixture.py mx_search "今日A股市场热点 大盘动态 北向资金"
  py backend/scripts/capture_mx_fixture.py mx_xuangu "市盈率小于20"

注意：回放时服务端生成的 query 必须与抓取时字符串完全一致（含空格）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT = _BACKEND.parent

sys.path.insert(0, str(_BACKEND))
for p in (
    _ROOT / "agents",
    _ROOT / "skills" / "金融数据" / "mx-data",
    _ROOT / "skills" / "资讯搜索" / "mx-search",
    _ROOT / "skills" / "智能选股" / "mx-xuangu",
    _ROOT,
):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


def main() -> None:
    parser = argparse.ArgumentParser(description="保存妙想原始响应为本地 fixture")
    parser.add_argument(
        "channel",
        choices=("mx_data", "mx_search", "mx_xuangu"),
        help="与路由使用的 skill 一致",
    )
    parser.add_argument("query", help="自然语言查询（须与线上一致）")
    args = parser.parse_args()

    from app.config import settings
    from app.utils.mx_fixture import fixture_path, save_raw_fixture

    if not settings.MX_APIKEY or settings.MX_APIKEY == "your-mx-apikey-here":
        print("错误：请在 .env 中配置 MX_APIKEY 后再抓取 fixture")
        sys.exit(1)

    if args.channel == "mx_data":
        import mx_data as _mx

        raw = _mx.MXData(api_key=settings.MX_APIKEY).query(args.query)
    elif args.channel == "mx_search":
        import mx_search as _mx

        raw = _mx.MXSearch(api_key=settings.MX_APIKEY).search(args.query)
    else:
        import mx_xuangu as _mx

        raw = _mx.MXSelectStock(api_key=settings.MX_APIKEY).search(args.query)

    path = save_raw_fixture(args.channel, args.query, raw)
    print(f"已写入: {path}")
    print(f"哈希文件名对应 query: {args.query!r}")
    print("回放：环境变量 MX_REPLAY_FIXTURES=1（可选 MX_FIXTURE_DIR 指向目录），重启后端")


if __name__ == "__main__":
    main()
