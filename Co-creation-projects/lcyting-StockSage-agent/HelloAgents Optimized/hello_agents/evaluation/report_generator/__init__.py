"""评估报告生成系统

根据受众类型自动生成不同详细程度的报告：
- 开发者报告：技术深度，失败样本+错误分布+修复建议
- 产品经理报告：业务视角，核心指标+版本对比+发布建议
- 用户报告：极简可视化，状态卡片+雷达图

使用示例：
    from hello_agents.evaluation.report_generator import ReportGenerator

    gen = ReportGenerator()
    dev_report = gen.generate(data, audience="developer")
    pm_report = gen.generate(data, audience="product")
    user_report = gen.generate(data, audience="user")
"""

from .generator import (
    ReportGenerator,
    report_for_developer,
    report_for_product,
    report_for_user,
)

__all__ = [
    "ReportGenerator",
    "report_for_developer",
    "report_for_product",
    "report_for_user",
]
