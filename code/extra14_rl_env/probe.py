"""用 oracle agent 跑不同的 solve.sh，检查 verifier 会不会判错。

用法：python3 probe.py <任务目录> [探针目录]，探针目录默认是 probes/
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent


def expectation(name):
    if name == "oracle" or name.startswith("variant"):
        return "== 1", lambda r: r == 1.0
    if name == "nop" or name.startswith("shortcut"):
        return "== 0", lambda r: r == 0.0
    return "< 1", lambda r: r < 1.0


def run_trial(task_dir, agent, solve_script=None):
    with tempfile.TemporaryDirectory() as tmp:
        task = Path(tmp) / task_dir.name
        shutil.copytree(task_dir, task)
        if solve_script:
            shutil.copy(solve_script, task / "solution" / "solve.sh")
        jobs = Path(tmp) / "jobs"
        subprocess.run(
            ["harbor", "run", "-p", str(task), "-a", agent, "-o", str(jobs), "-y", "-q"],
            capture_output=True,
        )
        rewards = list(jobs.glob("*/*/verifier/reward.txt"))
        return float(rewards[0].read_text()) if rewards else None


def main(task_dir, probe_dir=HERE / "probes"):
    probes = [("oracle", "oracle", None), ("nop", "nop", None)]
    probes += [(p.stem, "oracle", p) for p in sorted(Path(probe_dir).glob("*.sh"))]
    print(f"{'probe':<24}{'expect':<8}{'reward':<8}result")
    failures = 0
    for name, agent, script in probes:
        reward = run_trial(task_dir, agent, script)
        rule, ok = expectation(name)
        good = reward is not None and ok(reward)
        failures += not good
        shown = "error" if reward is None else f"{reward:.2f}"
        print(f"{name:<24}{rule:<8}{shown:<8}{'ok' if good else 'WRONG'}")
    print(f"\n{failures} probe(s) judged wrongly")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), *sys.argv[2:3]))
