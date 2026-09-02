import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from tool.config_handler import  Chroma_Config,Agent_Config,Rag_Config,Model_Config
from tool.logger_handler import logger
from abc import ABC,abstractmethod

class BaseModelGenerator(ABC):
    @abstractmethod
    def modelgenerator(self):
        pass


def _active_model_entry() -> dict | None:
    """返回 Model_Config 注册表中 active_model 指向的模型项；取不到则回退第一项"""
    active = Model_Config.get("active_model")
    models = Model_Config.get("models") or []
    for m in models:
        if m.get("name") == active:
            return m
    return models[0] if models else None


def _build_chat(model_name: str, base_url: str, api_key: str):
    """按配置构建聊天模型实例。

    base_url 非空 → 任意 OpenAI 兼容端点（ChatOpenAI，可配 url + apikey + 模型名）；
    base_url 为空   → 内置 DeepSeek 路径（ChatDeepSeek 走环境变量 DEEPSEEK_API_KEY）。
    注意：必须用 base_url= 参数，api_base= 是 Pydantic alias 之外的名字，不会生效。
    """
    model_name = model_name or "deepseek-v4-pro"
    base_url = (base_url or "").strip()
    api_key = (api_key or "").strip()
    if base_url:
        # 本地端点（如 Ollama）可能不需要 key → 传占位符避免构造失败
        return ChatOpenAI(model=model_name, base_url=base_url, api_key=api_key or "not-needed")
    return ChatDeepSeek(model=model_name)


# ── 辅助模型（Embedding / Reranker）默认值与入口解析 ──
_EMBEDDING_DEFAULTS = {"label": "DashScope Embedding（默认）", "model": "text-embedding-v4"}
_RERANKER_DEFAULTS = {"label": "DashScope Reranker（默认）", "model": "gte-rerank-v2"}


def _aux_entry(block_key: str, env_prefix: str, defaults: dict) -> dict:
    """读取 Model_Config 中的辅助模型块（embedding/reranker）。

    优先级：YAML 块值 > .env > 内置默认。
    块存在时：base_url 空 = 内置 DashScope 模式（不回退 env BASE_URL）；
    api_key 空回退 {env_prefix}_API_KEY（DashScope 模式最终由 SDK 兜底 DASHSCOPE_API_KEY）。
    """
    block = Model_Config.get(block_key)
    if isinstance(block, dict):
        return {
            "label": (block.get("label") or "").strip() or defaults["label"],
            "model": (block.get("model") or "").strip()
            or os.environ.get(f"{env_prefix}_MODEL")
            or defaults["model"],
            "base_url": (block.get("base_url") or "").strip(),
            "api_key": (block.get("api_key") or os.environ.get(f"{env_prefix}_API_KEY") or "").strip(),
        }
    return {
        "label": defaults["label"],
        "model": os.environ.get(f"{env_prefix}_MODEL") or defaults["model"],
        "base_url": (os.environ.get(f"{env_prefix}_BASE_URL") or "").strip(),
        "api_key": (os.environ.get(f"{env_prefix}_API_KEY") or "").strip(),
    }


def _embedding_entry() -> dict:
    return _aux_entry("embedding", "EMBEDDING", _EMBEDDING_DEFAULTS)


def _reranker_entry() -> dict:
    return _aux_entry("reranker", "RERANKER", _RERANKER_DEFAULTS)


class EmbeddingModelGenerator(BaseModelGenerator):
    def modelgenerator(self):
        return create_embeddingmodel()

class ChatModelGenerator(BaseModelGenerator):
    def modelgenerator(self):
        return create_chatmodel()

class RagSummarizeModelGenerator(BaseModelGenerator):
    def modelgenerator(self):
        return create_ragmodel()


def create_chatmodel(model_name: str | None = None):
    """工厂函数：按 Model_Config 当前 active 模型构建主对话模型（每次读取最新配置）。
    不替换模块级单例，仅用于按需创建。
    """
    entry = _active_model_entry()
    name = model_name or (
        entry.get("model") if entry else Agent_Config.get("chat_model_name", "deepseek-v4-pro")
    )
    return _build_chat(
        name,
        entry.get("base_url", "") if entry else "",
        entry.get("api_key", "") if entry else "",
    )


def create_ragmodel():
    """工厂函数：按 Model_Config 当前 active 模型构建 RAG 总结/切分模型"""
    entry = _active_model_entry()
    name = (
        entry.get("model") if entry
        else Rag_Config.get("rag_summarize_model_name", "deepseek-v4-flash")
    )
    return _build_chat(
        name,
        entry.get("base_url", "") if entry else "",
        entry.get("api_key", "") if entry else "",
    )


class _DashScopeReranker:
    """DashScope TextReRank 重排器（base_url 为空时的内置路径；key 空 → SDK 读 DASHSCOPE_API_KEY）"""

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key or None

    def rerank(self, query: str, documents: list[str], top_n: int = 5) -> list[str]:
        from http import HTTPStatus

        from dashscope import TextReRank

        resp = TextReRank.call(
            model=self.model,
            query=query,
            documents=documents,
            top_n=top_n,
            return_documents=True,
            api_key=self.api_key,
        )
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope rerank 失败: {resp.code} {resp.message}")
        ordered = []
        for r in resp.output.results:
            text = r.document.get("text") if isinstance(r.document, dict) else None
            ordered.append(text if text else documents[r.index])
        return ordered


