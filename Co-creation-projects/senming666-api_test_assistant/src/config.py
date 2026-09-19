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

# ============ 测试数据配置 ============

# 1x1 透明 PNG 的最小合法图片（base64 编码）
# 文件上传接口（multipart/form-data）需要一个真实文件才能通过后端的内容校验，
# 用这个最小合法图片作为占位测试文件，避免生成器拿不到二进制内容。
MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

# ============ 报告配置 ============

# 测试报告的输出目录
REPORT_OUTPUT_DIR = "reports"

# ============ Agent 配置 ============

# 主智能体名称
AGENT_NAME = "APITestAssistant"
