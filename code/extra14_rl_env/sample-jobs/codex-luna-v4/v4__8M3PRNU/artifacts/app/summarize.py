#!/usr/bin/env python3
"""Summarize reimbursement records and write records over 500 yuan."""

import csv
import sys
from decimal import Decimal


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: python summarize.py INPUT_CSV SUMMARY_CSV OVER_500_CSV"
        )

    input_path, summary_path, over_500_path = sys.argv[1:]
    totals = {}
    over_500_rows = []

    with open(input_path, "r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        expected = ["日期", "姓名", "类别", "金额"]
        if reader.fieldnames != expected:
            raise ValueError(f"CSV columns must be {expected!r}")

        for row in reader:
            name = row["姓名"]
            amount = Decimal(row["金额"])
            if name not in totals:
                totals[name] = Decimal("0")
            totals[name] += amount
            if amount > Decimal("500"):
                over_500_rows.append(row)

    with open(summary_path, "w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["姓名", "报销总额"])
        for name, total in totals.items():
            writer.writerow([name, f"{total:.2f}"])

    with open(over_500_path, "w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["日期", "姓名", "类别", "金额"])
        writer.writeheader()
        writer.writerows(over_500_rows)


if __name__ == "__main__":
    main()
