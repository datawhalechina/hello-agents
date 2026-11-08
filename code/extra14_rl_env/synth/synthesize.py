"""从种子批量生成 Harbor 任务，再逐个过门禁。

真实流水线里，“设计任务”和“写任务包”通常由 LLM 完成。这里用模板代替，
不需要 API key，重点放在门禁：坏任务必须被拦住。

用法：python3 synth/synthesize.py synth/seeds.json
"""
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from probe import run_trial  # noqa: E402

OUT = HERE / "generated"
REQUIRED = ["instruction.md", "task.toml", "environment/Dockerfile", "solution/solve.sh", "tests/test.sh"]

TOML = """schema_version = "1.4"
artifacts = ["/app/stats.py"]

[task]
name = "hello-agents/stats-{id}"
version = "1.0.0"

[verifier]
timeout_sec = 60.0
environment_mode = "separate"

[agent]
timeout_sec = 300.0

[environment]
build_timeout_sec = 300.0
cpus = 1
memory_mb = 1024
storage_mb = 2048
"""
DOCKERFILE = "FROM python:3.12-slim\nWORKDIR /app\nCOPY stats.py orders.csv /app/\n"
STATS = """import csv
import json
import sys

MULTIPLIERS = {{"order": 1, "{event}": {multiplier}}}

totals = {{}}
with open(sys.argv[1], newline="") as f:
    for row in csv.DictReader(f):
        amount = float(row["amount"]) * MULTIPLIERS[row["type"]]
        totals[row["user"]] = totals.get(row["user"], 0) + amount
print(json.dumps(totals, sort_keys=True))
"""
INSTRUCTION = """`/app/stats.py` 读取一份订单 CSV，按用户统计消费总额，并把结果以 JSON 打印到标准输出。

用法：`python3 /app/stats.py <csv路径>`。CSV 的表头是 `user,type,amount`，示例数据在 `/app/orders.csv`。

`type` 为 `{event}` 的行表示{meaning}。现在统计结果不对，请修复 `/app/stats.py`。
"""
CHECK = """import json
import math
import subprocess
import sys

cases = json.load(open("/tests/cases.json"))
passed = 0
for case in cases:
    try:
        out = subprocess.run(
            [sys.executable, "-I", "/app/stats.py", f"/tests/{case['csv']}"],
            capture_output=True, text=True, timeout=10, cwd="/tmp",
        )
        actual = json.loads(out.stdout)
        ok = set(actual) == set(case["expected"]) and all(
            math.isclose(actual[k], v, abs_tol=1e-6) for k, v in case["expected"].items()
        )
    except Exception:
        ok = False
    print(f"{case['csv']}: {'PASS' if ok else 'FAIL'}")
    passed += ok
open("/logs/verifier/reward.txt", "w").write(str(passed / len(cases)))
"""


def make_rows(rng, event):
    rows = []
    for user in rng.sample(["ann", "ben", "cai", "dan", "eve"], 2):
        rows.append((user, "order", rng.randint(20, 200)))
        rows.append((user, event, rng.randint(1, 19)))
    return rows


def gold(rows, event, multiplier):
    totals = {}
    for user, kind, amount in rows:
        totals[user] = totals.get(user, 0) + amount * (multiplier if kind == event else 1)
    return totals


def to_csv(rows):
    return "user,type,amount\n" + "".join(f"{u},{k},{a}\n" for u, k, a in rows)


