#!/usr/bin/env bash
# Build a standalone executable for macOS / Linux.
# Requires: python3 + pip.  Output: dist/coding-assistant (project root)
# Usage:  scripts/build_exe.sh   (or from project root:  bash scripts/build_exe.sh)
set -euo pipefail
# Switch to the project root (one level up from this script)
cd "$(dirname "$0")/.."

echo "[1/3] Installing build tools..."
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

echo "[2/3] Installing project dependencies..."
python3 -m pip install -r requirements.txt

echo "[3/3] Building executable..."
python3 -m PyInstaller --noconfirm --clean --onefile --console \
    --name coding-assistant \
    --collect-all coding_assistant \
    coding_assistant/__main__.py

echo "Done! Executable is at: dist/coding-assistant"
