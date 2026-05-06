"""
BFCL 评估器模块

负责评估智能体在 BFCL 基准测试上的表现
"""

from typing import Dict, Any, List, Optional, Union
import json
import re
import time
from pathlib import Path
from hello_agents.evaluation.benchmarks.bfcl.dataset import BFCLDataset
from hello_agents.evaluation.benchmarks.bfcl.metrics import BFCLMetrics
from hello_agents.evaluation.benchmarks.bfcl.ast_matcher import (
    create_default_matcher,
)
from hello_agents.evaluation.benchmarks.bfcl.extended_evaluation import (
    OrderValidator,
    EfficiencyAnalyzer,
    ErrorAnalyzer,
)


class BFCLEvaluator:
    """BFCL 评估器

    评估智能体的工具调用能力,包括:
    - 简单函数调用
    - 多函数调用
    - 并行函数调用
    - 无关检测

    支持两种评估模式:
    - AST评估: 抽象语法树匹配
    - 执行评估: 实际函数执行结果对比

    Attributes:
        dataset: BFCL 数据集
        metrics: 评估指标计算器
        evaluation_mode: 评估模式 ('ast' 或 'execution')
    """

    def __init__(
        self,
        dataset: Optional[BFCLDataset] = None,
        category: Optional[str] = None,
        evaluation_mode: str = "ast",
        local_data_dir: Optional[str] = None,
    ):
        """初始化 BFCL 评估器

        Args:
            dataset: BFCL 数据集,如果为 None 则自动创建
            category: 评估类别
            evaluation_mode: 评估模式 ('ast' 或 'execution')
            local_data_dir: 本地数据目录
        """
        self.dataset = dataset or BFCLDataset(
            category=category, local_data_dir=local_data_dir
        )
        self.metrics = BFCLMetrics()
        self.evaluation_mode = evaluation_mode
        self.category = category
        self.ast_matcher = create_default_matcher()
        self.order_validator = OrderValidator()
        self.efficiency_analyzer = EfficiencyAnalyzer()
        self.error_analyzer = ErrorAnalyzer()

    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """评估智能体

        Args:
            agent: 要评估的智能体
            max_samples: 最大评估样本数,None表示评估全部

        Returns:
            评估结果字典,包含各项指标
        """
        print("\n🔧 开始 BFCL 评估...")
        print(f"   智能体: {getattr(agent, 'name', 'Unknown')}")
        print(f"   评估模式: {self.evaluation_mode}")
        print(f"   类别: {self.category or '全部'}")

        # 加载数据集
        dataset = self.dataset.load()
        if not dataset:
            print("   ⚠️ 数据集为空,跳过评估")
            return self._create_empty_results(agent)

        # 限制样本数量
        if max_samples:
            dataset = dataset[:max_samples]

        print(f"   样本数量: {len(dataset)}")

        # 执行评估
        results = []
        categories = {}

        for i, sample in enumerate(dataset):
            if i % 10 == 0:
                print(f"   进度: {i + 1}/{len(dataset)}")

            try:
                sample_result = self.evaluate_sample(agent, sample)
                results.append(sample_result)

                # 按类别统计（使用评估器的category，而不是样本的category）
                category = (
                    self.category
                    if self.category
                    else sample.get("category", "unknown")
                )
                if category not in categories:
                    categories[category] = {"total": 0, "correct": 0, "results": []}

                categories[category]["total"] += 1
                if sample_result["success"]:
                    categories[category]["correct"] += 1
                categories[category]["results"].append(sample_result)

            except Exception as e:
                print(f"   ⚠️ 样本 {i} 评估失败: {e}")
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "predicted": None,
                        "expected": sample.get("ground_truth"),
                        "score": 0.0,
                    }
                )

        # 计算总体指标
        total_samples = len(results)
        correct_samples = sum(1 for r in results if r["success"])
        overall_accuracy = correct_samples / total_samples if total_samples > 0 else 0.0

        # 计算分类指标
        category_metrics = {}
        for cat, cat_data in categories.items():
            accuracy = (
                cat_data["correct"] / cat_data["total"]
                if cat_data["total"] > 0
                else 0.0
            )
            category_metrics[cat] = {
                "total": cat_data["total"],
                "correct": cat_data["correct"],
                "accuracy": accuracy,
            }

        # 生成错误分析报告
        error_report = self.error_analyzer.generate_report(total_samples, results)

        final_results = {
            "benchmark": "BFCL",
            "agent_name": getattr(agent, "name", "Unknown"),
            "evaluation_mode": self.evaluation_mode,
            "category": self.category,
            "total_samples": total_samples,
            "correct_samples": correct_samples,
            "overall_accuracy": overall_accuracy,
            "category_metrics": category_metrics,
            "detailed_results": results,
            "extended_analysis": {
                "order_stats": self._compute_order_stats(results),
                "efficiency_stats": self._compute_efficiency_stats(results),
                "error_categories": dict(self.error_analyzer.category_counts),
            },
            "error_report": error_report,
        }

        print(f"\n{'=' * 60}")
        print("✅ BFCL 评估完成")
        print(f"   总体准确率: {overall_accuracy:.2%}")
        for cat, metrics in category_metrics.items():
            print(
                f"   {cat}: {metrics['accuracy']:.2%} ({metrics['correct']}/{metrics['total']})"
            )

        error_count = self.error_analyzer.category_counts.get("total_errors", 0)
        if error_count > 0:
            top = sorted(
                [
                    (k, v)
                    for k, v in self.error_analyzer.category_counts.items()
                    if k != "total_errors"
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:3]
            if top:
                print(f"\n📊 常见错误 Top {len(top)}:")
                for name, count in top:
                    print(f"   {name}: {count} 次 ({count / error_count:.1%})")

        print(f"{'=' * 60}")

        return final_results

    def evaluate_sample(self, agent: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个样本

        Args:
            agent: 要评估的智能体
            sample: 样本数据

        Returns:
            单个样本的评估结果
        """
        try:
            # 准备输入
            question = sample.get("question", "")
            functions = sample.get("function", [])
            ground_truth = sample.get("ground_truth", [])

            # 构建函数调用提示
            prompt = self._build_function_calling_prompt(question, functions)

            # 调用智能体
            start_time = time.time()
            response = agent.run(prompt)
            execution_time = time.time() - start_time

            # 解析响应中的函数调用
            predicted_calls = self._extract_function_calls(response)

            # 评估结果
            if self.evaluation_mode == "ast":
                success, score = self._evaluate_ast_matching(
                    predicted_calls, ground_truth
                )
            else:
                success, score = self._evaluate_execution(
                    predicted_calls, ground_truth, functions
                )

            # 扩展评估：调用顺序验证
            order_result = self.order_validator.validate(predicted_calls, ground_truth)

            # 扩展评估：调用效率分析
            efficiency_result = self.efficiency_analyzer.analyze(
                predicted_calls, ground_truth
            )

            return {
                "success": success,
                "score": score,
                "predicted": predicted_calls,
                "expected": ground_truth,
                "response": response,
                "question": question,
                "execution_time": execution_time,
                "sample_id": sample.get("id", ""),
                "category": self.category
                if self.category
                else sample.get("category", "unknown"),
                "extended": {
                    "order": {
                        "correct": order_result.correct,
                        "violations": order_result.violations,
                        "score": order_result.score,
                        "actual_order": order_result.actual_order,
                        "expected_order": order_result.expected_order,
                    },
                    "efficiency": {
                        "is_optimal": efficiency_result.is_optimal,
                        "actual_calls": efficiency_result.actual_calls,
                        "optimal_calls": efficiency_result.optimal_calls,
                        "redundant_calls": efficiency_result.redundant_calls,
                        "score": efficiency_result.score,
                    },
                },
            }

        except Exception as e:
            return {
                "success": False,
                "score": 0.0,
                "predicted": None,
                "expected": sample.get("ground_truth", []),
                "question": sample.get("question", ""),
                "error": str(e),
                "sample_id": sample.get("id", ""),
                "category": self.category
                if self.category
                else sample.get("category", "unknown"),
                "extended": {
                    "order": {
                        "correct": False,
                        "violations": [str(e)],
                        "score": 0.0,
                        "actual_order": [],
                        "expected_order": [],
                    },
                    "efficiency": {
                        "is_optimal": False,
                        "actual_calls": 0,
                        "optimal_calls": 0,
                        "redundant_calls": [],
                        "score": 0.0,
                    },
                },
            }

    def _create_empty_results(self, agent: Any) -> Dict[str, Any]:
        """创建空的评估结果"""
        return {
            "benchmark": "BFCL",
            "agent_name": getattr(agent, "name", "Unknown"),
            "evaluation_mode": self.evaluation_mode,
            "category": self.category,
            "total_samples": 0,
            "correct_samples": 0,
            "overall_accuracy": 0.0,
            "category_metrics": {},
            "detailed_results": [],
        }

    def _build_function_calling_prompt(
        self, question: str, functions: List[Dict]
    ) -> str:
        """构建函数调用提示"""
        if not functions:
            return question

        prompt = "你是一个智能助手，可以调用以下函数来帮助回答问题：\n\n"

        # 添加函数定义
        for i, func in enumerate(functions, 1):
            func_name = func.get("name", f"function_{i}")
            func_desc = func.get("description", "")
            func_params = func.get("parameters", {})

            prompt += f"函数 {i}: {func_name}\n"
            prompt += f"描述: {func_desc}\n"

            if func_params:
                prompt += (
                    f"参数: {json.dumps(func_params, ensure_ascii=False, indent=2)}\n"
                )

            prompt += "\n"

        prompt += f"请根据以下问题，选择合适的函数进行调用：\n{question}\n\n"
        prompt += "请以JSON格式返回函数调用，例如：\n"
        prompt += '[{"name": "function_name", "arguments": {"param1": "value1"}}]'

        return prompt

    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """从响应中提取函数调用"""
        try:
            # 尝试直接解析JSON
            if response.strip().startswith("[") and response.strip().endswith("]"):
                return json.loads(response.strip())

            # 使用正则表达式查找JSON数组
            json_pattern = r"\[.*?\]"
            matches = re.findall(json_pattern, response, re.DOTALL)

            for match in matches:
                try:
                    calls = json.loads(match)
                    if isinstance(calls, list):
                        return calls
                except json.JSONDecodeError:
                    continue

            # 查找单个函数调用
            single_call_pattern = r'\{.*?"name".*?\}'
            matches = re.findall(single_call_pattern, response, re.DOTALL)

            calls = []
            for match in matches:
                try:
                    call = json.loads(match)
                    if "name" in call:
                        calls.append(call)
                except json.JSONDecodeError:
                    continue

            return calls

        except Exception:
            return []

    def _evaluate_ast_matching(
        self, predicted: List[Dict], expected: List
    ) -> tuple[bool, float]:
        """AST匹配评估

        使用改进的 ASTMatcher，支持：
        - 常量表达式求值
        - 参数别名映射
        - 类型感知比较
        - 默认参数补全
        - 浮点数容差

        支持两种 ground truth 格式：
        1. BFCL v4 格式：[{"func_name": {"param": [value1, value2]}}]
        2. 字符串格式：["func_name(param=value)"]
        """
        return self.ast_matcher.match(predicted, expected)

    def _evaluate_execution(
        self, predicted: List[Dict], expected: List[str], functions: List[Dict]
    ) -> tuple[bool, float]:
        """执行评估（简化版本）"""
        # 这里实现简化的执行评估
        # 在实际应用中，需要安全的代码执行环境
        return self._evaluate_ast_matching(predicted, expected)

    def _compute_order_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """汇总所有样本的顺序验证统计"""
        total = len(results)
        correct_order = sum(
            1
            for r in results
            if r.get("extended", {}).get("order", {}).get("correct", True)
        )
        return {
            "total_samples": total,
            "correct_order_count": correct_order,
            "correct_order_rate": correct_order / total if total > 0 else 0.0,
        }

    def _compute_efficiency_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """汇总所有样本的效率评估统计"""
        total = len(results)
        optimal_count = sum(
            1
            for r in results
            if r.get("extended", {}).get("efficiency", {}).get("is_optimal", True)
        )
        total_redundant = sum(
            len(r.get("extended", {}).get("efficiency", {}).get("redundant_calls", []))
            for r in results
        )
        return {
            "total_samples": total,
            "optimal_count": optimal_count,
            "optimal_rate": optimal_count / total if total > 0 else 0.0,
            "total_redundant_calls": total_redundant,
        }

    def generate_error_report(
        self,
        results: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """生成并保存错误分析报告

        Args:
            results: evaluate() 返回的评估结果
            output_path: 输出文件路径，None 则自动生成

        Returns:
            Markdown 报告字符串
        """
        total = results.get("total_samples", 0)
        details = results.get("detailed_results", [])
        report = self.error_analyzer.generate_report(total, details)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"📄 错误分析报告已保存: {output_path}")

        return report

    def export_to_bfcl_format(
        self,
        results: Dict[str, Any],
        output_path: Union[str, Path],
        include_inference_log: bool = True,
    ) -> None:
        """导出评估结果为BFCL官方格式

        BFCL官方格式示例：
        {
            "id": "simple_python_0",
            "model_result": [
                {
                    "name": "calculate_triangle_area",
                    "arguments": {"base": 10, "height": 5, "unit": "units"}
                }
            ],
            "inference_log": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

        Args:
            results: evaluate()方法返回的评估结果
            output_path: 输出文件路径
            include_inference_log: 是否包含推理日志
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为BFCL格式
        bfcl_results = []

        for detail in results.get("detailed_results", []):
            # 将predicted转换为字符串格式的函数调用
            predicted = detail.get("predicted", [])
            result_string = ""

            if predicted:
                call = predicted[0]  # 通常只有一个函数调用
                if isinstance(call, dict) and "name" in call:
                    func_name = call["name"]
                    args = call.get("arguments", {})

                    # 构建函数调用字符串
                    if args:
                        args_str = ", ".join(
                            [f"{k}={repr(v)}" for k, v in args.items()]
                        )
                        result_string = f"{func_name}({args_str})"
                    else:
                        result_string = f"{func_name}()"

            bfcl_item = {
                "id": detail.get("sample_id", ""),
                "result": result_string,  # BFCL期望的是单个字符串
            }

            # 添加推理日志（如果需要）
            if include_inference_log:
                question = detail.get("question", "")
                response = detail.get("response", "")

                bfcl_item["inference_log"] = [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response},
                ]

            bfcl_results.append(bfcl_item)

        # 写入JSONL格式（每行一个JSON对象）
        with open(output_path, "w", encoding="utf-8") as f:
            for item in bfcl_results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        print("\n✅ BFCL格式结果已导出")
        print(f"   输出文件: {output_path}")
        print(f"   样本数: {len(bfcl_results)}")
        print(f"   包含推理日志: {include_inference_log}")

        # 提示如何使用BFCL官方评估
        print("\n📝 使用BFCL官方评估工具：")
        print("   1. 安装: pip install bfcl-eval")
        print("   2. 设置环境变量: export BFCL_PROJECT_ROOT=.")
        print("   3. 将结果文件复制到: result/HelloAgents/")
        print(
            f"   4. 运行评估: bfcl evaluate --model HelloAgents --test-category {self.category}"
        )
