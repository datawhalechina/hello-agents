from pydantic import BaseModel, Field
from typing import List, Optional
from .common_model import Location, Hotel, Weather, Attraction, Dining


# --- API 请求模型 ---


class TripPlanRequest(BaseModel):
    """行程规划的API请求体"""
    destination: str = Field(..., description="目的地城市", example="北京")
    start_date: str = Field(..., description="开始日期", example="2024-10-01")
    end_date: str = Field(..., description="结束日期", example="2024-10-03")
    preferences: List[str] = Field(
        default_factory=list, description="旅行偏好", example=["历史", "美食"]
    )
    hotel_preferences: List[str] = Field(
        default_factory=list, description="酒店偏好", example=["经济型"]
    )
    budget: str = Field("中等", description="预算水平（如：经济、适中、豪华）", example="中等")


# --- API 响应模型（结构化输出） ---


class BudgetBreakdown(BaseModel):
    """整体预算拆分"""
    transport_cost: float = Field(0.0, description="交通费用")
    dining_cost: float = Field(0.0, description="餐饮费用")
    hotel_cost: float = Field(0.0, description="酒店费用")
    attraction_ticket_cost: float = Field(0.0, description="景点门票费用")
    total: float = Field(0.0, description="总预算（四项之和）")


class DailyBudget(BaseModel):
    """单日预算拆分"""
    transport_cost: float = Field(0.0, description="当日交通费用")
    dining_cost: float = Field(0.0, description="当日餐饮费用")
    hotel_cost: float = Field(0.0, description="当日酒店费用")
    attraction_ticket_cost: float = Field(0.0, description="当日景点门票费用")
    total: float = Field(0.0, description="当日总预算（四项之和）")


class DailyPlan(BaseModel):
    """
    每日行程计划

    设计要点：
    - **推荐住宿**：recommended_hotel
    - **景点列表**：attractions（只在这里挂载景点图片）
    - **餐饮列表**：dinings
    - **预算**：按天拆分为交通 / 餐饮 / 酒店 / 景点门票费用
    """

    day: int = Field(..., description="第几天")
    theme: str = Field("", description="当日主题")
    weather: Optional[Weather] = Field(default=None, description="当日天气信息")
    recommended_hotel: Optional[Hotel] = Field(
        default=None, description="当日推荐住宿（可为空）"
    )
    attractions: List[Attraction] = Field(
        default_factory=list, description="当日景点列表"
    )
    dinings: List[Dining] = Field(
        default_factory=list, description="当日餐饮列表"
    )
    budget: DailyBudget = Field(
        default_factory=DailyBudget, description="当日预算拆分"
    )


class TripPlanResponse(BaseModel):
    """行程规划的API响应体"""

    id: Optional[str] = Field(None, description="行程ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    trip_title: str = Field(..., description="行程标题")
    total_budget: BudgetBreakdown = Field(
        ..., description="整体预算（包含交通、餐饮、酒店、景点门票费用拆分）"
    )
    hotels: List[Hotel] = Field(default_factory=list, description="推荐酒店列表")
    days: List[DailyPlan] = Field(..., description="每日计划详情")