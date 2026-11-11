#!/bin/bash
# 另一种正确写法：用 float 和 csv.reader，应当满分
cat > /app/summarize.py <<'PY'
import csv
import sys

src, summary_path, over_path = sys.argv[1:4]
with open(src, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))
header, records = rows[0], rows[1:]

totals = {}
for date, name, category, amount in records:
    totals[name] = totals.get(name, 0.0) + float(amount)

with open(summary_path, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["姓名", "报销总额"])
    for name, total in totals.items():
        w.writerow([name, f"{total:.2f}"])

with open(over_path, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(r for r in records if float(r[3]) > 500)
PY
python3 /app/summarize.py /app/input.csv /app/summary.csv /app/over_500.csv
