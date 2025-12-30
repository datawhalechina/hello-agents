from __future__ import annotations

import argparse
import importlib


def main() -> None:
    p = argparse.ArgumentParser(description="LightRAG runner (optional integration)")
    p.add_argument("--check", action="store_true", help="Check if lightrag is installed")
    args = p.parse_args()

    try:
        importlib.import_module("lightrag")
        installed = True
    except Exception:
        installed = False

    if args.check:
        print("lightrag installed" if installed else "lightrag NOT installed")
        if not installed:
            print("Next: pip install lightrag (the package you intend to use) and add a runnable entry here.")
        return

    print("This project keeps LightRAG integration optional.")
    print("- If you have a specific LightRAG repo/package in mind, tell me its pip name and API.")


if __name__ == "__main__":
    main()
