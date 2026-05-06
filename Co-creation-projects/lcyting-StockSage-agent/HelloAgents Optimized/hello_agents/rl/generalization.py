"""泛化能力评估模块

提供模型泛化能力的系统评估，包括：
- 难度迁移测试
- 数值鲁棒性测试
- 结构鲁棒性测试
- 过拟合检测与警告
"""

import re
import random
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class DifficultyLevel(Enum):
    """难度级别"""

    EASY = 1  # 1-2步推理
    MEDIUM = 2  # 3-4步推理
    HARD = 3  # 5-6步推理
    EXPERT = 4  # 7+步推理


@dataclass
class GeneralizationMetrics:
    """泛化评估指标"""

    base_accuracy: float = 0.0
    easy_accuracy: float = 0.0
    medium_accuracy: float = 0.0
    hard_accuracy: float = 0.0
    expert_accuracy: float = 0.0
    difficulty_slope: float = 0.0  # 难度衰减斜率
    numerical_robustness: float = 0.0  # 数值鲁棒性
    structural_robustness: float = 0.0  # 结构鲁棒性
    generalization_score: float = 0.0  # 综合泛化得分


@dataclass
class OverfitWarning:
    """过拟合警告"""

    level: str  # "low", "medium", "high"
    message: str
    suggestions: List[str] = field(default_factory=list)


class NumberTransformer:
    """数值变换器 - 用于测试数值泛化能力"""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def transform(self, text: str, factor: float = 2.0) -> str:
        """对文本中的数值进行变换

        Args:
            text: 原始文本
            factor: 变换因子

        Returns:
            变换后的文本
        """

        # 找到所有数字
        def replace_number(match):
            num_str = match.group(0)
            if "." in num_str:
                try:
                    num = float(num_str)
                    new_num = int(num * factor) if num == int(num) else num * factor
                    return (
                        str(int(new_num))
                        if new_num == int(new_num)
                        else str(round(new_num, 2))
                    )
                except ValueError:
                    return num_str
            else:
                try:
                    num = int(num_str)
                    new_num = num * factor
                    return str(int(new_num))
                except ValueError:
                    return num_str

        # 匹配整数和小数
        pattern = r"-?\d+\.?\d*"
        return re.sub(pattern, replace_number, text)

    def random_transform(self, text: str) -> str:
        """随机变换数值"""
        factor = self.rng.uniform(0.5, 3.0)
        return self.transform(text, factor)

    def scale_up(self, text: str) -> str:
        """等比放大"""
        return self.transform(text, 2.0)

    def scale_down(self, text: str) -> str:
        """等比缩小"""
        return self.transform(text, 0.5)


