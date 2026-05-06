"""
Multi-Judge Evaluation Tool

使用多个LLM作为评审团进行综合评估的工具
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from hello_agents.tools.base import Tool
from hello_agents.evaluation.benchmarks.data_generation.dataset import AIDataset
from hello_agents.evaluation.benchmarks.data_generation.multi_judge import (
    MultiJudgeEvaluator,
    JudgeConfig,
    generate_report,
)
from hello_agents.core.llm import HelloAgentsLLM


DEFAULT_JUDGE_CONFIGS = [
    JudgeConfig(name="Judge-GPT4", model="gpt-4o", weight=1.0),
    JudgeConfig(name="Judge-Claude", model="claude-3-opus-20240229", weight=1.0),
    JudgeConfig(name="Judge-Qwen", model="qwen-max", weight=0.8),
]


class MultiJudgeTool(Tool):
    def __init__(
        self,
        llm: HelloAgentsLLM = None,
        judge_configs: Optional[List[JudgeConfig]] = None,
    ):
        super().__init__(
            name="multi_judge_evaluation", description="使用多个LLM评委进行评审团式评估"
        )
        self.llm = llm
        self.judge_configs = judge_configs or DEFAULT_JUDGE_CONFIGS

    def get_parameters(self) -> Dict[str, Any]:
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
                    "description": "AIME真题年份（可选）",
                },
                "max_samples": {
                    "type": "integer",
                    "description": "最大评估样本数（可选）",
                },
                "output_dir": {"type": "string", "description": "输出目录（可选）"},
                "enable_discussion": {
                    "type": "boolean",
                    "description": "是否启用讨论轮（可选，默认true）",
                },
                "enable_control_check": {
                    "type": "boolean",
                    "description": "是否启用对照样本校验（可选，默认true）",
                },
            },
            "required": ["generated_data_path"],
        }

    def run(self, params: Dict[str, Any]) -> str:
        generated_data_path = params["generated_data_path"]
        reference_data_path = params.get("reference_data_path")
        reference_year = params.get("reference_year")
        max_samples = params.get("max_samples")
        output_dir = params.get("output_dir", "evaluation_results/multi_judge")
        enable_discussion = params.get("enable_discussion", True)
        enable_control_check = params.get("enable_control_check", True)

        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print("🎯 多评委评估系统")
        print("=" * 60)
        print("\n评委阵容:")
        for c in self.judge_configs:
            print(f"   - {c.name} ({c.model}) weight={c.weight}")

        print("\n📥 步骤1: 加载生成数据")
        gen_dataset = AIDataset(dataset_type="generated", data_path=generated_data_path)
        gen_problems = gen_dataset.load()
        if max_samples:
            gen_problems = gen_problems[:max_samples]

        ref_problems = None
        if reference_data_path:
            print("📥 加载参考数据（本地）")
            ref_dataset = AIDataset(
                dataset_type="generated", data_path=reference_data_path
            )
            ref_problems = ref_dataset.load()
        elif reference_year:
            print(f"📥 加载参考数据（AIME {reference_year}）")
            ref_dataset = AIDataset(dataset_type="real", year=reference_year)
            ref_problems = ref_dataset.load()

        print("\n🔧 步骤2: 创建多评委评估器")

        def llm_provider(
            model: str, prompt: str, temperature: float = 0.2, max_tokens: int = 1024
        ) -> str:
            llm = self.llm or HelloAgentsLLM(model=model)
            return llm.invoke(
                [{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

        evaluator = MultiJudgeEvaluator(
            judges=self.judge_configs,
            llm_provider=llm_provider,
            enable_control_check=enable_control_check,
            max_discussion_rounds=2 if enable_discussion else 0,
        )

        print("\n🚀 步骤3: 开始评估")
        results = evaluator.evaluate_batch(gen_problems, ref_problems)

        print("\n💾 步骤4: 保存结果")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        serializable = self._to_serializable(results)
        result_file = os.path.join(output_dir, f"multi_judge_results_{timestamp}.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 结果已保存: {result_file}")

        report_file = os.path.join(output_dir, f"multi_judge_report_{timestamp}.md")
        report = generate_report(serializable)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"   ✅ 报告已保存: {report_file}")

        print("\n" + "=" * 60)
        print("✅ 多评委评估完成")
        print("=" * 60)

        metrics = results.get("metrics", {})
        return json.dumps(
            {
                "status": "success",
                "metrics": {
                    "average_final_score": metrics.get("average_final_score", 0),
                    "average_confidence": metrics.get("average_confidence", 0),
                    "pass_rate": metrics.get("pass_rate", 0),
                    "excellent_rate": metrics.get("excellent_rate", 0),
                    "arbitration_rate": metrics.get("arbitration_rate", 0),
                },
                "num_problems": results.get("num_problems", 0),
                "judges": [c.name for c in self.judge_configs],
                "result_file": result_file,
                "report_file": report_file,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _to_serializable(self, results: Dict) -> Dict:
        serializable = dict(results)
        serializable["results"] = []
        for r in results.get("results", []):
            serializable["results"].append(
                {
                    "item_id": r.item_id,
                    "final_score": r.final_score,
                    "confidence": r.confidence,
                    "agreement_level": r.agreement_level,
                    "arbitration_used": r.arbitration_used,
                    "anomaly_flags": r.anomaly_flags,
                    "verdicts": [
                        {
                            "judge_name": v.judge_name,
                            "scores": v.scores,
                            "total_score": v.total_score,
                            "adjusted": v.adjusted,
                        }
                        for v in r.verdicts
                    ],
                    "discussion_rounds": [
                        {
                            "round_number": dr.round_number,
                            "disagreement_level": dr.disagreement_level,
                            "verdicts": [
                                {
                                    "judge_name": v.judge_name,
                                    "total_score": v.total_score,
                                    "adjusted": v.adjusted,
                                }
                                for v in dr.verdicts
                            ],
                        }
                        for dr in r.discussion_rounds
                    ],
                    "arbitrator_verdict": {
                        "judge_name": r.arbitrator_verdict.judge_name,
                        "total_score": r.arbitrator_verdict.total_score,
                        "reason": r.arbitrator_verdict.reason,
                    }
                    if r.arbitrator_verdict
                    else None,
                }
            )
        return serializable
