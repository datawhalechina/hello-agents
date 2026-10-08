"""Terminal entry point for the three-agent matching demonstration."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    """Load CLI configuration and report failures with a nonzero exit status."""
    parser = argparse.ArgumentParser(description="JobMatch Agent — 简历与职位匹配评估")
    parser.add_argument(
        "--cv", type=Path, default=Path("data/java_backend_resume_beijing_5years.md")
    )
    parser.add_argument("--jobs", type=Path, default=Path("data/job.csv"))
    parser.add_argument(
        "--report", type=Path, default=Path("output/matching_report.html")
    )
    args = parser.parse_args()
    try:
        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
        for key in ("LLM_MODEL_ID", "LLM_PROVIDER", "LLM_API_KEY"):
            if not os.environ.get(key, "").strip():
                raise ValueError(f"缺少模型配置 {key}")
        from jobmatch.pipeline import evaluate

        evaluate(args.cv, args.jobs, args.report)
    except Exception as exc:  # noqa: BLE001 - CLI reports failures instead of a traceback
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
