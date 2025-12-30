from __future__ import annotations

import argparse
import importlib


def main() -> None:
    p = argparse.ArgumentParser(description="GraphRAG runner (optional integration)")
    p.add_argument("--check", action="store_true", help="Check if graphrag is installed")
    args = p.parse_args()

    try:
        importlib.import_module("graphrag")
        installed = True
    except Exception:
        installed = False

    if args.check:
        print("graphrag installed" if installed else "graphrag NOT installed")
        if not installed:
            print("Next: install the GraphRAG package you intend to use (e.g., Microsoft's GraphRAG).")
        return

    print("This project keeps GraphRAG integration optional.")
    print("- If you want official GraphRAG, install it first, then wire its CLI/indexing here.")


if __name__ == "__main__":
    main()
