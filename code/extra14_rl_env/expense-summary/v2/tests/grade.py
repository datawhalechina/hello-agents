import csv
import os
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation


SCRIPT = "/app/summarize.py"
TASK_INPUT = "/tests/task_input.csv"
TEST_INPUT = "/tests/input.csv"
SUMMARY = "/app/summary.csv"
FILTERED = "/app/over_500.csv"
DETAIL_HEADER = ["日期", "姓名", "类别", "金额"]
SUMMARY_HEADER = ["姓名", "报销总额"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream))


def fail(message):
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as reward:
        reward.write("0\n")
    print(message)
    raise SystemExit(0)


def expected_rows(source):
    if not source or source[0] != DETAIL_HEADER:
        raise ValueError("invalid verifier input")
    totals = {}
    order = []
    filtered = []
    for row in source[1:]:
        if len(row) != 4:
            raise ValueError("invalid verifier input")
        _, name, _, raw_amount = row
        amount = Decimal(raw_amount)
        if name not in totals:
            totals[name] = Decimal("0")
            order.append(name)
        totals[name] += amount
        if amount > Decimal("500"):
            filtered.append(row)
    summary = [SUMMARY_HEADER]
    summary.extend([[name, f"{totals[name]:.2f}"] for name in order])
    return summary, [DETAIL_HEADER, *filtered]


def check_outputs(input_path, summary_path, filtered_path):
    source = read_csv(input_path)
    summary, filtered = expected_rows(source)
    if read_csv(summary_path) != summary or read_csv(filtered_path) != filtered:
        return False
    return True


def main():
    try:
        if not os.path.isfile(SCRIPT):
            fail("Required summary program is missing.")
        if not check_outputs(TASK_INPUT, SUMMARY, FILTERED):
            fail("Outputs for the provided CSV do not match the task requirements.")

        test_source = read_csv(TEST_INPUT)
        expected_rows(test_source)
        with tempfile.TemporaryDirectory(prefix="expense-summary-") as temp_dir:
            summary_path = os.path.join(temp_dir, "summary.csv")
            filtered_path = os.path.join(temp_dir, "over_500.csv")
            try:
                subprocess.run(
                    [sys.executable, SCRIPT, TEST_INPUT, summary_path, filtered_path],
                    check=True,
                    timeout=20,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.SubprocessError):
                fail("Summary program could not process the verifier CSV.")
            if not check_outputs(TEST_INPUT, summary_path, filtered_path):
                fail("Summary program output does not meet the task requirements.")
    except (OSError, csv.Error, InvalidOperation, ValueError, KeyError):
        fail("Required CSV files are missing, unreadable, or invalid.")

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as reward:
        reward.write("1\n")
    print("Outputs meet the task requirements.")


if __name__ == "__main__":
    main()
