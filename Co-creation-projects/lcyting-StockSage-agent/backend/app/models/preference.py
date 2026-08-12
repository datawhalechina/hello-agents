"""
智能股票分析助手 — 用户偏好数据模型

定义用户投资偏好、风控参数、界面偏好等持久化存储结构。
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, func
from app.models.database import Base


class UserPreference(Base):
    """用户偏好模型"""

    __tablename__ = "user_preferences"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联用户（当前简化：单用户模式，后续可扩展多用户）
    user_id = Column(String(64), default="default", unique=True, nullable=False, comment="用户ID")

    # =========================================================================
    # 投资偏好
    # =========================================================================
    risk_tolerance = Column(
        String(20), default="moderate", nullable=False,
        comment="风险承受度: conservative / moderate / aggressive"
    )
    investment_style = Column(
        String(20), default="blend", nullable=False,
        comment="投资风格: value / growth / momentum / dividend / blend"
    )
    preferred_sectors = Column(
        Text, default="[]",
        comment="偏好行业 (JSON数组)"
    )
    excluded_sectors = Column(
        Text, default="[]",
        comment="排除行业 (JSON数组)"
    )
    investment_horizon = Column(
        String(20), default="medium",
        comment="投资期限: short / medium / long"
    )
    target_return_rate = Column(
        Float, default=10.0, nullable=False,
        comment="目标年化收益率(%)"
    )

    # =========================================================================
    # 风控参数
    # =========================================================================
    max_position_ratio = Column(
        Float, default=30.0, nullable=False,
        comment="单只股票最大仓位比例(%)"
    )
    max_drawdown_limit = Column(
        Float, default=-15.0, nullable=False,
        comment="最大回撤预警线(%)"
    )

    # =========================================================================
    # 通知设置
    # =========================================================================
    notification_enabled = Column(
        Boolean, default=True, nullable=False,
        comment="是否启用通知"
    )
    notification_channels = Column(
        Text, default='["push"]',
        comment="通知渠道 (JSON: email/sms/push)"
    )
    market_alert_threshold = Column(
        Float, default=5.0, nullable=False,
        comment="行情异动提醒阈值(%)"
    )

    # =========================================================================
    # 界面偏好
    # =========================================================================
    language = Column(
        String(10), default="zh", nullable=False,
        comment="界面语言: zh / en"
    )
    theme = Column(
        String(10), default="auto", nullable=False,
        comment="主题: light / dark / auto"
    )
    default_view = Column(
        String(20), default="dashboard", nullable=False,
        comment="默认首页: dashboard / watchlist"
    )

    # =========================================================================
    # 时间戳
    # =========================================================================
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def to_dict(self) -> dict:
        """转为字典（用于API响应）"""
        import json

        return {
            "id": self.id,
            "user_id": self.user_id,
            "risk_tolerance": self.risk_tolerance,
            "investment_style": self.investment_style,
            "preferred_sectors": json.loads(self.preferred_sectors),
            "excluded_sectors": json.loads(self.excluded_sectors),
            "investment_horizon": self.investment_horizon,
            "target_return_rate": self.target_return_rate,
            "max_position_ratio": self.max_position_ratio,
            "max_drawdown_limit": self.max_drawdown_limit,
            "notification_enabled": self.notification_enabled,
            "notification_channels": json.loads(self.notification_channels),
            "market_alert_threshold": self.market_alert_threshold,
            "language": self.language,
            "theme": self.theme,
            "default_view": self.default_view,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create_default(cls, user_id: str = "default") -> "UserPreference":
        """创建默认偏好实例"""
        return cls(
            user_id=user_id,
            risk_tolerance="moderate",
            investment_style="blend",
            preferred_sectors="[]",
            excluded_sectors="[]",
            investment_horizon="medium",
            target_return_rate=10.0,
            max_position_ratio=30.0,
            max_drawdown_limit=-15.0,
            notification_enabled=True,
            notification_channels='["push"]',
            market_alert_threshold=5.0,
            language="zh",
            theme="auto",
            default_view="dashboard",
        )
