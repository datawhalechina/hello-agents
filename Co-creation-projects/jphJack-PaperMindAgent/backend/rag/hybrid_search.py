"""混合搜索：组合向量检索 + BM25 检索，加权分数归一化重排"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from backend.models.schemas import ParsedPaper, Section
from backend.rag.bm25_store import BM25Store
from backend.rag.embedding import Embedder, get_default_embedder
from backend.rag.vector_store import ChromaStore

logger = logging.getLogger(__name__)

# 分块目标字符数
CHUNK_SIZE = 500


class HybridSearcher:
    """混合检索器：ChromaStore + BM25Store + Embedder"""

    def __init__(
        self,
        vector_store: Optional[ChromaStore] = None,
        bm25_store: Optional[BM25Store] = None,
        embedder: Optional[Embedder] = None,
        chunk_size: int = CHUNK_SIZE,
    ):
        self.embedder = embedder or get_default_embedder()
        self.vector_store = vector_store or ChromaStore(embedder=self.embedder)
        self.bm25_store = bm25_store or BM25Store()
        self.chunk_size = chunk_size

    # ---------- 分块 ----------

    def _chunk_section(self, section: Section) -> list[dict]:
        """将单章节按段落分块，块大小约 chunk_size 字符。

        Returns:
            list[dict]，每项 {section, text}
        """
        content = section.content or ""
        heading = section.heading or ""
        # 按换行切段落，丢弃空段
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        chunks: list[dict] = []
        buf = ""
        for para in paragraphs:
            # 累计超过阈值则落块
            if buf and len(buf) + len(para) > self.chunk_size:
                chunks.append({"section": heading, "text": buf})
                buf = para
            else:
                buf = f"{buf}\n{para}".strip() if buf else para
        if buf:
            chunks.append({"section": heading, "text": buf})

        # 处理单段过长的情况：按 chunk_size 强制切分
        final: list[dict] = []
        for c in chunks:
            text = c["text"]
            if len(text) <= self.chunk_size * 2:
                final.append(c)
            else:
                for i in range(0, len(text), self.chunk_size):
                    final.append(
                        {"section": c["section"], "text": text[i : i + self.chunk_size]}
                    )
        return final

    # ---------- 写入 ----------

    def add_paper(self, paper: ParsedPaper):
        """把单篇论文章节分块后加入向量库与 BM25 库"""
        t_start = time.perf_counter()
        all_chunks: list[dict] = []
        for section in paper.sections:
            all_chunks.extend(self._chunk_section(section))
        t_chunk = time.perf_counter()
        logger.info(
            "[add_paper] %s 分块完成: %d sections → %d chunks, 用时 %.2fs",
            paper.path, len(paper.sections), len(all_chunks), t_chunk - t_start,
        )
        if not all_chunks:
            return
        # 向量库：传入 paper_path/title + chunks[{section, text}]
        self.vector_store.add_chunks(paper.path, paper.title, all_chunks)
        t_vec = time.perf_counter()
        logger.info(
            "[add_paper] %s 向量库写入完成: 用时 %.2fs (累计 %.2fs)",
            paper.path, t_vec - t_chunk, t_vec - t_start,
        )
        # BM25：chunks 需带 paper_path/title
        bm25_chunks = [
            {**c, "paper_path": paper.path, "title": paper.title} for c in all_chunks
        ]
        self.bm25_store.add_chunks(bm25_chunks)
        t_bm25 = time.perf_counter()
        logger.info(
            "[add_paper] %s BM25 写入完成: 用时 %.2fs (累计 %.2fs)",
            paper.path, t_bm25 - t_vec, t_bm25 - t_start,
        )

    def load_all(self, papers: list[ParsedPaper]):
        """批量加载多篇论文"""
        for paper in papers:
            self.add_paper(paper)

    # ---------- 检索 ----------

    def search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> list[dict]:
        """混合检索：向量 + BM25 各取 top_k*2，加权分数归一化重排。

        Returns:
            list[dict]，每项 {text, paper_path, title, section, score}，按融合分数降序
        """
        fetch_k = top_k * 2
        vector_results = self.vector_store.vector_search(query, top_k=fetch_k)
        bm25_results = self.bm25_store.bm25_search(query, top_k=fetch_k)

        # 各路结果做 min-max 归一化到 [0,1]
        vector_results = self._normalize(vector_results)
        bm25_results = self._normalize(bm25_results)

        # 以 text 为 key 合并去重，加权累加分数
        merged: dict[str, dict] = {}
        for r in vector_results:
            key = r["text"]
            s = vector_weight * r["norm_score"]
            if key not in merged:
                merged[key] = {
                    "text": r["text"],
                    "paper_path": r["paper_path"],
                    "title": r["title"],
                    "section": r["section"],
                    "score": s,
                }
            else:
                merged[key]["score"] += s
        for r in bm25_results:
            key = r["text"]
            s = bm25_weight * r["norm_score"]
            if key not in merged:
                merged[key] = {
                    "text": r["text"],
                    "paper_path": r["paper_path"],
                    "title": r["title"],
                    "section": r["section"],
                    "score": s,
                }
            else:
                merged[key]["score"] += s

        # 按融合分数降序取 top_k
        out = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:top_k]
        return out

    @staticmethod
    def _normalize(results: list[dict]) -> list[dict]:
        """对结果列表的 score 做 min-max 归一化，写入 norm_score 字段"""
        if not results:
            return results
        scores = [r["score"] for r in results]
        lo, hi = min(scores), max(scores)
        rng = hi - lo if hi > lo else 1.0
        for r in results:
            r["norm_score"] = (r["score"] - lo) / rng
        return results

    # ---------- 异步友好封装 ----------

    async def async_add_paper(self, paper: ParsedPaper):
        """异步写入单篇论文"""
        await asyncio.to_thread(self.add_paper, paper)

    async def async_load_all(self, papers: list[ParsedPaper]):
        """异步批量加载"""
        await asyncio.to_thread(self.load_all, papers)

    async def async_search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> list[dict]:
        """异步混合检索"""
        return await asyncio.to_thread(
            self.search, query, top_k, vector_weight, bm25_weight
        )
