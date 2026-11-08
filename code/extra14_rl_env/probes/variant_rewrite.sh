#!/bin/bash
# 另一种正确写法：应当满分
cat > /app/stats.py <<'PY'
import csv
import json
import sys
from collections import defaultdict

SIGN = {"order": 1, "refund": -1}

totals = defaultdict(float)
with open(sys.argv[1], newline="") as f:
    for row in csv.DictReader(f):
        totals[row["user"]] += SIGN[row["type"]] * float(row["amount"])
print(json.dumps(totals))
PY
