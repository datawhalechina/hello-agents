"""
BFCL 扩展评估模块

提供三个扩展评估功能：
1. 调用顺序验证（OrderValidator）：检查有依赖关系的多个工具调用的执行顺序
2. 调用效率评估（EfficiencyAnalyzer）：评估是否使用了最少的调用次数
3. 错误分析报告（ErrorAnalyzer）：生成详细的错误类型分类统计
"""

import json
from typing import Any, Dict, List, Optional, Set
from collections import Counter, defaultdict
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 1. 调用顺序验证器
# ---------------------------------------------------------------------------


@dataclass
class DependencyRule:
    """描述两个函数调用之间的依赖关系

    producer: 先执行的函数名（产出数据）
    consumer: 后执行的函数名（消费数据）
    param_mapping: producer 输出参数名 → consumer 输入参数名的映射
    """

    producer: str
    consumer: str
    param_mapping: Dict[str, str]


@dataclass
class OrderResult:
    """顺序验证结果"""

    correct: bool
    violations: List[str] = field(default_factory=list)
    actual_order: List[str] = field(default_factory=list)
    expected_order: List[str] = field(default_factory=list)
    score: float = 1.0


class OrderValidator:
    """调用顺序验证器

    检测有依赖关系的多个工具调用的执行顺序是否正确。
    支持两种模式：
    - strict: 必须完全按依赖顺序（如 multiple_edge_1: power → is_prime → factorize）
    - relaxed: 仅检查违反依赖的情况，不要求全覆盖（默认）
    """

    # 预定义的常见依赖规则
    COMMON_RULES = [
        # 搜索 → 过滤
        DependencyRule("search_books", "filter_books", {"books": "books"}),
        DependencyRule("search_flight", "book_seat", {"flight_id": "flight_id"}),
        # 计算 → 下一步计算
        DependencyRule("power", "is_prime", {"result": "n"}),
        DependencyRule("power", "factorize", {"result": "n"}),
        DependencyRule("is_prime", "factorize", {"number": "n"}),
        # 折扣 → 计税 → 四舍五入
        DependencyRule("apply_discount", "apply_tax", {"discounted_price": "price"}),
        DependencyRule("apply_tax", "round_price", {"price_after_tax": "price"}),
    ]

    def __init__(
        self,
        custom_rules: Optional[List[DependencyRule]] = None,
        mode: str = "relaxed",
    ):
        self.rules = custom_rules or self.COMMON_RULES
        self.mode = mode

    def validate(
        self,
        predicted: List[Dict[str, Any]],
        expected: Optional[List[Dict]] = None,
    ) -> OrderResult:
        """验证 predicted 中各函数调用的顺序

        从 predicted 中提取函数名序列，然后检查：
        1. 是否存在已知的依赖规则适用于这些函数
        2. 如果存在依赖，producer 是否在 consumer 之前

        Args:
            predicted: [{"name": "func_name", "arguments": {...}}]
            expected: [{"func_name": {"param": [...]}}]（可选，用于 strict 模式）

        Returns:
            OrderResult
        """
        actual_order = [
            call.get("name", "") for call in predicted if isinstance(call, dict)
        ]
        violations = []
        score = 1.0

        if self.mode == "strict" and expected:
            expected_order = self._extract_expected_order(expected)
            if expected_order and actual_order != expected_order:
                violations.append(
                    f"调用顺序不匹配: 期望 {expected_order}, 实际 {actual_order}"
                )
                score = 0.0

        # 检查已知依赖规则
        used_rules = self._find_applicable_rules(actual_order)
        for rule in used_rules:
            producer_idx = self._last_position(actual_order, rule.producer)
            consumer_idx = self._first_position(actual_order, rule.consumer)
            if producer_idx == -1:
                violations.append(f"缺少依赖提供者: {rule.producer}")
                score = 0.0
            elif consumer_idx == -1:
                if self.mode == "strict":
                    violations.append(f"缺少依赖消费者: {rule.consumer}")
                    score = 0.0
            elif producer_idx > consumer_idx:
                violations.append(
                    f"顺序错误: {rule.producer} (位置 {producer_idx}) 应在 "
                    f"{rule.consumer} (位置 {consumer_idx}) 之前"
                )
                score = 0.0

        correct = len(violations) == 0
        return OrderResult(
            correct=correct,
            violations=violations,
            actual_order=actual_order,
            expected_order=self._extract_expected_order(expected) if expected else [],
            score=score,
        )

    def _extract_expected_order(self, expected: List[Dict]) -> List[str]:
        """从 expected 中提取期望的函数名顺序"""
        order = []
        for entry in expected:
            if isinstance(entry, dict):
                for func_name in entry:
                    order.append(func_name)
        return order

    def _find_applicable_rules(self, func_names: List[str]) -> List[DependencyRule]:
        """找出适用于当前函数调用序列的依赖规则

        仅当规则中的 producer 和 consumer 都在调用序列中出现时才适用。
        """
        name_set = set(func_names)
        applicable = []
        for rule in self.rules:
            if rule.producer in name_set and rule.consumer in name_set:
                applicable.append(rule)
        return applicable

    @staticmethod
    def _last_position(names: List[str], target: str) -> int:
        """返回 target 在 names 中最后一次出现的位置"""
        for i in range(len(names) - 1, -1, -1):
            if names[i] == target:
                return i
        return -1

    @staticmethod
    def _first_position(names: List[str], target: str) -> int:
        """返回 target 在 names 中第一次出现的位置"""
        try:
            return names.index(target)
        except ValueError:
            return -1


