"""
前端 UI 冒烟测试：驱动 Edge 打开设置面板，验证模型设置组件真实渲染。
前置：后端已在 8001 运行，frontend/dist 已构建。
用法：uv run python tests/ui_smoke.py
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CDP = "http://127.0.0.1:9222"
PROFILE = os.path.join(ROOT, ".edge_cdp_profile")


async def main() -> int:
    proc = subprocess.Popen(
        [EDGE, "--headless=new", "--disable-gpu",
         f"--user-data-dir={PROFILE}",
         "--remote-debugging-port=9222", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        import websockets

        page = None
        for _ in range(40):
            try:
                with urllib.request.urlopen(CDP + "/json", timeout=3) as r:
                    pages = json.loads(r.read())
                page = next((p for p in pages if p.get("type") == "page"), None)
                if page:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.25)
        if not page:
            print("FAIL  无法连接 Edge CDP")
            return 1

        ws_url = page["webSocketDebuggerUrl"]
        js_errors: list = []
        pending: dict = {}

        async with websockets.connect(ws_url, max_size=2 ** 24) as ws:
            async def recv_loop():
                while True:
                    try:
                        raw = await ws.recv()
                    except Exception:
                        return
                    msg = json.loads(raw)
                    if msg.get("id") in pending:
                        pending[msg["id"]].set_result(msg.get("result", {}))
                    elif msg.get("method") == "Runtime.exceptionThrown":
                        js_errors.append(msg)

            recv_task = asyncio.get_event_loop().create_task(recv_loop())

            async def cmd(method, params=None):
                fut = asyncio.get_event_loop().create_future()
                cid = len(pending) + 1
                pending[cid] = fut
                await ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
                return await fut

            async def ev(expr):
                res = await cmd("Runtime.evaluate",
                                {"expression": expr, "returnByValue": True})
                return res.get("result", {}).get("value")

            await cmd("Runtime.enable")
            await cmd("Page.enable")
            await cmd("Page.navigate", {"url": "http://localhost:8001"})
            await asyncio.sleep(6)

            results = []
            def check(name, cond, detail=""):
                results.append((name, bool(cond), detail))
                print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")

            title = await ev("document.title")
            check("页面标题", title == "Dadu Agent-Personalized Agent", title)

            clicked = await ev("""
                (() => {
                  const btn = [...document.querySelectorAll('button')].find(
                    b => b.textContent.includes('设置与工具'));
                  if (!btn) return false;
                  btn.click(); return true;
                })()
            """)
            check("打开设置面板", bool(clicked), "")
            await asyncio.sleep(1.5)

            text = await ev("document.body.innerText") or ""
            check("模型设置区渲染",
                  "模型设置" in text and "添加模型" in text and "DeepSeek（默认）" in text,
                  f"add={'添加模型' in text} default={'DeepSeek（默认）' in text}")

            form_open = await ev("""
                (() => {
                  const btn = [...document.querySelectorAll('button')].find(
                    b => b.textContent.includes('添加模型'));
                  if (!btn) return false;
                  btn.click(); return true;
                })()
            """)
            await asyncio.sleep(0.8)
            text2 = await ev("document.body.innerText") or ""
            check("添加模型表单展开",
                  bool(form_open) and "API 地址 (base_url)" in text2 and "API Key" in text2 and "模型名 (model)" in text2,
                  "")

            # ── 反思笔记面板冒烟（只读，不写库）──
            ref_clicked = await ev("""
                (() => {
                  const btn = [...document.querySelectorAll('button')].find(
                    b => b.textContent.includes('反思笔记'));
                  if (!btn) return false;
                  btn.click(); return true;
                })()
            """)
            check("打开反思笔记区", bool(ref_clicked), "")
            await asyncio.sleep(1.5)

            text3 = await ev("document.body.innerText") or ""
            check("反思笔记区渲染",
                  "反思笔记" in text3 and "新增笔记" in text3,
                  f"add={'新增笔记' in text3}")
            check("反思严重程度筛选渲染",
                  "全部 (" in text3 and "致命 (" in text3 and "严重 (" in text3,
                  f"all={'全部 (' in text3} fatal={'致命 (' in text3} high={'严重 (' in text3}")

            ref_form = await ev("""
                (() => {
                  const btn = [...document.querySelectorAll('button')].find(
                    b => b.textContent.includes('新增笔记'));
                  if (!btn) return false;
                  btn.click(); return true;
                })()
            """)
            await asyncio.sleep(0.8)
            text4 = await ev("document.body.innerText") or ""
            check("新增笔记表单展开",
                  bool(ref_form) and "错误描述" in text4 and "实时预览" in text4 and "严重程度" in text4,
                  "")

            await asyncio.sleep(0.5)
            check("无 JS 异常", len(js_errors) == 0, f"exceptions={len(js_errors)}")

            recv_task.cancel()
            return 0 if all(ok for _, ok, _ in results) else 1
    finally:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        except Exception:
            pass
        shutil.rmtree(PROFILE, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
