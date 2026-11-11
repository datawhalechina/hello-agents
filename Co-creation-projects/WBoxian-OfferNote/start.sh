#!/usr/bin/env sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_path="$project_root/.venv/bin/python"
if [ ! -x "$python_path" ]; then
    echo "Missing .venv. Follow README to install project dependencies." >&2
    exit 1
fi
if [ ! -f "$project_root/frontend/dist/index.html" ]; then
    echo "Build the frontend first: cd frontend && npm ci && npm run build" >&2
    exit 1
fi
exec "$python_path" "$project_root/main.py" "$@"
