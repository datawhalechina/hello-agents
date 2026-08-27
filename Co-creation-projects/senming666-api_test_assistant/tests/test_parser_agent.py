"""ParserAgent 解析 OpenAPI 文档的单元测试"""
from src.agents.parser_agent import ParserAgent


def _parser():
    return ParserAgent()


# --- parse_text：空输入 / JSON / YAML / 非 dict ---

def test_parse_text_empty():
    assert _parser().parse_text("") == []
    assert _parser().parse_text("   ") == []


def test_parse_text_json():
    doc = '{"openapi": "3.0.0", "paths": {"/users": {"get": {"summary": "list", "responses": {"200": {"description": "ok"}}}}}}'
    endpoints = _parser().parse_text(doc)
    assert len(endpoints) == 1
    assert endpoints[0]["path"] == "/users"
    assert endpoints[0]["method"] == "GET"


def test_parse_text_yaml():
    doc = """
openapi: 3.0.0
paths:
  /users:
    get:
      summary: list users
      responses:
        '200':
          description: ok
"""
    endpoints = _parser().parse_text(doc)
    assert len(endpoints) == 1
    assert endpoints[0]["method"] == "GET"


def test_parse_text_non_dict():
    # "null" 会被解析成 None，应返回空列表而不是崩溃
    assert _parser().parse_text("null") == []


# --- extract_endpoints：类型容错 + requestBody ---

def test_extract_endpoints_non_dict_input():
    p = _parser()
    assert p.extract_endpoints(None) == []
    assert p.extract_endpoints("not a dict") == []
    assert p.extract_endpoints([]) == []


def test_extract_endpoints_request_body():
    doc = {
        "paths": {
            "/create": {
                "post": {
                    "requestBody": {"required": True},
                    "responses": {"200": {}},
                }
            }
        }
    }
    endpoints = _parser().extract_endpoints(doc)
    assert len(endpoints) == 1
    assert endpoints[0]["method"] == "POST"
    assert endpoints[0]["request_body"] == {"required": True}


# --- get_expected_status ---

def test_expected_status_normal_prefers_2xx():
    ep = {"responses": {"200": {}, "400": {}}}
    assert _parser().get_expected_status(ep, "normal") == 200


def test_expected_status_error_prefers_4xx():
    ep = {"responses": {"200": {}, "400": {}}}
    assert _parser().get_expected_status(ep, "error") == 400


def test_expected_status_default_200_when_no_responses():
    assert _parser().get_expected_status({"responses": {}}, "normal") == 200


# --- parse_file ---

def test_parse_file(tmp_path):
    f = tmp_path / "api.yaml"
    f.write_text(
        "openapi: 3.0.0\npaths:\n  /a:\n    get:\n      responses:\n        '200': {}\n",
        encoding="utf-8",
    )
    endpoints = _parser().parse_file(str(f))
    assert len(endpoints) == 1
    assert endpoints[0]["path"] == "/a"
