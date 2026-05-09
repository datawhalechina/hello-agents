"""BFCL评估工具

Berkeley Function Calling Leaderboard (BFCL) 一键评估工具

本工具封装了完整的BFCL评估流程：
1. 自动检查和准备BFCL数据
2. 运行HelloAgents评估
3. 导出BFCL格式结果
4. 调用BFCL官方评估工具（可选）
5. 生成评估报告

使用示例：
    from hello_agents import SimpleAgent, HelloAgentsLLM
    from hello_agents.tools.builtin import BFCLEvaluationTool

    # 创建智能体
    llm = HelloAgentsLLM()
    agent = SimpleAgent(name="TestAgent", llm=llm)

    # 创建评估工具
    bfcl_tool = BFCLEvaluationTool()

    # 运行评估（默认会运行BFCL官方评估）
    results = bfcl_tool.run(
        agent=agent,
        category="simple_python",
        max_samples=5
    )

    print(f"准确率: {results['overall_accuracy']:.2%}")
    # 报告自动生成到: evaluation_reports/bfcl_report_{timestamp}.md
"""

import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from ..base import Tool, ToolParameter


class BFCLEvaluationTool(Tool):
    """BFCL一键评估工具

    封装了完整的BFCL评估流程，提供简单易用的接口。

    支持的评估类别：
    - simple_python: 简单Python函数调用（400样本）
    - simple_java: 简单Java函数调用（400样本）
    - simple_javascript: 简单JavaScript函数调用（400样本）
    - multiple: 多函数调用（240样本）
    - parallel: 并行函数调用（280样本）
    - parallel_multiple: 并行多函数调用（200样本）
    - irrelevance: 无关检测（200样本）
    """

    def __init__(
        self, bfcl_data_dir: Optional[str] = None, project_root: Optional[str] = None
    ):
        """初始化BFCL评估工具

        Args:
            bfcl_data_dir: BFCL数据目录路径（默认：./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data）
            project_root: 项目根目录（默认：当前目录）
        """
        super().__init__(
            name="bfcl_evaluation",
            description=(
                "BFCL一键评估工具。评估智能体的工具调用能力，支持多个评估类别。"
                "自动完成数据加载、评估运行、结果导出和报告生成。"
            ),
        )

        # 设置路径
        self.project_root = Path(project_root) if project_root else Path.cwd()
        if bfcl_data_dir:
            self.bfcl_data_dir = Path(bfcl_data_dir)
        else:
            self.bfcl_data_dir = (
                self.project_root
                / "temp_gorilla"
                / "berkeley-function-call-leaderboard"
                / "bfcl_eval"
                / "data"
            )

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="agent",
                type="object",
                description="要评估的智能体实例",
                required=True,
            ),
            ToolParameter(
                name="category",
                type="string",
                description="评估类别：simple_python, simple_java, simple_javascript, multiple, parallel, parallel_multiple, irrelevance",
                required=False,
                default="simple_python",
            ),
            ToolParameter(
                name="max_samples",
                type="integer",
                description="评估样本数（默认：5，设为0表示全部）",
                required=False,
                default=5,
            ),
            ToolParameter(
                name="run_official_eval",
                type="boolean",
                description="是否运行BFCL官方评估",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="model_name",
                type="string",
                description="模型名称（用于BFCL官方评估）",
                required=False,
                default="Qwen/Qwen3-8B",
            ),
        ]

    def run(
        self,
        agent: Any,
        category: str = "simple_python",
        max_samples: int = 5,
        run_official_eval: bool = True,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """运行BFCL评估

        Args:
            agent: 要评估的智能体
            category: 评估类别（默认：simple_python）
            max_samples: 评估样本数（默认：5，设为0表示全部）
            run_official_eval: 是否运行BFCL官方评估（默认：True）
            model_name: 模型名称（用于BFCL官方评估，默认：Qwen/Qwen3-8B）

        Returns:
            评估结果字典，包含：
            - overall_accuracy: 总体准确率
            - correct_samples: 正确样本数
            - total_samples: 总样本数
            - category_metrics: 分类指标
            - detailed_results: 详细结果
        """
        from hello_agents.evaluation import BFCLDataset, BFCLEvaluator

        print("\n" + "=" * 60)
        print("BFCL一键评估")
        print("=" * 60)
        print("\n配置:")
        print(f"   评估类别: {category}")
        print(f"   样本数量: {max_samples if max_samples > 0 else '全部'}")
        print(f"   智能体: {getattr(agent, 'name', 'Unknown')}")

        # 步骤1: 检查BFCL数据
        if not self._check_bfcl_data():
            return self._create_error_result("BFCL数据目录不存在")

        # 步骤2: 运行HelloAgents评估
        print("\n" + "=" * 60)
        print("步骤1: 运行HelloAgents评估")
        print("=" * 60)

        dataset = BFCLDataset(bfcl_data_dir=str(self.bfcl_data_dir), category=category)
        evaluator = BFCLEvaluator(dataset=dataset, category=category)

        if max_samples > 0:
            results = evaluator.evaluate(agent, max_samples=max_samples)
        else:
            results = evaluator.evaluate(agent, max_samples=None)

        print("\n📊 评估结果:")
        print(f"   准确率: {results['overall_accuracy']:.2%}")
        print(f"   正确数: {results['correct_samples']}/{results['total_samples']}")

        # 步骤3: 导出BFCL格式结果
        print("\n" + "=" * 60)
        print("步骤2: 导出BFCL格式结果")
        print("=" * 60)

        output_dir = self.project_root / "evaluation_results" / "bfcl_official"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"BFCL_v4_{category}_result.json"

        evaluator.export_to_bfcl_format(results, output_file)

        # 步骤4: 运行BFCL官方评估（可选）
        if run_official_eval:
            if not model_name:
                model_name = "Qwen/Qwen3-8B"

            self._run_official_evaluation(output_file, model_name, category)

        # 步骤5: 生成评估报告
        print("\n" + "=" * 60)
        print("步骤3: 生成评估报告")
        print("=" * 60)

        # 添加智能体和类别信息到结果中
        results["agent_name"] = getattr(agent, "name", "Unknown")
        results["category"] = category

        self.generate_report(results)

        return results

    def _check_bfcl_data(self) -> bool:
        """检查BFCL数据是否存在"""
        if not self.bfcl_data_dir.exists():
            print(f"\n❌ BFCL数据目录不存在: {self.bfcl_data_dir}")
            print("\n请先克隆BFCL仓库：")
            print(
                "   git clone --depth 1 https://github.com/ShishirPatil/gorilla.git temp_gorilla"
            )
            return False
        return True

    def _run_official_evaluation(
        self, source_file: Path, model_name: str, category: str
    ):
        """运行BFCL官方评估"""
        print("\n" + "=" * 60)
        print("步骤3: 运行BFCL官方评估")
        print("=" * 60)

        # 复制结果文件到BFCL结果目录
        safe_model_name = model_name.replace("/", "_")
        result_dir = self.project_root / "result" / safe_model_name
        result_dir.mkdir(parents=True, exist_ok=True)

        target_file = result_dir / f"BFCL_v4_{category}_result.json"
        shutil.copy(source_file, target_file)

        print("\n✅ 结果文件已复制到:")
        print(f"   {target_file}")

        # 运行BFCL评估
        try:
            import os

            os.environ["PYTHONUTF8"] = "1"

            cmd = [
                "bfcl",
                "evaluate",
                "--model",
                model_name,
                "--test-category",
                category,
                "--partial-eval",
            ]

            print(f"\n🔄 运行命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            if result.stdout:
                print(result.stdout)

            if result.returncode != 0:
                print("\n❌ BFCL评估失败:")
                if result.stderr:
                    print(result.stderr)
            else:
                self._show_official_results(model_name, category)

        except FileNotFoundError:
            print("\n❌ 未找到bfcl命令")
            print("   请先安装: pip install bfcl-eval")
        except Exception as e:
            print(f"\n❌ 运行BFCL评估时出错: {e}")

    def _show_official_results(self, model_name: str, category: str):
        """展示BFCL官方评估结果"""
        print("\n" + "=" * 60)
        print("BFCL官方评估结果")
        print("=" * 60)

        # CSV文件
        csv_file = self.project_root / "score" / "data_non_live.csv"

        if csv_file.exists():
            print("\n📊 评估结果汇总:")
            with open(csv_file, "r", encoding="utf-8") as f:
                content = f.read()
                print(content)

        # 详细评分文件
        safe_model_name = model_name.replace("/", "_")
        score_file = (
            self.project_root
            / "score"
            / safe_model_name
            / "non_live"
            / f"BFCL_v4_{category}_score.json"
        )

        if score_file.exists():
            print("\n📝 详细评分文件:")
            print(f"   {score_file}")

            with open(score_file, "r", encoding="utf-8") as f:
                first_line = f.readline()
                summary = json.loads(first_line)
                print("\n🎯 最终结果:")
                print(f"   准确率: {summary['accuracy']:.2%}")
                print(f"   正确数: {summary['correct_count']}/{summary['total_count']}")

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "error": error_message,
            "overall_accuracy": 0.0,
            "correct_samples": 0,
            "total_samples": 0,
            "category_metrics": {},
            "detailed_results": [],
        }

    def generate_report(
        self, results: Dict[str, Any], output_file: Optional[str] = None
    ) -> str:
        """生成评估报告

        Args:
            results: 评估结果字典
            output_file: 输出文件路径（可选，默认：evaluation_reports/bfcl_report_{timestamp}.md）

        Returns:
            报告内容（Markdown格式）
        """
        from datetime import datetime

        # 生成报告内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# BFCL评估报告

**生成时间**: {timestamp}

## 📊 评估概览

- **智能体**: {results.get("agent_name", "Unknown")}
- **评估类别**: {results.get("category", "Unknown")}
- **总体准确率**: {results["overall_accuracy"]:.2%}
- **正确样本数**: {results["correct_samples"]}/{results["total_samples"]}

## 📈 详细指标

"""

        # 添加分类指标
        if "category_metrics" in results and results["category_metrics"]:
            report += "### 分类准确率\n\n"
            for category, metrics in results["category_metrics"].items():
                accuracy = metrics.get("accuracy", 0.0)
                correct = metrics.get("correct", 0)
                total = metrics.get("total", 0)
                report += f"- **{category}**: {accuracy:.2%} ({correct}/{total})\n"
            report += "\n"

        # 添加样本详情
        if "detailed_results" in results and results["detailed_results"]:
            report += "## 📝 样本详情\n\n"
            report += "| 样本ID | 问题 | 预测结果 | 正确答案 | 是否正确 |\n"
            report += "|--------|------|----------|----------|----------|\n"

            for detail in results["detailed_results"][:10]:  # 只显示前10个
                sample_id = detail.get("sample_id", "N/A")

                # 提取问题文本
                question = detail.get("question", "N/A")
                if isinstance(question, list) and len(question) > 0:
                    if isinstance(question[0], list) and len(question[0]) > 0:
                        if (
                            isinstance(question[0][0], dict)
                            and "content" in question[0][0]
                        ):
                            question = question[0][0]["content"]
                question_str = str(question)
                if len(question_str) > 60:
                    question_str = question_str[:60] + "..."

                # 提取预测结果（字段名是predicted）
                prediction = detail.get("predicted", "N/A")
                if prediction and prediction != "N/A":
                    pred_str = str(prediction)
                    if len(pred_str) > 40:
                        pred_str = pred_str[:40] + "..."
                else:
                    pred_str = "N/A"

                # 提取正确答案（字段名是expected）
                ground_truth = detail.get("expected", "N/A")
                if ground_truth and ground_truth != "N/A":
                    gt_str = str(ground_truth)
                    if len(gt_str) > 40:
                        gt_str = gt_str[:40] + "..."
                else:
                    gt_str = "N/A"

                # 判断是否正确（字段名是success）
                is_correct = "✅" if detail.get("success", False) else "❌"

                report += f"| {sample_id} | {question_str} | {pred_str} | {gt_str} | {is_correct} |\n"

            if len(results["detailed_results"]) > 10:
                report += (
                    f"\n*显示前10个样本，共{len(results['detailed_results'])}个样本*\n"
                )
            report += "\n"

        # 添加可视化（ASCII图表）
        report += "## 📊 准确率可视化\n\n"
        report += "```\n"
        accuracy = results["overall_accuracy"]
        bar_length = int(accuracy * 50)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        report += f"准确率: {bar} {accuracy:.2%}\n"
        report += "```\n\n"

        # 添加建议
        report += "## 💡 建议\n\n"
        if accuracy >= 0.9:
            report += "- ✅ 表现优秀！智能体在工具调用方面表现出色。\n"
        elif accuracy >= 0.7:
            report += "- ⚠️ 表现良好，但仍有提升空间。建议检查错误样本，优化提示词。\n"
        else:
            report += "- ❌ 表现需要改进。建议：\n"
            report += "  1. 检查智能体的工具调用逻辑\n"
            report += "  2. 优化系统提示词\n"
            report += "  3. 增加更多训练样本\n"

        # 保存报告
        if output_file is None:
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self.project_root / "evaluation_reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"bfcl_report_{timestamp_file}.md"
        else:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📄 报告已生成: {output_file}")

        return report
