"""
配置常量文件
集中管理项目中用到的所有固定常量，避免"魔法数字"散落在代码各处。

用法：其他文件里写  from src.config import REQUEST_TIMEOUT
"""

# ============ HTTP 请求配置 ============

# 单个接口测试的默认超时时间（秒）
REQUEST_TIMEOUT = 30

# 请求失败后的最大重试次数
REQUEST_MAX_RETRIES = 2

# 并发执行测试的最大线程数（控制同时发几个请求）
MAX_CONCURRENCY = 5

# ============ 测试用例生成配置 ============

# 每个接口默认生成多少个测试用例
TEST_CASES_PER_ENDPOINT = 3

# 用例类型：正常 / 边界 / 异常
CASE_TYPES = ["normal", "boundary", "error"]

# ============ 报告配置 ============

# 测试报告的输出目录
REPORT_OUTPUT_DIR = "reports"

# ============ Agent 配置 ============

# 主智能体名称
AGENT_NAME = "APITestAssistant"
