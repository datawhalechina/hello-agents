"""构建检索索引：课程卡片 → RAGStore（SQLite+BM25）+ 向量索引缓存。

- RAGStore：一门课一个 document（document_id=course_code，version=数据日期+内容摘要），
  chunk_size=4000 保证 1 卡 = 1 chunk
- 向量索引：对 embedding-2 / embedding-3 各建一份缓存（金标评估对比后拍板默认模型）

幂等：同版本同原文重复导入为 no-op；卡片内容变化 → version 变 → 自动替换。

用法：.venv/Scripts/python.exe scripts/build_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hello_agents.retrieval import RAGStore  # noqa: E402
from src.cards import load_jsonl  # noqa: E402
from src.config import (COURSE_CARDS_PATH, DATA_DIR, RAG_DB_PATH,  # noqa: E402
                        ZHIPU_API_KEY, ZHIPU_BASE_URL)
from src.vector_store import VectorSearchBackend, make_zhipu_provider  # noqa: E402

# 单卡单 chunk：卡片均 < 2000 字符，4000 上限确保不切片
CHUNK_SIZE = 4000

MODELS = ("embedding-2", "embedding-3")


def ingest_cards(store: RAGStore) -> int:
    cards = load_jsonl(COURSE_CARDS_PATH)
    for card in cards:
        store.add_document(
            text=card["card_text"],
            source=card["source_url"],
            version=card["version"],
            document_id=card["course_code"],
            chunk_size=CHUNK_SIZE,
            overlap=0,
        )
    revision, chunks = store.snapshot()
    # 护栏：一卡一 chunk
    assert len(chunks) == len(cards), \
        f"chunk 数 {len(chunks)} != 卡片数 {len(cards)}，存在被切片的卡"
    print(f"[store] 导入 {len(cards)} 门课（revision={revision}，{RAG_DB_PATH.name}）")
    return len(cards)


def build_vector_caches(store: RAGStore) -> None:
    for model in MODELS:
        provider = make_zhipu_provider(model, ZHIPU_API_KEY, ZHIPU_BASE_URL)
        backend = VectorSearchBackend(
            store, provider, cache_path=DATA_DIR / f"vector_index_{model}.json")
        backend._ensure_index()  # noqa: SLF001 构建期显式建索引


def main():
    store = RAGStore(str(RAG_DB_PATH))
    ingest_cards(store)
    build_vector_caches(store)
    print("==> 索引构建完成")


if __name__ == "__main__":
    main()
