"""
工具管理 REST API
"""
from fastapi import APIRouter, HTTPException, Query
from tool.logger_handler import logger

router = APIRouter()

# 工具元数据（名称 + 描述）
TOOLS_META = [
    {
        "name": "search",
        "description": "Tavily 网络搜索 — 获取时效性信息和外部知识",
        "category": "knowledge",
    },
    {
        "name": "calculator",
        "description": "安全数学表达式求值 — 支持运算符、三角函数、对数等",
        "category": "compute",
    },
    {
        "name": "todo",
        "description": "待办清单 — 任务规划与执行进度追踪",
        "category": "planning",
    },
    {
        "name": "reflection",
        "description": "反思笔记本 — 经验沉淀、语义搜索与回顾",
        "category": "memory",
    },
    {
        "name": "rag_summarize",
        "description": "本地知识库检索总结 — 基于 Chroma RAG",
        "category": "knowledge",
    },
    {
        "name": "file_manage",
        "description": "文件系统管理 — 9 种子命令的 CRUD 操作",
        "category": "system",
    },
    {
        "name": "ask_for_answer",
        "description": "需求澄清与用户确认 — Agent 主动提问",
        "category": "interaction",
    },
    {
        "name": "session",
        "description": "会话管理 — 创建、切换、删除对话会话",
        "category": "system",
    },
]


@router.get("/tools")
async def api_list_tools():
    """列出所有工具及其描述"""
    return {"tools": TOOLS_META}


@router.get("/tools/reflections")
async def api_reflections_stats():
    """反思笔记本统计"""
    try:
        from agent_tools.agent_tools import _cmd_stats
        stats_result = _cmd_stats()
        return {"stats": stats_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取反思统计失败: {str(e)}")


@router.get("/tools/reflections/search")
async def api_reflections_search(q: str = Query(..., description="搜索关键词")):
    """语义搜索反思笔记"""
    try:
        from agent_tools.agent_tools import _cmd_search
        results = _cmd_search(q)
        return {"query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/tools/todos")
async def api_get_todos():
    """获取当前 todo 状态"""
    try:
        from agent_tools.agent_tools import get_todo_state
        todos, counter = get_todo_state()
        return {"todos": todos, "counter": counter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 todo 失败: {str(e)}")
