"""论文库服务：包装官方 RAGTool + MemoryTool + NoteTool

    PDF → MarkItDown → Markdown → 智能分块 → 向量化 → Qdrant 存储
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from hello_agents.tools import RAGTool

logger = logging.getLogger(__name__)


class PaperLibraryService:
    """论文库：管理 PDF 的 RAG 索引与检索"""

    def __init__(
        self,
        library_path: str = "./workspace/paper_library",
        rag_namespace: Optional[str] = None,
        pdf_dir: Optional[str] = None,
    ):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)

        self.pdf_dir = Path(pdf_dir) if pdf_dir else self.library_path / "pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        self.rag_dir = self.library_path / "rag"
        self.rag_dir.mkdir(parents=True, exist_ok=True)

        if not rag_namespace:
            h = hashlib.md5(str(self.library_path.resolve()).encode()).hexdigest()[:8]
            rag_namespace = f"papers_{h}"
        self.rag_namespace = rag_namespace

        # 参照第八章使用 RAGTool
        try:
            self.rag_tool = RAGTool(
                knowledge_base_path=str(self.rag_dir),
                collection_name="paper_library",
                rag_namespace=rag_namespace,
            )
            logger.info("PaperLibrary RAGTool 就绪: namespace=%s", rag_namespace)
        except Exception as exc:
            logger.exception("RAGTool 初始化失败: %s", exc)
            self.rag_tool = None

        self._manifest_path = self.rag_dir / "index_manifest.json"
        self._manifest: Dict[str, Dict[str, Any]] = self._load_manifest()

    # ------------------------------------------------------------------
    def index_paper(
        self,
        pdf_path: str,
        paper_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> Dict[str, Any]:
        """将下载的 PDF 加入 RAG 索引（内部走 MarkItDown → Markdown → 分块 → 向量化）"""
        if not self.rag_tool:
            return {"success": False, "error": "RAGTool 未初始化"}

        if paper_id in self._manifest:
            return {"success": True, "skipped": True, "paper_id": paper_id,
                    "chunks": self._manifest[paper_id].get("chunks", 0)}

        path = Path(pdf_path)
        if not path.exists():
            return {"success": False, "error": f"PDF 不存在: {pdf_path}"}

        try:
            # 参照第八章 8.4.2 的调用方式
            result = self.rag_tool.execute(
                "add_document",
                file_path=str(path),
                document_id=paper_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if isinstance(result, dict):
                success = result.get("success", True)
                chunks = result.get("chunks") or result.get("chunk_count") or 0
            else:
                success = True
                chunks = 0

            if success:
                self._manifest[paper_id] = {
                    "pdf_path": str(path),
                    "chunks": chunks,
                    "indexed_at": datetime.now().isoformat(),
                    "metadata": metadata or {},
                }
                self._save_manifest()
                logger.info("索引 %s 成功 (%d chunks)", paper_id, chunks)

            return {"success": success, "paper_id": paper_id, "chunks": chunks}

        except Exception as exc:
            logger.exception("索引 %s 失败", paper_id)
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.1,
        enable_advanced: bool = False,
    ) -> str:
        """检索论文库（参照第八章 8.4.3 的 RAGTool.execute("search") 方式）"""
        if not self.rag_tool:
            return "❌ RAGTool 未初始化"
        try:
            kwargs: Dict[str, Any] = {
                "query": query, "limit": limit, "min_score": min_score,
            }
            if enable_advanced:
                kwargs.update({
                    "enable_advanced_search": True,
                    "enable_mqe": True,
                    "enable_hyde": True,
                })
            result = self.rag_tool.execute("search", **kwargs)
            return str(result) if not isinstance(result, str) else result
        except Exception as exc:
            logger.exception("论文库检索失败")
            return f"❌ 检索失败: {exc}"

    def ask(self, question: str, limit: int = 5) -> str:
        """基于论文库直接回答（RAG 增强生成，参照第八章 8.4.3）"""
        if not self.rag_tool:
            return "❌ RAGTool 未初始化"
        try:
            result = self.rag_tool.execute("ask", question=question, limit=limit)
            return str(result) if not isinstance(result, str) else result
        except Exception as exc:
            return f"❌ 问答失败: {exc}"

    def stats(self) -> Dict[str, Any]:
        return {
            "library_path": str(self.library_path),
            "rag_namespace": self.rag_namespace,
            "indexed_papers": len(self._manifest),
            "papers": [
                {"paper_id": pid, "chunks": info.get("chunks", 0),
                 "indexed_at": info.get("indexed_at")}
                for pid, info in self._manifest.items()
            ],
        }

    # ------------------------------------------------------------------
    def _load_manifest(self) -> Dict[str, Dict[str, Any]]:
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("manifest 读取失败: %s", exc)
        return {}

    def _save_manifest(self) -> None:
        try:
            with open(self._manifest_path, "w", encoding="utf-8") as f:
                json.dump(self._manifest, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("manifest 写入失败: %s", exc)