"""仅限本机的服务控制；随机令牌验证实例，避免按端口误停其他程序。"""

import hmac
import json
import os
import secrets
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "server.json"


def control(state, action):
    request = Request(
        f"http://127.0.0.1:{int(state['port'])}/api/_local/{action}",
        headers={"X-OfferNote-Control": state["token"]},
        method="POST" if action == "stop" else "GET",
        data=b"" if action == "stop" else None,
    )
    with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
        return json.load(response)


def read_runtime():
    try:
        return json.loads(RUNTIME.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def release(state):
    if read_runtime() == state:
        RUNTIME.unlink(missing_ok=True)


def stop():
    state = read_runtime()
    if state is None:
        print("OfferNote is already stopped.")
        return
    try:
        control(state, "stop")
    except URLError as exc:
        # HTTP 拒绝代表端口上可能是其他服务，保留文件供排查。
        from urllib.error import HTTPError

        if isinstance(exc, HTTPError):
            raise RuntimeError(
                "The local instance rejected the stop request."
            ) from None
        if time.time() - RUNTIME.stat().st_mtime < 10:
            raise RuntimeError(
                "OfferNote may still be starting. Retry in a few seconds."
            ) from None
        release(state)
        print("OfferNote is not reachable; stale runtime metadata removed.")
        return
    for _ in range(100):
        try:
            control(state, "status")
        except URLError:
            print("OfferNote stopped.")
            return
        time.sleep(0.1)
    raise RuntimeError(
        "OfferNote is shutting down; active requests may still be finishing."
    )


def attach(app, server, port):
    from fastapi import HTTPException, Request as FastAPIRequest

    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    previous = read_runtime()
    if previous is not None:
        try:
            control(previous, "status")
        except URLError:
            if time.time() - RUNTIME.stat().st_mtime < 10:
                raise RuntimeError(
                    "OfferNote is starting or recently stopped. Retry in a few seconds."
                ) from None
            release(previous)
        else:
            raise RuntimeError(
                "OfferNote is already running. Stop it before starting again."
            )
    state = {"port": port, "token": secrets.token_urlsafe(32)}
    descriptor = os.open(RUNTIME, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(state, handle)

    def authorize(request):
        if (
            request.headers.get("origin")
            or request.client.host not in ("127.0.0.1", "::1")
            or not hmac.compare_digest(
                request.headers.get("x-offernote-control", ""), state["token"]
            )
        ):
            raise HTTPException(403, "Local control token required.")

    @app.get("/api/_local/status", include_in_schema=False)
    def status(request: FastAPIRequest):
        authorize(request)
        return {"status": "running"}

    @app.post("/api/_local/stop", include_in_schema=False)
    def shutdown(request: FastAPIRequest):
        authorize(request)
        server.should_exit = True
        return {"status": "stopping"}

    # 控制接口必须位于前端 StaticFiles('/') 兜底路由之前。
    control_routes = app.router.routes[-2:]
    app.router.routes[-2:] = []
    app.router.routes[0:0] = control_routes
    return state
