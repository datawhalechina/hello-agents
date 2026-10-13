# -*- coding: utf-8 -*-
"""本地演示服务测试：页面生成、路由与参数校验。

在随机端口起一个真实的服务实例，用 HTTP 请求验证，不调用模型。
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import web_demo


@pytest.fixture(scope="module")
def base_url():
    """在随机空闲端口启动演示服务，测完关闭。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_demo.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


def http_get(url: str, timeout: int = 10) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def http_post(url: str, payload, timeout: int = 30) -> tuple[int, dict]:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body}


class Test页面:
    def test_首页可访问(self, base_url: str) -> None:
        status, body = http_get(base_url + "/")
        assert status == 200
        assert "售后政策应答的多范式实证对比" in body

    def test_占位符已全部替换(self, base_url: str) -> None:
        _, body = http_get(base_url + "/")
        assert "__RULE_COUNT__" not in body, "规则数占位符未被替换"
        assert "__SAMPLE__" not in body, "示例工单占位符未被替换"

    def test_页面含三个模式选项(self, base_url: str) -> None:
        _, body = http_get(base_url + "/")
        for label in ("无检索直答", "单跳检索", "多步自治"):
            assert label in body

    def test_页面含渲染函数(self, base_url: str) -> None:
        _, body = http_get(base_url + "/")
        assert "function mdToHtml" in body
        assert "function inline" in body

    def test_页面脚本转义未被破坏(self, base_url: str) -> None:
        """页面里的 JS 转义必须原样下发，否则脚本会语法错误、按钮点不动。"""
        _, body = http_get(base_url + "/")
        assert "split('\\n')" in body, "JS 的 \\n 被提前解释成了真实换行"

    def test_未知路径返回404(self, base_url: str) -> None:
        status, _ = http_get(base_url + "/nope")
        assert status == 404

    def test_图标请求不再返回404(self, base_url: str) -> None:
        """浏览器会自动请求图标，返回 204 可以避免控制台出现无意义的 404 噪音。"""
        status, _ = http_get(base_url + "/favicon.ico")
        assert status == 204


class Test接口:
    def test_空工单返回错误而不是崩溃(self, base_url: str) -> None:
        status, payload = http_post(base_url + "/api/run", {"ticket": "   ", "modes": ["A"]})
        assert status == 200
        assert "error" in payload

    def test_缺少工单字段返回错误(self, base_url: str) -> None:
        _, payload = http_post(base_url + "/api/run", {"modes": ["A"]})
        assert "error" in payload

    def test_非法JSON返回错误(self, base_url: str) -> None:
        _, payload = http_post(base_url + "/api/run", b"{not-json")
        assert "error" in payload

    def test_未知路径POST返回404(self, base_url: str) -> None:
        status, _ = http_post(base_url + "/api/nope", {"ticket": "x"})
        assert status == 404

    def test_模式全部非法时给出明确错误(self, base_url: str) -> None:
        """若静默返回空结果，页面会显示"完成：已生成 0 个结果"，用户看不出问题在哪。"""
        status, payload = http_post(base_url + "/api/run", {"ticket": "订单没发货", "modes": ["X", "Y"]})
        assert status == 200
        assert "error" in payload, f"应当明确报错，实际返回：{payload}"

    def test_模式字段类型异常时给出明确错误(self, base_url: str) -> None:
        _, payload = http_post(base_url + "/api/run", {"ticket": "订单没发货", "modes": "A"})
        assert "error" in payload, f"字符串形式的模式应当被拒绝，实际返回：{payload}"


class Test离线逻辑:
    def test_非法模式被忽略(self) -> None:
        assert web_demo.run_modes("随便一条工单", ["X", "Y"]) == []

    def test_空模式列表返回空(self) -> None:
        assert web_demo.run_modes("随便一条工单", []) == []

    def test_示例工单非空(self) -> None:
        assert web_demo.SAMPLE_TICKET.strip()
        assert "订单" in web_demo.SAMPLE_TICKET
