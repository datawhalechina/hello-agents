"""Pytest bootstrap for the backend test suite."""

import sys
from pathlib import Path

# Allow tests to import the src package regardless of the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
