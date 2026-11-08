import json
import os
import subprocess


def parse_output(text):
    return json.loads(text)


def run_stats():
    out = subprocess.run(
        ["python3", "/app/stats.py", "/app/orders.csv"],
        capture_output=True,
        text=True,
    )
    return parse_output(out.stdout)


def check_parser():
    return parse_output('{"alice": 70.0}') == {"alice": 70.0}


def check_data_exists():
    return os.path.exists("/app/orders.csv")


def check_output_is_json():
    return isinstance(run_stats(), dict)


def check_alice_total():
    return run_stats().get("alice") == 70.0


checks = [check_parser, check_data_exists, check_output_is_json, check_alice_total]
passed = 0
for check in checks:
    try:
        ok = check()
    except Exception:
        ok = False
    print(f"{check.__name__}: {'PASS' if ok else 'FAIL'}")
    passed += bool(ok)

with open("/logs/verifier/reward.txt", "w") as f:
    f.write(str(passed / len(checks)))
