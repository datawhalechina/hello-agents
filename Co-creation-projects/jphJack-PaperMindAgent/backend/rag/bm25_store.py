"""BM25 关键词检索：基于 rank_bm25 的内存检索，中英文兼容分词"""
from __future__ import annotations

import re
from typing import Optional

from rank_bm25 import BM25Okapi


class BM25Store:
    """BM25 内存文档库，懒构建索引"""

    def __init__(self):
        # 原始文档与对应分词结果并行维护
        self._docs: list[dict] = []
        self._tokenized: list[list[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._dirty = False  # 标记索引是否需要重建

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中英文兼容分词（不依赖 jieba）。

        - 英文/数字：按连续字母数字切词，统一小写
        - 中文：按单字切分（字粒度，兼容无词典场景）
        """
        if not text:
            return []
        tokens: list[str] = []
        # 英文单词与数字
        for m in re.findall(r"[A-Za-z0-9]+", text):
            tokens.append(m.lower())
        # 中文字符逐字切分
        for ch in re.findall(r"[\u4e00-\u9fff]", text):
            tokens.append(ch)
        return tokens

    def add_chunks(self, chunks: list[dict]):
        """添加文档。

        每个 chunk 形如 {text, paper_path, title, section}。
        """
        for c in chunks:
            doc = {
                "text": c.get("text", ""),
                "paper_path": c.get("paper_path", ""),
                "title": c.get("title", ""),
                "section": c.get("section", ""),
            }
            self._docs.append(doc)
            self._tokenized.append(self._tokenize(doc["text"]))
        self._dirty = True

    def _ensure_index(self):
        """懒构建 BM25 索引：有新增时重建"""
        if self._dirty or self._bm25 is None:
            if self._tokenized:
                self._bm25 = BM25Okapi(self._tokenized)
            else:
                self._bm25 = None
            self._dirty = False

    def bm25_search(self, query: str, top_k: int = 5) -> list[dict]:
        """BM25 检索，返回 top_k 结果。

        Returns:
            list[dict]，每项 {text, paper_path, title, section, score}
        """
        self._ensure_index()
        if self._bm25 is None or not self._docs:
            return []
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []
        scores = self._bm25.get_scores(q_tokens)
        q_set = set(q_tokens)
        # 仅保留至少包含一个查询词的文档，避免返回无关结果
        # （注意：小语料下 BM25Okapi 的 IDF 可能为 0，不能再用 score>0 过滤）
        candidate_idx = [
            i for i, toks in enumerate(self._tokenized) if q_set & set(toks)
        ]
        if not candidate_idx:
            return []
        # 在候选中按分数降序取 top_k
        candidate_idx.sort(key=lambda i: scores[i], reverse=True)
        out: list[dict] = []
        for i in candidate_idx[:top_k]:
            doc = self._docs[i]
            out.append(
                {
                    "text": doc["text"],
                    "paper_path": doc["paper_path"],
                    "title": doc["title"],
                    "section": doc["section"],
                    "score": float(scores[i]),
                }
            )
        return out

    def clear(self):
        """清空文档库"""
        self._docs = []
        self._tokenized = []
        self._bm25 = None
        self._dirty = False
