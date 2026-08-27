"""ExecutorAgent 路径参数替换与 URL 拼接的单元测试"""
from src.agents.executor_agent import ExecutorAgent


def _executor():
    return ExecutorAgent()


# --- _replace_path_params ---

def test_replace_path_params_basic():
    path, params = _executor()._replace_path_params("/status/{codes}", {"codes": "200"})
    assert path == "/status/200"
    assert params == {}


def test_replace_path_params_keeps_query_params():
    path, params = _executor()._replace_path_params("/users/{id}", {"id": 1, "page": 2})
    assert path == "/users/1"
    assert params == {"page": 2}


def test_replace_path_params_missing_value_keeps_placeholder():
    # error 用例缺少参数时，占位符应保留原样
    path, params = _executor()._replace_path_params("/status/{codes}", {})
    assert path == "/status/{codes}"
    assert params == {}


def test_replace_path_params_multiple():
    path, _ = _executor()._replace_path_params("/x/{a}/y/{b}", {"a": 1, "b": 2})
    assert path == "/x/1/y/2"


# --- execute_one：URL 拼接 ---

def test_execute_one_url_join_and_param_removal():
    class FakeClient:
        def request(self, method, url, headers=None, params=None, body=None):
            return {"method": method, "url": url, "params": params, "body": body}

    ex = _executor()
    ex.http_client = FakeClient()
    case = {"path": "/status/{codes}", "method": "GET", "params": {"codes": "200"}}

    out = ex.execute_one(case, "https://httpbin.org/")

    assert out["case"] is case
    assert out["result"]["url"] == "https://httpbin.org/status/200"
    assert out["result"]["params"] == {}
    assert out["result"]["method"] == "GET"
