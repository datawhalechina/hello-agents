"""
多 Agent 饮食流水线：各阶段固定输出 Schema（Pydantic v2）。
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEMA_VERSION = "2"


class FoodItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_time: str = Field(default="", max_length=40)
    food_name: str = Field(min_length=1, max_length=120)
    portion_text: str = Field(min_length=1, max_length=120)
    confidence: float = Field(default=0.7, ge=0, le=1)


class NutritionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protein_g: float = Field(default=0, ge=0, le=800)
    carb_g: float = Field(default=0, ge=0, le=1200)
    fat_g: float = Field(default=0, ge=0, le=800)
    fiber_g: float = Field(default=0, ge=0, le=300)
    sodium_mg: float = Field(default=0, ge=0, le=20000)
    calories_kcal: float = Field(default=0, ge=0, le=12000)


class FoodParseOutput(BaseModel):
    """饮食日志解析：由 LLM 从自由文本抽取食物条目并估算营养。"""

    model_config = ConfigDict(extra="forbid")

    items: List[FoodItem] = Field(default_factory=list, max_length=40)
    nutrition_summary: NutritionSummary = Field(default_factory=NutritionSummary)
    parse_notes: str = Field(default="", max_length=1200)


class MealPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    portion: str = Field(min_length=1, max_length=220)
    est_protein_g: float = Field(ge=0, le=250)
    why: str = Field(default="", max_length=600)


class MealPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[MealPlanItem] = Field(min_length=1, max_length=15)
    total_est_protein_g: float = Field(ge=0, le=500)
    tips: List[str] = Field(default_factory=list, max_length=12)

    @field_validator("tips")
    @classmethod
    def cap_tip_len(cls, v: List[str]) -> List[str]:
        return [t.strip()[:500] for t in v if t and t.strip()][:12]


class NutritionistOutput(BaseModel):
    """营养师 Agent：缺口与检索方向。"""

    model_config = ConfigDict(extra="forbid")

    protein_gap_g: float = Field(ge=0, le=400)
    rationale: str = Field(min_length=4, max_length=2000)
    suggested_lookup_queries: List[str] = Field(min_length=1, max_length=10)
    candidate_focus: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("suggested_lookup_queries")
    @classmethod
    def v_queries(cls, v: List[str]) -> List[str]:
        out = [str(s).strip() for s in v if s and str(s).strip()]
        if not out:
            raise ValueError("至少提供一条 suggested_lookup_queries")
        return out[:10]

    @field_validator("candidate_focus")
    @classmethod
    def v_focus(cls, v: List[str]) -> List[str]:
        return [str(s).strip() for s in v if s and str(s).strip()][:10]


class CoachOutput(BaseModel):
    """运动恢复 Coach：时间与恢复约束。"""

    model_config = ConfigDict(extra="forbid")

    training_recovery_note: str = Field(min_length=4, max_length=2000)
    timing_constraints: str = Field(min_length=4, max_length=1200)
    energy_note: str = Field(default="", max_length=1200)
    coach_constraints_for_menu: List[str] = Field(default_factory=list, max_length=12)


class HabitOutput(BaseModel):
    """习惯 Agent：对齐 Reflect + 最终可执行菜单。"""

    model_config = ConfigDict(extra="forbid")

    reflect_alignment: str = Field(min_length=4, max_length=2000)
    execution_hints: List[str] = Field(default_factory=list, max_length=12)
    meal_plan: MealPlan

    @field_validator("execution_hints")
    @classmethod
    def strip_hints(cls, v: List[str]) -> List[str]:
        return [t.strip()[:400] for t in v if t and t.strip()][:12]
