"""
BFCL 评估指标模块

计算 BFCL 相关的评估指标
"""

from typing import Dict, Any, List
import ast
import numpy as np


class BFCLMetrics:
    """BFCL 评估指标计算器

    计算工具调用相关的评估指标:
    - 准确率 (Accuracy): 完全正确的比例
    - AST 匹配度 (AST Match): 抽象语法树匹配度
    - 参数准确率 (Parameter Accuracy): 参数正确的比例
    - F1分数: 精确率和召回率的调和平均
    - 执行成功率: 可执行函数调用的成功率
    """

    @staticmethod
    def calculate_accuracy(predictions: List[Any], references: List[Any]) -> float:
        """计算准确率

        Args:
            predictions: 预测结果列表
            references: 参考答案列表

        Returns:
            准确率 (0-1)
        """
        if not predictions or not references:
            return 0.0

        min_len = min(len(predictions), len(references))
        correct = sum(
            1 for p, r in zip(predictions[:min_len], references[:min_len]) if p == r
        )
        return correct / min_len

    @staticmethod
    def calculate_ast_match(predicted: str, expected: str) -> float:
        """计算 AST 匹配度

        Args:
            predicted: 预测的函数调用
            expected: 期望的函数调用

        Returns:
            匹配度 (0-1)
        """
        try:
            # 尝试解析为AST
            pred_ast = ast.parse(predicted, mode="eval")
            exp_ast = ast.parse(expected, mode="eval")

            # 比较AST结构
            pred_dump = ast.dump(pred_ast)
            exp_dump = ast.dump(exp_ast)

            if pred_dump == exp_dump:
                return 1.0

            # 计算结构相似度
            similarity = BFCLMetrics._calculate_string_similarity(pred_dump, exp_dump)
            return similarity

        except SyntaxError:
            # 如果无法解析，使用字符串相似度
            return BFCLMetrics._calculate_string_similarity(predicted, expected)

    @staticmethod
    def _calculate_string_similarity(s1: str, s2: str) -> float:
        """计算字符串相似度（简化版Levenshtein距离）"""
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        # 使用集合交集计算相似度
        set1 = set(s1.split())
        set2 = set(s2.split())

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def calculate_parameter_accuracy(
        predicted_params: Dict[str, Any], expected_params: Dict[str, Any]
    ) -> float:
        """计算参数准确率

        Args:
            predicted_params: 预测的参数
            expected_params: 期望的参数

        Returns:
            参数准确率 (0-1)
        """
        if not expected_params:
            return 1.0 if not predicted_params else 0.0

        if not predicted_params:
            return 0.0

        correct = 0
        for key, expected_value in expected_params.items():
            if key in predicted_params:
                predicted_value = predicted_params[key]
                if BFCLMetrics._values_match(predicted_value, expected_value):
                    correct += 1

        return correct / len(expected_params)

    @staticmethod
    def _values_match(v1: Any, v2: Any) -> bool:
        """比较两个值是否匹配"""
        # 处理数值类型
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return abs(v1 - v2) < 1e-6

        # 处理字符串类型
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip().lower() == v2.strip().lower()

        # 处理列表类型
        if isinstance(v1, list) and isinstance(v2, list):
            if len(v1) != len(v2):
                return False
            return all(BFCLMetrics._values_match(a, b) for a, b in zip(v1, v2))

        # 处理字典类型
        if isinstance(v1, dict) and isinstance(v2, dict):
            if set(v1.keys()) != set(v2.keys()):
                return False
            return all(BFCLMetrics._values_match(v1[k], v2[k]) for k in v1.keys())

        # 默认使用相等比较
        return v1 == v2

    def compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算综合指标

        Args:
            results: 评估结果列表

        Returns:
            指标字典，包含各种评估指标
        """
        if not results:
            return self._empty_metrics()

        total = len(results)

        # 基础指标
        success_count = sum(1 for r in results if r.get("success", False))
        accuracy = success_count / total

        # 分数统计
        scores = [r.get("score", 0.0) for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # 执行时间统计
        execution_times = [
            r.get("execution_time", 0.0) for r in results if "execution_time" in r
        ]
        avg_execution_time = (
            sum(execution_times) / len(execution_times) if execution_times else 0.0
        )

        # 按类别统计
        category_metrics = self._compute_category_metrics(results)

        # 函数调用统计
        function_call_stats = self._compute_function_call_stats(results)

        return {
            "total_samples": total,
            "success_count": success_count,
            "accuracy": accuracy,
            "average_score": avg_score,
            "average_execution_time": avg_execution_time,
            "category_metrics": category_metrics,
            "function_call_stats": function_call_stats,
            "score_distribution": self._compute_score_distribution(scores),
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """返回空指标"""
        return {
            "total_samples": 0,
            "success_count": 0,
            "accuracy": 0.0,
            "average_score": 0.0,
            "average_execution_time": 0.0,
            "category_metrics": {},
            "function_call_stats": {},
            "score_distribution": {},
        }

    def _compute_category_metrics(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """计算分类别指标"""
        categories = {}

        for result in results:
            category = result.get("category", "unknown")
            if category not in categories:
                categories[category] = {"total": 0, "success": 0, "scores": []}

            categories[category]["total"] += 1
            if result.get("success", False):
                categories[category]["success"] += 1
            categories[category]["scores"].append(result.get("score", 0.0))

        # 计算每个类别的统计信息
        category_metrics = {}
        for category, stats in categories.items():
            accuracy = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
            avg_score = (
                sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
            )

            category_metrics[category] = {
                "total": stats["total"],
                "success": stats["success"],
                "accuracy": accuracy,
                "average_score": avg_score,
            }

        return category_metrics

    def _compute_function_call_stats(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算函数调用统计"""
        total_calls = 0
        successful_calls = 0
        function_names = set()

        for result in results:
            predicted = result.get("predicted", [])
            if isinstance(predicted, list):
                total_calls += len(predicted)
                for call in predicted:
                    if isinstance(call, dict) and "name" in call:
                        function_names.add(call["name"])
                        if result.get("success", False):
                            successful_calls += 1

        return {
            "total_function_calls": total_calls,
            "successful_calls": successful_calls,
            "unique_functions": len(function_names),
            "function_names": sorted(list(function_names)),
            "avg_calls_per_sample": total_calls / len(results) if results else 0.0,
        }

    def _compute_score_distribution(self, scores: List[float]) -> Dict[str, Any]:
        """计算分数分布"""
        if not scores:
            return {}

        return {
            "min": min(scores),
            "max": max(scores),
            "mean": sum(scores) / len(scores),
            "median": sorted(scores)[len(scores) // 2],
            "std": np.std(scores) if len(scores) > 1 else 0.0,
            "quartiles": {
                "q1": sorted(scores)[len(scores) // 4],
                "q2": sorted(scores)[len(scores) // 2],
                "q3": sorted(scores)[3 * len(scores) // 4],
            },
        }

    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        """计算F1分数

        Args:
            precision: 精确率
            recall: 召回率

        Returns:
            F1分数
        """
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def calculate_precision_recall(
        predicted: List[Dict[str, Any]], expected: List[Dict[str, Any]]
    ) -> tuple[float, float]:
        """计算精确率和召回率

        Args:
            predicted: 预测的函数调用列表
            expected: 期望的函数调用列表

        Returns:
            (precision, recall) 元组
        """
        if not expected:
            return 1.0 if not predicted else 0.0, 1.0

        if not predicted:
            return 0.0, 0.0

        # 简化版本：基于函数名匹配
        pred_names = set(
            call.get("name", "") for call in predicted if isinstance(call, dict)
        )
        exp_names = set(
            call.get("name", "") for call in expected if isinstance(call, dict)
        )

        true_positives = len(pred_names & exp_names)

        precision = true_positives / len(pred_names) if pred_names else 0.0
        recall = true_positives / len(exp_names) if exp_names else 0.0

        return precision, recall
