"""ParserAgent 解析 OpenAPI 文档的单元测试"""
import json
from pathlib import Path

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


def test_extract_endpoints_request_body_and_content_type():
    doc = {
        "paths": {
            "/create": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {"name": {"type": "string"}},
                                }
                            }
                        }
                    },
                    "responses": {"200": {}},
                }
            }
        }
    }
    endpoints = _parser().extract_endpoints(doc)
    assert len(endpoints) == 1
    ep = endpoints[0]
    assert ep["method"] == "POST"
    # 请求体被解析成真正的 schema，而不是原始 requestBody 对象
    assert ep["request_body"] == {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    }
    assert ep["request_content_type"] == "application/json"


# --- $ref 展开 ---

def _ref_doc():
    """一个带 components/schemas 和 $ref 的最小文档"""
    return {
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                    },
                },
                "Nested": {
                    "type": "object",
                    "properties": {"user": {"$ref": "#/components/schemas/User"}},
                },
            }
        },
        "paths": {
            "/register": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"},
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Nested"},
                                }
                            }
                        }
                    },
                }
            }
        },
    }


def test_request_body_ref_resolved():
    endpoints = _parser().extract_endpoints(_ref_doc())
    ep = endpoints[0]
    # $ref 被展开，字段直接可见
    assert ep["request_body"]["required"] == ["username", "password"]
    assert "username" in ep["request_body"]["properties"]


def test_response_schema_ref_resolved():
    endpoints = _parser().extract_endpoints(_ref_doc())
    ep = endpoints[0]
    # 主成功响应（201）的 schema 被展开，且嵌套 $ref 也递归展开
    assert ep["response_schema"]["properties"]["user"]["type"] == "object"
    assert "username" in ep["response_schema"]["properties"]["user"]["properties"]


def test_get_response_schema_by_status():
    endpoints = _parser().extract_endpoints(_ref_doc())
    ep = endpoints[0]
    assert _parser().get_response_schema(ep, 201)["properties"]["user"]["type"] == "object"
    # 没有声明的状态码返回 None
    assert _parser().get_response_schema(ep, 404) is None


# --- get_expected_status ---

def test_expected_status_normal_prefers_2xx():
    ep = {"responses": {"200": {}, "400": {}}}
    assert _parser().get_expected_status(ep, "normal") == 200


def test_expected_status_boundary_prefers_2xx():
    ep = {"responses": {"201": {}, "422": {}}}
    assert _parser().get_expected_status(ep, "boundary") == 201


def test_expected_status_error_prefers_4xx():
    ep = {"responses": {"200": {}, "400": {}}}
    assert _parser().get_expected_status(ep, "error") == 400


def test_expected_status_error_with_body_validation():
    # 有必填请求体字段 → 缺字段 → 校验失败 422
    ep = {
        "responses": {"201": {}, "422": {}},
        "request_body": {"required": ["name"], "properties": {"name": {"type": "string"}}},
        "parameters": [],
    }
    assert _parser().get_expected_status(ep, "error") == 422


def test_expected_status_error_with_only_path_param():
    # 只有必填路径参数 → 缺路径参数 → 路由不匹配 404（而非 422）
    ep = {
        "responses": {"200": {}, "422": {}},
        "request_body": None,
        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
    }
    assert _parser().get_expected_status(ep, "error") == 404


def test_expected_status_default_200_when_no_responses():
    assert _parser().get_expected_status({"responses": {}}, "normal") == 200


# --- 结构判断辅助 ---

def test_has_testable_inputs():
    # 没参数没请求体 → 无可测输入
    assert _parser().has_testable_inputs({"parameters": [], "request_body": None}) is False
    # 有请求体 → 可测
    assert _parser().has_testable_inputs({"parameters": [], "request_body": {"type": "object"}}) is True
    # 有 query 参数 → 可测
    assert _parser().has_testable_inputs(
        {"parameters": [{"in": "query", "name": "limit"}], "request_body": None}
    ) is True


def test_has_validation_input():
    assert _parser().has_validation_input(
        {"parameters": [], "request_body": {"required": ["name"]}}
    ) is True
    assert _parser().has_validation_input({"parameters": [], "request_body": None}) is False


def test_has_required_path_param():
    assert _parser().has_required_path_param(
        {"parameters": [{"in": "path", "name": "id", "required": True}]}
    ) is True
    assert _parser().has_required_path_param(
        {"parameters": [{"in": "query", "name": "limit"}]}
    ) is False


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


# --- 真实 Chat openapi.json 集成解析 ---

def _chat_endpoints():
    fixture = Path(__file__).parent / "fixtures" / "chat_openapi.json"
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    return _parser().extract_endpoints(doc)


def test_chat_register_body_ref_resolved():
    ep = next(e for e in _chat_endpoints() if e["path"] == "/api/auth/register")
    # 注册请求体应能看到真实字段，而不是 $ref 字符串
    assert ep["request_body"]["required"] == [
        "username", "display_name", "password", "confirm_password"
    ]
    assert set(ep["request_body"]["properties"]) == {
        "username", "display_name", "password", "confirm_password"
    }


def test_chat_login_response_schema_resolved():
    ep = next(e for e in _chat_endpoints() if e["path"] == "/api/auth/login")
    # 登录成功响应的 schema 展开后应包含 access_token 字段
    assert "access_token" in ep["response_schema"]["properties"]


def test_chat_health_has_no_testable_inputs():
    ep = next(e for e in _chat_endpoints() if e["path"] == "/api/health")
    assert _parser().has_testable_inputs(ep) is False
    assert _parser().has_validation_input(ep) is False
    assert _parser().has_required_path_param(ep) is False


def test_chat_files_images_is_multipart():
    ep = next(e for e in _chat_endpoints() if e["path"] == "/api/files/images")
    assert ep["request_content_type"] == "multipart/form-data"
    # 文件字段用 contentMediaType 标识
    assert "contentMediaType" in ep["request_body"]["properties"]["file"]
