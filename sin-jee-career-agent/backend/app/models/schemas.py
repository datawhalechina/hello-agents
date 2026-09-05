"""数据模型定义 — 智能求职助手"""

from typing import List, Optional
from pydantic import BaseModel, Field


class JobListing(BaseModel):
    """职位信息"""
    title: str = Field(..., description="职位名称")
    company: str = Field(..., description="公司名称")
    location: str = Field(..., description="工作地点")
    salary_range: Optional[str] = Field(default=None, description="薪资范围")
    description: str = Field(..., description="职位描述")
    requirements: List[str] = Field(default_factory=list, description="任职要求列表")
    url: Optional[str] = Field(default=None, description="招聘链接")
    source: Optional[str] = Field(default=None, description="招聘来源")
    posted_date: Optional[str] = Field(default=None, description="发布日期")
    employment_type: Optional[str] = Field(default="全职", description="工作类型")


class CompanyInfo(BaseModel):
    """公司信息"""
    name: str = Field(..., description="公司名称")
    industry: Optional[str] = Field(default=None, description="行业")
    size: Optional[str] = Field(default=None, description="公司规模")
    headquarters: Optional[str] = Field(default=None, description="总部地点")
    description: Optional[str] = Field(default=None, description="公司简介")
    culture: Optional[str] = Field(default=None, description="公司文化/氛围")
    funding_stage: Optional[str] = Field(default=None, description="融资阶段")
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="综合评分")
    pros: List[str] = Field(default_factory=list, description="优势")
    cons: List[str] = Field(default_factory=list, description="劣势/风险")


class SalaryInfo(BaseModel):
    """行业薪资信息"""
    role: str = Field(..., description="职位")
    city: str = Field(..., description="城市")
    experience_level: Optional[str] = Field(default=None, description="经验级别")
    avg_salary: Optional[str] = Field(default=None, description="平均薪资")
    salary_range_low: Optional[int] = Field(default=None, description="薪资下限（元/月）")
    salary_range_high: Optional[int] = Field(default=None, description="薪资上限（元/月）")
    source: Optional[str] = Field(default=None, description="数据来源")
    confidence: Optional[str] = Field(default="medium", description="数据置信度")


class JobTask(BaseModel):
    """每日求职任务"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_index: int = Field(..., description="第几天（从0开始）")
    description: str = Field(..., description="当日任务概述")
    tasks: List[str] = Field(default_factory=list, description="具体任务清单")
    target_companies: List[str] = Field(default_factory=list, description="当日目标公司")
    target_jobs: List[str] = Field(default_factory=list, description="当日目标职位")
    preparation_tips: Optional[str] = Field(default=None, description="当日准备工作提示")


class CareerBudget(BaseModel):
    """求职预算"""
    transportation: int = Field(default=0, description="交通费用估算")
    printing: int = Field(default=0, description="打印/材料费用")
    training: int = Field(default=0, description="培训/课程费用")
    others: int = Field(default=0, description="其他费用")
    total: int = Field(default=0, description="总预算")


class CareerPlan(BaseModel):
    """完整求职计划"""
    target_role: str = Field(..., description="目标职位")
    city: str = Field(..., description="目标城市")
    start_date: str = Field(..., description="开始日期")
    target_days: int = Field(..., description="求职周期（天）")
    jobs: List[JobListing] = Field(default_factory=list, description="推荐职位列表")
    companies: List[CompanyInfo] = Field(default_factory=list, description="目标公司信息")
    salary_info: List[SalaryInfo] = Field(default_factory=list, description="行业薪资数据")
    daily_tasks: List[JobTask] = Field(default_factory=list, description="每日求职任务")
    resume_tips: str = Field(default="", description="简历优化建议")
    interview_prep: str = Field(default="", description="面试准备清单")
    overall_strategy: str = Field(..., description="总体求职策略")
    budget: Optional[CareerBudget] = Field(default=None, description="求职预算")


class CareerRequest(BaseModel):
    """求职规划请求"""
    target_role: str = Field(..., description="目标职位", example="后端开发工程师")
    city: str = Field(..., description="目标城市", example="北京")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD", example="2026-06-15")
    target_days: int = Field(default=7, description="求职周期（天）", ge=1, le=90)
    salary_expectation: str = Field(default="面议", description="薪资期望", example="15k-25k")
    experience_level: str = Field(default="1-3年", description="经验级别", example="1-3年")
    industry: str = Field(default="互联网", description="目标行业")
    preferences: List[str] = Field(default_factory=list, description="偏好标签", example=["大厂", "技术氛围好"])
    free_text_input: Optional[str] = Field(default="", description="额外要求", example="希望找Go或Python方向")

    class Config:
        json_schema_extra = {
            "example": {
                "target_role": "后端开发工程师",
                "city": "北京",
                "start_date": "2026-06-15",
                "target_days": 7,
                "salary_expectation": "15k-25k",
                "experience_level": "1-3年",
                "industry": "互联网",
                "preferences": ["大厂", "技术氛围好"],
                "free_text_input": "希望找Go或Python方向"
            }
        }


class CareerPlanResponse(BaseModel):
    """求职计划响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[CareerPlan] = Field(default=None, description="求职计划数据")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False)
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(default=None, description="错误代码")
