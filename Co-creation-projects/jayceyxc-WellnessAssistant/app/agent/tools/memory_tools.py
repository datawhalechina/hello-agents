"""长期记忆读写工具。"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.tools.base import WellnessTool
from app.services import memory_service


class AddMemoryParams(BaseModel):
    fact: str = Field(description="需要长期记住的事实，必须来自用户明确表述或已保存的记录")
    category: str = Field(default="general", description="类别：goal、baseline、constraint、feedback 或 general")
    confidence: float = Field(default=1.0, description="置信度，0~1")


class DeactivateMemoryParams(BaseModel):
    memory_id: int = Field(description="需要停用的记忆 ID")


def _add(params: AddMemoryParams, db: Session) -> dict:
    memory = memory_service.add_fact(
        db,
        fact=params.fact,
        category=params.category,
        confidence=params.confidence,
    )
    return {
        "message": "长期记忆已保存",
        "memory": {
            "id": memory.id,
            "fact": memory.fact,
            "category": memory.category,
        },
    }


def _deactivate(params: DeactivateMemoryParams, db: Session) -> dict:
    found = memory_service.deactivate_fact(db, params.memory_id)
    return {
        "message": "记忆已停用" if found else "未找到该记忆",
        "memory_id": params.memory_id,
        "found": found,
    }


def build_memory_tools() -> list[WellnessTool]:
    return [
        WellnessTool(
            "add_health_memory",
            "长期保存用户明确表述的健康基线、目标、限制或反馈事实",
            AddMemoryParams,
            _add,
        ),
        WellnessTool(
            "deactivate_health_memory",
            "用户纠正信息时停用错误的长期记忆，保留历史不物理删除",
            DeactivateMemoryParams,
            _deactivate,
        ),
    ]
