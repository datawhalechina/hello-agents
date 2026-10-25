"""金标评估：对比 BM25 / 向量(两模型) / 混合检索的命中率，拍板默认方案。

指标（框架 evaluate_retrieval）：recall@5 / MRR@5 / nDCG@5。
用法：.venv/Scripts/python.exe scripts/eval_retrieval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hello_agents.retrieval import HybridSearch, evaluate_retrieval  # noqa: E402
from src.config import (DATA_DIR, EVAL_DIR, RAG_DB_PATH,  # noqa: E402
                        ZHIPU_API_KEY, ZHIPU_BASE_URL)
from hello_agents.retrieval import RAGStore  # noqa: E402
from src.vector_store import VectorSearchBackend, make_zhipu_provider  # noqa: E402


def load_cases(store: RAGStore) -> list[dict]:
    """金标课程码 → chunk_id（document_id = course_code）。"""
    raw = json.loads((EVAL_DIR / "golden_queries.json").read_text(encoding="utf-8"))
    code_to_chunk = {}
    for chunk in store.snapshot()[1]:
        code_to_chunk.setdefault(chunk.document_id, chunk.chunk_id)
    missing = [code for case in raw["cases"] for code in case["relevance"]
               if code not in code_to_chunk]
    assert not missing, f"金标课程码不在卡片库中：{missing}"
    cases = []
    for case in raw["cases"]:
        cases.append({
            "query": case["query"],
            "relevance": {code_to_chunk[code]: grade
                          for code, grade in case["relevance"].items()},
        })
    return cases


def main():
    store = RAGStore(str(RAG_DB_PATH))
    cases = load_cases(store)

    backends = {"bm25": store}
    for model in ("embedding-2", "embedding-3"):
        provider = make_zhipu_provider(model, ZHIPU_API_KEY, ZHIPU_BASE_URL)
        backends[f"vector({model})"] = VectorSearchBackend(
            store, provider, cache_path=DATA_DIR / f"vector_index_{model}.json")
    backends["hybrid(e2)"] = HybridSearch([store, backends["vector(embedding-2)"]])
    backends["hybrid(e3)"] = HybridSearch([store, backends["vector(embedding-3)"]])

    k = json.loads((EVAL_DIR / "golden_queries.json").read_text(encoding="utf-8"))["k"]
    results = {}
    print(f"金标 {len(cases)} 条，top-{k}：\n")
    header = f"{'backend':<18}{'recall@5':>10}{'MRR@5':>10}{'nDCG@5':>10}"
    print(header); print("-" * len(header))
    for name, backend in backends.items():
        report = evaluate_retrieval(backend, cases, k=k)
        results[name] = report
        m = report["mean"]
        print(f"{name:<18}{m['recall_at_k']:>10.3f}{m['mrr_at_k']:>10.3f}{m['ndcg_at_k']:>10.3f}")

    # 细节：各方案未拿满分的查询（驱动迭代）
    for name, report in results.items():
        bad = [(r["query"], r["retrieved_ids"], r["recall_at_k"])
               for r in report["cases"] if r["recall_at_k"] is not None and r["recall_at_k"] < 1.0]
        if bad:
            print(f"\n[{name}] 未满分 {len(bad)} 条：")
            for query, ids, recall in bad:
                print(f"  recall={recall:.2f} {query}")
                print(f"    top: {ids[:3]}")


if __name__ == "__main__":
    main()
