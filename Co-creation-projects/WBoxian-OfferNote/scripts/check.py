"""执行后端回归与前端生产构建；任何失败均退出非零。"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
if npm is None:
    raise SystemExit(
        "npm is required; install the Node.js version documented in README."
    )
commands = [
    ([sys.executable, "-m", "pytest", "backend/tests", "-q", "--tb=short"], ROOT),
    ([sys.executable, "-m", "ruff", "check", "backend", "scripts", "main.py"], ROOT),
    (
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "backend",
            "scripts",
            "main.py",
        ],
        ROOT,
    ),
    ([npm, "run", "format:check"], ROOT / "frontend"),
    ([npm, "run", "build"], ROOT / "frontend"),
]
for command, directory in commands:
    result = subprocess.run(command, cwd=directory, env=env)
    if result.returncode:
        sys.exit(result.returncode)
