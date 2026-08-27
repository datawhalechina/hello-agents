"""HttpClient 工具层的单元测试"""
from unittest.mock import Mock, patch

import pytest

from src.tools.http_client import HttpClient


# --- _parse_body ---

def test_parse_body_json():
    resp = Mock()
    resp.json.return_value = {"a": 1}
    assert HttpClient()._parse_body(resp) == {"a": 1}


def test_parse_body_fallback_to_text():
    resp = Mock()
    resp.json.side_effect = ValueError("not json")
    resp.text = "plain text"
    assert HttpClient()._parse_body(resp) == "plain text"


# --- _error_result ---

def test_error_result_shape():
    r = HttpClient()._error_result("boom")
    assert r == {"success": False, "status_code": None, "body": None, "elapsed": 0.0, "error": "boom"}


# --- request ---

def test_request_unsupported_method():
    r = HttpClient().request("TRACE", "http://x")
    assert r["success"] is False
    assert "不支持" in r["error"]


def test_request_success():
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {"ok": True}

    with patch("requests.request", return_value=resp):
        r = HttpClient(max_retries=0).request("GET", "http://x")

    assert r["success"] is True
    assert r["status_code"] == 200
    assert r["body"] == {"ok": True}


def test_request_retry_then_success(monkeypatch):
    import requests.exceptions

    # 去掉重试之间的 1 秒 sleep，加快测试
    monkeypatch.setattr("src.tools.http_client.time.sleep", lambda s: None)

    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {}

    with patch(
        "requests.request",
        side_effect=[requests.exceptions.ConnectionError("网络断开"), resp],
    ):
        r = HttpClient(max_retries=1).request("GET", "http://x")

    assert r["success"] is True
    assert r["status_code"] == 200
