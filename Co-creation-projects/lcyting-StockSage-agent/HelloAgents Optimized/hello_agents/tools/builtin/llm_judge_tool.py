"""
LLM Judge Evaluation Tool

使用LLM作为评委评估数据生成质量的工具
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

from hello_agents.tools.base import Tool
from hello_agents.evaluation.benchmarks.data_generation.dataset import AIDataset
from hello_agents.evaluation.benchmarks.data_generation.llm_judge import (
    LLMJudgeEvaluator,
)
from hello_agents.core.llm import HelloAgentsLLM


class LLMJudgeTool(Tool):
    """LLM Judge评估工具"""

    def __init__(self, llm: HelloAgentsLLM = None):
        """
        初始化LLM Judge工具

        Args:
            llm: LLM实例，用于评估
        """
        super().__init__(
            name="llm_judge_evaluation", description="使用LLM作为评委评估数据生成质量"
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
                    "description": "参考数据的JSON文件路径（可选，用于对比）",
                },
                "reference_year": {
                    "type": "integer",
                    "description": "AIME真题年份（可选，如2024, 2025）",
                },
                "max_samples": {
                    "type": "integer",
                    "description": "最大评估样本数（可选，默认评估所有）",
                },
                "output_dir": {
                    "type": "string",
                    "description": "输出目录（可选，默认为evaluation_results/llm_judge）",
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
        运行LLM Judge评估

        Args:
            params: 工具参数

        Returns:
            评估结果的JSON字符串
        """
        # 解析参数
        generated_data_path = params["generated_data_path"]
        reference_data_path = params.get("reference_data_path")
        reference_year = params.get("reference_year")
        max_samples = params.get("max_samples")
        output_dir = params.get("output_dir", "evaluation_results/llm_judge")
        judge_model = params.get("judge_model", "gpt-4o")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print("🎯 LLM Judge评估")
        print("=" * 60)

        # 1. 加载生成数据
        print("\n📥 步骤1: 加载生成数据")
        gen_dataset = AIDataset(dataset_type="generated", data_path=generated_data_path)
        gen_problems = gen_dataset.load()

        if max_samples:
            gen_problems = gen_problems[:max_samples]
            print(f"   限制评估样本数: {max_samples}")

        # 2. 加载参考数据（可选）
        ref_problems = None
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
            print("\n⏭️  步骤2: 跳过参考数据加载（无对比）")

        # 3. 创建评估器
        print("\n🔧 步骤3: 创建LLM Judge评估器")
        evaluator = LLMJudgeEvaluator(llm=self.llm, judge_model=judge_model)

        # 4. 运行评估
        print("\n🚀 步骤4: 开始评估")
        results = evaluator.evaluate_batch(gen_problems, ref_problems)

        # 5. 保存结果
        print("\n💾 步骤5: 保存评估结果")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(output_dir, f"llm_judge_results_{timestamp}.json")
        evaluator.export_results(results, result_file)

        # 6. 生成报告
        print("\n📊 步骤6: 生成评估报告")
        report_file = os.path.join(output_dir, f"llm_judge_report_{timestamp}.md")
        self._generate_report(results, report_file)

        print("\n" + "=" * 60)
        print("✅ LLM Judge评估完成")
        print("=" * 60)
        print("\n📁 输出文件:")
        print(f"   - 评估结果: {result_file}")
        print(f"   - 评估报告: {report_file}")

        # 返回简化的结果
        return json.dumps(
            {
                "status": "success",
                "metrics": results["metrics"],
                "num_problems": results["num_problems"],
                "result_file": result_file,
                "report_file": report_file,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _generate_report(self, results: Dict[str, Any], output_path: str):
        """生成Markdown评估报告"""
        metrics = results["metrics"]

        report = f"""# LLM Judge评估报告

## 基本信息

- **评估日期**: {results["evaluation_date"]}
- **评委模型**: {results["judge_model"]}
- **评估数量**: {results["num_problems"]} 个题目

## 评估结果

### 总体评分

- **平均总分**: {metrics["average_total_score"]:.2f}/5.0
- **通过率**: {metrics["pass_rate"]:.2%} (≥3.5分)
- **优秀率**: {metrics["excellent_rate"]:.2%} (≥4.5分)

### 各维度评分

| 维度 | 平均分 | 评级 |
|------|--------|------|
| 正确性 (Correctness) | {metrics["dimension_averages"]["correctness"]:.2f}/5.0 | {self._get_rating(metrics["dimension_averages"]["correctness"])} |
| 清晰度 (Clarity) | {metrics["dimension_averages"]["clarity"]:.2f}/5.0 | {self._get_rating(metrics["dimension_averages"]["clarity"])} |
| 难度匹配 (Difficulty Match) | {metrics["dimension_averages"]["difficulty_match"]:.2f}/5.0 | {self._get_rating(metrics["dimension_averages"]["difficulty_match"])} |
| 完整性 (Completeness) | {metrics["dimension_averages"]["completeness"]:.2f}/5.0 | {self._get_rating(metrics["dimension_averages"]["completeness"])} |

## 详细结果

"""

        # 添加每个题目的详细评分
        for idx, result in enumerate(results["results"][:10]):  # 只显示前10个
            report += f"""
### 题目 {idx + 1}: {result["problem_id"]}

- **总分**: {result["total_score"]:.2f}/5.0
- **各维度评分**:
  - 正确性: {result["scores"]["correctness"]:.1f}
  - 清晰度: {result["scores"]["clarity"]:.1f}
  - 难度匹配: {result["scores"]["difficulty_match"]:.1f}
  - 完整性: {result["scores"]["completeness"]:.1f}
"""

        if len(results["results"]) > 10:
            report += "\n*（仅显示前10个题目的详细评分，完整结果请查看JSON文件）*\n"

        report += f"""
## 结论

基于LLM Judge的评估，生成的数据集质量{"优秀" if metrics["average_total_score"] >= 4.5 else "良好" if metrics["average_total_score"] >= 3.5 else "需要改进"}。

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✅ 评估报告已保存: {output_path}")

    def _get_rating(self, score: float) -> str:
        """根据分数获取评级"""
        if score >= 4.5:
            return "优秀 ⭐⭐⭐⭐⭐"
        elif score >= 4.0:
            return "良好 ⭐⭐⭐⭐"
        elif score >= 3.5:
            return "合格 ⭐⭐⭐"
        elif score >= 3.0:
            return "一般 ⭐⭐"
        else:
            return "需改进 ⭐"
