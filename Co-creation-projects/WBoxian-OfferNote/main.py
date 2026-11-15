"""Hello-Agents 共创项目的 Web 与离线演示入口。"""

import argparse

from scripts.demo import run_demo
from scripts.serve import serve


def main():
    parser = argparse.ArgumentParser(description="OfferNote 求职面试工作台")
    parser.add_argument(
        "--demo", action="store_true", help="运行离线闭环，不启动服务器"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="本地 Web 端口，默认 8765"
    )
    parser.add_argument(
        "--stop", action="store_true", help="停止由 main.py 启动的本机服务"
    )
    args = parser.parse_args()
    if args.stop:
        from scripts.server_control import stop

        try:
            stop()
        except RuntimeError as exc:
            parser.exit(1, f"{exc}\n")
    elif args.demo:
        import json

        print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
    else:
        serve(args.port)


if __name__ == "__main__":
    main()
