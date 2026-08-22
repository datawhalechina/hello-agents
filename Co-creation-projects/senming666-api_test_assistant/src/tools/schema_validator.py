"""
Schema 校验工具
负责验证接口返回的数据是否符合文档约定。

这是"工具层"——没有大脑，只会严格地对照规则检查。
"""

import jsonschema
from jsonschema import ValidationError


class SchemaValidator:
    """结果校验工具

    用 JSON Schema 规则来检查接口响应：
    - 状态码是否符合预期
    - 响应体数据结构是否符合约定
    """

    def validate_status_code(self, actual, expected):
        """校验状态码是否符合预期

        Args:
            actual: 实际返回的状态码，如 200
            expected: 期望的状态码，如 200

        Returns:
            (是否通过, 错误信息) —— 通过时错误信息为 None
        """
        if actual == expected:
            return True, None
        return False, f"状态码不符：期望 {expected}，实际 {actual}"

    def validate_body(self, body, schema):
        """校验响应体是否符合 JSON Schema

        Args:
            body: 实际返回的响应体（dict 或字符串）
            schema: JSON Schema 说明书（dict）

        Returns:
            (是否通过, 错误信息)
        """
        # 没有给 schema，就不校验（跳过）
        if schema is None:
            return True, None

        try:
            jsonschema.validate(body, schema)
            return True, None
        except ValidationError as e:
            # e.message 是 jsonschema 给的"哪里不符合"的说明
            return False, f"数据结构不符：{e.message}"

    def validate(self, result, expected_status=None, expected_schema=None):
        """综合校验一个请求结果

        Args:
            result: http_client 返回的标准化结果字典
            expected_status: 期望的状态码（可选）
            expected_schema: 期望的 JSON Schema（可选）

        Returns:
            校验结果字典：
            {
                "success": bool,        # 是否全部通过
                "errors": [str, ...]    # 所有不通过的原因列表
            }
        """
        errors = []

        # 1. 请求本身是否成功（网络层）
        if not result["success"]:
            errors.append(f"请求失败：{result['error']}")
            # 请求都失败了，后面的状态码和结构检查没有意义，直接返回
            return {"success": False, "errors": errors}

        # 2. 状态码检查
        if expected_status is not None:
            ok, msg = self.validate_status_code(
                result["status_code"], expected_status
            )
            if not ok:
                errors.append(msg)

        # 3. 响应体结构检查
        if expected_schema is not None:
            ok, msg = self.validate_body(result["body"], expected_schema)
            if not ok:
                errors.append(msg)

        return {
            "success": len(errors) == 0,
            "errors": errors,
        }
