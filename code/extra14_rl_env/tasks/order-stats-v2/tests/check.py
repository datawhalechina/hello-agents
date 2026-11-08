import json
import math
import subprocess
import sys

# 每条用例都含退款行，没修复的脚本一条也过不了，空解不会白拿分
CASES = {
    "refund_is_subtracted": ("basic.csv", {"dave": 170.0, "erin": 40.0}),
    "refund_only_user_goes_negative": ("refund_only.csv", {"frank": -25.0, "grace": 5.0}),
    "decimal_amounts": ("decimals.csv", {"heidi": 15.25}),
    "refund_before_order": ("refund_first.csv", {"ivan": 90.0}),
}


def run_candidate(csv_path):
    # -I 让候选代码目录里的同名模块无法劫持解释器
    out = subprocess.run(
        [sys.executable, "-I", "/app/stats.py", csv_path],
        capture_output=True,
        text=True,
        timeout=10,
        cwd="/tmp",
    )
    return json.loads(out.stdout)


def matches(actual, expected):
    if set(actual) != set(expected):
        return False
    return all(math.isclose(actual[k], expected[k], abs_tol=1e-6) for k in expected)


passed = 0
for name, (filename, expected) in CASES.items():
    try:
        ok = matches(run_candidate(f"/tests/cases/{filename}"), expected)
    except Exception:
        ok = False
    # 日志只写通过与否，不写期望值
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
    passed += ok

with open("/logs/verifier/reward.txt", "w") as f:
    f.write(str(passed / len(CASES)))