class QuestionParaphraser:
    """问题改写器 - 用于测试结构泛化能力"""

    # 同义表达映射
    PARAPHRASE_PATTERNS = [
        # 加法
        (r"(\d+)\s*\+\s*(\d+)", lambda m: f"{m.group(1)} added to {m.group(2)}"),
        # 减法
        (r"(\d+)\s*-\s*(\d+)", lambda m: f"{m.group(1)} subtract {m.group(2)}"),
        # 乘法
        (r"(\d+)\s*\*\s*(\d+)", lambda m: f"{m.group(1)} multiplied by {m.group(2)}"),
        (r"(\d+)\s*×\s*(\d+)", lambda m: f"{m.group(1)} times {m.group(2)}"),
        # 除法
        (r"(\d+)\s*/\s*(\d+)", lambda m: f"{m.group(1)} divided by {m.group(2)}"),
        (r"(\d+)\s*÷\s*(\d+)", lambda m: f"{m.group(1)} divided by {m.group(2)}"),
    ]

    # 问法变体
    QUESTION_TEMPLATES = [
        "How much is {}?",
        "What is the result of {}?",
        "Calculate {}",
        "Compute {}",
        "{} equals what?",
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def paraphrase(self, question: str) -> str:
        """对问题进行同义改写"""
        result = question

        # 替换运算符
        for pattern, replacement in self.PARAPHRASE_PATTERNS:
            result = re.sub(pattern, replacement, result)

        # 改变问法
        if self.rng.random() > 0.5:
            # 提取计算部分
            calc_match = re.search(r"[\d+\-*/×÷.]+", result)
            if calc_match:
                calc = calc_match.group(0)
                template = self.rng.choice(self.QUESTION_TEMPLATES)
                result = template.format(calc)

        return result

    def synonym_replace(self, text: str) -> str:
        """同义词替换"""
        synonyms = {
            "plus": ["added to", "more than", "increased by"],
            "minus": ["subtract", "less than", "decreased by"],
            "times": ["multiplied by", "of", "times"],
            "divided by": ["over", "per"],
            "How many": ["What is the total number of", "Find the count of"],
            "total": ["entire", "overall", "sum of"],
        }

        result = text
        for word, alternatives in synonyms.items():
            if word in result.lower():
                replacement = self.rng.choice(alternatives)
                result = re.sub(
                    r"\b" + re.escape(word) + r"\b",
                    replacement,
                    result,
                    flags=re.IGNORECASE,
                )

        return result


class DifficultyAnalyzer:
    """难度分析器"""

    @staticmethod
    def count_reasoning_steps(answer_text: str) -> int:
        """估算推理步骤数

        通过统计等号数量和中间计算来估算
        """
        if not answer_text:
            return 1

        # 统计 <<...>> 格式的计算步骤
        calc_steps = answer_text.count("<<")

        # 统计独立计算行
        calc_lines = len(
            [
                line
                for line in answer_text.split("\n")
                if "=" in line and "==" not in line
            ]
        )

        # 统计 "Step X:" 模式
        step_matches = len(re.findall(r"Step\s*\d+:?", answer_text, re.IGNORECASE))

        steps = max(calc_steps, calc_lines, step_matches, 1)

        # 返回实际的步骤数（让 classify_difficulty 处理难度分类）
        return steps

    @staticmethod
    def classify_difficulty(steps: int) -> DifficultyLevel:
        """根据步骤数分类难度

        阈值设计：
        - EASY: 1-2步推理（基础算术）
        - MEDIUM: 3-4步推理（多步应用题）
        - HARD: 5-6步推理（复杂问题）
        - EXPERT: 7+步推理（竞赛级别）
        """
        if steps <= 2:
            return DifficultyLevel.EASY
        elif steps <= 4:
            return DifficultyLevel.MEDIUM
        elif steps <= 6:
            return DifficultyLevel.HARD
        else:
            return DifficultyLevel.EXPERT


class GeneralizationEvaluator:
    """泛化能力评估器

    核心功能：
    1. 难度曲线评估 - 测试不同难度题目上的表现
    2. 数值鲁棒性 - 改变数值后是否仍能正确
    3. 结��鲁棒性 - 改变问题表述后是否仍能正确
    4. 过拟合检测 - 生成警告和建议
    """

    def __init__(
        self,
        model: Any = None,
        generate_fn: Callable[[str], str] = None,
        answer_extractor: Callable[[str], Optional[str]] = None,
    ):
        """
        初始化

        Args:
            model: 模型（可选）
            generate_fn: 生成函数，接收问题返回答案
            answer_extractor: 答案提取函数
        """
        self.model = model
        self.generate_fn = generate_fn
        self.answer_extractor = answer_extractor or self._default_answer_extractor

        self.number_transformer = NumberTransformer()
        self.paraphraser = QuestionParaphraser()
        self.difficulty_analyzer = DifficultyAnalyzer()

    @staticmethod
    def _default_answer_extractor(text: str) -> Optional[str]:
        """默认答案提取器"""
        # 尝试多种格式
        patterns = [
            r"####\s*([^\n]+)",
            r"Final Answer:\s*([^\n]+)",
            r"=\s*([^\n]+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                return match.group(1).strip()

        # 取最后一个数字
        numbers = re.findall(r"-?\d+\.?\d*", text)
        if numbers:
            return numbers[-1]

        return None

    def evaluate(
        self, test_data: List[Dict[str, Any]], train_data: List[Dict[str, Any]] = None
    ) -> GeneralizationMetrics:
        """
        执行完整泛化评估

        Args:
            test_data: 测试数据，格式：[{"question": str, "answer": str}, ...]
            train_data: 训练数据（可选，用于对比）

        Returns:
            泛化评估指标
        """
        metrics = GeneralizationMetrics()

        if not test_data:
            return metrics

        # 1. 基础准确率
        metrics.base_accuracy = self._evaluate_base(test_data)

        # 2. 按难度分组评估
        difficulty_results = self._evaluate_by_difficulty(test_data)
        metrics.easy_accuracy = difficulty_results.get(DifficultyLevel.EASY, 0.0)
        metrics.medium_accuracy = difficulty_results.get(DifficultyLevel.MEDIUM, 0.0)
        metrics.hard_accuracy = difficulty_results.get(DifficultyLevel.HARD, 0.0)
        metrics.expert_accuracy = difficulty_results.get(DifficultyLevel.EXPERT, 0.0)

        # 计算难度斜率（难度增加时准确率的衰减）
        if metrics.easy_accuracy > 0:
            metrics.difficulty_slope = (
                (metrics.easy_accuracy - metrics.medium_accuracy)
                + (metrics.medium_accuracy - metrics.hard_accuracy)
                + (metrics.hard_accuracy - metrics.expert_accuracy)
            ) / 3

        # 3. 数值鲁棒性
        metrics.numerical_robustness = self._evaluate_numerical_robustness(test_data)

        # 4. 结构鲁棒性
        metrics.structural_robustness = self._evaluate_structural_robustness(test_data)

        # 5. 综合泛化得分
        metrics.generalization_score = self._compute_generalization_score(metrics)

        return metrics

    def _evaluate_base(self, test_data: List[Dict]) -> float:
        """基础准确率评估"""
        if not self.generate_fn:
            return 0.0

        correct = 0
        total = len(test_data)

        for item in test_data:
            question = item.get("question", "")
            expected = item.get("answer", "")

            # 生成答案
            generated = self.generate_fn(question)

            # 提取并比较
            pred = self.answer_extractor(generated)
            truth = self.answer_extractor(expected)

            if pred and truth and self._compare_numbers(pred, truth):
                correct += 1

        return correct / total if total > 0 else 0.0

    def _evaluate_by_difficulty(
        self, test_data: List[Dict]
    ) -> Dict[DifficultyLevel, float]:
        """按难度分组评估"""
        groups = defaultdict(list)

        for item in test_data:
            answer = item.get("answer", "")
            steps = self.difficulty_analyzer.count_reasoning_steps(answer)
            difficulty = self.difficulty_analyzer.classify_difficulty(steps)
            groups[difficulty].append(item)

        results = {}
        for difficulty, items in groups.items():
            accuracy = self._evaluate_group(items)
            results[difficulty] = accuracy

        return results

    def _evaluate_group(self, items: List[Dict]) -> float:
        """评估一组数据"""
        if not self.generate_fn:
            return 0.0

        correct = 0
        total = len(items)

        for item in items:
            question = item.get("question", "")
            expected = item.get("answer", "")

            generated = self.generate_fn(question)
            pred = self.answer_extractor(generated)
            truth = self.answer_extractor(expected)

            if pred and truth and self._compare_numbers(pred, truth):
                correct += 1

        return correct / total if total > 0 else 0.0

    def _evaluate_numerical_robustness(self, test_data: List[Dict]) -> float:
        """数值鲁棒性评估

        对数值进行变换后测试模型是否仍能正确解答
        """
        if not self.generate_fn:
            return 0.0

        correct = 0
        total = 0

        for item in test_data:
            question = item.get("question", "")
            expected = item.get("answer", "")

            # 变换数值
            transformed_q = self.number_transformer.transform(question, 2.0)
            transformed_a = self.number_transformer.transform(expected, 2.0)

            if transformed_q == question:
                continue  # 没有可变换的数值

            total += 1

            # 生成并比较
            generated = self.generate_fn(transformed_q)
            pred = self.answer_extractor(generated)
            truth = self.answer_extractor(transformed_a)

            if pred and truth and self._compare_numbers(pred, truth):
                correct += 1

        return correct / total if total > 0 else 0.0

    def _evaluate_structural_robustness(self, test_data: List[Dict]) -> float:
        """结构鲁棒性评估

        改变问题的表述方式后测试模型是否仍能正确解答
        """
        if not self.generate_fn:
            return 0.0

        correct = 0
        total = 0

        for item in test_data:
            question = item.get("question", "")
            expected = item.get("answer", "")

            # 改写问题
            paraphrased = self.paraphraser.paraphrase(question)

            if paraphrased == question:
                continue

            total += 1

            # 生成并比较
            generated = self.generate_fn(paraphrased)
            pred = self.answer_extractor(generated)
            truth = self.answer_extractor(expected)

            if pred and truth and self._compare_numbers(pred, truth):
                correct += 1

        return correct / total if total > 0 else 0.0

    @staticmethod
    def _compare_numbers(pred: str, truth: str, tolerance: float = 1e-4) -> bool:
        """比较两个数值答案"""
        try:
            pred_num = float(re.sub(r"[^\d.]", "", pred))
            truth_num = float(re.sub(r"[^\d.]", "", truth))
            return abs(pred_num - truth_num) < tolerance
        except (ValueError, TypeError):
            return pred.strip() == truth.strip()

    def _compute_generalization_score(self, metrics: GeneralizationMetrics) -> float:
        """计算综合泛化得分

        公式：
        G = 0.25 * base + 0.2 * difficulty_trend +
            0.25 * numerical + 0.3 * structural

        其中 difficulty_trend 衡量难度增加时准确率的保持程度
        """
        # 难度趋势：简单题目与困难题目的比值
        if metrics.easy_accuracy > 0:
            difficulty_trend = min(1.0, metrics.hard_accuracy / metrics.easy_accuracy)
        else:
            difficulty_trend = 0.0

        score = (
            0.25 * metrics.base_accuracy
            + 0.20 * difficulty_trend
            + 0.25 * metrics.numerical_robustness
            + 0.30 * metrics.structural_robustness
        )

        return min(1.0, max(0.0, score))

    def detect_overfitting(
        self, metrics: GeneralizationMetrics, train_accuracy: float = None
    ) -> List[OverfitWarning]:
        """检测过拟合

        Args:
            metrics: 泛化评估指标
            train_accuracy: 训练集准确率（如果有）

        Returns:
            过拟合警告列表
        """
        warnings = []

        # 警告1：训练准确率高但泛化得分低
        if train_accuracy and metrics.generalization_score:
            gap = train_accuracy - metrics.generalization_score
            if gap > 0.3:
                warnings.append(
                    OverfitWarning(
                        level="high",
                        message=f"严重过拟合：训练准确率{train_accuracy:.1%}但泛化得分仅{metrics.generalization_score:.1%}",
                        suggestions=[
                            "增加训练数据量或使用数据增强",
                            "使用更强的正则化(weight_decay, dropout)",
                            "减少模型容量或训练轮数",
                            "使用early stopping",
                        ],
                    )
                )
            elif gap > 0.15:
                warnings.append(
                    OverfitWarning(
                        level="medium",
                        message=f"中等过拟合：训练准确率{train_accuracy:.1%}，泛化得分{metrics.generalization_score:.1%}",
                        suggestions=[
                            "添加正则化",
                            "检查数据增强策略",
                            "考虑使用验证集early stopping",
                        ],
                    )
                )

        # 警告2：数值鲁棒性差
        if metrics.numerical_robustness < 0.5 and metrics.base_accuracy > 0.6:
            warnings.append(
                OverfitWarning(
                    level="medium",
                    message=f"数值泛化不足：数值鲁棒性仅{metrics.numerical_robustness:.1%}",
                    suggestions=[
                        "训练时对数值进行随机变换",
                        "增加数值范围的多样性",
                        "使用课程学习从简单数值到复杂数值",
                    ],
                )
            )

        # 警告3：结构鲁棒性差
        if metrics.structural_robustness < 0.5 and metrics.base_accuracy > 0.6:
            warnings.append(
                OverfitWarning(
                    level="medium",
                    message=f"结构泛化不足：结构鲁棒性仅{metrics.structural_robustness:.1%}",
                    suggestions=[
                        "使用问题改写进行数据增强",
                        "增加问题表述的多样性",
                        "在训练时使用同义词替换",
                    ],
                )
            )

        # 警告4：难度衰减严重
        if metrics.difficulty_slope > 0.2 and metrics.easy_accuracy > 0.7:
            warnings.append(
                OverfitWarning(
                    level="low",
                    message=f"难度泛化不足：难度斜率{metrics.difficulty_slope:.2f}",
                    suggestions=[
                        "在训练集中增加难题比例",
                        "使用课程学习策略",
                        "单独增强难题的训练",
                    ],
                )
            )

        return warnings


class DataAugmentor:
    """数据增强器

    提供多种数据增强策略以提升泛化能力：
    1. 数值变换 - 改变数值
    2. 问题改写 - 改变表述
    3. 逆向生成 - 从答案生成问题
    4. 难度调整 - 增减步骤
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.number_transformer = NumberTransformer(seed)
        self.paraphraser = QuestionParaphraser(seed)

    def augment(
        self,
        data: List[Dict[str, Any]],
        num_augmentations: int = 3,
        strategies: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        数据增强

        Args:
            data: 原始数据
            num_augmentations: 每个样本增强次数
            strategies: 增强策略列表

        Returns:
            增强后的数据
        """
        if strategies is None:
            strategies = ["number", "paraphrase", "both"]

        augmented = []

        for item in data:
            for _ in range(num_augmentations):
                strategy = self.rng.choice(strategies)

                if strategy == "number":
                    new_item = self._augment_number(item)
                elif strategy == "paraphrase":
                    new_item = self._augment_paraphrase(item)
                elif strategy == "both":
                    new_item = self._augment_both(item)
                else:
                    new_item = item

                if new_item:
                    augmented.append(new_item)

        return data + augmented

    def _augment_number(self, item: Dict) -> Optional[Dict]:
        """数值变换增强"""
        try:
            question = item.get("question", "")
            answer = item.get("answer", "")

            # 随机变换因子
            factor = self.rng.choice([0.5, 1.5, 2.0, 3.0])

            new_q = self.number_transformer.transform(question, factor)
            new_a = self.number_transformer.transform(answer, factor)

            if new_q != question and new_a != answer:
                return {
                    "question": new_q,
                    "answer": new_a,
                    "augmented": True,
                    "strategy": "number",
                }
        except Exception:
            pass

        return None

    def _augment_paraphrase(self, item: Dict) -> Optional[Dict]:
        """问题改写增强"""
        try:
            question = item.get("question", "")
            answer = item.get("answer", "")

            new_q = self.paraphraser.paraphrase(question)

            if new_q != question:
                return {
                    "question": new_q,
                    "answer": answer,
                    "augmented": True,
                    "strategy": "paraphrase",
                }
        except Exception:
            pass

        return None

    def _augment_both(self, item: Dict) -> Optional[Dict]:
        """组合增强"""
        try:
            question = item.get("question", "")
            answer = item.get("answer", "")

            # 先变换数值
            factor = self.rng.choice([1.5, 2.0])
            new_q = self.number_transformer.transform(question, factor)
            new_a = self.number_transformer.transform(answer, factor)

            # 再改写问题
            new_q = self.paraphraser.paraphrase(new_q)

            if new_q != question and new_a != answer:
                return {
                    "question": new_q,
                    "answer": new_a,
                    "augmented": True,
                    "strategy": "both",
                }
        except Exception:
            pass

        return None


def create_generalization_evaluator(
    generate_fn: Callable[[str], str] = None,
    answer_extractor: Callable[[str], Optional[str]] = None,
) -> GeneralizationEvaluator:
    """
    创建泛化能力评估器（便捷函数）
    """
    return GeneralizationEvaluator(
        generate_fn=generate_fn, answer_extractor=answer_extractor
    )


def create_data_augmentor(seed: int = 42) -> DataAugmentor:
    """创建数据增强器（便捷函数）"""
    return DataAugmentor(seed=seed)


# 示例用法
if __name__ == "__main__":
    # 创建模拟的生成函数
    def mock_generate(question: str) -> str:
        # 模拟模型输出
        if "48" in question and "24" in question:
            return "Step 1: 48 + 24 = 72\nFinal Answer: 72"
        elif "16" in question:
            return "Step 1: 16 / 2 = 8\nFinal Answer: 8"
        else:
            return "Final Answer: 42"

    # 创建评估器
    evaluator = GeneralizationEvaluator(generate_fn=mock_generate)

    # 测试数据
    test_data = [
        {"question": "What is 48 + 24?", "answer": "72"},
        {"question": "What is 16 divided by 2?", "answer": "8"},
        {
            "question": "If Maria has 5 apples and buys 3 more, how many does she have?",
            "answer": "8",
        },
    ]

    # 评估泛化能力
    metrics = evaluator.evaluate(test_data)

    print("=" * 50)
    print("泛化能力评估结果")
    print("=" * 50)
    print(f"基础准确率: {metrics.base_accuracy:.1%}")
    print(f"简单题准确率: {metrics.easy_accuracy:.1%}")
    print(f"中等题准确率: {metrics.medium_accuracy:.1%}")
    print(f"困难题准确率: {metrics.hard_accuracy:.1%}")
    print(f"数值鲁棒性: {metrics.numerical_robustness:.1%}")
    print(f"结构鲁棒性: {metrics.structural_robustness:.1%}")
    print(f"综合泛化得分: {metrics.generalization_score:.1%}")

    # 检测过拟合
    warnings = evaluator.detect_overfitting(metrics, train_accuracy=0.95)

    print("\n过拟合警告:")
    for w in warnings:
        print(f"  [{w.level.upper()}] {w.message}")
        for s in w.suggestions:
            print(f"    - {s}")

    # 数据增强
    print("\n" + "=" * 50)
    print("数据增强示例")
    print("=" * 50)

    augmentor = DataAugmentor()
    sample_data = [
        {"question": "What is 10 + 5?", "answer": "15"},
    ]

    augmented = augmentor.augment(sample_data, num_augmentations=3)

    for item in augmented:
        print(f"Q: {item['question']}")
        print(f"A: {item['answer']}")
        if item.get("augmented"):
            print(f"(增强策略: {item['strategy']})")
        print()
