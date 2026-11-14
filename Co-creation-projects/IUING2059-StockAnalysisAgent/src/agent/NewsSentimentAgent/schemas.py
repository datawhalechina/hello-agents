# src/agent/NewsSentimentAgent/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Literal, Optional

from src.common.agent_result import BaseAgentOutput, SafeFloat


# ---------------- 基础数据结构 ----------------

class RawNewsSchema(BaseModel):
    """从 akshare 获取的原始新闻数据结构"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(description="新闻标题")
    content: Optional[str] = Field(default=None, description="新闻正文或摘要")
    publish_time: Optional[str] = Field(default=None, description="发布时间")
    source: Optional[str] = Field(default=None, description="新闻来源")
    url: str = Field(description="新闻链接")


# ---------------- LLM 情感分析结构 ----------------

class SingleNewsAnalysisSchema(BaseModel):
    """大模型对单条新闻的分析结果"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(description="对应的新闻标题")
    sentiment_label: Literal["positive", "negative", "neutral"] = Field(
        description="情绪标签：positive / negative / neutral"
    )
    sentiment_score: SafeFloat = Field(default=None, description="情绪得分，范围 -1.0 到 1.0")
    impact_judgment: Literal["利好", "利空", "中性"] = Field(
        description="利好/利空判断：利好 / 利空 / 中性"
    )
    impact_reason: Optional[str] = Field(default=None, description="判断依据（一句话说明）")
    one_line_summary: str = Field(description="一句话中文摘要，30字以内")
    confidence: SafeFloat = Field(
        default=None, ge=0.0, le=1.0, description="模型判断的置信度，0.0 到 1.0"
    )


# ---------------- 聚合输出结构 ----------------

class NewsSentimentResultSchema(BaseAgentOutput):
    """给主 Agent 的最终汇总输出（继承 BaseAgentOutput，统一 to_json）。"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    # 数据统计
    analyzed_count: int = Field(default=0, description="成功完成情感分析的新闻总数")
    failed_count: int = Field(default=0, description="分析失败的条数")

    # 整体舆情信号
    overall_sentiment: Optional[Literal["偏多", "偏空", "中性"]] = Field(
        default=None, description="整体舆情倾向：偏多 / 偏空 / 中性"
    )
    weighted_sentiment_score: SafeFloat = Field(default=None, description="加权综合得分")
    positive_ratio: SafeFloat = Field(default=None, description="利好新闻占比")
    negative_ratio: SafeFloat = Field(default=None, description="利空新闻占比")
    neutral_ratio: SafeFloat = Field(default=None, description="中性新闻占比")

    # 核心驱动新闻（主 Agent 写报告直接引用）
    top_positive_news: List[SingleNewsAnalysisSchema] = Field(
        default_factory=list, description="最重要的 3 条利好新闻"
    )
    top_negative_news: List[SingleNewsAnalysisSchema] = Field(
        default_factory=list, description="最重要的 3 条利空新闻"
    )

    # 全部明细
    articles: List[SingleNewsAnalysisSchema] = Field(
        default_factory=list, description="全部新闻的逐条分析结果"
    )

    # 👇 补上这一行!（按截图要求添加）
    error_msg: Optional[str] = Field(default=None, description="错误信息记录")