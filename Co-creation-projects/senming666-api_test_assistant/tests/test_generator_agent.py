"""GeneratorAgent 纯逻辑部分（prompt 构造 / 响应解析）的单元测试

注意：这里只测不依赖 LLM 的方法，用 object.__new__ 跳过 __init__，
避免真正创建 HelloAgentsLLM 实例。
"""
from src.agents.generator_agent import GeneratorAgent


def _gen():
    # 不调用 __init__（__init__ 会创建 LLM 实例并读 .env），只测纯函数
    return object.__new__(GeneratorAgent)


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
    prompt = _gen()._build_prompt(ep)
    assert "/users" in prompt
    assert "GET" in prompt
