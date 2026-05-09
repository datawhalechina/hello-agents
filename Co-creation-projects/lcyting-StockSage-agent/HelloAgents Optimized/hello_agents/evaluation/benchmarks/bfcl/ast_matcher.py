"""
BFCL AST 匹配算法模块

提供改进的抽象语法树匹配，比简单字符串匹配更智能：
1. 常量表达式求值：2+3 → 5
2. 类型感知比较：数值容差、字符串归一化、列表排序后比较
3. 参数别名映射：loc → location
4. 默认参数补全：未提供的可选参数用默认值填充
5. 浮点数容差比较
6. 忽略参数顺序、格式差异
"""

import ast
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from numbers import Number


class ASTMatcher:
    """改进的 AST 匹配器

    支持语义等价的函数调用比较，减少假阳性和假阴性。
    """

    def __init__(
        self,
        param_aliases: Optional[Dict[str, List[str]]] = None,
        default_params: Optional[Dict[str, Dict[str, Any]]] = None,
        float_tolerance: float = 1e-9,
        normalize_strings: bool = True,
        order_sensitive: bool = False,
    ):
        """
        Args:
            param_aliases: 参数别名映射，如 {"location": ["loc", "city"]}
            default_params: 函数默认参数，如 {"func": {"optional_param": "default_value"}}
            float_tolerance: 浮点数比较容差
            normalize_strings: 是否归一化字符串（去空格、转小写）
            order_sensitive: 是否对参数顺序敏感（Python 位置参数需要）
        """
        self.param_aliases = param_aliases or {}
        self.default_params = default_params or {}
        self.float_tolerance = float_tolerance
        self.normalize_strings = normalize_strings
        self.order_sensitive = order_sensitive

    def match(
        self,
        predicted: List[Dict[str, Any]],
        expected: Union[List[Dict[str, Any]], List[str]],
    ) -> Tuple[bool, float]:
        """匹配预测与期望的函数调用

        Args:
            predicted: [{"name": "func", "arguments": {"param": value}}]
            expected: BFCL v4 格式 [{"func_name": {"param": [values]}}]
                      或字符串格式 ["func(param=value)"]

        Returns:
            (是否完全匹配, 匹配得分 0~1)
        """
        if not expected:
            return len(predicted) == 0, 1.0 if len(predicted) == 0 else 0.0

        try:
            if expected and isinstance(expected[0], dict):
                return self._match_bfcl_v4(predicted, expected)
            else:
                return self._match_strings(predicted, expected)
        except Exception:
            return False, 0.0

    def _match_bfcl_v4(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
    ) -> Tuple[bool, float]:
        """匹配 BFCL v4 格式

        predicted:  [{"name": "func_name", "arguments": {"param": value}}]
        expected:   [{"func_name": {"param": [value1, value2]}}]
        """
        if len(predicted) != len(expected):
            return False, 0.0

        matches = 0
        used = set()

        for pred_call in predicted:
            if not isinstance(pred_call, dict) or "name" not in pred_call:
                continue

            pred_name = pred_call["name"]
            pred_args = pred_call.get("arguments", {})

            for idx, exp_call in enumerate(expected):
                if idx in used:
                    continue
                if not isinstance(exp_call, dict):
                    continue

                for exp_name, exp_params in exp_call.items():
                    if (
                        exp_name != pred_name
                        and pred_name not in self.param_aliases.get(exp_name, [])
                    ):
                        continue

                    if self._compare_parameters(pred_args, exp_params, exp_name):
                        matches += 1
                        used.add(idx)
                        break

        success = matches == len(expected)
        score = matches / len(expected) if expected else 0.0
        return success, score

    def _match_strings(
        self,
        predicted: List[Dict[str, Any]],
        expected: List[str],
    ) -> Tuple[bool, float]:
        """匹配字符串格式"""
        if len(predicted) != len(expected):
            return False, 0.0

        matches = 0
        for pred_call in predicted:
            if not isinstance(pred_call, dict) or "name" not in pred_call:
                continue

            for exp_str in expected:
                if self._ast_string_match(pred_call, exp_str):
                    matches += 1
                    break

        success = matches == len(expected)
        score = matches / len(expected) if expected else 0.0
        return success, score

    def _ast_string_match(self, predicted: Dict[str, Any], expected_str: str) -> bool:
        """将预测 dict 与字符串格式的期望进行 AST 比较"""
        pred_name = predicted.get("name", "")
        pred_args = predicted.get("arguments", {})

        try:
            exp_ast = ast.parse(expected_str.strip(), mode="eval")
            if not isinstance(exp_ast.body, ast.Call):
                return expected_str.strip() == f"{pred_name}()" and not pred_args

            exp_call = exp_ast.body
            exp_name = self._get_func_name(exp_call)
            if exp_name is None or (
                exp_name != pred_name
                and pred_name not in self.param_aliases.get(exp_name, [])
            ):
                return False

            exp_args = self._parse_ast_args(exp_call)
            return self._compare_parameters(pred_args, exp_args, exp_name)
        except SyntaxError:
            return False

    def _get_func_name(self, call_node: ast.Call) -> Optional[str]:
        """从 AST Call 节点提取函数名"""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    def _parse_ast_args(self, call_node: ast.Call) -> Dict[str, Any]:
        """将 AST Call 节点的参数解析为 dict

        处理位置参数和关键字参数：
        - func(a=1, b=2) -> {"a": 1, "b": 2}
        - func(1, 2) -> {"_pos_0": 1, "_pos_1": 2} （位置参数用 _pos_N 标记）
        """
        args = {}
        for i, arg in enumerate(call_node.args):
            value = self._eval_ast_node(arg)
            key = f"_pos_{i}" if self.order_sensitive else "_pos"
            args[key] = value

        for kw in call_node.keywords:
            if kw.arg is not None:
                args[kw.arg] = self._eval_ast_node(kw.value)

        return args

    def _eval_ast_node(self, node: ast.AST) -> Any:
        """对 AST 节点进行常量折叠求值

        将常量表达式化简：
        - 2+3 -> 5
        - "hello" + " world" -> "hello world"
        - [1, 2, 3] -> [1, 2, 3]
        - 非折叠表达式原样保留
        """
        try:
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.UnaryOp):
                operand = self._eval_ast_node(node.operand)
                if isinstance(node.op, ast.UAdd):
                    return +operand
                elif isinstance(node.op, ast.USub):
                    return -operand
                elif isinstance(node.op, ast.Not):
                    return not operand
            elif isinstance(node, ast.BinOp):
                left = self._eval_ast_node(node.left)
                right = self._eval_ast_node(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    return left / right
                elif isinstance(node.op, ast.FloorDiv):
                    return left // right
                elif isinstance(node.op, ast.Mod):
                    return left % right
                elif isinstance(node.op, ast.Pow):
                    return left**right
            elif isinstance(node, ast.List):
                return [self._eval_ast_node(el) for el in node.elts]
            elif isinstance(node, ast.Tuple):
                return tuple(self._eval_ast_node(el) for el in node.elts)
            elif isinstance(node, ast.Dict):
                return {
                    self._eval_ast_node(k): self._eval_ast_node(v)
                    for k, v in zip(node.keys, node.values)
                    if k is not None
                }
            elif isinstance(node, ast.Str):
                return node.s
            elif isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.NameConstant):
                return node.value
            elif isinstance(node, ast.Name):
                return node.id
        except Exception:
            pass
        return ast.dump(node)

    def _compare_parameters(
        self,
        pred_params: Dict[str, Any],
        exp_params: Dict[str, Any],
        func_name: str = "",
    ) -> bool:
        """比较参数，支持别名和默认值补全"""
        exp_params = self._normalize_exp_params(exp_params)
        pred_params = dict(pred_params)

        # 补全默认参数
        defaults = self.default_params.get(func_name, {})
        for key, default_val in defaults.items():
            if key not in pred_params:
                pred_params[key] = default_val

        # 归一化参数名（处理别名）
        resolved_pred = self._resolve_param_aliases(pred_params, func_name)

        # 检查 exp_params 中的每个键在 pred_params 中是否存在
        for param_name, expected_values in exp_params.items():
            if isinstance(expected_values, list):
                param_found = any(
                    self._values_match(resolved_pred.get(pn), exp_val)
                    for pn in resolved_pred
                    for exp_val in expected_values
                )
            else:
                param_found = any(
                    self._values_match(resolved_pred.get(pn), expected_values)
                    for pn in resolved_pred
                )

            if not param_found:
                return False

        # 如果开启顺序敏感，额外检查位置参数顺序
        if self.order_sensitive:
            if not self._check_positional_order(pred_params, exp_params):
                return False

        return True

    def _normalize_exp_params(self, exp_params: Dict[str, Any]) -> Dict[str, Any]:
        """归一化期望参数字典

        BFCL v4 格式语义：
        - {"param": [val1, val2]} 表示 param 可接受 val1 或 val2
        - {"param": [[1,2,3]]} 表示 param 期望值为列表 [1,2,3]

        因此单元素列表只有当元素本身不是 list 时才 unwrap。
        """
        normalized = {}
        for key, value in exp_params.items():
            if (
                isinstance(value, list)
                and len(value) == 1
                and not isinstance(value[0], list)
            ):
                normalized[key] = value[0]
            else:
                normalized[key] = value
        return normalized

    def _resolve_param_aliases(
        self, params: Dict[str, Any], func_name: str
    ) -> Dict[str, Any]:
        """将参数名归一化到规范名称"""
        resolved = {}
        reverse_map = {}
        for canonical, aliases in self.param_aliases.items():
            for alias in aliases:
                reverse_map[alias] = canonical

        for key, value in params.items():
            canonical_key = reverse_map.get(key, key)
            resolved[canonical_key] = value

        return resolved

    def _values_match(self, v1: Any, v2: Any) -> bool:
        """智能值比较

        处理：
        - 浮点数容差
        - 字符串归一化
        - 列表排序后比较
        - 类型转换
        """
        if v1 is None and v2 is None:
            return True
        if v1 is None or v2 is None:
            return False

        # 数值比较（含浮点容差）
        if isinstance(v1, Number) and isinstance(v2, Number):
            if isinstance(v1, float) or isinstance(v2, float):
                return abs(float(v1) - float(v2)) < self.float_tolerance
            return v1 == v2

        # 字符串比较（归一化）
        if isinstance(v1, str) and isinstance(v2, str):
            return self._strings_match(v1, v2)

        # 列表比较（排序后）
        if isinstance(v1, list) and isinstance(v2, list):
            if len(v1) != len(v2):
                return False
            try:
                sorted_v1 = sorted(v1, key=str)
                sorted_v2 = sorted(v2, key=str)
            except TypeError:
                sorted_v1, sorted_v2 = v1, v2
            return all(self._values_match(a, b) for a, b in zip(sorted_v1, sorted_v2))

        # 字典比较
        if isinstance(v1, dict) and isinstance(v2, dict):
            if v1.keys() != v2.keys():
                return False
            return all(self._values_match(v1[k], v2[k]) for k in v1)

        # bool 特殊处理
        if isinstance(v1, bool) and isinstance(v2, bool):
            return v1 == v2

        return v1 == v2

    def _strings_match(self, s1: str, s2: str) -> bool:
        """字符串匹配（归一化后比较）"""
        if not self.normalize_strings:
            return s1 == s2

        def normalize(s: str) -> str:
            s = s.strip().lower()
            s = re.sub(r"\s+", " ", s)
            s = s.rstrip(".,;:!?")
            articles = ["the ", "a ", "an "]
            for art in articles:
                if s.startswith(art):
                    s = s[len(art) :]
                    break
            return s

        return normalize(s1) == normalize(s2)

    def _check_positional_order(
        self,
        pred_params: Dict[str, Any],
        exp_params: Dict[str, Any],
    ) -> bool:
        """检查位置参数顺序（order_sensitive=True 时使用）"""
        pred_pos = [(k, v) for k, v in pred_params.items() if k.startswith("_pos_")]
        exp_pos = [(k, v) for k, v in exp_params.items() if k.startswith("_pos_")]

        if len(pred_pos) != len(exp_pos):
            return len(pred_pos) == 0

        for (pk, pv), (ek, ev) in zip(pred_pos, exp_pos):
            if not self._values_match(pv, ev):
                return False
        return True


def create_default_matcher() -> ASTMatcher:
    """创建默认配置的 AST 匹配器"""
    return ASTMatcher(
        param_aliases={
            "location": ["loc", "city", "place", "address"],
            "temperature": ["temp", "t"],
            "query": ["q", "search_query", "keyword"],
            "email": ["mail", "recipient"],
            "date": ["dt", "day"],
            "time": ["tm"],
        },
        default_params={},
        float_tolerance=1e-9,
        normalize_strings=True,
        order_sensitive=False,
    )
