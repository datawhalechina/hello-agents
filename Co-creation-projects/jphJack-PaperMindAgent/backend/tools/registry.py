"""工具注册表：组装所有 Function Calling 工具"""
from __future__ import annotations

from backend.tools.base import ToolRegistry


def build_default_registry() -> ToolRegistry:
    """构建默认工具注册表，包含全部 10 个工具"""
    registry = ToolRegistry()

    # 步骤1 解析
    from backend.tools.scan_folder import scan_folder_tool
    from backend.tools.parse_pdf import parse_pdf_tool
    registry.register(scan_folder_tool)
    registry.register(parse_pdf_tool)

    # 步骤2 抽取
    from backend.tools.extract_paper_structure import extract_paper_structure_tool
    registry.register(extract_paper_structure_tool)

    # 步骤3 索引
    from backend.tools.build_vector_index import build_vector_index_tool
    registry.register(build_vector_index_tool)

    # 混合搜索
    from backend.tools.hybrid_search_tool import hybrid_search_tool
    registry.register(hybrid_search_tool)

    # 步骤4 Gap
    from backend.tools.analyze_gaps import analyze_gaps_tool
    registry.register(analyze_gaps_tool)

    # 步骤5 创新
    from backend.tools.generate_innovations import generate_innovations_tool
    registry.register(generate_innovations_tool)

    # 步骤6 实验
    from backend.tools.design_experiments import design_experiments_tool
    registry.register(design_experiments_tool)

    # 联网搜索
    from backend.tools.web_search import web_search_tool
    registry.register(web_search_tool)

    # Memory
    from backend.tools.memory_tools import save_memory_tool, load_memory_tool
    registry.register(save_memory_tool)
    registry.register(load_memory_tool)

    return registry
