"""Offline regression tests for the chapter 7 calculator example."""

import math
import unittest

from my_calculator_tool import create_calculator_registry, my_calculate


class CalculatorValidationTests(unittest.TestCase):
    def test_supported_expressions(self):
        cases = {
            "2 + 3": "5",
            "10 - 4": "6",
            "5 * 6": "30",
            "15 / 3": "5.0",
            "sqrt(16) + 2 * 3": "10.0",
            "pi": str(math.pi),
            "2 * pi": str(2 * math.pi),
            "-2 + 3": "1",
            "+2": "2",
            "1 + -2": "-1",
            "-(2 + 3)": "-5",
            "-sqrt(9)": "-3.0",
            "0.5 + 1.25": "1.75",
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(my_calculate(expression), expected)

    def test_invalid_expressions(self):
        expressions = [
            "unknown",
            "unknown(1)",
            "[1, 2]",
            "{'x': 1}",
            "(1, 2)",
            "'a' * 3",
            "b'1'",
            "True + 1",
            "False",
            "None",
            "1j",
            "sqrt",
            "pi()",
            "sqrt(9, ignored=1)",
            "sqrt(x=9)",
            "sqrt(*[9])",
            "sqrt(9, **{})",
            "math.sqrt(9)",
            "1 < 2",
            "1 and 2",
            "2 ** 3",
            "1 // 2",
            "1 % 2",
            "~1",
            "1 / 0",
            "sqrt(-1)",
            "sqrt()",
            "sqrt(1, 2)",
            "2 +",
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertEqual(my_calculate(expression), "计算失败，请检查表达式格式")

    def test_empty_expressions(self):
        for expression in ("", "  ", "\t\n"):
            with self.subTest(expression=expression):
                self.assertEqual(my_calculate(expression), "计算表达式不能为空")

    def test_registered_calculator(self):
        registry = create_calculator_registry()
        cases = {
            "sqrt(16) + 2 * 3": "10.0",
            "-2 + 3": "1",
            "unknown": "计算失败，请检查表达式格式",
            "sqrt(9, ignored=1)": "计算失败，请检查表达式格式",
            "": "计算表达式不能为空",
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(
                    registry.execute_tool("my_calculator", expression), expected
                )


if __name__ == "__main__":
    unittest.main()
