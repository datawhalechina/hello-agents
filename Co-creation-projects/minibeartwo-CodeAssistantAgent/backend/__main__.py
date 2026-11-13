"""Start the loopback sidecar; Electron supplies an ephemeral token and a free port."""
import argparse
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from .app import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=os.getenv("CODE_ASSISTANT_TOKEN"))
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    if not args.token:
        parser.error("需要 --token 或 CODE_ASSISTANT_TOKEN。")
    app = create_app(args.data_dir, args.token, persist_secrets=os.getenv("CODE_ASSISTANT_DISABLE_KEYRING") != "1")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
