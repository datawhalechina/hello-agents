"""对 Agent 生成的任务跑门禁：静态检查、参考解、空解。

用法：python3 synth/gate.py <任务目录>
有没通过的检查时，会打印细节，可以存成文件交给 run_agent.sh 修改。
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def last_error(output):
    """从 Harbor 的报错栈里取出最后一条 XxxError: ... 信息。"""
    text = re.sub(r"[│╭╮╰╯─]", " ", output)
    text = re.sub(r"ExceptionGroup: unhandled errors in a TaskGroup \(\d+ sub-exceptions?\)", " ", text)
    text = " ".join(text.split())
    errors = re.findall(r"\b\w+(?:Error|Exception): .*?(?=\s\w+(?:Error|Exception): |$)", text)
    errors = [e for e in errors if not e.startswith("ExceptionGroup")]
    return errors[-1][:500] if errors else text[-500:]


def run_trial(task, agent):
    """跑一次 trial，返回 (reward, 输出)。拿不到 reward 时，输出是 Harbor 的报错。"""
    with tempfile.TemporaryDirectory() as tmp:
        jobs = Path(tmp) / "jobs"
        proc = subprocess.run(
            ["harbor", "run", "-p", str(task), "-a", agent, "-o", str(jobs), "-y", "-q"],
            capture_output=True,
            text=True,
        )
        rewards = list(jobs.glob("*/*/verifier/reward.txt"))
        if not rewards:
            return None, last_error(proc.stdout + proc.stderr)
        stdout = list(jobs.glob("*/*/verifier/test-stdout.txt"))
        return float(rewards[0].read_text()), stdout[0].read_text() if stdout else ""


def main(task_dir):
    task = Path(task_dir).resolve()
    rows, details = [], []

    lint = subprocess.run(["harbor", "lint", str(task)], capture_output=True, text=True)
    ok = lint.returncode == 0
    rows.append(("lint", "no error", "ok" if ok else "error", ok))
    if not ok:
        details.append("harbor lint 输出：\n" + (lint.stdout + lint.stderr).strip())

    for agent, rule, check in (("oracle", "== 1", lambda r: r == 1.0), ("nop", "== 0", lambda r: r == 0.0)):
        reward, stdout = run_trial(task, agent)
        if reward is None:
            # 没拿到 reward 是运行出错，不是任务本身没通过，要先排查环境
            rows.append((agent, rule, "infra", False))
            details.append(f"{agent} 没有拿到 reward，Harbor 输出：\n{stdout}")
            continue
        ok = check(reward)
        rows.append((agent, rule, f"{reward:.2f}", ok))
        if not ok:
            details.append(f"{agent} 得分 {reward:.2f}，判分脚本输出：\n{stdout.strip()}")

    print(f"{'gate':<8}{'expect':<10}{'result':<8}status")
    for name, rule, shown, ok in rows:
        print(f"{name:<8}{rule:<10}{shown:<8}{'ok' if ok else 'FAIL'}")
    for d in details:
        print("\n" + d)
    return 0 if all(r[3] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
