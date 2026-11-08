#!/bin/bash
set -e
python3 - <<'PY'
from pathlib import Path

p = Path("/app/stats.py")
src = p.read_text()
old = 'amount = float(row["amount"])\n'
new = old + '            if row["type"] == "refund":\n                amount = -amount\n'
assert old in src
p.write_text(src.replace(old, new))
PY
