import csv
import os
import pwd
import stat
import shutil
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
REWARD_DIR = "/logs/verifier"
REWARD = os.path.join(REWARD_DIR, "reward.txt")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        return list(csv.reader(stream))


def fail(message):
    os.makedirs(REWARD_DIR, exist_ok=True)
    with open(REWARD, "w", encoding="utf-8") as reward:
        reward.write("0\n")
    print(message)
    raise SystemExit(0)


def drop_privileges(uid, gid):
    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)


def run_untrusted_script():
    if os.geteuid() != 0:
        raise RuntimeError("Verifier must run as root to isolate the submitted program.")

    nobody = pwd.getpwnam("nobody")
    with tempfile.TemporaryDirectory(prefix="expense-summary-") as temp_dir:
        os.chown(temp_dir, nobody.pw_uid, nobody.pw_gid)
        os.chmod(temp_dir, 0o700)
        staged_input = os.path.join(temp_dir, "input.csv")
        summary_path = os.path.join(temp_dir, "summary.csv")
        filtered_path = os.path.join(temp_dir, "over_500.csv")
        shutil.copyfile(TEST_INPUT, staged_input)
        os.chown(staged_input, nobody.pw_uid, nobody.pw_gid)
        os.chmod(staged_input, 0o400)
        subprocess.run(
            [sys.executable, SCRIPT, staged_input, summary_path, filtered_path],
            check=True,
            timeout=20,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=lambda: drop_privileges(nobody.pw_uid, nobody.pw_gid),
        )
        return read_csv(summary_path), read_csv(filtered_path)


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
    return outputs_match(summary_path, filtered_path, summary, filtered)


def outputs_match(summary_path, filtered_path, summary, filtered):
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
        expected_summary, expected_filtered = expected_rows(test_source)
        os.makedirs(REWARD_DIR, exist_ok=True)
        os.chmod(REWARD_DIR, 0o700)
        with open(REWARD, "w", encoding="utf-8") as reward:
            reward.write("0\n")
        os.chmod(REWARD, 0o600)

        original_mode = stat.S_IMODE(os.stat(TEST_INPUT).st_mode)
        os.chmod(TEST_INPUT, 0)
        try:
            try:
                actual_summary, actual_filtered = run_untrusted_script()
            except (OSError, subprocess.SubprocessError, RuntimeError):
                fail("Summary program could not process the verifier CSV.")
        finally:
            os.chmod(TEST_INPUT, original_mode)
        if (
            actual_summary != expected_summary
            or actual_filtered != expected_filtered
        ):
            fail("Summary program output does not meet the task requirements.")
    except (OSError, csv.Error, InvalidOperation, ValueError, KeyError):
        fail("Required CSV files are missing, unreadable, or invalid.")

    with open(REWARD, "w", encoding="utf-8") as reward:
        reward.write("1\n")
    print("Outputs meet the task requirements.")


if __name__ == "__main__":
    main()
