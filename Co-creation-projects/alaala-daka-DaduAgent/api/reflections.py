"""
反思笔记 REST API

对应设置面板"反思笔记"可视化面板：列表 / 新增 / 单条查询 / 编辑 / 删除。
数据存于 Chroma `agent_reflections` 集合（agent_tools.agent_tools）。
ref_id / timestamp / updated_at 由系统维护，用户不可改。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ReflectionCreate(BaseModel):
    error_desc: str
    solution: str
    philosophy: str
    tags: str = "general"
    severity: str = "medium"


class ReflectionUpdate(BaseModel):
    error_desc: str | None = None
    solution: str | None = None
    philosophy: str | None = None
    tags: str | None = None
    severity: str | None = None


@router.get("/reflections")
async def api_list_reflections():
    """列出全部反思笔记（timestamp 倒序）"""
    try:
        from agent_tools.agent_tools import list_reflections
        return {"reflections": list_reflections()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取反思笔记失败: {e}")


@router.post("/reflections")
async def api_create_reflection(req: ReflectionCreate):
    """新增反思笔记。id 由系统分配（max+1，稳定不复用）。"""
    try:
        from agent_tools.agent_tools import create_reflection
        item = create_reflection(req.error_desc, req.solution, req.philosophy, req.tags, req.severity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增反思笔记失败: {e}")
    return {"reflection": item}


@router.get("/reflections/{ref_id}")
async def api_get_reflection(ref_id: str):
    """按 id 查询单条反思笔记"""
    try:
        from agent_tools.agent_tools import get_reflection
        item = get_reflection(ref_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取反思笔记失败: {e}")
    if item is None:
        raise HTTPException(status_code=404, detail=f"反思笔记 [{ref_id}] 不存在")
    return {"reflection": item}


@router.put("/reflections/{ref_id}")
async def api_update_reflection(ref_id: str, req: ReflectionUpdate):
    """局部更新：仅合并传入的非空字段，保留原 timestamp，写入 updated_at。"""
    try:
        from agent_tools.agent_tools import update_reflection
        item = update_reflection(
            ref_id,
            error_desc=req.error_desc,
            solution=req.solution,
            philosophy=req.philosophy,
            tags=req.tags,
            severity=req.severity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新反思笔记失败: {e}")
    if item is None:
        raise HTTPException(status_code=404, detail=f"反思笔记 [{ref_id}] 不存在")
    return {"reflection": item}


@router.delete("/reflections/{ref_id}")
async def api_delete_reflection(ref_id: str):
    """删除反思笔记（不重排、不重编号，其余 id 稳定不变）"""
    try:
        from agent_tools.agent_tools import delete_reflection
        ok = delete_reflection(ref_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除反思笔记失败: {e}")
    if not ok:
        raise HTTPException(status_code=404, detail=f"反思笔记 [{ref_id}] 不存在")
    return {"deleted": ref_id}
