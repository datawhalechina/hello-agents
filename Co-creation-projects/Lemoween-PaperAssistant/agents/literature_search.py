"""文献检索 Agent（基于 Paper Search MCP）

链路：
  LLM 调用 papersearch_search_papers → 返回 JSON（含 source + paper_id）
  Python 层逐篇调用 MCPTool.run({action: call_tool, ...}) → 直接调用 download_with_fallback
  下载成功的 PDF → PaperLibraryService.index_paper（内部走 RAGTool）
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from hello_agents import HelloAgentsLLM, ToolAwareSimpleAgent

from config import Configuration
from models import PaperSection
from prompts import literature_search_system_prompt
from services.paper_library import PaperLibraryService
from services.tool_events import ToolCallTracker
from tools import create_paper_search_mcp_tool

logger = logging.getLogger(__name__)


class LiteratureSearchAgent:
    """文献检索 Agent：检索 → 下载 → RAG 索引"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        config: Configuration,
        tool_tracker: Optional[ToolCallTracker] = None,
    ):
        self._config = config
        self._tracker = tool_tracker
        self._prefix = config.paper_search_mcp_prefix
        self._mcp_tool = None  # ★ 保存原始 MCPTool 引用

        # 1. 论文库服务（复用第八章 RAGTool）
        self.library = PaperLibraryService(
            library_path=config.paper_library_path,
            rag_namespace=config.paper_library_rag_namespace,
            pdf_dir=str(config.paper_library_path.rstrip("/") + "/pdfs"),
        )

        # 2. Agent（参照第十四章 ToolAwareSimpleAgent 用法）
        self._agent = ToolAwareSimpleAgent(
            name="文献检索专家",
            llm=llm,
            system_prompt="你是一名学术文献检索专家。",
            enable_tool_calling=True,
            tool_registry=None,
            tool_call_listener=self._tracker.record if self._tracker else None,
        )

        # 3. 装配 Paper Search MCP
        self._register_mcp_tool()

        # 4. 刷新系统提示
        self._agent.system_prompt = self._build_system_prompt()

    # ------------------------------------------------------------------
    def _register_mcp_tool(self) -> None:
        """装配 Paper Search MCP"""
        command = self._config.resolve_paper_search_mcp_command()
        if not command:
            logger.warning("未配置 PAPER_SEARCH_MCP_COMMAND，文献检索能力不可用")
            return

        try:
            mcp_tool = create_paper_search_mcp_tool(
                server_command=command,
                prefix=self._prefix,
            )
            self._agent.add_tool(mcp_tool)
            self._mcp_tool = mcp_tool     # ★ 保存引用，供直接调用
            logger.info("Paper Search MCP 已装配: %s", command)
        except Exception as exc:
            logger.exception("Paper Search MCP 装配失败: %s", exc)

    def _build_system_prompt(self) -> str:
        """★ 补回此方法：把工具清单注入检索提示词"""
        tools_desc = (
            self._agent.tool_registry.get_tools_description()
            if self._agent.tool_registry else "暂无可用工具"
        )
        return literature_search_system_prompt.format(
            tools_placeholder=tools_desc,
            prefix=self._prefix,
        )

    # ------------------------------------------------------------------
    def search_for_section(self, section: PaperSection) -> List[Dict[str, Any]]:
        """对单个章节执行检索 → 下载 → 索引"""
        keywords = section.keywords or [section.title]
        query = " ".join(keywords)
        limit = self._config.max_references_per_section

        # ------ 步骤 1: 让 LLM 调用 papersearch_search_papers 完成检索 ------
        prompt = (
            f"请为以下论文章节检索 {limit} 篇高质量学术论文。\n\n"
            f"章节标题：{section.title}\n"
            f"章节意图：{section.intent}\n"
            f"检索关键词：{query}\n\n"
            f"## 操作指令\n"
            f"调用一次 `{self._prefix}_search_papers`，参数：\n"
            f"```json\n"
            f'{{"query": "{query}", '
            f'"sources": "arxiv,semantic,crossref,openalex,dblp", '
            f'"max_results_per_source": {limit}}}\n'
            f"```\n\n"
            f"## 返回要求\n"
            f"检索完成后，**只输出 JSON**，格式如下（不要任何解释文字）：\n"
            f'{{"papers": ['
            f'{{"title":"...","authors":[...],"year":...,'
            f'"venue":"...","doi":"...","source":"arxiv",'
            f'"paper_id":"..."}}]}}\n'
            f"注意：source 与 paper_id 必填，用于后续下载。"
        )

        response = self._agent.run(prompt)

        # ===== 诊断 1：检索 Agent 原始输出 =====
        print("=" * 70)
        print("【诊断】检索 Agent 原始输出：")
        print(response[:2000])
        print("=" * 70)

        papers = self._parse_papers(response)
        papers = self._deduplicate(papers)[:limit]

        # ===== 诊断 2：解析出的 papers 列表 =====
        print("=" * 70)
        print(f"【诊断】解析出 {len(papers)} 篇论文：")
        for i, p in enumerate(papers, 1):
            print(f"  [{i}] title     : {(p.get('title') or '')[:60]}")
            print(f"      source    : {p.get('source')!r}")
            print(f"      paper_id  : {p.get('paper_id')!r}")
            print(f"      arxiv_id  : {p.get('arxiv_id')!r}")
            print(f"      doi       : {p.get('doi')!r}")
            print(f"      所有字段  : {list(p.keys())}")
        print("=" * 70)

        # ------ 步骤 2: Python 层逐篇调用 download_with_fallback ------
        for p in papers:
            self._download_paper(p)

        # ------ 步骤 3: 已下载的 PDF 加入 RAG 索引 ------
        for p in papers:
            self._index_if_downloaded(p)

        logger.info(
            "章节「%s」检索 %d 篇，已下载 %d 篇，已索引 %d 篇",
            section.title, len(papers),
            sum(1 for p in papers if p.get("pdf_path")),
            sum(1 for p in papers if p.get("indexed")),
        )
        return papers

    # ------------------------------------------------------------------
    def _download_paper(self, paper: Dict[str, Any]) -> None:
        """调用 download_with_fallback 下载单篇论文

        直接调用底层 MCPTool.run()，避免经过 wrapper 的参数包装。
        """
        source = (paper.get("source") or "").strip()
        paper_id = (paper.get("paper_id") or "").strip()
        if not source or not paper_id:
            logger.debug("论文《%s》缺少 source/paper_id，跳过下载",
                         (paper.get("title") or "")[:60])
            paper["pdf_path"] = None
            return

        unsupported = {"google_scholar", "dblp", "ssrn", "unpaywall"}
        if source in unsupported:
            logger.debug("源 %s 不支持全文下载，跳过", source)
            paper["pdf_path"] = None
            return

        if self._mcp_tool is None:
            logger.warning("MCPTool 未装配，无法下载")
            paper["pdf_path"] = None
            return

        save_path = str(self.library.pdf_dir)

        # ===== 诊断 =====
        print("=" * 70)
        print("【诊断】直接调用 MCPTool.run() 下载：")
        print(f"  source   : {source!r}")
        print(f"  paper_id : {paper_id!r}")
        print(f"  save_path: {save_path!r}")
        print("=" * 70)

        # ★ 关键：直接调用 MCPTool，参数不经过 wrapper 的 {"input": ...} 包装
        try:
            result = self._mcp_tool.run({
                "action": "call_tool",
                "tool_name": "download_with_fallback",
                "arguments": {
                    "source": source,
                    "paper_id": paper_id,
                    "doi": paper.get("doi", "") or "",
                    "title": paper.get("title", "") or "",
                    "save_path": save_path,
                    "use_scihub": False,
                },
            })
        except Exception as exc:
            logger.warning("下载工具调用失败 source=%s paper_id=%s: %s",
                           source, paper_id, exc)
            paper["pdf_path"] = None
            return

        # ===== 诊断 =====
        print("=" * 70)
        print("【诊断】download_with_fallback 返回值（全文）：")
        print(str(result))
        print("=" * 70)

        pdf_path = self._extract_pdf_path(str(result))
        paper["pdf_path"] = pdf_path
        if pdf_path:
            logger.info("下载成功: %s", pdf_path)
        else:
            logger.debug("未能从下载结果中提取 PDF 路径: %s", str(result)[:200])

    @staticmethod
    def _extract_pdf_path(result_text: str) -> Optional[str]:
        """从 download_with_fallback 的返回值里提取 PDF 路径

        典型返回值：
            工具 'download_with_fallback' 执行结果:
            workspace\\paper_library\\pdfs/2502.00632v2.pdf

        提取规则：
        1. 逐行从后往前找以 .pdf 结尾的行，去掉 "xxx:" 前缀
        2. 若整行就是路径，直接返回
        3. 兜底：抓取任何含目录分隔符且以 .pdf 结尾的片段
        """
        if not result_text:
            return None

        text = result_text.strip()

        # 1. 整段就是纯路径
        if text.endswith(".pdf") and "\n" not in text:
            return text

        # 2. 逐行从后往前找
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            # 去掉 "工具 'xxx' 执行结果:" 之类的中英文冒号前缀
            line = re.sub(r'^[^:\n]*[:：]\s*', '', line)
            if line.endswith(".pdf"):
                return line
            # 行末包含路径的情况，如 "Downloaded to: xxx.pdf"
            m = re.search(r'([^\s:"\']+\.pdf)\s*$', line)
            if m:
                return m.group(1)

        # 3. 兜底：任何含目录分隔符且以 .pdf 结尾的片段
        #    要求路径里至少出现一个 \ 或 / 且不是开头就 /
        m = re.search(
            r'([A-Za-z]:[\\/][^\s:"\']+\.pdf'  # Windows 绝对路径
            r'|[^\s:"\'/\\]+[\\/][^\s:"\']+\.pdf)'  # 相对路径（至少一级目录）
            , text
        )
        if m:
            return m.group(1)

        return None

    def _index_if_downloaded(self, paper: Dict[str, Any]) -> None:
        """若已下载 PDF，则加入 RAG 索引"""
        pdf_path = paper.get("pdf_path")
        if not pdf_path or not Path(pdf_path).exists():
            paper["indexed"] = False
            return

        doi = (paper.get("doi") or "").strip()
        title = (paper.get("title") or "").strip()
        paper_id = (paper.get("paper_id") or "").strip()
        stable_id = self._make_stable_id(doi, paper_id, title)
        if not stable_id:
            paper["indexed"] = False
            return

        paper["stable_id"] = stable_id

        index_result = self.library.index_paper(
            pdf_path=pdf_path,
            paper_id=stable_id,
            metadata={
                "title": title,
                "doi": doi,
                "source": paper.get("source"),
                "source_id": paper_id,
                "year": paper.get("year"),
                "venue": paper.get("venue"),
            },
        )
        paper["indexed"] = bool(index_result.get("success"))
        paper["chunks"] = index_result.get("chunks", 0)

    @staticmethod
    def _make_stable_id(doi: str, source_id: str, title: str) -> Optional[str]:
        if doi:
            return f"doi_{hashlib.md5(doi.lower().encode()).hexdigest()[:16]}"
        if source_id:
            safe = re.sub(r"[^\w\-]", "_", source_id)[:40]
            return f"sid_{safe}"
        if title:
            return f"title_{hashlib.md5(title.lower().encode()).hexdigest()[:16]}"
        return None

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_papers(response: str) -> List[Dict[str, Any]]:
        if not response:
            return []

        try:
            data = json.loads(response)
            if isinstance(data, dict) and isinstance(data.get("papers"), list):
                return [p for p in data["papers"] if isinstance(p, dict)]
        except json.JSONDecodeError:
            pass

        start, end = response.find("{"), response.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(response[start:end + 1])
                if isinstance(data, dict) and isinstance(data.get("papers"), list):
                    return [p for p in data["papers"] if isinstance(p, dict)]
            except json.JSONDecodeError:
                pass

        m = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                if isinstance(data, dict) and isinstance(data.get("papers"), list):
                    return [p for p in data["papers"] if isinstance(p, dict)]
            except json.JSONDecodeError:
                pass

        logger.warning("未能从检索 Agent 输出中解析 papers")
        return []

    @staticmethod
    def _deduplicate(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen, unique = set(), []
        for p in papers:
            doi = (p.get("doi") or "").strip().lower()
            title = re.sub(r"\s+", " ", (p.get("title") or "").strip().lower())
            key = doi or title
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(p)
        return unique

    # ------------------------------------------------------------------
    def list_tools(self) -> List[str]:
        return self._agent.list_tools() if self._agent else []

    def library_stats(self) -> Dict[str, Any]:
        return self.library.stats()