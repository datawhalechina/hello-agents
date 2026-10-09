"""Paper Search MCP

把 openags/paper-search-mcp 包装为 HelloAgents 的 MCPTool。
auto_expand=True 会自动展开为 papersearch_search_papers、
papersearch_download_with_fallback 等独立工具。
"""
import logging
from typing import List, Optional

from hello_agents.tools import MCPTool

logger = logging.getLogger(__name__)


def create_paper_search_mcp_tool(
    server_command: List[str],
    prefix: str = "papersearch",
    env: Optional[dict] = None,
) -> MCPTool:
    """创建 Paper Search MCP 工具

    Args:
        server_command: 启动命令列表，如 ["uvx", "paper-search-mcp"]
        prefix: 展开后工具的前缀（如 papersearch_search_papers）
        env: 传给 MCP 子进程的环境变量（API Key 等）

    Returns:
        已启用 auto_expand 的 MCPTool 实例
    """
    if not server_command:
        raise ValueError("Paper Search MCP 需要提供 server_command")

    logger.info("初始化 Paper Search MCP: %s", server_command)

    return MCPTool(
        name=prefix,
        description=(
            "Paper Search MCP：跨源学术文献检索与全文下载"
            "（arXiv/PubMed/Semantic Scholar/CrossRef/OpenAlex/dblp 等 20+ 源）。"
            "主要工具：search_papers（统一检索）、"
            "download_with_fallback（按 DOI/arXiv ID 下载全文）。"
        ),
        server_command=server_command,
        env=env or {},
        auto_expand=True,
    )