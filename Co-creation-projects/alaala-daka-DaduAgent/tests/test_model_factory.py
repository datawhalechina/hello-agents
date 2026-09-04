"""
模型工厂测试
===========
验证 create_chatmodel / create_ragmodel 按 Model_Config 的 active 模型构建：
base_url 非空 → ChatOpenAI（任意 OpenAI 协议端点）；
base_url 为空 → ChatDeepSeek（内置 DeepSeek + 环境变量）。

辅助模型（embedding / reranker）：
base_url 非空 → OpenAI 兼容端点（OpenAIEmbeddings / _HTTPReranker）；
base_url 为空 → DashScope 内置（DashScopeEmbeddings / _DashScopeReranker）。
"""
import pytest
from types import SimpleNamespace

import httpx
import dashscope
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

import factory.model_generator as mg
from api.models import _mask


@pytest.fixture
def custom_model_config(monkeypatch):
    """把 Model_Config 指向一个含自定义 OpenAI 协议模型的注册表"""
    cfg = {
        "active_model": "custom",
        "models": [
            {
                "name": "custom",
                "label": "Custom",
                "base_url": "http://127.0.0.1:9000/v1",
                "api_key": "sk-test-1234",
                "model": "gpt-4o-mini",
            },
            {
                "name": "default",
                "label": "DeepSeek",
                "base_url": "",
                "api_key": "",
                "model": "deepseek-v4-pro",
            },
        ],
    }
    monkeypatch.setattr(mg, "Model_Config", cfg)
    return cfg


def test_create_chatmodel_uses_custom_base_url(custom_model_config):
    cm = mg.create_chatmodel()
    assert isinstance(cm, ChatOpenAI)
    assert cm.model_name == "gpt-4o-mini"
    # base_url 是 openai_api_base 的 alias（必须用 base_url= 传参才会生效）
    assert cm.openai_api_base == "http://127.0.0.1:9000/v1"
    assert cm.openai_api_key.get_secret_value() == "sk-test-1234"


def test_create_chatmodel_uses_deepseek_when_no_base_url(monkeypatch):
    cfg = {
        "active_model": "default",
        "models": [
            {
                "name": "default",
                "label": "DeepSeek",
                "base_url": "",
                "api_key": "",
                "model": "deepseek-v4-pro",
            }
        ],
    }
    monkeypatch.setattr(mg, "Model_Config", cfg)
    cm = mg.create_chatmodel()
    assert isinstance(cm, ChatDeepSeek)
    assert cm.model_name == "deepseek-v4-pro"


def test_create_chatmodel_model_name_override(custom_model_config):
    cm = mg.create_chatmodel(model_name="deepseek-chat")
    assert cm.model_name == "deepseek-chat"


def test_create_ragmodel_uses_active_model(custom_model_config):
    rm = mg.create_ragmodel()
    assert isinstance(rm, ChatOpenAI)
    assert rm.model_name == "gpt-4o-mini"
    assert rm.openai_api_base == "http://127.0.0.1:9000/v1"


def test_active_missing_falls_back_to_first(custom_model_config):
    custom_model_config["active_model"] = "not-exist"
    cm = mg.create_chatmodel()
    assert cm.model_name == "gpt-4o-mini"


def test_mask():
    assert _mask("") == ""
    assert _mask("abc12345") == "****"           # 短 key
    assert _mask("sk-abcdefghijkl1234") == "sk****1234"   # 长 key 保留首2尾4


# ── 辅助模型：embedding / reranker 双模式 ──

@pytest.fixture
def aux_config(monkeypatch):
    """含 embedding / reranker 辅助块的配置（自定义 OpenAI 兼容端点）"""
    cfg = {
        "active_model": "custom",
        "models": [
            {
                "name": "custom",
                "label": "Custom",
                "base_url": "http://127.0.0.1:9000/v1",
                "api_key": "sk-test-1234",
                "model": "gpt-4o-mini",
            }
        ],
        "embedding": {
            "label": "Custom Embedding",
            "base_url": "http://127.0.0.1:9000/v1",
            "api_key": "sk-embed-1234",
            "model": "bge-m3",
        },
        "reranker": {
            "label": "Custom Reranker",
            "base_url": "https://api.jina.ai/v1",
            "api_key": "sk-rerank-1234",
            "model": "jina-reranker-v2-base-multilingual",
        },
    }
    monkeypatch.setattr(mg, "Model_Config", cfg)
    return cfg


