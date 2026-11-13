"""Bounded test/build execution with process-tree cancellation."""
from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path


def test_command(argv: list[str]) -> list[str]:
    if not argv or len(argv) > 30 or any(len(arg) > 1000 for arg in argv):
        raise ValueError("测试命令无效。")
    executable = Path(argv[0]).name.lower()
    if executable in {"python", "python3", "python.exe"}:
        if len(argv) < 3 or argv[1] != "-m" or argv[2] not in {"pytest", "unittest", "compileall"}:
            raise ValueError("Python 测试仅支持 -m pytest、unittest 或 compileall。")
        return [sys.executable, "-E", *argv[1:]]
    if executable in {"pytest", "pytest.exe"}:
        return [sys.executable, "-E", "-m", "pytest", *argv[1:]]
    if executable in {"npm", "npm.cmd"}:
        if len(argv) < 2 or not (argv[1] == "test" or (len(argv) >= 3 and argv[1] == "run" and argv[2] in {"test", "build", "lint", "typecheck"})):
            raise ValueError("npm 仅支持 test、run test/build/lint/typecheck。")
        # Launch npm-cli.js through Node, never through cmd.exe or shell=True.
        node, npm = shutil.which("node"), shutil.which("npm")
        candidates = [Path(npm).parent / "node_modules/npm/bin/npm-cli.js"] if npm else []
        if os.getenv("APPDATA"):
            candidates.append(Path(os.environ["APPDATA"]) / "npm/node_modules/npm/bin/npm-cli.js")
        cli = next((path for path in candidates if path.is_file()), None)
        if not node or not cli:
            raise ValueError("找不到 Node.js 的 npm-cli.js，请检查 Node.js 安装。")
        return [node, str(cli), *argv[1:]]
    raise ValueError("当前只支持 Python 和 npm 的测试、构建命令。")


async def stop_process(process):
    if process.returncode is not None:
        return
    if os.name == "nt":
        killer = await asyncio.create_subprocess_exec("taskkill", "/PID", str(process.pid), "/T", "/F", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await killer.wait()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    await process.wait()


async def run_command(argv: list[str], cwd: Path, emit, timeout: int = 90) -> dict:
    actual = test_command(argv)
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONHOME", "PYTHONPATH", "LLM_API_KEY", "OPENAI_API_KEY", "CODE_ASSISTANT_TOKEN"}}
    env["PYTHONIOENCODING"] = "utf-8"
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = await asyncio.create_subprocess_exec(*actual, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **options)
    chunks, total, truncated = [], 0, False
    try:
        async with asyncio.timeout(timeout):
            while chunk := await process.stdout.read(4096):
                text = chunk.decode("utf-8", errors="replace")
                if total < 200_000:
                    text = text[:200_000-total]
                    total += len(text)
                    chunks.append(text)
                    await emit("command.output", {"text": text})
                else:
                    truncated = True
            await process.wait()
    except TimeoutError:
        await stop_process(process)
        await emit("command.output", {"text": "\n命令超时，已停止进程树。\n"})
        return {"argv": argv, "exit_code": None, "timed_out": True, "output": "".join(chunks)}
    except BaseException:
        await stop_process(process)
        raise
    return {"argv": argv, "exit_code": process.returncode, "timed_out": False, "truncated": truncated, "output": "".join(chunks)}
