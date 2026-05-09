"""
智能股票分析助手 — 分析报告数据模型

存储个股深度分析报告，支持报告持久化与历史查询。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.models.database import Base


class AnalysisReport(Base):
    """分析报告表"""

    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="报告ID")
    user_id = Column(String(64), nullable=False, default="default", comment="用户标识")
    stock_code = Column(String(16), nullable=False, comment="股票代码")
    stock_name = Column(String(64), default="", comment="股票名称")
    report_type = Column(String(32), default="full", comment="报告类型: full=完整分析, quick=快速概览")
    summary = Column(String(1024), default="", comment="报告摘要（投资建议一句话）")
    content = Column(Text, default="", comment="报告完整内容（Markdown格式）")
    data_snapshot = Column(Text, default="{}", comment="数据快照（JSON格式，存储查询到的原始数据）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "report_type": self.report_type,
            "summary": self.summary,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