class _HTTPReranker:
    """OpenAI 兼容 /rerank 重排器（如 Jina）。POST {base_url}/rerank，Bearer 鉴权"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "not-needed"
        self.model = model

    def rerank(self, query: str, documents: list[str], top_n: int = 5) -> list[str]:
        import httpx

        resp = httpx.post(
            f"{self.base_url}/rerank",
            json={
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
                "return_documents": True,
            },
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        ordered = []
        for r in data.get("results", []):
            text = (r.get("document") or {}).get("text") if isinstance(r.get("document"), dict) else None
            ordered.append(text if text else documents[r["index"]])
        return ordered


def create_rerankmodel():
    """工厂函数：按 Model_Config 的 reranker 块构建重排器。

    base_url 非空 → OpenAI 兼容 /rerank 端点（_HTTPReranker）；
    base_url 为空   → DashScope TextReRank 内置（_DashScopeReranker）。
    """
    entry = _reranker_entry()
    base_url = entry["base_url"].strip()
    model = entry["model"] or "gte-rerank-v2"
    if base_url:
        return _HTTPReranker(base_url=base_url, api_key=entry["api_key"], model=model)
    return _DashScopeReranker(model=model, api_key=entry["api_key"])


def create_embeddingmodel():
    """工厂函数：按 Model_Config 的 embedding 块构建向量化模型。

    base_url 非空 → OpenAI 兼容 /embeddings（OpenAIEmbeddings，base_url 为 Pydantic alias）；
    base_url 为空   → DashScope 内置（DashScopeEmbeddings，key 空 → SDK 读 DASHSCOPE_API_KEY）。
    """
    entry = _embedding_entry()
    base_url = entry["base_url"].strip()
    model = entry["model"] or "text-embedding-v4"
    if base_url:
        return OpenAIEmbeddings(model=model, base_url=base_url, api_key=entry["api_key"] or "not-needed")
    return DashScopeEmbeddings(model=model, dashscope_api_key=entry["api_key"] or None)


ragsummarizemodel=RagSummarizeModelGenerator().modelgenerator()
chatmodel=ChatModelGenerator().modelgenerator()
embeddingmodel=EmbeddingModelGenerator().modelgenerator()
rerankermodel=create_rerankmodel()


def get_model_info() -> dict:
    """返回当前 Agent 使用的模型信息（含辅助模型 embedding / reranker）"""
    entry = _active_model_entry()
    name = entry.get("model") if entry else Agent_Config.get("chat_model_name", "deepseek-v4-pro")
    base_url = (entry.get("base_url", "") if entry else "") or "env:DEEPSEEK_API_KEY"
    emb, rrk = _embedding_entry(), _reranker_entry()
    return {
        "chat_model": name,
        "provider": "ChatOpenAI" if (entry and (entry.get("base_url") or "").strip()) else "ChatDeepSeek",
        "base_url": base_url,
        "rag_model": name,
        "embedding_model": emb["model"],
        "embedding_base_url": emb["base_url"] or "env:DASHSCOPE_API_KEY",
        "reranker_model": rrk["model"],
        "reranker_base_url": rrk["base_url"] or "env:DASHSCOPE_API_KEY",
    }


def rebuild_singletons() -> None:
    """配置变更后重建全部模型单例，并重绑消费方模块的 import 别名。

    永远新建对象再重绑名字，绝不修改旧对象——进行中的 WebSocket 持有自己的
    agent 局部引用，其流与保存不受影响。
    """
    global chatmodel, ragsummarizemodel, embeddingmodel, rerankermodel
    chatmodel = create_chatmodel()
    ragsummarizemodel = create_ragmodel()
    embeddingmodel = create_embeddingmodel()
    rerankermodel = create_rerankmodel()

    # 1) Agent 模块在 import 时绑定的是 mg.chatmodel → 必须同步重绑，
    #    否则 Agent.__init__ 与 _generate_title 读到的还是旧模型。
    import Agent as agent_mod
    agent_mod.chatmodel = chatmodel

    # 2) RAG 服务：重建单例并同步 agent_tools 的 import 别名。
    #    较重（重开 Chroma），失败不阻断切换。
    #    同时重绑反思库 _reflection_chroma——它使用与知识库相同的 embedding。
    try:
        import vector_uploader_service.rag_summarize as rs
        rs.ragsummarizemodel = ragsummarizemodel
        rs.Rag_Summarize = rs._Rag_Summarize()
        import agent_tools.agent_tools as at
        at.Rag_Summarize = rs.Rag_Summarize
        at._reflection_chroma = at._build_reflection_chroma()
    except Exception as e:
        logger.warning(f"[model] RAG 服务重建失败: {e}")

    # 3) file_uploader 单例重建（api/files.py 每次上传新建 File_Uploader，此项可选）
    try:
        import vector_uploader_service.file_uploader as fu
        fu._file_upload_service = fu.File_Uploader()
    except Exception as e:
        logger.warning(f"[model] file_uploader 重建失败: {e}")


def apply_model_change() -> dict:
    """模型配置变更后的完整生效流程：重读配置 → 重建单例 → 驱逐 Agent 缓存。

    调用方（api/models.py）负责先持久化 ModelConfig.yml。
    """
    from tool.config_handler import reload_model_config
    reload_model_config()
    rebuild_singletons()
    from api.chat import evict_all_agents_for_model_change
    evict_all_agents_for_model_change()
    return get_model_info()


def apply_aux_model_change() -> dict:
    """Embedding / Reranker 配置变更后的生效流程：重读配置 → 重建单例（含 RAG / 反思库 / 上传器）。

    与 apply_model_change 不同：不驱逐 Agent 缓存——辅助模型不影响对话主模型，
    正在进行的对话无需重建 agent。
    """
    from tool.config_handler import reload_model_config
    reload_model_config()
    rebuild_singletons()
    return get_model_info()