def render_task(seed):
    """把种子渲染成任务目录。答案由程序算出，而不是由作者手写。"""
    event, multiplier = seed["event"], seed["multiplier"]
    rng = random.Random(seed["id"])
    task = OUT / seed["id"]
    shutil.rmtree(task, ignore_errors=True)
    for sub in ("environment", "solution", "tests"):
        (task / sub).mkdir(parents=True)

    public_rows = make_rows(rng, event)
    (task / "task.toml").write_text(TOML.format(id=seed["id"]))
    (task / "instruction.md").write_text(INSTRUCTION.format(event=event, meaning=seed["meaning"]))
    (task / "environment/Dockerfile").write_text(DOCKERFILE)
    (task / "environment/orders.csv").write_text(to_csv(public_rows))
    # 待修复的脚本把新事件当普通订单处理
    (task / "environment/stats.py").write_text(STATS.format(event=event, multiplier=1))

    fixed = STATS.format(event=event, multiplier=seed.get("solution_multiplier", multiplier))
    (task / "solution/solve.sh").write_text(f"#!/bin/bash\ncat > /app/stats.py <<'PY'\n{fixed}PY\n")
    (task / "solution/solve.sh").chmod(0o755)

    cases = []
    for i in range(3):
        rows = make_rows(rng, event)
        (task / f"tests/case{i}.csv").write_text(to_csv(rows))
        cases.append({"csv": f"case{i}.csv", "expected": gold(rows, event, multiplier)})
    (task / "tests/cases.json").write_text(json.dumps(cases))
    (task / "tests/check.py").write_text(CHECK)
    (task / "tests/test.sh").write_text("#!/bin/bash\npython3 /tests/check.py\n")
    (task / "tests/test.sh").chmod(0o755)
    return task, gold(public_rows, event, multiplier), cases


def static_gate(task, cases):
    if not all((task / f).exists() for f in REQUIRED):
        return False
    # 隐藏用例的答案不能出现在 agent 看得到的文件里
    public = (task / "instruction.md").read_text() + (task / "environment/orders.csv").read_text()
    answers = {str(v) for case in cases for v in case["expected"].values()}
    return not any(answer in public for answer in answers)


def shortcut_reward(task, public_answer):
    """取巧探针：直接打印示例数据的正确答案。"""
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "solve.sh"
        script.write_text(
            f"#!/bin/bash\ncat > /app/stats.py <<'PY'\nprint({json.dumps(json.dumps(public_answer))})\nPY\n"
        )
        return run_trial(task, "oracle", script)


def gate(seed, seen):
    """返回 (各门禁的展示值, 结论)。前一道没过，后面就不再跑。"""
    row = {"static": "-", "dedup": "-", "oracle": "-", "nop": "-", "shortcut": "-"}
    task, public_answer, cases = render_task(seed)

    row["static"] = "ok" if static_gate(task, cases) else "FAIL"
    if row["static"] == "FAIL":
        return row, "reject: leak or missing file"

    # 按决定任务的东西去重：换个说法、行为相同，仍然算同一道题
    key = seed["multiplier"]
    row["dedup"] = "dup" if key in seen else "ok"
    if key in seen:
        return row, f"reject: same behavior as {seen[key]}"
    seen[key] = seed["id"]

    oracle = run_trial(task, "oracle")
    row["oracle"] = "error" if oracle is None else f"{oracle:.2f}"
    if oracle != 1.0:
        return row, "reject: reference solution fails"

    nop = run_trial(task, "nop")
    row["nop"] = "error" if nop is None else f"{nop:.2f}"
    if nop != 0.0:
        return row, "reject: doing nothing scores"

    shortcut = shortcut_reward(task, public_answer)
    row["shortcut"] = "error" if shortcut is None else f"{shortcut:.2f}"
    if shortcut != 0.0:
        return row, "reject: hardcoded answer scores"
    return row, "accept"


def main(seed_file):
    seeds = json.loads(Path(seed_file).read_text())
    seen = {}
    print(f"{'seed':<14}{'static':<8}{'dedup':<7}{'oracle':<8}{'nop':<6}{'shortcut':<10}decision")
    for seed in seeds:
        row, decision = gate(seed, seen)
        print(
            f"{seed['id']:<14}{row['static']:<8}{row['dedup']:<7}{row['oracle']:<8}"
            f"{row['nop']:<6}{row['shortcut']:<10}{decision}"
        )


if __name__ == "__main__":
    main(sys.argv[1])
