"""
验证Agent - 负责判断测试结果是否正确

这是"智能体层"里第二个"用工具"的 Agent——
它自己不判断，而是调用 schema_validator 工具去判断。
"""

from src.tools.schema_validator import SchemaValidator


class ValidatorAgent:
    """验证测试结果，判断每个用例是否通过"""

    def __init__(self):
        # 依赖 SchemaValidator 工具：判断对错的活交给它
        self.validator = SchemaValidator()

    def validate(self, execution_results):
        """验证一组执行结果

        Args:
            execution_results: ExecutorAgent 返回的结果列表，
                每个元素是 {"case": {...}, "result": {...}}

        Returns:
            验证结果列表，每个元素是：
            {
                "case": {...},     # 原始用例
                "result": {...},   # 执行结果
                "passed": bool,    # 是否通过
                "errors": [...],   # 失败原因列表（通过时为空）
            }
        """
        validated = []

        for item in execution_results:
            validated.append(self.validate_one(item))

        return validated

    def validate_one(self, item):
        """验证单个执行结果

        Args:
            item: {"case": ..., "result": ...}

        Returns:
            加了 passed/errors 字段的完整结果
        """
        case = item["case"]
        result = item["result"]

        # 从用例里取"期望值"（可能没有，所以用 .get 安全取值）
        expected_status = case.get("expected_status")
        expected_schema = case.get("expected_schema")

        # 调用工具做实际判断
        check = self.validator.validate(
            result,
            expected_status=expected_status,
            expected_schema=expected_schema,
        )

        # 打包返回：用例 + 执行结果 + 验证结论
        return {
            "case": case,
            "result": result,
            "passed": check["success"],
            "errors": check["errors"],
        }
