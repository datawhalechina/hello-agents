"""
分析历史记录 ORM 模型（实现方案约定文件名）
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.models.database import Base


class AnalysisHistory(Base):
    """分析历史记录表 — 按天存储各类分析报告"""

    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    user_id = Column(String(64), nullable=False, default="default", comment="用户标识")
    date = Column(String(16), nullable=False, comment="日期 yyyy-mm-dd")
    type = Column(String(32), nullable=False, comment="类型: sentiment/data_analysis/buffett/chat")
    stock_code = Column(String(16), nullable=True, comment="股票代码")
    stock_name = Column(String(64), nullable=True, comment="股票名称")
    title = Column(String(256), nullable=True, comment="标题")
    content = Column(Text, nullable=False, comment="内容（Markdown格式）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date,
            "type": self.type,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
