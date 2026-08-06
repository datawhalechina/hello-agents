"""共享数据模型：Pydantic schemas，跨模块复用"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------- 步骤1：PDF 解析 ----------

class Section(BaseModel):
    """论文章节"""
    heading: str = Field(description="章节标题")
    content: str = Field(description="章节正文")
    figure_captions: list[str] = Field(default_factory=list, description="章节内图表标题")


class ParsedPaper(BaseModel):
    """步骤1 输出：解析后的论文"""
    path: str
    title: str
    sections: list[Section]
    parsed_at: datetime = Field(default_factory=datetime.now)


# ---------- 步骤2：结构化抽取 ----------

class FieldSource(BaseModel):
    """字段来源标注，防编造、可回溯"""
    value: str
    source_sections: list[str] = Field(description="原文出处章节")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class PaperRecord(BaseModel):
    """步骤2 输出：单篇论文结构化记录（papers.jsonl 一行一条）"""
    path: str
    title: str
    task_problem: FieldSource = Field(description="研究任务/问题")
    method: FieldSource = Field(description="核心方法")
    key_contributions: FieldSource = Field(description="主要贡献")
    datasets: FieldSource = Field(description="使用的数据集")
    metrics: FieldSource = Field(description="评估指标")
    results: FieldSource = Field(description="实验结果")
    limitations: FieldSource = Field(description="局限性（重点字段，须论文明确承认或可推断）")
    future_work: FieldSource = Field(description="未来工作")
    extracted_at: datetime = Field(default_factory=datetime.now)


# ---------- 步骤4：Gap 识别 ----------

class GapType(str, Enum):
    REPEATED_LIMITATION = "repeated_limitation"  # 重复局限
    METHOD_GAP = "method_gap"                      # 方法空白
    CONTRADICTORY = "contradictory"                # 矛盾结论
    UNFULFILLED_FUTURE = "unfulfilled_future"      # 未兑现的未来工作


class Gap(BaseModel):
    """候选研究空白"""
    description: str
    gap_type: GapType
    source_papers: list[str] = Field(description="来源论文标题列表")
    evidence: str = Field(description="论证")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


# ---------- 步骤5：创新点 ----------

class InnovationSource(str, Enum):
    METHOD_COMBINATION = "method_combination"    # 方法组合
    LIMITATION_FIX = "limitation_fix"            # 局限改进
    CROSS_DOMAIN = "cross_domain"                # 跨域迁移
    NEW_SCENARIO = "new_scenario"                # 新场景应用


class ThreeDScore(BaseModel):
    """三维评分：新颖性/可行性/显著性"""
    novelty: float = Field(ge=0.0, le=10.0)
    feasibility: float = Field(ge=0.0, le=10.0)
    significance: float = Field(ge=0.0, le=10.0)

    @property
    def total(self) -> float:
        return round(self.novelty + self.feasibility + self.significance, 2)


class Innovation(BaseModel):
    """创新点"""
    title: str
    idea: str = Field(description="创新思路")
    source: InnovationSource
    gap_origin: str = Field(description="Gap 来源描述")
    score: ThreeDScore
    novelty_check: Optional[str] = Field(default=None, description="联网新颖性验证结果")
    supporting_evidence: str = Field(default="", description="论据支撑")


# ---------- 步骤6：实验方案 ----------

class ExperimentPlan(BaseModel):
    """实验方案"""
    innovation_title: str
    hypothesis: str = Field(description="研究假设")
    datasets: list[str]
    baselines: list[str] = Field(description="基线方法")
    metrics: list[str]
    ablation: list[str] = Field(description="消融实验设计")
    steps: list[str] = Field(description="实验步骤")
    expected_results: str
    risks: str


# ---------- 评估 ----------

class ToolCallRecord(BaseModel):
    """工具调用记录"""
    tool_name: str
    args_summary: str
    success: bool
    duration_sec: float
    error: Optional[str] = None
    # 工具返回的结构化结果（dict/list/str），供 ReportAgent 整合使用
    result: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class EvaluationReport(BaseModel):
    """评估报告"""
    innovations_scores: list[ThreeDScore]
    tool_call_success_rate: float = Field(description="工具调用成功率 0-1")
    total_tool_calls: int
    failed_tool_calls: int
    avg_confidence: float = Field(description="平均自校验置信度")
    tool_calls: list[ToolCallRecord]


# ---------- 最终报告 ----------

class FinalReport(BaseModel):
    """步骤7 整合输出"""
    background_review: str = Field(description="背景综述")
    innovations: list[Innovation]
    experiment_plans: list[ExperimentPlan]
    references: list[dict] = Field(description="参考文献溯源 {title, path, sections}")
    evaluation: Optional[EvaluationReport] = None
    markdown: str = Field(default="", description="完整 Markdown 报告")
    generated_at: datetime = Field(default_factory=datetime.now)


# ---------- 进度事件 ----------

class StepStage(str, Enum):
    PARSE = "step1_parse"
    EXTRACT = "step2_extract"
    INDEX = "step3_index"
    GAP = "step4_gap"
    INNOVATION = "step5_innovation"
    EXPERIMENT = "step6_experiment"
    INTEGRATE = "step7_integrate"


class ProgressEvent(BaseModel):
    """前端进度推送事件"""
    stage: StepStage
    status: str = Field(description="running/done/failed/degraded")
    message: str
    progress: float = Field(ge=0.0, le=1.0, description="整体进度 0-1")
    payload: Optional[dict[str, Any]] = None
