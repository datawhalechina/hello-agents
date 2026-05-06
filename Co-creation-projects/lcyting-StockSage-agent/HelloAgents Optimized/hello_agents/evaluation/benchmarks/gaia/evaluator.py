"""
GAIA 评估器模块

负责评估智能体在 GAIA 基准测试上的表现
"""

from typing import Dict, Any, Optional, Union
import time
import re
import json
from pathlib import Path
from hello_agents.evaluation.benchmarks.gaia.dataset import GAIADataset
from hello_agents.evaluation.benchmarks.gaia.metrics import GAIAMetrics


class GAIAEvaluator:
    """GAIA 评估器

    评估智能体的通用AI助手能力,包括:
    - 问题理解和推理
    - 多步骤问题解决
    - 工具使用能力
    - 答案准确性

    GAIA评估采用严格的答案匹配标准:
    - 精确匹配: 答案完全一致
    - 部分匹配: 答案包含正确信息但格式不同

    Attributes:
        dataset: GAIA 数据集
        metrics: 评估指标计算器
        level: 难度级别
        strict_mode: 是否使用严格匹配模式
    """

    def __init__(
        self,
        dataset: Optional[GAIADataset] = None,
        level: Optional[int] = None,
        local_data_dir: Optional[str] = None,
        strict_mode: bool = True,
    ):
        """初始化 GAIA 评估器

        Args:
            dataset: GAIA 数据集,如果为 None 则自动创建
            level: 难度级别 (1-3)
            local_data_dir: 本地数据目录
            strict_mode: 是否使用严格匹配模式
        """
        self.dataset = dataset or GAIADataset(
            level=level, local_data_dir=local_data_dir
        )
        self.metrics = GAIAMetrics()
        self.level = level
        self.strict_mode = strict_mode

    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """评估智能体

        Args:
            agent: 要评估的智能体
            max_samples: 最大评估样本数,None表示评估全部

        Returns:
            评估结果字典,包含各项指标
        """
        print("\n🌟 开始 GAIA 评估...")
        print(f"   智能体: {getattr(agent, 'name', 'Unknown')}")
        print(f"   难度级别: {self.level or '全部'}")
        print(f"   匹配模式: {'严格' if self.strict_mode else '宽松'}")

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
        level_stats = {
            1: {"total": 0, "correct": 0, "partial": 0},
            2: {"total": 0, "correct": 0, "partial": 0},
            3: {"total": 0, "correct": 0, "partial": 0},
        }

        for i, sample in enumerate(dataset):
            if i % 10 == 0:
                print(f"   进度: {i + 1}/{len(dataset)}")

            try:
                sample_result = self.evaluate_sample(agent, sample)
                results.append(sample_result)

                # 按级别统计
                level = sample.get("level", 1)
                if level in level_stats:
                    level_stats[level]["total"] += 1
                    if sample_result["exact_match"]:
                        level_stats[level]["correct"] += 1
                    if sample_result["partial_match"]:
                        level_stats[level]["partial"] += 1

            except Exception as e:
                print(f"   ⚠️ 样本 {i} 评估失败: {e}")
                results.append(
                    {
                        "exact_match": False,
                        "partial_match": False,
                        "predicted": None,
                        "expected": sample.get("final_answer"),
                        "error": str(e),
                        "score": 0.0,
                    }
                )

        # 计算总体指标
        total_samples = len(results)
        exact_matches = sum(1 for r in results if r["exact_match"])
        partial_matches = sum(1 for r in results if r["partial_match"])

        exact_match_rate = exact_matches / total_samples if total_samples > 0 else 0.0
        partial_match_rate = (
            partial_matches / total_samples if total_samples > 0 else 0.0
        )

        # 计算分级指标
        level_metrics = {}
        for level, stats in level_stats.items():
            if stats["total"] > 0:
                level_metrics[f"Level_{level}"] = {
                    "total": stats["total"],
                    "exact_matches": stats["correct"],
                    "partial_matches": stats["partial"],
                    "exact_match_rate": stats["correct"] / stats["total"],
                    "partial_match_rate": stats["partial"] / stats["total"],
                }

        final_results = {
            "benchmark": "GAIA",
            "agent_name": getattr(agent, "name", "Unknown"),
            "strict_mode": self.strict_mode,
            "level_filter": self.level,
            "total_samples": total_samples,
            "exact_matches": exact_matches,
            "partial_matches": partial_matches,
            "exact_match_rate": exact_match_rate,
            "partial_match_rate": partial_match_rate,
            "level_metrics": level_metrics,
            "detailed_results": results,
        }

        print("✅ GAIA 评估完成")
        print(f"   精确匹配率: {exact_match_rate:.2%}")
        print(f"   部分匹配率: {partial_match_rate:.2%}")
        for level_name, metrics in level_metrics.items():
            print(
                f"   {level_name}: {metrics['exact_match_rate']:.2%} 精确 / {metrics['partial_match_rate']:.2%} 部分"
            )

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
            expected_answer = sample.get("final_answer", "")
            level = sample.get("level", 1)
            task_id = sample.get("task_id", "")

            # 构建提示
            prompt = self._build_prompt(question, sample)

            # 调用智能体
            start_time = time.time()
            response = agent.run(prompt)
            execution_time = time.time() - start_time

            # 提取答案
            predicted_answer = self._extract_answer(response)

            # 评估答案
            exact_match = self._check_exact_match(predicted_answer, expected_answer)
            partial_match = self._check_partial_match(predicted_answer, expected_answer)

            # 计算分数
            if exact_match:
                score = 1.0
            elif partial_match:
                score = 0.5
            else:
                score = 0.0

            return {
                "task_id": task_id,
                "level": level,
                "exact_match": exact_match,
                "partial_match": partial_match,
                "score": score,
                "predicted": predicted_answer,
                "expected": expected_answer,
                "response": response,
                "execution_time": execution_time,
            }

        except Exception as e:
            return {
                "task_id": sample.get("task_id", ""),
                "level": sample.get("level", 1),
                "exact_match": False,
                "partial_match": False,
                "score": 0.0,
                "predicted": None,
                "expected": sample.get("final_answer", ""),
                "error": str(e),
            }

    def _create_empty_results(self, agent: Any) -> Dict[str, Any]:
        """创建空的评估结果"""
        return {
            "benchmark": "GAIA",
            "agent_name": getattr(agent, "name", "Unknown"),
            "strict_mode": self.strict_mode,
            "level_filter": self.level,
            "total_samples": 0,
            "exact_matches": 0,
            "partial_matches": 0,
            "exact_match_rate": 0.0,
            "partial_match_rate": 0.0,
            "level_metrics": {},
            "detailed_results": [],
        }

    def _build_prompt(self, question: str, sample: Dict[str, Any]) -> str:
        """构建评估提示"""
        # 构建问题提示
        prompt = f"{question}"

        # 如果有文件附件，添加提示
        if sample.get("file_name"):
            prompt += f"\n\nNote: This question may require reference to the file: {sample['file_name']}"

        return prompt

    def _extract_answer(self, response: str) -> str:
        """从响应中提取答案（GAIA格式）

        GAIA要求答案格式为：FINAL ANSWER: [答案]
        """
        # 首先尝试提取GAIA官方格式的答案
        final_answer_pattern = r"FINAL ANSWER:\s*(.+?)(?:\n|$)"
        match = re.search(final_answer_pattern, response, re.IGNORECASE | re.MULTILINE)
        if match:
            answer = match.group(1).strip()
            # 移除可能的方括号
            answer = answer.strip("[]")
            return answer

        # 备用方案：查找其他答案标记
        answer_patterns = [
            r"答案[：:]\s*(.+)",
            r"最终答案[：:]\s*(.+)",
            r"Final answer[：:]\s*(.+)",
            r"Answer[：:]\s*(.+)",
        ]

        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # 如果没有找到标记，返回最后一个非空行
        lines = response.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("#"):
                return line

        return response.strip()

    def _check_exact_match(self, predicted: str, expected: str) -> bool:
        """检查精确匹配"""
        if not predicted or not expected:
            return False

        # 标准化字符串
        pred_normalized = self._normalize_answer(predicted)
        exp_normalized = self._normalize_answer(expected)

        return pred_normalized == exp_normalized

    def _check_partial_match(self, predicted: str, expected: str) -> bool:
        """检查部分匹配"""
        if not predicted or not expected:
            return False

        # 标准化字符串
        pred_normalized = self._normalize_answer(predicted)
        exp_normalized = self._normalize_answer(expected)

        # 检查包含关系
        if exp_normalized in pred_normalized or pred_normalized in exp_normalized:
            return True

        # 检查关键词匹配
        pred_words = set(pred_normalized.split())
        exp_words = set(exp_normalized.split())

        if not exp_words:
            return False

        # 如果超过70%的期望词汇出现在预测中，认为部分匹配
        overlap = len(pred_words & exp_words)
        return overlap / len(exp_words) >= 0.7

    def _normalize_answer(self, answer: str) -> str:
        """标准化答案字符串（GAIA官方标准化规则）

        根据GAIA论文的标准化规则：
        1. 数字：移除逗号分隔符和单位符号
        2. 字符串：移除冠词、转小写、移除多余空格
        3. 列表：按逗号分隔，每个元素独立标准化
        """
        if not answer:
            return ""

        answer = answer.strip()

        # 检查是否是逗号分隔的列表
        if "," in answer:
            # 分隔并标准化每个元素
            parts = [
                self._normalize_single_answer(p.strip()) for p in answer.split(",")
            ]
            # 按字母顺序排序（GAIA要求）
            parts.sort()
            return ",".join(parts)
        else:
            return self._normalize_single_answer(answer)

    def _normalize_single_answer(self, answer: str) -> str:
        """标准化单个答案（不包含逗号的答案）"""
        answer = answer.strip().lower()

        # 移除常见的冠词
        articles = ["the", "a", "an"]
        words = answer.split()
        if words and words[0] in articles:
            words = words[1:]
            answer = " ".join(words)

        # 移除货币符号和百分号
        answer = (
            answer.replace("$", "").replace("%", "").replace("€", "").replace("£", "")
        )

        # 移除数字中的逗号分隔符（如 1,000 -> 1000）
        # 但保留小数点
        answer = re.sub(r"(\d),(\d)", r"\1\2", answer)

        # 移除多余空格
        answer = " ".join(answer.split())

        # 移除末尾的标点符号
        answer = answer.rstrip(".,;:!?")

        return answer

    def export_to_gaia_format(
        self,
        results: Dict[str, Any],
        output_path: Union[str, Path],
        include_reasoning: bool = True,
    ) -> None:
        """导出为GAIA官方格式

        GAIA格式要求：
        - JSONL格式（每行一个JSON对象）
        - 每个对象包含：task_id, model_answer, reasoning_trace（可选）

        Args:
            results: 评估结果
            output_path: 输出文件路径
            include_reasoning: 是否包含推理轨迹
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        detailed_results = results.get("detailed_results", [])

        with open(output_path, "w", encoding="utf-8") as f:
            for result in detailed_results:
                gaia_result = {
                    "task_id": result.get("task_id", ""),
                    "model_answer": result.get("predicted", ""),
                }

                if include_reasoning:
                    gaia_result["reasoning_trace"] = result.get("response", "")

                f.write(json.dumps(gaia_result, ensure_ascii=False) + "\n")

        print("✅ GAIA格式结果已导出")
        print(f"   输出文件: {output_path}")
        print(f"   样本数: {len(detailed_results)}")
        print(f"   包含推理轨迹: {include_reasoning}")
