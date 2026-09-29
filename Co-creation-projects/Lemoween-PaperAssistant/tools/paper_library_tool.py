"""论文库检索/问答工具（包装 RAGTool，返回 str）"""
from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter


class PaperLibrarySearchTool(Tool):
    """检索已索引的论文库（PDF 原文分块）"""

    def __init__(self, library_service):
        super().__init__(
            name="search_paper_library",
            description=(
                "在本地论文库中检索与查询最相关的原文片段。"
                "所有片段来自已下载的学术论文 PDF"
                "（经 MarkItDown 转换 → 智能分块 → 向量化）。"
                "撰写章节正文时获取论文细节的主要方式。"
            ),
        )
        self._library = library_service

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="query", type="string",
                          description="英文检索查询", required=True),
            ToolParameter(name="limit", type="integer",
                          description="返回片段数，默认 5", required=False),
            ToolParameter(name="use_advanced", type="boolean",
                          description="是否启用 MQE + HyDE 高级检索",
                          required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        query = (parameters.get("query") or "").strip()
        if not query:
            return "❌ query 不能为空"

        try:
            text = self._library.search(
                query=query,
                limit=int(parameters.get("limit") or 5),
                enable_advanced=bool(parameters.get("use_advanced", False)),
            )
            return text or "未检索到相关论文片段"
        except Exception as exc:
            return f"❌ 论文库检索失败: {exc}"


class PaperLibraryAskTool(Tool):
    """基于论文库直接回答（RAG 增强生成）"""

    def __init__(self, library_service):
        super().__init__(
            name="ask_paper_library",
            description=(
                "基于已索引论文库直接回答学术问题，"
                "返回带引用来源的回答。"
            ),
        )
        self._library = library_service

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="question", type="string",
                          description="学术问题", required=True),
            ToolParameter(name="limit", type="integer",
                          description="检索片段数，默认 5", required=False),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        question = (parameters.get("question") or "").strip()
        if not question:
            return "❌ question 不能为空"

        try:
            answer = self._library.ask(
                question=question,
                limit=int(parameters.get("limit") or 5),
            )
            return answer or "未得到回答"
        except Exception as exc:
            return f"❌ 论文库问答失败: {exc}"