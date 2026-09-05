"""混合搜索工具：向量 + BM25 混合检索"""
from __future__ import annotations

from backend.tools.base import Tool


async def hybrid_search(query: str, top_k: int = 5) -> dict:
    """混合检索向量库，返回相关段落。

    复用 build_vector_index 模块的 HybridSearcher 单例，
    保证索引写入与检索读取共享同一实例。

    Returns:
        {"query": query, "results": [{text, paper_path, title, section, score}]}
    """
    # 复用 build_vector_index 的单例，确保索引数据可被检索
    from backend.tools.build_vector_index import _get_searcher

    searcher = _get_searcher()
    results = await searcher.async_search(query, top_k=top_k)
    return {"query": query, "results": results}


# ---------- Tool 定义 ----------

_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "检索查询文本",
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量，默认 5",
            "default": 5,
        },
    },
    "required": ["query"],
}

hybrid_search_tool = Tool(
    name="hybrid_search",
    description=(
        "混合搜索（向量相似度 + BM25 关键词）论文向量库，返回相关段落。"
        "用于回溯原文细节。返回 {query, results: [{text, paper_path, title, section, score}]}。"
    ),
    parameters=_PARAMETERS,
    func=hybrid_search,
)