# ---------------------------------------------------------------------------
# 2. 调用效率评估器
# ---------------------------------------------------------------------------


@dataclass
class EfficiencyResult:
    """效率评估结果"""

    is_optimal: bool
    actual_calls: int
    optimal_calls: int
    redundant_calls: List[Dict[str, Any]] = field(default_factory=list)
    unnecessary_redundancy: bool = False
    missed_parallelization: bool = False
    score: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)


class EfficiencyAnalyzer:
    """调用效率评估器

    评估智能体是否使用了最少数量的函数调用。
    三种效率问题：
    1. 冗余调用：同一函数同一参数被多次调用（可缓存合并）
    2. 不必要的冗余：本可用批量 API 却逐个调用
    3. 遗漏并行化：本可并行的调用被串行执行（不扣分，仅记录）
    """

    # 已知的批量 API 替代模式：{逐个调用函数: 批量调用函数}
    BATCH_ALTERNATIVES = {
        "send_email": "send_bulk_email",
        "book_seat": "book_seats",
    }

    # 已知的无副作用的纯查询函数（可缓存）
    PURE_QUERY_FUNCTIONS = {
        "get_weather",
        "get_local_time",
        "search_books",
        "search_flight",
        "get_price",
    }

    def __init__(self, custom_batch_map: Optional[Dict[str, str]] = None):
        if custom_batch_map:
            self.batch_map = custom_batch_map
        else:
            self.batch_map = dict(self.BATCH_ALTERNATIVES)

    def analyze(
        self,
        predicted: List[Dict[str, Any]],
        expected: List,
    ) -> EfficiencyResult:
        """分析调用效率

        从 predicted 中检测：
        1. 冗余调用：纯查询函数传入完全相同参数的重复调用
        2. 冗余 vs 期望调用次数的对比
        3. 是否有批量 API 替代方案

        Args:
            predicted: [{"name": "func_name", "arguments": {...}}]
            expected: ground truth

        Returns:
            EfficiencyResult
        """
        actual_count = len(predicted)
        redundant = []

        # 检测冗余调用（纯查询函数+相同参数）
        seen_signatures = Counter()
        for call in predicted:
            sig = self._call_signature(call)
            seen_signatures[sig] += 1

        for sig, count in seen_signatures.items():
            if count > 1:
                func_name = sig.split("|")[0]
                if func_name in self.PURE_QUERY_FUNCTIONS:
                    redundant.append(
                        {
                            "signature": sig,
                            "count": count,
                            "reason": f"{func_name} 被调用了 {count} 次，但前 {count - 1} 次结果可缓存复用",
                        }
                    )

        # 检测尝试批量替代
        unnecessary_redundancy = False
        individual_calls = defaultdict(int)
        for call in predicted:
            name = call.get("name", "")
            if name in self.batch_map:
                individual_calls[name] += 1
        for name, count in individual_calls.items():
            if count > 1:
                batch_name = self.batch_map[name]
                unnecessary_redundancy = True
                redundant.append(
                    {
                        "signature": f"{name} x{count}",
                        "count": count,
                        "reason": f"推荐使用 {batch_name} 批量调用替代 {count} 次 {name} 单独调用",
                    }
                )

        # 计算最优调用次数
        is_optimal = True
        if redundant:
            is_optimal = False

        if expected:
            expected_count = len(expected)
            if actual_count > expected_count:
                is_optimal = False
                redundant.append(
                    {
                        "signature": "overall",
                        "count": actual_count - expected_count,
                        "reason": f"实际调用 {actual_count} 次，期望 {expected_count} 次，多出 {actual_count - expected_count} 次",
                    }
                )
            elif actual_count < expected_count:
                redundant.append(
                    {
                        "signature": "overall",
                        "count": expected_count - actual_count,
                        "reason": f"实际调用 {actual_count} 次，期望 {expected_count} 次，缺少 {expected_count - actual_count} 次",
                    }
                )

        optimal_calls_count = expected_count if expected else actual_count
        score = 1.0 if is_optimal else 0.5

        return EfficiencyResult(
            is_optimal=is_optimal,
            actual_calls=actual_count,
            optimal_calls=optimal_calls_count,
            redundant_calls=redundant,
            unnecessary_redundancy=unnecessary_redundancy,
            score=score,
            details={
                "redundant_count": len(redundant),
                "has_unnecessary_redundancy": unnecessary_redundancy,
            },
        )

    def _call_signature(self, call: Dict) -> str:
        """生成函数调用的唯一签名（函数名 + JSON 序列化的参数）"""
        name = call.get("name", "")
        args = call.get("arguments", {})
        # 对参数按键排序，确保相同参数的不同顺序得到相同签名
        sorted_args = json.dumps(args, sort_keys=True, ensure_ascii=False)
        return f"{name}|{sorted_args}"

    def _build_optimal_call_set(self, expected: List) -> Set[str]:
        """从 expected 构建最优调用集合"""
        optimal = set()
        for entry in expected:
            if isinstance(entry, dict):
                for func_name, params in entry.items():
                    sorted_params = json.dumps(params, sort_keys=True)
                    optimal.add(f"{func_name}|{sorted_params}")
            elif isinstance(entry, str):
                optimal.add(entry)
        return optimal