def test_create_embeddingmodel_uses_openai_endpoint(aux_config):
    emb = mg.create_embeddingmodel()
    assert isinstance(emb, OpenAIEmbeddings)
    assert emb.model == "bge-m3"
    # base_url 是 openai_api_base 的 alias（必须用 base_url= 传参才会生效）
    assert emb.openai_api_base == "http://127.0.0.1:9000/v1"
    assert emb.openai_api_key.get_secret_value() == "sk-embed-1234"


def test_create_embeddingmodel_uses_dashscope_when_no_base_url(aux_config):
    aux_config["embedding"]["base_url"] = ""
    emb = mg.create_embeddingmodel()
    assert isinstance(emb, DashScopeEmbeddings)
    assert emb.model == "bge-m3"


def test_create_rerankmodel_uses_http_when_base_url(aux_config):
    r = mg.create_rerankmodel()
    assert isinstance(r, mg._HTTPReranker)
    assert r.base_url == "https://api.jina.ai/v1"
    assert r.model == "jina-reranker-v2-base-multilingual"
    assert r.api_key == "sk-rerank-1234"


def test_create_rerankmodel_uses_dashscope_when_no_base_url(aux_config):
    aux_config["reranker"]["base_url"] = ""
    r = mg.create_rerankmodel()
    assert isinstance(r, mg._DashScopeReranker)
    assert r.model == "jina-reranker-v2-base-multilingual"


def test_aux_entry_falls_back_to_env(monkeypatch):
    """Model_Config 无 aux 块时回退 .env（EMBEDDING_MODEL / EMBEDDING_API_KEY）"""
    monkeypatch.setattr(mg, "Model_Config", {"active_model": "default", "models": []})
    monkeypatch.setenv("EMBEDDING_MODEL", "env-embed")
    monkeypatch.setenv("EMBEDDING_API_KEY", "sk-env")
    emb = mg._embedding_entry()
    assert emb["model"] == "env-embed"
    assert emb["api_key"] == "sk-env"
    assert emb["base_url"] == ""   # env BASE_URL 未设 → 空 = 内置 DashScope 模式


def test_http_reranker_normalizes_results(monkeypatch):
    """_HTTPReranker：POST {base_url}/rerank，结果按 results 顺序取 document 文本"""
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, json=json, headers=headers)

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "results": [
                        {"index": 2, "relevance_score": 0.9, "document": {"text": "docC"}},
                        {"index": 0, "relevance_score": 0.8},   # 无 document → 回退 documents[index]
                    ]
                }

        return FakeResp()

    monkeypatch.setattr(httpx, "post", fake_post)
    r = mg._HTTPReranker(base_url="https://api.jina.ai/v1", api_key="sk-x", model="jina-reranker-v2")
    out = r.rerank("q", ["docA", "docB", "docC"], top_n=5)
    assert captured["url"] == "https://api.jina.ai/v1/rerank"
    assert captured["json"]["model"] == "jina-reranker-v2"
    assert captured["json"]["documents"] == ["docA", "docB", "docC"]
    assert captured["headers"]["Authorization"] == "Bearer sk-x"
    assert out == ["docC", "docA"]


def test_dashscope_reranker_normalizes_results(monkeypatch):
    """_DashScopeReranker：TextReRank.call 结果按 output.results 取 document 文本"""
    captured = {}

    class FakeResp:
        status_code = 200
        code = 200
        message = "ok"
        output = SimpleNamespace(
            results=[
                SimpleNamespace(index=1, document={"text": "docB"}),
                SimpleNamespace(index=0, document=None),
            ]
        )

    def fake_call(**kwargs):
        captured.update(kwargs)
        return FakeResp()

    monkeypatch.setattr(dashscope, "TextReRank", SimpleNamespace(call=fake_call))
    r = mg._DashScopeReranker(model="gte-rerank-v2", api_key="")
    out = r.rerank("q", ["docA", "docB"], top_n=5)
    assert captured["model"] == "gte-rerank-v2"
    assert captured["top_n"] == 5
    assert out == ["docB", "docA"]
