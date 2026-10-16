# my_calculator_tool.py
import ast
import operator
import math
from hello_agents import ToolRegistry

def my_calculate(expression: str) -> str:
    """简单的数学计算函数"""
    if not expression.strip():
        return "计算表达式不能为空"

    # 支持的基本运算
    operators = {
        ast.Add: operator.add,      # +
        ast.Sub: operator.sub,      # -
        ast.Mult: operator.mul,     # *
        ast.Div: operator.truediv,  # /
        ast.UAdd: operator.pos,     # 一元 +
        ast.USub: operator.neg,     # 一元 -
    }

    # 支持的基本函数
    functions = {
        'sqrt': math.sqrt,
        'pi': math.pi,
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except Exception:
        return "计算失败，请检查表达式格式"

def _eval_node(node, operators, functions):
    """简化的表达式求值"""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in operators:
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)
        op = operators[type(node.op)]
        return op(left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in operators:
        operand = _eval_node(node.operand, operators, functions)
        return operators[type(node.op)](operand)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        func = functions.get(node.func.id)
        if callable(func):
            args = [_eval_node(arg, operators, functions) for arg in node.args]
            return func(*args)
    elif isinstance(node, ast.Name):
        if node.id in functions and not callable(functions[node.id]):
            return functions[node.id]

    raise ValueError("不支持的计算表达式")

def create_calculator_registry():
    """创建包含计算器的工具注册表"""
    registry = ToolRegistry()

    # 注册计算器函数
    registry.register_function(
        name="my_calculator",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和sqrt函数",
        func=my_calculate
    )

    return registry
