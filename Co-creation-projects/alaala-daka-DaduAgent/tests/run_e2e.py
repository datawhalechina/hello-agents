"""
端到端验证：自定义 OpenAI 协议模型链路
====================================
启动 mock OpenAI 服务器(9000) + 真实后端(8001)，
验证：添加模型 → 切换 active → api_key 掩码 → WS 对话走自定义模型 → 文件切分走同一模型。

用法：uv run python tests/run_e2e.py
（需保证 8001 / 9000 端口空闲；结束后自动清理测试模型并终止进程）
"""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
BASE = "http://127.0.0.1:8001/api"
MOCK_LOG = os.path.join(ROOT, "tests", "mock_log.jsonl")
CFG = os.path.join(ROOT, "config", "ModelConfig.yml")

procs = []


def start(cmd, out):
    f = open(out, "w", encoding="utf-8")
    p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    procs.append(p)
    return p


def http(method, path, payload=None):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def wait_healthy(timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st, _ = http("GET", "/health")
            if st == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    backup = None
    if os.path.exists(CFG):
        with open(CFG, encoding="utf-8") as f:
            backup = f.read()
    if os.path.exists(MOCK_LOG):
        os.remove(MOCK_LOG)

    results = []
    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")

    try:
        start(["uv", "run", "uvicorn", "tests.mock_openai:app",
               "--host", "127.0.0.1", "--port", "9000"], "tests/e2e_mock.out")
        start(["uv", "run", "uvicorn", "server:app",
               "--host", "127.0.0.1", "--port", "8001"], "tests/e2e_server.out")
        check("后端健康检查", wait_healthy(), "")

        st, body = http("POST", "/models", {
            "name": "e2e-mock", "label": "E2E Mock",
            "base_url": "http://127.0.0.1:9000/v1",
            "api_key": "sk-e2e-test", "model": "e2e-model",
        })
        check("添加模型", st == 200 and body.get("created") == "e2e-mock", str(body))

        st, body = http("PUT", "/models/active", {"name": "e2e-mock"})
        check("切换 active", st == 200 and body.get("active") == "e2e-mock", str(body)[:140])

        st, body = http("GET", "/models")
        api_key_field = next(
            (m.get("api_key") for m in body.get("models", []) if m.get("name") == "e2e-mock"), None)
        check("api_key 掩码返回", api_key_field == "sk****test", f"got={api_key_field!r}")

        async def ws_chat():
            import websockets
            async with websockets.connect("ws://127.0.0.1:8001/ws/chat/e2e_test_session") as ws:
                await ws.recv()  # session_info
                await ws.send(json.dumps({"type": "chat", "content": "你好，测试一下自定义模型"}))
                chunks = []
                while True:
                    msg = json.loads(await ws.recv())
                    t = msg.get("type")
                    if t == "chunk":
                        chunks.append(msg.get("content", ""))
                    elif t in ("done", "error", "interrupted"):
                        break
                return "".join(chunks)
        try:
            reply = asyncio.run(ws_chat())
            check("WS 对话走自定义模型", "e2e-model" in reply, reply[:200])
        except Exception as e:
            check("WS 对话走自定义模型", False, str(e)[:200])

        log_lines = []
        if os.path.exists(MOCK_LOG):
            with open(MOCK_LOG, encoding="utf-8") as f:
                log_lines = [json.loads(l) for l in f if l.strip()]
        models_hit = {e.get("model") for e in log_lines}
        check("mock 收到 chat 请求", "e2e-model" in models_hit, f"hit={models_hit}")

        from vector_uploader_service.file_uploader import File_Uploader
        try:
            fu = File_Uploader()
            res = fu.chain.invoke({"input": "这是一段用于测试切分模型是否跟随 active 配置的文本。"})
            check("文件切分模型走自定义模型", "e2e-model" in res, res[:120])
        except Exception as e:
            check("文件切分模型走自定义模型", False, str(e)[:200])

        st, body = http("DELETE", "/models/e2e-mock")
        check("删除测试模型并回退 active", st == 200, str(body))
    finally:
        # uv run 会拉起进程树；terminate() 只杀 uv 包装进程，需 taskkill /T 杀整棵
        for p in procs:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    capture_output=True, timeout=10,
                )
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        time.sleep(1.0)
        if backup is not None:
            with open(CFG, "w", encoding="utf-8") as f:
                f.write(backup)
        # 清理 e2e 会话文件
        for name in ("e2e_test_session.jsonl", "e2e_test_session.meta.json"):
            p = os.path.join(ROOT, "sessions", name)
            if os.path.exists(p):
                os.remove(p)

    print("\n=== 结果汇总 ===")
    for name, ok, _ in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
