"""
医疗领域 GAIA 评估器

不依赖 hello_agents 包，直接导入 smart_answer_matcher。
设计思路：
1. 使用 MedicalGAIADataset 作为数据源
2. 支持 alternative_answers 的智能匹配
3. 提供领域特定的评分报告（按科室/题型分组）
4. 加权评分：高难度临床决策题（ICU/评分）权重更高
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import re
import time
from datetime import datetime
import sys
import os

_GAIA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _GAIA_DIR not in sys.path:
    sys.path.insert(0, _GAIA_DIR)

from smart_answer_matcher import SmartAnswerMatcher  # noqa: E402
from medical.dataset import MedicalGAIADataset  # noqa: E402


class MedicalGAIAEvaluator:
    """医疗领域定制版 GAIA 评估器

    Features:
    - SmartAnswerMatcher 多策略级联匹配
    - alternative_answers 扩展匹配
    - 领域分组统计（按科室）
    - 加权评分（高难度临床题更高权重）
    - 医疗专用 Markdown 报告
    """

    DOMAIN_WEIGHTS = {
        "infectious_disease": 1.0,
        "medical_terminology": 1.0,
        "clinical_laboratory": 1.0,
        "dosing_calculation": 1.2,
        "anticoagulation": 1.2,
        "clinical_calculation": 1.0,
        "iv_infusion": 1.2,
        "critical_care": 1.5,
        "clinical_scoring": 1.5,
        "abg_interpretation": 1.5,
    }

    def __init__(
        self,
        level: Optional[int] = None,
        llm=None,
        use_semantic: bool = True,
        use_llm_judge: bool = False,
    ):
        self.dataset = MedicalGAIADataset(level=level)
        self.matcher = SmartAnswerMatcher(
            llm=llm,
            use_semantic=use_semantic,
            use_llm_judge=use_llm_judge,
        )
        self.level = level
        self.use_semantic = use_semantic
        self.use_llm_judge = use_llm_judge

    def evaluate_sample(self, agent: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个医疗样本（支持 alternative_answers 和加权评分）"""
        try:
            question = sample.get("question", "")
            expected_answer = sample.get("final_answer", "")
            alternative_answers = sample.get("alternative_answers", [])
            level = sample.get("level", 1)
            task_id = sample.get("task_id", "")
            domain = sample.get("domain", "general")

            prompt = self._build_prompt(question)
            start_time = time.time()
            response = agent.run(prompt)
            execution_time = time.time() - start_time

            predicted_answer = self._extract_answer(response)

            # 精确匹配
            exact_match = self._check_exact_match(predicted_answer, expected_answer)
            partial_match = self._check_partial_match(predicted_answer, expected_answer)

            # SmartAnswerMatcher 对标准答案
            smart_main = self.matcher.match(predicted_answer, expected_answer)

            # 对 alternative_answers 尝试匹配
            smart_alt = False
            alt_method = "none"
            alt_confidence = 0.0
            for alt in alternative_answers:
                r = self.matcher.match(predicted_answer, alt)
                if r.match:
                    smart_alt = True
                    alt_method = r.method
                    alt_confidence = max(alt_confidence, r.confidence)

            smart_match = smart_main.match or smart_alt
            smart_method = smart_main.method if smart_main.match else alt_method
            smart_confidence = max(smart_main.confidence, alt_confidence)

            # 评分
            if exact_match:
                score = 1.0
            elif smart_match:
                score = 0.9
            elif partial_match:
                score = 0.5
            else:
                score = 0.0

            return {
                "task_id": task_id,
                "level": level,
                "domain": domain,
                "exact_match": exact_match,
                "partial_match": partial_match,
                "smart_match": smart_match,
                "smart_method": smart_method,
                "smart_confidence": smart_confidence,
                "score": score,
                "weighted_score": score * self.DOMAIN_WEIGHTS.get(domain, 1.0),
                "predicted": predicted_answer,
                "expected": expected_answer,
                "alternative_answers": alternative_answers,
                "response": response,
                "execution_time": execution_time,
            }
        except Exception as e:
            return {
                "task_id": sample.get("task_id", ""),
                "level": sample.get("level", 1),
                "domain": sample.get("domain", "general"),
                "exact_match": False,
                "partial_match": False,
                "smart_match": False,
                "smart_method": "error",
                "smart_confidence": 0.0,
                "score": 0.0,
                "weighted_score": 0.0,
                "predicted": None,
                "expected": sample.get("final_answer", ""),
                "error": str(e),
            }

    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """运行完整医疗 GAIA 评估"""
        print("\n🏥 开始医疗 GAIA 评估...")
        print(f"   智能体: {getattr(agent, 'name', 'Unknown')}")
        print(f"   难度级别: {self.level or '全部 (1-3)'}")

        dataset = self.dataset.load()
        if not dataset:
            print("   ⚠️ 数据集为空")
            return self._create_empty_results(agent)

        if max_samples:
            dataset = dataset[:max_samples]

        print(f"   样本数: {len(dataset)}")

        results = []
        for i, sample in enumerate(dataset):
            result = self.evaluate_sample(agent, sample)
            results.append(result)

        return self._aggregate_results(results, agent)

    def _aggregate_results(self, results: List[Dict], agent: Any) -> Dict[str, Any]:
        total = len(results)
        exact_matches = sum(1 for r in results if r["exact_match"])
        smart_matches = sum(1 for r in results if r["smart_match"])
        partial_matches = sum(1 for r in results if r["partial_match"])

        # 按级别
        level_stats: Dict[int, Dict] = {}
        for r in results:
            lv = r["level"]
            if lv not in level_stats:
                level_stats[lv] = {"total": 0, "exact": 0, "smart": 0}
            level_stats[lv]["total"] += 1
            if r["exact_match"]:
                level_stats[lv]["exact"] += 1
            if r["smart_match"]:
                level_stats[lv]["smart"] += 1

        # 按领域
        domain_stats: Dict[str, Dict] = {}
        for r in results:
            dom = r.get("domain", "general")
            if dom not in domain_stats:
                domain_stats[dom] = {"total": 0, "exact": 0, "smart": 0}
            domain_stats[dom]["total"] += 1
            if r["exact_match"]:
                domain_stats[dom]["exact"] += 1
            if r["smart_match"]:
                domain_stats[dom]["smart"] += 1

        # 匹配方法分布
        method_stats: Dict[str, int] = {}
        for r in results:
            m = r.get("smart_method", "none")
            method_stats[m] = method_stats.get(m, 0) + 1

        total_weighted = sum(r.get("weighted_score", 0.0) for r in results)
        max_weighted = sum(
            self.DOMAIN_WEIGHTS.get(r.get("domain", "general"), 1.0) for r in results
        )

        final_results = {
            "benchmark": "Medical-GAIA",
            "agent_name": getattr(agent, "name", "Unknown"),
            "total_samples": total,
            "exact_matches": exact_matches,
            "smart_matches": smart_matches,
            "partial_matches": partial_matches,
            "exact_match_rate": exact_matches / total if total > 0 else 0.0,
            "smart_match_rate": smart_matches / total if total > 0 else 0.0,
            "partial_match_rate": partial_matches / total if total > 0 else 0.0,
            "weighted_score": round(total_weighted, 2),
            "max_weighted_score": round(max_weighted, 2),
            "weighted_accuracy": total_weighted / max_weighted
            if max_weighted > 0
            else 0.0,
            "improvement": {
                "extra_matches_via_smart": smart_matches - exact_matches,
                "exact_match_rate": exact_matches / total if total > 0 else 0.0,
                "smart_match_rate": smart_matches / total if total > 0 else 0.0,
            },
            "level_stats": level_stats,
            "domain_stats": domain_stats,
            "method_stats": method_stats,
            "detailed_results": results,
        }

        self._print_summary(final_results)
        return final_results

    def _print_summary(self, results: Dict[str, Any]) -> None:
        print("\n✅ 医疗 GAIA 评估完成")
        print(f"   {'=' * 40}")
        print(f"   总样本: {results['total_samples']}")
        print(f"   精确匹配率: {results['exact_match_rate']:.2%}")
        print(f"   智能匹配率: {results['smart_match_rate']:.2%}")
        print(
            f"   额外匹配(智能): +{results['improvement']['extra_matches_via_smart']}"
        )
        print(f"   加权准确率: {results['weighted_accuracy']:.2%}")
        print(f"   {'=' * 40}")
        print("   按级别:")
        for lv in sorted(results.get("level_stats", {})):
            s = results["level_stats"][lv]
            print(
                f"     Level {lv}: 精确 {s['exact']}/{s['total']} "
                f"({s['exact'] / s['total']:.0%}), "
                f"智能 {s['smart']}/{s['total']} ({s['smart'] / s['total']:.0%})"
            )
        print(f"   匹配方法: {results.get('method_stats', {})}")

    def _create_empty_results(self, agent: Any) -> Dict[str, Any]:
        return {
            "benchmark": "Medical-GAIA",
            "agent_name": getattr(agent, "name", "Unknown"),
            "total_samples": 0,
            "exact_matches": 0,
            "smart_matches": 0,
            "partial_matches": 0,
            "exact_match_rate": 0.0,
            "smart_match_rate": 0.0,
            "partial_match_rate": 0.0,
            "weighted_score": 0.0,
            "max_weighted_score": 0.0,
            "weighted_accuracy": 0.0,
            "improvement": {},
            "level_stats": {},
            "domain_stats": {},
            "method_stats": {},
            "detailed_results": [],
        }

    def _build_prompt(self, question: str) -> str:
        return (
            f"{question}\n\n"
            f"Please provide your FINAL ANSWER in the format: FINAL ANSWER: <your answer>"
        )

    def _extract_answer(self, response: str) -> str:
        patterns = [
            r"FINAL ANSWER:\s*(.+?)(?:\n|$)",
            r"最终答案[：:]\s*(.+)",
            r"Answer[：:]\s*(.+)",
        ]
        for pat in patterns:
            m = re.search(pat, response, re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip().strip("[]")
        lines = response.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return response.strip()

    def _check_exact_match(self, predicted: str, expected: str) -> bool:
        if not predicted or not expected:
            return False
        return self._normalize_answer(predicted) == self._normalize_answer(expected)

    def _check_partial_match(self, predicted: str, expected: str) -> bool:
        if not predicted or not expected:
            return False
        pn = self._normalize_answer(predicted)
        en = self._normalize_answer(expected)
        if en in pn or pn in en:
            return True
        pw = set(pn.split())
        ew = set(en.split())
        if not ew:
            return False
        return len(pw & ew) / len(ew) >= 0.7

    def _normalize_answer(self, answer: str) -> str:
        if not answer:
            return ""
        answer = answer.strip()
        if "," in answer:
            parts = [self._normalize_single(p.strip()) for p in answer.split(",")]
            parts.sort()
            return ",".join(parts)
        return self._normalize_single(answer)

    def _normalize_single(self, answer: str) -> str:
        answer = answer.strip().lower()
        articles = ["the", "a", "an"]
        words = answer.split()
        if words and words[0] in articles:
            words = words[1:]
            answer = " ".join(words)
        answer = (
            answer.replace("$", "").replace("%", "").replace("€", "").replace("£", "")
        )
        answer = re.sub(r"(\d),(\d)", r"\1\2", answer)
        answer = " ".join(answer.split())
        answer = answer.rstrip(".,;:!?")
        return answer

    def generate_medical_report(
        self,
        results: Dict[str, Any],
        output_file: Optional[Union[str, Path]] = None,
    ) -> str:
        """生成医疗领域专属评估报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        domain_rows = []
        for dom, s in sorted(results.get("domain_stats", {}).items()):
            if s["total"] == 0:
                continue
            exact_pct = s["exact"] / s["total"] * 100
            smart_pct = s["smart"] / s["total"] * 100
            bar = "█" * int(smart_pct / 5)
            domain_rows.append(
                f"| {dom:25s} | {s['total']:3d} | {exact_pct:5.1f}% | {smart_pct:5.1f}% | {bar}"
            )
        domain_table = "\n".join(domain_rows) if domain_rows else "  (无数据)"

        level_rows = []
        for lv in sorted(results.get("level_stats", {})):
            s = results["level_stats"][lv]
            exact_pct = s["exact"] / s["total"] * 100
            smart_pct = s["smart"] / s["total"] * 100
            level_rows.append(
                f"| Level {lv} | {s['total']:3d} | {exact_pct:5.1f}% | {smart_pct:5.1f}%"
            )
        level_table = "\n".join(level_rows)

        detailed = results.get("detailed_results", [])[:10]
        sample_rows = []
        for r in detailed:
            em = "✅" if r.get("exact_match") else "❌"
            sm = "✅" if r.get("smart_match") else "❌"
            method = r.get("smart_method", "-")[:14]
            pred = (r.get("predicted") or "")[:35]
            exp = (r.get("expected") or "")[:35]
            sample_rows.append(
                f"| {r.get('task_id', ''):8s} | {em} | {sm} | {method:14s} | {pred:35s} | {exp:35s} |"
            )
        sample_table = "\n".join(sample_rows) if sample_rows else "  (无样本)"

        improvement = results.get("improvement", {})

        report = f"""# 医疗 GAIA 评估报告

**生成时间**: {now}

## 📊 评估概览

| 指标 | 数值 |
|------|------|
| **基准** | Medical-GAIA |
| **智能体** | {results.get("agent_name", "Unknown")} |
| **总样本数** | {results.get("total_samples", 0)} |
| **精确匹配率** | {results.get("exact_match_rate", 0):.2%} |
| **智能匹配率** | {results["smart_match_rate"]:.2%} |
| **额外匹配（智能 vs 精确）** | +{improvement.get("extra_matches_via_smart", 0)} |
| **加权准确率** | {results.get("weighted_accuracy", 0):.2%} |

## 📈 按难度级别

| 级别 | 样本 | 精确匹配 | 智能匹配 |
|------|------|----------|----------|
{level_table}

## 🏥 按医疗领域

| 领域 | 样本 | 精确 | 智能 | 可视化 |
|------|------|------|------|--------|
{domain_table}

## 🔬 匹配方法分布

{results.get("method_stats", {})}

## 📝 样本详情（前10个）

| 任务ID | 精确 | 智能 | 方法 | 预测答案（截断） | 标准答案（截断） |
|--------|------|------|------|------------------|------------------|
{sample_table}

## 💊 临床建议

{self._generate_clinical_suggestions(results)}

---

*报告由 MedicalGAIAEvaluator 自动生成*
"""
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"✅ 医疗评估报告已导出: {output_path}")

        return report

    def _generate_clinical_suggestions(self, results: Dict) -> str:
        suggestions = []
        domain_stats = results.get("domain_stats", {})
        low_performing = [
            (dom, s)
            for dom, s in domain_stats.items()
            if s["total"] > 0 and s["smart"] / s["total"] < 0.5
        ]
        if low_performing:
            doms = ", ".join(d for d, _ in low_performing)
            suggestions.append(
                f"⚠️ 以下领域表现较弱（<50%）：{doms}。建议针对这些领域优化智能体知识。"
            )

        exact = results.get("exact_match_rate", 0)
        smart = results.get("smart_match_rate", 0)
        if smart > exact + 0.1:
            suggestions.append(
                f"💡 智能匹配贡献显著（+{(smart - exact) * 100:.0f}%），"
                f"说明模型答案在数值等价、单位换算等层面正确但格式不一致。"
            )

        weighted = results.get("weighted_accuracy", 0)
        if weighted >= 0.8:
            suggestions.append(
                "✅ 临床决策质量优秀。智能体在关键科室（ICU、用药）表现可靠。"
            )
        elif weighted >= 0.5:
            suggestions.append(
                "⚠️ 临床决策质量中等。高权重题目（重症、评分）需重点改进。"
            )
        else:
            suggestions.append("❌ 临床决策质量不足。建议增加医学领域训练数据。")

        if not suggestions:
            suggestions.append("✅ 所有领域表现正常。")

        return "\n".join(f"  {s}" for s in suggestions)
