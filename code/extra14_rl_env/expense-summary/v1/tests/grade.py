import csv
import os
from collections import OrderedDict
from decimal import Decimal, InvalidOperation


INPUT = "/tests/input.csv"
SUMMARY = "/app/summary.csv"
FILTERED = "/app/over_500.csv"
SUMMARY_HEADER = ["姓名", "报销总额"]
DETAIL_HEADER = ["日期", "姓名", "类别", "金额"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream))


def fail(message):
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as reward:
        reward.write("0\n")
    print(message)
    raise SystemExit(0)


def main():
    try:
        source = read_csv(INPUT)
        summary = read_csv(SUMMARY)
        filtered = read_csv(FILTERED)
    except (OSError, csv.Error):
        fail("Required CSV output is missing or unreadable.")

    if not source or source[0] != DETAIL_HEADER:
        fail("Verifier input is invalid.")
    if summary[:1] != [SUMMARY_HEADER]:
        fail("Summary CSV header is incorrect.")
    if filtered[:1] != [DETAIL_HEADER]:
        fail("Filtered CSV header is incorrect.")

    totals = OrderedDict()
    expected_filtered = []
    try:
        for row in source[1:]:
            if len(row) != 4:
                fail("Verifier input is invalid.")
            date, name, category, raw_amount = row
            amount = Decimal(raw_amount)
            totals[name] = totals.get(name, Decimal("0")) + amount
            if amount > Decimal("500"):
                expected_filtered.append(row)
    except InvalidOperation:
        fail("Verifier input is invalid.")

    expected_summary = [SUMMARY_HEADER]
    expected_summary.extend([[name, f"{total:.2f}"] for name, total in totals.items()])
    if summary != expected_summary:
        fail("Summary CSV does not match the required per-person totals.")
    if filtered != [DETAIL_HEADER, *expected_filtered]:
        fail("Filtered CSV does not match the required records.")

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as reward:
        reward.write("1\n")
    print("Outputs meet the task requirements.")


if __name__ == "__main__":
    main()
