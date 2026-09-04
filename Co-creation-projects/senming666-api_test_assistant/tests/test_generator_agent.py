"""GeneratorAgent 纯逻辑部分（prompt 构造 / 响应解析 / 用例规范化）的单元测试

注意：这里只测不依赖 LLM 的方法，用 object.__new__ 跳过 __init__，
避免真正创建 HelloAgentsLLM 实例。
"""
from src.agents.generator_agent import GeneratorAgent
from src.agents.parser_agent import ParserAgent


def _gen():
    # 不调用 __init__（__init__ 会创建 LLM 实例并读 .env），只测纯函数
    g = object.__new__(GeneratorAgent)
    # _normalize_case/_decide_case_types 依赖 parser，手动补上
    g.parser = ParserAgent()
    return g


# --- _parse_response ---

def test_parse_response_clean_json():
    cases = _gen()._parse_response('[{"name": "a", "case_type": "normal"}]')
    assert isinstance(cases, list)
    assert len(cases) == 1
    assert cases[0]["name"] == "a"


def test_parse_response_with_markdown_fence():
    resp = '```json\n[{"name": "a", "case_type": "normal"}]\n```'
    cases = _gen()._parse_response(resp)
    assert len(cases) == 1
    assert cases[0]["name"] == "a"


def test_parse_response_with_extra_text():
    resp = '好的，以下是测试用例：\n[{"name": "a"}]\n希望有帮助'
    cases = _gen()._parse_response(resp)
    assert len(cases) == 1


def test_parse_response_invalid_json():
    assert _gen()._parse_response("没有 JSON 数组") == []


# --- _build_prompt ---

def test_build_prompt_contains_endpoint_fields():
    ep = {
        "path": "/users",
        "method": "GET",
        "parameters": [],
        "request_body": None,
        "responses": {"200": {}},
    }
    prompt = _gen()._build_prompt(ep, ["normal"])
    assert "/users" in prompt
    assert "GET" in prompt


# --- _decide_case_types ---

def test_decide_case_types_no_input_only_normal():
    ep = {"parameters": [], "request_body": None, "responses": {"200": {}}}
    assert _gen()._decide_case_types(ep) == ["normal"]


def test_decide_case_types_with_body():
    ep = {
        "parameters": [],
        "request_body": {"required": ["name"], "properties": {"name": {"type": "string"}}},
        "responses": {"201": {}, "422": {}},
    }
    # 有请求体 → 有 boundary（可测输入）和 error（必填字段）
    assert _gen()._decide_case_types(ep) == ["normal", "boundary", "error"]


def test_decide_case_types_path_param_only():
    ep = {
        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
        "request_body": None,
        "responses": {"200": {}, "422": {}},
    }
    # 只有路径参数 → 有 error（缺路径参数→404），但没有 boundary（路径参数不可取边界值）
    assert _gen()._decide_case_types(ep) == ["normal", "error"]


# --- _normalize_case ---

def test_normalize_case_overrides_llm_status_and_injects_schema():
    ep = {
        "path": "/register",
        "method": "POST",
        "parameters": [],
        "request_body": {"required": ["name"]},
        "request_content_type": "application/json",
        "responses": {
            "201": {
                "content": {
                    "application/json": {
                        "schema": {"type": "object", "properties": {"id": {"type": "integer"}}}
                    }
                }
            },
            "422": {},
        },
    }
    # LLM 把 expected_status 写错成 400，规范化后应被覆盖成文档的 201
    case = {"name": "注册", "case_type": "normal", "body": {"name": "x"}, "expected_status": 400}
    out = _gen()._normalize_case(case, ep)

    assert out["path"] == "/register"
    assert out["method"] == "POST"
    assert out["expected_status"] == 201
    # 期望响应 schema 被注入
    assert out["expected_schema"]["properties"]["id"]["type"] == "integer"
    assert out["content_type"] == "application/json"


def test_normalize_case_error_status():
    ep = {
        "path": "/x",
        "method": "POST",
        "parameters": [],
        "request_body": {"required": ["name"]},
        "request_content_type": "application/json",
        "responses": {"201": {}, "422": {}},
    }
    case = {"name": "缺字段", "case_type": "error", "body": {}, "expected_status": 500}
    out = _gen()._normalize_case(case, ep)
    assert out["expected_status"] == 422


def test_normalize_case_invalid_case_type_falls_back():
    ep = {
        "path": "/x", "method": "GET", "parameters": [], "request_body": None,
        "responses": {"200": {}},
    }
    case = {"name": "x", "case_type": "whatever", "body": "not dict"}
    out = _gen()._normalize_case(case, ep)
    assert out["case_type"] == "normal"
    # body 非 dict 被兜底成空 dict，避免后续 multipart 拆分报错
    assert out["body"] == {}


# --- _build_files ---

def test_build_files_extracts_file_field():
    ep = {
        "request_body": {
            "type": "object",
            "required": ["file"],
            "properties": {"file": {"type": "string", "contentMediaType": "application/octet-stream"}},
        }
    }
    body = {"file": "test_image.jpg"}  # LLM 给的任意文件名
    files = _gen()._build_files(ep, body)
    assert files is not None
    assert "file" in files
    filename, content, mime = files["file"]
    # 占位内容固定是 PNG，文件名强制 .png，避免扩展名和 MIME 不一致导致 415
    assert filename == "file.png"
    assert isinstance(content, bytes) and content  # 非空字节
    assert mime == "image/png"
    # 文件字段从 body 里弹出，body 不再含它
    assert "file" not in body


def test_build_files_no_file_field_returns_none():
    ep = {
        "request_body": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
    }
    body = {"name": "x"}
    assert _gen()._build_files(ep, body) is None
    assert body == {"name": "x"}
