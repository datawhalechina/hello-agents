"""独立的 RAGTool 实现

基于 hello_agents Tool 基类，提供文档处理、文本分块、TF-IDF 检索和智能问答功能。
纯内存实现，无需外部向量数据库，适合学习和演示用途。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import math
import os
import re
import uuid

from hello_agents.tools import Tool, ToolParameter, ToolResponse


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class Chunk:
    """文档分块"""
    chunk_id: str
    document_id: str
    content: str
    index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── 文本处理工具 ──────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """中英文混合分词"""
    text = text.lower()
    # 按空白和标点切分，保留中文字符作为单字 token
    tokens = re.findall(r'[一-鿿]|[a-zA-Z0-9_]+', text)
    return tokens


def _chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """按字符数分块，支持重叠"""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # 尝试按段落分割
    paragraphs = re.split(r'\n{2,}', text)
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 1 <= chunk_size:
            current = current + "\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            # 段落本身超过 chunk_size，按 chunk_size 强制切分
            while len(para) > chunk_size:
                chunks.append(para[:chunk_size])
                para = para[chunk_size - chunk_overlap:]
            current = para

    if current:
        chunks.append(current)

    return chunks


def _read_file(file_path: str) -> str:
    """读取文件内容，支持常见格式"""
    ext = os.path.splitext(file_path)[1].lower()
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 简单的 HTML 标签清理
    if ext in (".html", ".htm"):
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()

    return content


# ── TF-IDF 索引 ──────────────────────────────────────────────

class _TfIdfIndex:
    """轻量级 TF-IDF 索引，纯内存实现"""

    def __init__(self):
        self._doc_tokens: Dict[str, List[str]] = {}  # chunk_id -> tokens
        self._doc_count = 0
        self._df: Dict[str, int] = {}  # term -> document frequency

    def add(self, chunk_id: str, tokens: List[str]):
        self._doc_tokens[chunk_id] = tokens
        self._doc_count += 1
        seen = set(tokens)
        for t in seen:
            self._df[t] = self._df.get(t, 0) + 1

    def search(self, query_tokens: List[str], top_k: int = 5) -> List[tuple]:
        """返回 [(chunk_id, score), ...] 按分数降序"""
        if not query_tokens or not self._doc_tokens:
            return []

        query_tf: Dict[str, int] = {}
        for t in query_tokens:
            query_tf[t] = query_tf.get(t, 0) + 1

        # 计算 query 向量的 IDF 权重
        query_vec: Dict[str, float] = {}
        for t, tf in query_tf.items():
            df = self._df.get(t, 0)
            idf = math.log((self._doc_count + 1) / (df + 1)) + 1
            query_vec[t] = (tf / len(query_tokens)) * idf

        results = []
        for chunk_id, tokens in self._doc_tokens.items():
            doc_tf: Dict[str, int] = {}
            for t in tokens:
                doc_tf[t] = doc_tf.get(t, 0) + 1

            doc_vec: Dict[str, float] = {}
            for t, tf in doc_tf.items():
                df = self._df.get(t, 0)
                idf = math.log((self._doc_count + 1) / (df + 1)) + 1
                doc_vec[t] = (tf / len(tokens)) * idf

            # 余弦相似度
            dot = sum(query_vec.get(t, 0) * doc_vec.get(t, 0) for t in query_vec)
            q_norm = math.sqrt(sum(v * v for v in query_vec.values()))
            d_norm = math.sqrt(sum(v * v for v in doc_vec.values()))
            if q_norm > 0 and d_norm > 0 and dot > 0:
                score = dot / (q_norm * d_norm)
            else:
                score = 0.0

            if score > 0:
                results.append((chunk_id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# ── RAGTool ──────────────────────────────────────────────────

class RAGTool(Tool):
    """RAG 检索增强生成工具

    支持文档导入、文本分块、TF-IDF 语义检索和基于上下文的问答。
    所有数据存储在内存中，进程结束后清空。
    """

    def __init__(
        self,
        knowledge_base_path: str = "./rag_kb",
        rag_namespace: str = "default",
    ):
        super().__init__(
            name="rag",
            description="RAG工具，支持文档处理、智能问答和知识检索",
        )
        self.knowledge_base_path = knowledge_base_path
        self.rag_namespace = rag_namespace

        self._documents: Dict[str, str] = {}  # document_id -> original text
        self._chunks: Dict[str, Chunk] = {}   # chunk_id -> Chunk
        self._index = _TfIdfIndex()
        self._add_count = 0

    def run(self, parameters) -> str:
        if isinstance(parameters, str):
            parameters = {"action": parameters}
        action = parameters.get("action")
        if not action:
            return "缺少 action 参数"

        kwargs = {k: v for k, v in parameters.items() if k != "action"}
        handler = {
            "add_document": self._add_document,
            "add_text": self._add_text,
            "search": self._search,
            "ask": self._ask,
            "stats": self._stats,
        }.get(action)

        if handler is None:
            return f"不支持的操作: {action}"

        try:
            resp = handler(**kwargs)
            return resp.text
        except Exception as e:
            return f"执行错误: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="action", type="string", description="操作类型", required=True)]

    # ── 公开方法（供演示脚本直接调用） ────────────────────────

    def batch_add_texts(self, texts: List[str], document_ids: List[str] = None, **kwargs) -> str:
        """批量添加文本"""
        ids = document_ids or [f"doc_{i}" for i in range(len(texts))]
        added = 0
        for text, doc_id in zip(texts, ids):
            self._ingest_text(text, doc_id, **kwargs)
            added += 1
        return f"批量添加完成，共 {added} 个文档"

    # ── 内部实现 ──────────────────────────────────────────────

    def _add_document(self, file_path: str = "", **kwargs) -> ToolResponse:
        if not file_path or not os.path.exists(file_path):
            return ToolResponse.error(code="FILE_NOT_FOUND", message=f"文件不存在: {file_path}")

        content = _read_file(file_path)
        doc_id = os.path.basename(file_path)
        chunk_count = self._ingest_text(content, doc_id, **kwargs)
        return ToolResponse.success(
            text=f"文档已添加: {doc_id} ({chunk_count} 个分块)",
            data={"document_id": doc_id, "chunks": chunk_count},
        )

    def _add_text(self, text: str = "", document_id: str = None, chunk_size: int = 500, chunk_overlap: int = 50, **kwargs) -> ToolResponse:
        if not text:
            return ToolResponse.error(code="EMPTY_TEXT", message="文本内容为空")
        doc_id = document_id or f"text_{uuid.uuid4().hex[:8]}"
        chunk_count = self._ingest_text(text, doc_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return ToolResponse.success(
            text=f"文本已添加: {doc_id} ({chunk_count} 个分块)",
            data={"document_id": doc_id, "chunks": chunk_count},
        )

    def _search(self, query: str = "", limit: int = 5, enable_advanced_search: bool = False, **_) -> ToolResponse:
        if not query:
            return ToolResponse.error(code="EMPTY_QUERY", message="查询内容为空")

        tokens = _tokenize(query)

        if enable_advanced_search:
            # 多查询扩展：为每个关键词单独查询再合并
            all_results: Dict[str, float] = {}
            for token in tokens:
                hits = self._index.search([token], top_k=limit)
                for cid, score in hits:
                    all_results[cid] = max(all_results.get(cid, 0), score)
            # 也查一次完整查询
            for cid, score in self._index.search(tokens, top_k=limit):
                all_results[cid] = max(all_results.get(cid, 0), score)
            sorted_hits = sorted(all_results.items(), key=lambda x: x[1], reverse=True)[:limit]
        else:
            sorted_hits = self._index.search(tokens, top_k=limit)

        if not sorted_hits:
            return ToolResponse.success(text=f"未找到与 '{query}' 相关的内容", data={"results": []})

        lines = [f"找到 {len(sorted_hits)} 条相关结果:"]
        results_data = []
        for i, (cid, score) in enumerate(sorted_hits, 1):
            chunk = self._chunks.get(cid)
            if chunk:
                preview = chunk.content[:150] + ("..." if len(chunk.content) > 150 else "")
                lines.append(f"{i}. [相似度: {score:.3f}] 来源: {chunk.document_id}")
                lines.append(f"   {preview}")
                results_data.append({
                    "chunk_id": cid,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "score": round(score, 4),
                })

        return ToolResponse.success(text="\n".join(lines), data={"results": results_data})

    def _ask(self, question: str = "", limit: int = 3, include_citations: bool = False, enable_advanced_search: bool = False, max_chars: int = 2000, **_) -> ToolResponse:
        if not question:
            return ToolResponse.error(code="EMPTY_QUESTION", message="问题为空")

        # 检索相关片段
        tokens = _tokenize(question)
        if enable_advanced_search:
            all_results: Dict[str, float] = {}
            for token in tokens:
                for cid, score in self._index.search([token], top_k=limit):
                    all_results[cid] = max(all_results.get(cid, 0), score)
            for cid, score in self._index.search(tokens, top_k=limit):
                all_results[cid] = max(all_results.get(cid, 0), score)
            sorted_hits = sorted(all_results.items(), key=lambda x: x[1], reverse=True)[:limit]
        else:
            sorted_hits = self._index.search(tokens, top_k=limit)

        if not sorted_hits:
            return ToolResponse.success(text=f"抱歉，未找到与 '{question}' 相关的知识内容。")

        # 构建上下文
        context_parts = []
        citations = []
        total_chars = 0
        for cid, score in sorted_hits:
            chunk = self._chunks.get(cid)
            if chunk is None:
                continue
            if total_chars + len(chunk.content) > max_chars:
                break
            context_parts.append(chunk.content)
            citations.append(f"- {chunk.document_id} (相似度: {score:.3f})")
            total_chars += len(chunk.content)

        context = "\n\n---\n\n".join(context_parts)

        # 构建回答
        answer_parts = [
            f"基于知识库检索，关于「{question}」的回答：\n",
            "以下是检索到的相关内容：\n",
            context,
        ]

        if include_citations and citations:
            answer_parts.append("\n\n参考来源：")
            answer_parts.extend(citations)

        return ToolResponse.success(text="\n".join(answer_parts))

    def _stats(self) -> ToolResponse:
        doc_count = len(self._documents)
        chunk_count = len(self._chunks)
        total_chars = sum(len(c.content) for c in self._chunks.values())
        return ToolResponse.success(
            text=f"RAG知识库统计\n文档数: {doc_count}\n分块数: {chunk_count}\n总字符数: {total_chars}\n命名空间: {self.rag_namespace}",
            data={
                "documents": doc_count,
                "chunks": chunk_count,
                "total_chars": total_chars,
                "namespace": self.rag_namespace,
            },
        )

    # ── 辅助方法 ──────────────────────────────────────────────

    def _ingest_text(self, text: str, document_id: str, chunk_size: int = 500, chunk_overlap: int = 50) -> int:
        """将文本分块并加入索引，返回分块数"""
        self._documents[document_id] = text
        chunks_text = _chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        for i, chunk_text in enumerate(chunks_text):
            cid = f"{document_id}_chunk_{i}"
            chunk = Chunk(
                chunk_id=cid,
                document_id=document_id,
                content=chunk_text,
                index=i,
            )
            self._chunks[cid] = chunk
            tokens = _tokenize(chunk_text)
            self._index.add(cid, tokens)
            self._add_count += 1

        return len(chunks_text)
