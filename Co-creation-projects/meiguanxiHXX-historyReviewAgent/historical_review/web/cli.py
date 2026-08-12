from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("HISTORY_REVIEW_HOST", "127.0.0.1")
    port = int(os.getenv("HISTORY_REVIEW_PORT", "8777"))
    reload = os.getenv("HISTORY_REVIEW_RELOAD", "1").strip() not in {"0", "false", "False"}

    uvicorn.run(
        "historical_review.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()