# ---------------------------------------------------------------------------
# 3. 错误分析报告生成器
# ---------------------------------------------------------------------------


@dataclass
class ErrorCategory:
    """错误类别定义"""

    name: str
    description: str
    detect: callable  # (predicted, expected) -> bool


class ErrorAnalyzer:
    """详细错误分析报告生成器

    对每条评估失败的样本进行分类，统计最常见的错误类型。
    """

    ERROR_CATEGORIES = [
        ErrorCategory(
            "missing_call",
            "遗漏调用",
            lambda p, e: (
                (p is not None and isinstance(e, list) and len(p) < len(e))
                or (p is None and isinstance(e, list) and len(e) > 0)
            ),
        ),
        ErrorCategory(
            "extra_call",
            "多余调用",
            lambda p, e: (
                isinstance(p, list) and isinstance(e, list) and len(p) > len(e)
            ),
        ),
        ErrorCategory(
            "wrong_function",
            "函数名错误",
            lambda p, e: (
                len(p) == len(e)
                and isinstance(e, list)
                and any(
                    p[i].get("name") != list(e[i].keys())[0]
                    if isinstance(e[i], dict) and isinstance(p[i], dict)
                    else False
                    for i in range(min(len(p), len(e)))
                )
            ),
        ),
        ErrorCategory(
            "wrong_param_name",
            "参数名错误",
            lambda p, e: _check_param_error(p, e, check_type="name"),
        ),
        ErrorCategory(
            "wrong_param_value",
            "参数值错误",
            lambda p, e: _check_param_error(p, e, check_type="value"),
        ),
        ErrorCategory(
            "missing_param",
            "缺失参数",
            lambda p, e: _check_param_error(p, e, check_type="missing"),
        ),
        ErrorCategory(
            "wrong_order",
            "调用顺序错误",
            lambda p, e: (
                len(p) > 1
                and isinstance(e, list)
                and len(e) > 1
                and _check_order_error(p, e)
            ),
        ),
        ErrorCategory(
            "unnecessary_call",
            "不必要调用",
            lambda p, e: len(p) > 0 and len(e) == 0,
        ),
        ErrorCategory(
            "format_error",
            "格式解析错误",
            lambda p, e: (
                p is None or (isinstance(p, list) and len(p) == 0 and len(e) > 0)
            ),
        ),
    ]

    def __init__(self):
        self.category_counts: Dict[str, int] = defaultdict(int)
        self.category_samples: Dict[str, List[Dict]] = defaultdict(list)

    def analyze_result(self, result: Dict[str, Any]):
        """对单个评估结果进行错误分类

        Args:
            result: evaluate_sample() 返回的单个评估结果
        """
        predicted = result.get("predicted")
        expected = result.get("expected", [])

        if result.get("success", False):
            return

        self.category_counts["total_errors"] += 1

        for cat in self.ERROR_CATEGORIES:
            try:
                if cat.detect(predicted, expected):
                    self.category_counts[cat.name] += 1
                    self.category_samples[cat.name].append(result)
            except Exception:
                continue

        # 如果没有任何分类匹配，归为 unknown
        matched = any(cat.detect(predicted, expected) for cat in self.ERROR_CATEGORIES)
        if not matched:
            self.category_counts["unknown"] += 1
            self.category_samples["unknown"].append(result)

    def generate_report(
        self,
        total_samples: int,
        detailed_results: List[Dict],
    ) -> str:
        """生成详细的 Markdown 格式错误分析报告

        Args:
            total_samples: 总样本数
            detailed_results: evaluate() 返回的详细结果列表

        Returns:
            Markdown 格式的报告字符串
        """
        # 先对每个结果进行分析
        for r in detailed_results:
            self.analyze_result(r)

        total_errors = self.category_counts.get("total_errors", 0)
        accuracy = 1.0 - (total_errors / total_samples) if total_samples > 0 else 0.0

        lines = []
        lines.append("# BFCL 错误分析报告")
        lines.append("")
        lines.append(f"**总样本数**: {total_samples}")
        lines.append(f"**正确数**: {total_samples - total_errors}")
        lines.append(f"**错误数**: {total_errors}")
        lines.append(f"**准确率**: {accuracy:.2%}")
        lines.append("")

        if total_errors == 0:
            lines.append("🎉 没有发现错误！")
            lines.append("")
            return "\n".join(lines)

        lines.append("## 错误类型分布")
        lines.append("")
        lines.append("| 错误类型 | 数量 | 占比 | 说明 |")
        lines.append("|----------|------|------|------|")
        lines.append("")

        cat_descriptions = {cat.name: cat.description for cat in self.ERROR_CATEGORIES}
        cat_descriptions["total_errors"] = "总错误数"
        cat_descriptions["unknown"] = "未分类错误"

        for cat_name in sorted(
            self.category_counts.keys(),
            key=lambda x: self.category_counts[x],
            reverse=True,
        ):
            if cat_name == "total_errors":
                continue
            count = self.category_counts[cat_name]
            percentage = count / total_errors if total_errors > 0 else 0.0
            desc = cat_descriptions.get(cat_name, "")
            bar = "█" * int(percentage * 30) + "░" * (30 - int(percentage * 30))
            lines.append(f"| **{cat_name}** | {count} | {percentage:.1%} | {desc} |")
            lines.append(f"| {bar} | | | |")

        lines.append("")
        lines.append("## 各错误类型详情")
        lines.append("")

        for cat_name in sorted(
            self.category_counts.keys(),
            key=lambda x: self.category_counts[x],
            reverse=True,
        ):
            if cat_name in ("total_errors",) or cat_name not in self.category_samples:
                continue
            samples = self.category_samples[cat_name]
            if not samples:
                continue

            desc = cat_descriptions.get(cat_name, "")
            lines.append(f"### {cat_name}")
            lines.append(f"**说明**: {desc}")
            lines.append(f"**出现次数**: {len(samples)}")
            lines.append("")
            lines.append("| 样本ID | 问题 | 预测 | 期望 |")
            lines.append("|--------|------|------|------|")
            lines.append("")

            for s in samples[:10]:
                sample_id = s.get("sample_id", "")[:30]
                question = s.get("question", "")[:40]
                pred_str = json.dumps(s.get("predicted", []), ensure_ascii=False)[:40]
                exp_str = json.dumps(s.get("expected", []), ensure_ascii=False)[:40]
                lines.append(
                    f"| {sample_id} | {question}... | {pred_str}... | {exp_str}... |"
                )

            if len(samples) > 10:
                lines.append(f"| ... 还有 {len(samples) - 10} 个类似样本 ... | | | |")

            lines.append("")

        lines.append("## 改进建议")
        lines.append("")

        suggestions = self._generate_suggestions(total_errors)
        lines.extend(suggestions)
        lines.append("")

        return "\n".join(lines)

    def _generate_suggestions(self, total_errors: int) -> List[str]:
        """根据错误分布生成改进建议"""
        suggestions = []
        top_errors = sorted(
            [(k, v) for k, v in self.category_counts.items() if k != "total_errors"],
            key=lambda x: x[1],
            reverse=True,
        )

        if not top_errors:
            suggestions.append("- ✅ 表现优秀！没有发现错误。")
            return suggestions

        if top_errors[0][1] / total_errors > 0.3:
            cat_name = top_errors[0][0]
            suggestions.append(
                f"- ⚠️ 主要问题: **{cat_name}** 占比 {top_errors[0][1] / total_errors:.0%}，建议优先解决"
            )

        for cat_name, count in top_errors:
            if cat_name == "missing_call":
                suggestions.append(
                    "- 💡 **遗漏调用**: 检查智能体是否理解了问题的所有子任务，考虑改进提示词中的多步骤指令"
                )
            elif cat_name == "extra_call":
                suggestions.append(
                    "- 💡 **多余调用**: 检查智能体是否过度使用工具，强化 '仅当需要时调用' 的原则"
                )
            elif cat_name == "wrong_function":
                suggestions.append(
                    "- 💡 **函数名错误**: 检查函数描述是否清晰，考虑添加更多函数使用示例"
                )
            elif cat_name == "wrong_param_name":
                suggestions.append(
                    "- 💡 **参数名错误**: 检查参数描述，考虑添加参数别名支持"
                )
            elif cat_name == "wrong_param_value":
                suggestions.append(
                    "- 💡 **参数值错误**: 检查用户指令中的数值提取能力，考虑添加类型转换提示"
                )
            elif cat_name == "missing_param":
                suggestions.append(
                    "- 💡 **缺失参数**: 引导智能体提取问题中的所有关键信息作为参数"
                )
            elif cat_name == "wrong_order":
                suggestions.append(
                    "- 💡 **顺序错误**: 在多步骤任务中，引导智能体按正确的依赖顺序调用函数"
                )
            elif cat_name == "unnecessary_call":
                suggestions.append(
                    "- 💡 **不必要调用**: 智能体在可凭知识回答的问题上过度使用工具，需优化 irrelevance 检测能力"
                )
            elif cat_name == "format_error":
                suggestions.append(
                    "- 💡 **格式错误**: 智能体输出的函数调用格式不符合预期，检查输出格式要求是否清晰"
                )

        return suggestions


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _check_param_error(
    predicted: Any,
    expected: Any,
    check_type: str = "value",
) -> bool:
    """检查参数级别的错误"""
    if not isinstance(predicted, list) or not isinstance(expected, list):
        return False
    if len(predicted) != len(expected):
        return False

    for p, e in zip(predicted, expected):
        if not isinstance(p, dict) or not isinstance(e, dict):
            continue
        if "name" not in p:
            continue

        p_args = p.get("arguments", {})
        # 从 expected 提取参数
        for e_name, e_params in e.items():
            if e_name != p.get("name"):
                continue

            if check_type == "name":
                # 检查是否有参数名不匹配
                e_keys = set(e_params.keys()) if isinstance(e_params, dict) else set()
                p_keys = set(p_args.keys())
                return bool(p_keys - e_keys)

            elif check_type == "value":
                # 检查是否有参数名相同但值不匹配
                for k in p_args:
                    if k in e_params:
                        e_vals = e_params[k]
                        if isinstance(e_vals, list):
                            if p_args.get(k) not in e_vals:
                                return True
                return False

            elif check_type == "missing":
                # 检查 expected 中的必需参数在 predicted 中缺失
                for e_key in e_params:
                    if e_key not in p_args:
                        return True

    return False


def _check_order_error(predicted: List[Dict], expected: List[Dict]) -> bool:
    """检查顺序错误：
    所有函数名都正确但顺序不同（通过去重后集合相同但顺序不同来判断）
    """
    pred_names = [c.get("name", "") for c in predicted]
    exp_names = []
    for e in expected:
        if isinstance(e, dict):
            exp_names.extend(e.keys())

    if set(pred_names) == set(exp_names):
        return pred_names != exp_names
    return False
