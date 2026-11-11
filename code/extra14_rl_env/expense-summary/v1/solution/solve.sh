#!/bin/sh
set -eu
python - <<'PY'
import csv
from collections import OrderedDict
from decimal import Decimal

with open("/app/input.csv", encoding="utf-8-sig", newline="") as source:
    rows = list(csv.DictReader(source))

totals = OrderedDict()
for row in rows:
    totals[row["姓名"]] = totals.get(row["姓名"], Decimal("0")) + Decimal(row["金额"])

with open("/app/summary.csv", "w", encoding="utf-8", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(["姓名", "报销总额"])
    for name, total in totals.items():
        writer.writerow([name, f"{total:.2f}"])

with open("/app/over_500.csv", "w", encoding="utf-8", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(["日期", "姓名", "类别", "金额"])
    for row in rows:
        if Decimal(row["金额"]) > Decimal("500"):
            writer.writerow([row["日期"], row["姓名"], row["类别"], row["金额"]])
PY
