"""
Win Rate Evaluation Tool

通过成对对比计算生成数据相对于真题的胜率
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

from hello_agents.tools.base import Tool
from hello_agents.evaluation.benchmarks.data_generation.dataset import AIDataset
from hello_agents.evaluation.benchmarks.data_generation.win_rate import WinRateEvaluator
from hello_agents.core.llm import HelloAgentsLLM


class WinRateTool(Tool):
    """Win Rate评估工具"""

    def __init__(self, llm: HelloAgentsLLM = None):
        """
        初始化Win Rate工具

        Args:
            llm: LLM实例，用于评估
        """
        super().__init__(
            name="win_rate_evaluation",
            description="通过成对对比计算生成数据相对于真题的胜率",
        )
        self.llm = llm

    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数定义"""
        return {
            "type": "object",
            "properties": {
                "generated_data_path": {
                    "type": "string",
                    "description": "生成数据的JSON文件路径",
                },
                "reference_data_path": {
                    "type": "string",
                    "description": "参考数据的JSON文件路径（可选）",
                },
                "reference_year": {
                    "type": "integer",
                    "description": "AIME真题年份（可选，如2024, 2025）",
                },
                "num_comparisons": {
                    "type": "integer",
                    "description": "对比次数（可选，默认为min(生成数据数量, 参考数据数量)）",
                },
                "output_dir": {
                    "type": "string",
                    "description": "输出目录（可选，默认为evaluation_results/win_rate）",
                },
                "judge_model": {
                    "type": "string",
                    "description": "评委模型名称（可选，默认为gpt-4o）",
                },
            },
            "required": ["generated_data_path"],
        }

    def run(self, params: Dict[str, Any]) -> str:
        """
        运行Win Rate评估

        Args:
            params: 工具参数

        Returns:
            评估结果的JSON字符串
        """
        # 解析参数
        generated_data_path = params["generated_data_path"]
        reference_data_path = params.get("reference_data_path")
        reference_year = params.get("reference_year")
        num_comparisons = params.get("num_comparisons")
        output_dir = params.get("output_dir", "evaluation_results/win_rate")
        judge_model = params.get("judge_model", "gpt-4o")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print("🏆 Win Rate评估")
        print("=" * 60)

        # 1. 加载生成数据
        print("\n📥 步骤1: 加载生成数据")
        gen_dataset = AIDataset(dataset_type="generated", data_path=generated_data_path)
        gen_problems = gen_dataset.load()

        # 2. 加载参考数据
        if reference_data_path:
            print("\n📥 步骤2: 加载参考数据（本地文件）")
            ref_dataset = AIDataset(
                dataset_type="generated", data_path=reference_data_path
            )
            ref_problems = ref_dataset.load()
        elif reference_year:
            print(f"\n📥 步骤2: 加载参考数据（AIME {reference_year}真题）")
            ref_dataset = AIDataset(dataset_type="real", year=reference_year)
            ref_problems = ref_dataset.load()
        else:
            raise ValueError("必须提供reference_data_path或reference_year之一")

        # 3. 创建评估器
        print("\n🔧 步骤3: 创建Win Rate评估器")
        evaluator = WinRateEvaluator(llm=self.llm, judge_model=judge_model)

        # 4. 运行评估
        print("\n🚀 步骤4: 开始成对对比")
        results = evaluator.evaluate_win_rate(
            gen_problems, ref_problems, num_comparisons=num_comparisons
        )

        # 5. 保存结果
        print("\n💾 步骤5: 保存评估结果")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(output_dir, f"win_rate_results_{timestamp}.json")
        evaluator.export_results(results, result_file)

        # 6. 生成报告
        print("\n📊 步骤6: 生成评估报告")
        report_file = os.path.join(output_dir, f"win_rate_report_{timestamp}.md")
        self._generate_report(results, report_file)

        print("\n" + "=" * 60)
        print("✅ Win Rate评估完成")
        print("=" * 60)
        print("\n📁 输出文件:")
        print(f"   - 评估结果: {result_file}")
        print(f"   - 评估报告: {report_file}")

        # 返回简化的结果
        return json.dumps(
            {
                "status": "success",
                "metrics": results["metrics"],
                "result_file": result_file,
                "report_file": report_file,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _generate_report(self, results: Dict[str, Any], output_path: str):
        """生成Markdown评估报告"""
        metrics = results["metrics"]

        report = f"""# Win Rate评估报告

## 基本信息

- **评估日期**: {results["evaluation_date"]}
- **评委模型**: {results["judge_model"]}
- **对比次数**: {metrics["total_comparisons"]} 次

## 评估结果

### 胜率统计

| 指标 | 数值 | 百分比 |
|------|------|--------|
| 生成数据胜出 | {metrics["wins"]} 次 | {metrics["win_rate"]:.2%} |
| 参考数据胜出 | {metrics["losses"]} 次 | {metrics["loss_rate"]:.2%} |
| 平局 | {metrics["ties"]} 次 | {metrics["tie_rate"]:.2%} |

### 结果分析

**Win Rate**: {metrics["win_rate"]:.2%}

{self._get_win_rate_analysis(metrics["win_rate"])}

## 详细对比结果

"""

        # 添加前10次对比的详细结果
        for idx, comparison in enumerate(results["comparisons"][:10]):
            winner_emoji = (
                "🏆"
                if comparison["winner"] == "Generated"
                else "❌"
                if comparison["winner"] == "Reference"
                else "🤝"
            )
            report += f"""
### 对比 {idx + 1}

- **生成题目**: {comparison["problem_a_id"]}
- **参考题目**: {comparison["problem_b_id"]}
- **胜者**: {winner_emoji} {comparison["winner"]}
- **理由**: {comparison["reason"]}
"""

        if len(results["comparisons"]) > 10:
            report += "\n*（仅显示前10次对比的详细结果，完整结果请查看JSON文件）*\n"

        report += f"""
## 结论

{self._get_conclusion(metrics["win_rate"])}

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✅ 评估报告已保存: {output_path}")

    def _get_win_rate_analysis(self, win_rate: float) -> str:
        """根据胜率生成分析"""
        if win_rate >= 0.55:
            return """
✅ **优秀**: 生成数据质量超过参考数据！这表明数据生成系统表现出色。
"""
        elif win_rate >= 0.45:
            return """
✅ **良好**: 生成数据质量接近参考数据（差距<10%）。这是理想的结果，说明生成质量达到了真题水平。
"""
        elif win_rate >= 0.35:
            return """
⚠️ **合格**: 生成数据质量略低于参考数据，但仍在可接受范围内。建议进一步优化生成策略。
"""
        else:
            return """
❌ **需改进**: 生成数据质量明显低于参考数据。建议检查生成Pipeline并进行优化。
"""

    def _get_conclusion(self, win_rate: float) -> str:
        """根据胜率生成结论"""
        if win_rate >= 0.45:
            return f"""基于Win Rate评估，生成数据集的质量**接近或达到AIME真题水平**（Win Rate = {win_rate:.2%}）。

这证明了数据生成系统的有效性，生成的题目在质量上可以与真题相媲美。
"""
        else:
            return f"""基于Win Rate评估，生成数据集的质量**仍有提升空间**（Win Rate = {win_rate:.2%}）。

建议：
1. 优化题目生成的提示词
2. 增加质量过滤步骤
3. 使用更强的生成模型
4. 增加人工审核环节
"""
