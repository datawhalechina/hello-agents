#!/usr/bin/env python3
import csv
import sys
from collections import OrderedDict
from decimal import Decimal


INPUT_HEADER = ["日期", "姓名", "类别", "金额"]
SUMMARY_HEADER = ["姓名", "报销总额"]


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: summarize.py INPUT_CSV SUMMARY_CSV OVER_500_CSV")

    input_path, summary_path, filtered_path = sys.argv[1:]
    with open(input_path, encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != INPUT_HEADER:
            raise ValueError("unexpected input columns")
        rows = list(reader)

    totals = OrderedDict()
    for row in rows:
        name = row["姓名"]
        totals[name] = totals.get(name, Decimal("0")) + Decimal(row["金额"])

    with open(summary_path, "w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(SUMMARY_HEADER)
        for name, total in totals.items():
            writer.writerow([name, f"{total:.2f}"])

    with open(filtered_path, "w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(INPUT_HEADER)
        for row in rows:
            if Decimal(row["金额"]) > Decimal("500"):
                writer.writerow([row[column] for column in INPUT_HEADER])


if __name__ == "__main__":
    main()
