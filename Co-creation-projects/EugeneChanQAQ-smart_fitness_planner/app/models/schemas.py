from typing import Dict, Optional, Union, List
from pydantic import BaseModel, Field, field_validator

# ========== 请求模型 ==========
class FitnessRequest(BaseModel):
    """运动计划请求"""
    height: int = Field(..., description="身高", examples=183)
    weight: int = Field(..., description="体重", examples=76)
    age: int = Field(..., description="年龄", examples=26)

    class Config:
        json_schema_extra = {
            "example": {
                "height": 183,
                "weight": 76,
                "age": 26
            }
        }

# ========== 单日训练计划模型 ==========
class TrainPlan(BaseModel):
    day: int = Field(..., description="训练日（1～7）")
    action: str = Field(..., description="训练动作")
    muscle: str = Field(default=None, description="肌肉群")
    group_num: int = Field(default=None, description="组数")
    amount: int = Field(default=None, description="每组数量")

# ========== 响应模型（支持 7 天列表） ==========
class FitnessResponse(BaseModel):
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    fitness_plan: List[TrainPlan] = Field(..., description="7 天训练计划")

# ========== 错误响应 ==========
class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")