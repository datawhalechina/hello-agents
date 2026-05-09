"""
扩展的 SFT 训练流程

功能：
1. 支持多轮对话数据的训练
2. 数据增强策略（同义改写、难度调整）
3. 训练过程可视化监控（loss曲线、样本质量评估）
"""

from typing import Dict, Any, List
import random
import re

from datasets import Dataset
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# 1. 多轮对话数据支持
# ============================================================================


class MultiTurnConversationDataset:
    """多轮对话数据集

    支持训练包含多轮交互的对话数据，
    如客服对话、谈判、推理过程等。
    """

    def __init__(self, tokenizer=None, max_turns: int = 5, max_length: int = 2048):
        """
        初始化多轮对话数据集

        Args:
            tokenizer: tokenizer对象
            max_turns: 最大轮数
            max_length: 最大序列长度
        """
        self.tokenizer = tokenizer
        self.max_turns = max_turns
        self.max_length = max_length

    def format_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, str]:
        """
        格式化多轮对话

        Args:
            messages: [{"role": "user"/"assistant", "content": "..."}]

        Returns:
            格式化后的 dict: prompt, completion
        """
        if not messages:
            raise ValueError("消息列表不能为空")

        # 构建 prompt（到倒数第二轮 user 消息）
        prompt_messages = messages[:-1] if len(messages) > 1 else messages[:1]

        # 构建 completion（最后一条 assistant 消息）
        completion_message = messages[-1]

        # 应用 chat template
        if self.tokenizer:
            prompt_text = self.tokenizer.apply_chat_template(
                prompt_messages, tokenize=False, add_generation_prompt=True
            )
            completion_text = completion_message["content"]
        else:
            # 手动构建
            prompt_lines = []
            for msg in prompt_messages:
                role = msg["role"]
                content = msg["content"]
                prompt_lines.append(f"{role}: {content}")
            prompt_text = "\n".join(prompt_lines)
            completion_text = completion_message["content"]

        return {
            "prompt": prompt_text,
            "completion": completion_text,
            "messages": messages,  # 保留原始消息
        }

    def create_sample(
        self, question: str, reasoning: str, answer: str, include_steps: bool = True
    ) -> Dict[str, Any]:
        """
        创建单轮训练样本

        Args:
            question: 问题
            reasoning: 推理过程
            answer: 最终答案
            include_steps: 是否包含推理步骤

        Returns:
            格式化后的样本
        """
        if include_steps:
            completion = f"{reasoning}\n\nFinal Answer: {answer}"
        else:
            completion = answer

        messages = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": completion},
        ]

        return self.format_conversation(messages)

    def create_multi_turn_sample(
        self, conversation_history: List[Dict[str, str]], final_answer: str
    ) -> Dict[str, Any]:
        """
        创建多轮对话训练样本

        Args:
            conversation_history: [{"role": "...", "content": "..."}]
            final_answer: 最终答案

        Returns:
            格式化后的多轮对话样本
        """
        # 添加 assistant 的最终回复
        messages = conversation_history + [
            {"role": "assistant", "content": final_answer}
        ]

        return self.format_conversation(messages)


class ConversationFormatter:
    """对话格式化工具

    用于将不同格式的对话数据转换为训练格式。
    """

    SUPPORTED_FORMATS = ["sharegpt", "anthropic", "oai", "custom"]

    @staticmethod
    def from_sharegpt(dataset: Dataset, tokenizer=None) -> Dataset:
        """
        从 ShareGPT 格式转换

        ShareGPT 格式:
        [{"id": "...", "conversations": [{"from": "human", "value": "..."}, ...]}]
        """

        def convert(example):
            convs = example.get("conversations", [])
            messages = []
            for conv in convs:
                role = "user" if conv["from"] == "human" else "assistant"
                messages.append({"role": role, "content": conv["value"]})
            return {"messages": messages}

        converted = dataset.map(convert)
        return converted

    @staticmethod
    def from_anthropic(dataset: Dataset, tokenizer=None) -> Dataset:
        """
        从 Anthropic 格式转换

        Anthropic 格式:
        [{"role": "user", "content": "..."}, ...]
        """
        return dataset

    @staticmethod
    def create_sft_format(
        self,
        messages: List[Dict[str, str]],
        tokenizer=None,
        add_generation_prompt: bool = True,
    ) -> str:
        """创建 SFT 格式的文本"""
        if tokenizer:
            return tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=add_generation_prompt
            )
        else:
            return "\n".join(f"{m['role']}: {m['content']}" for m in messages)


# ============================================================================
# 2. 数据增强策略
# ============================================================================


class DataAugmentation:
    """数据增强工具

    提供多种数据增强策略：
    - 同义改写
    - 难度调整
    - 数据合成
    """

    # 数学问题同义词替换
    MATH_SYNONYMS = {
        "add": ["plus", "added to", "sum of"],
        "subtract": ["minus", "difference between", "subtracted by"],
        "multiply": ["times", "product of", "multiplied by"],
        "divide": ["divided by", "quotient of", "over"],
        "equal": ["is", "equals", "is equal to"],
    }

    # 问题类型改写模板
    QUESTION_REWRITE = [
        "Can you solve this: {}",
        "Please calculate: {}",
        "What is the result of: {}",
        "Help me with: {}",
        "Compute: {}",
    ]

    @staticmethod
    def paraphrase_numbers(example: Dict[str, Any], seed: int = None) -> Dict[str, Any]:
        """
        数字改写增强

        将数字替换为等价的数学表达式。
        例如: 50 -> 100/2, 25*2
        """
        if seed is not None:
            random.seed(seed)

        def replace_number(match):
            num = int(match.group(0))
            # 简单替换策略
            if num > 10 and num % 5 == 0:
                return f"({num // 5} * 5)"
            elif num > 20:
                factors = [i for i in range(2, num // 2 + 1) if num % i == 0]
                if factors:
                    f = random.choice(factors[:3])
                    return f"({num // f} × {f})"
            return str(num)

        question = example.get("question", "")
        answer = example.get("answer", "")

        # 替换数字
        new_question = re.sub(r"\d+", replace_number, question)
        new_answer = re.sub(r"\d+", replace_number, answer)

        return {
            "question": new_question,
            "answer": new_answer,
            "augmentation_type": "paraphrase_numbers",
        }

    @staticmethod
    def rewrite_question(example: Dict[str, Any], seed: int = None) -> Dict[str, Any]:
        """
        问题改写增强

        使用不同的问题措辞。
        """
        if seed is not None:
            random.seed(seed)

        question = example.get("question", "")

        # 随机选择一个改写模板
        template = random.choice(DataAugmentation.QUESTION_REWRITE)

        return {
            "question": template.format(question),
            "answer": example.get("answer", ""),
            "augmentation_type": "rewrite_question",
        }

    @staticmethod
    def add_distractors(
        example: Dict[str, Any], num_distractors: int = 2, seed: int = None
    ) -> Dict[str, Any]:
        """
        添加干扰信息

        在问题中添加无关的信息，增加难度。
        """
        if seed is not None:
            random.seed(seed)

        question = example.get("question", "")

        # 常见的干扰信息模板
        distractors = [
            "Note that this information is not relevant.",
            "Ignore any previous context.",
            "Also note that the time mentioned is incorrect.",
            "Assume all conditions are met.",
        ]

        selected = random.sample(distractors, min(num_distractors, len(distractors)))
        distractor_text = " ".join(selected)

        return {
            "question": f"{question} {distractor_text}",
            "answer": example.get("answer", ""),
            "augmentation_type": "add_distractors",
        }

    @staticmethod
    def simplify_reasoning(example: Dict[str, Any], seed: int = None) -> Dict[str, Any]:
        """
        简化推理过程

        删除中间步骤，只保留最终答案。
        """
        if seed is not None:
            random.seed(seed)

        answer = example.get("answer", "")

        if "####" in answer:
            parts = answer.split("####")
            reasoning = parts[0].strip()
            final_answer = parts[1].strip()

            # 简化推理步骤
            reasoning_lines = reasoning.split("\n")
            if len(reasoning_lines) > 2:
                # 只保留第一条和最后一条推理
                simplified = "\n".join([reasoning_lines[0], reasoning_lines[-1]])
                answer = f"{simplified}\n#### {final_answer}"

        return {
            "question": example.get("question", ""),
            "answer": answer,
            "augmentation_type": "simplify_reasoning",
        }

    @staticmethod
    def augment_dataset(
        dataset: Dataset,
        augmentation_types: List[str] = None,
        augmentation_ratio: float = 0.2,
        seed: int = 42,
    ) -> Dataset:
        """
        对数据集进行增强

        Args:
            dataset: 原始数据集
            augmentation_types: 增强类型列表
            augmentation_ratio: 增强比例（0.2 表示增加 20% 的数据）
            seed: 随机种子

        Returns:
            增强后的数据集
        """
        if augmentation_types is None:
            augmentation_types = ["paraphrase", "rewrite"]

        if "paraphrase" in augmentation_types:
            _ = dataset.map(
                lambda ex: DataAugmentation.paraphrase_numbers(ex, seed),
                batched=False,
                remove_columns=dataset.column_names,
            )
            dataset = dataset.select(range(len(dataset)))  # 重置

    @staticmethod
    def reverse_reasoning(example: Dict[str, Any], seed: int = None) -> Dict[str, Any]:
        """
        逆向推理增强

        将问题逆向化，例如：
        原来: "A 有 50 个苹果，B 给 A 2 个，现在 A 有多少？"
        变成: "A 有 52 个苹果，B 给 A 2 个，原来 A 有多少？"
        """
        if seed is not None:
            random.seed(seed)

        question = example.get("question", "")
        answer = example.get("answer", "")

        # 提取数字
        numbers = re.findall(r"\d+", question)
        if len(numbers) >= 2:
            # 简单逆向：交换两个数字的位置
            nums = [int(n) for n in numbers]
            if len(nums) >= 2 and nums[0] != nums[1]:
                # 改变操作方向
                question = re.sub(r"(\d+)", str(nums[1]), question, count=1)
                question = re.sub(r"(\d+)", str(nums[0]), question, count=1)

        return {
            "question": question,
            "answer": answer,
            "augmentation_type": "reverse_reasoning",
        }


class DifficultyAdjuster:
    """难度调整工具

    根据模型能力调整训练数据的难度。
    """

    @staticmethod
    def estimate_difficulty(example: Dict[str, Any]) -> float:
        """
        估计问题难度

        基于：
        - 数字数量
        - 文本长度
        - 推理步骤数

        Returns:
            难度分数 (0-1)，越高越难
        """
        question = example.get("question", "")
        answer = example.get("answer", "")

        # 数字数量
        num_count = len(re.findall(r"\d+", question))

        # 文本长度
        text_length = len(question.split())

        # 推理步骤（用 "=" 出现次数估算）
        step_count = (
            answer.count("=")
            if "####" not in answer
            else answer.split("####")[0].count("=")
        )

        # 计算难度分数
        difficulty = (
            min(num_count / 5, 1.0) * 0.4
            + min(text_length / 50, 1.0) * 0.3
            + min(step_count / 5, 1.0) * 0.3
        )

        return difficulty

    @staticmethod
    def filter_by_difficulty(
        dataset: Dataset, min_difficulty: float = 0.0, max_difficulty: float = 1.0
    ) -> Dataset:
        """
        按难度筛选数据

        Args:
            dataset: 数据集
            min_difficulty: 最小难度
            max_difficulty: 最大难度

        Returns:
            筛选后的数据集
        """
        difficulties = [DifficultyAdjuster.estimate_difficulty(ex) for ex in dataset]

        indices = [
            i
            for i, d in enumerate(difficulties)
            if min_difficulty <= d <= max_difficulty
        ]

        return dataset.select(indices)

    @staticmethod
    def get_difficulty_distribution(dataset: Dataset) -> Dict[str, Any]:
        """
        获取难度分布

        Returns:
            难度分布统计
        """
        difficulties = np.array(
            [DifficultyAdjuster.estimate_difficulty(ex) for ex in dataset]
        )

        return {
            "mean": float(np.mean(difficulties)),
            "std": float(np.std(difficulties)),
            "min": float(np.min(difficulties)),
            "max": float(np.max(difficulties)),
            "q25": float(np.percentile(difficulties, 25)),
            "q50": float(np.percentile(difficulties, 50)),
            "q75": float(np.percentile(difficulties, 75)),
        }


# ============================================================================
# 3. 训练过程可视化监控
# ============================================================================


class TrainingMonitor:
    """训练过程监控

    监控指标：
    - Loss 曲线
    - 学习率变化
    - 样本质量评估
    - 梯度统计
    """

    def __init__(self):
        self.history = {
            "loss": [],
            "learning_rate": [],
            "grad_norm": [],
            "epoch": [],
            "step": [],
        }
        self.sample_metrics = {
            "accuracy": [],
            "length": [],
            "step_count": [],
        }

    def log(self, metrics: Dict[str, Any]):
        """记录训练指标"""
        for key, value in metrics.items():
            if key in self.history:
                self.history[key].append(value)

    def log_sample(self, sample: Dict[str, Any], prediction: str = None):
        """记录样本质量指标"""
        # 计算长度
        if "completion" in sample:
            length = len(sample["completion"].split())
            self.sample_metrics["length"].append(length)

        # 估计推理步骤数
        if "completion" in sample:
            step_count = sample["completion"].count("Step")
            self.sample_metrics["step_count"].append(step_count)

    def get_loss_curve(self) -> Dict[str, List[float]]:
        """获取 Loss 曲线数据"""
        return {
            "steps": self.history["step"],
            "loss": self.history["loss"],
        }

    def get_learning_rate_curve(self) -> Dict[str, List[float]]:
        """获取学习率曲线"""
        return {
            "steps": self.history["step"],
            "learning_rate": self.history["learning_rate"],
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取训练摘要"""

        # 过滤有效值
        valid_losses = [loss for loss in self.history["loss"] if loss is not None]

        summary = {
            "total_steps": len(self.history["step"]),
            "final_loss": valid_losses[-1] if valid_losses else None,
            "best_loss": min(valid_losses) if valid_losses else None,
            "avg_loss": np.mean(valid_losses) if valid_losses else None,
        }

        # 样本质量
        if self.sample_metrics["length"]:
            summary["avg_length"] = np.mean(self.sample_metrics["length"])
            summary["avg_steps"] = np.mean(self.sample_metrics["step_count"])

        return summary

    def export_for_tensorboard(self) -> Dict[str, Any]:
        """导出 TensorBoard 格式"""
        return {
            "loss": self.history["loss"],
            "learning_rate": self.history["learning_rate"],
            "grad_norm": self.history["grad_norm"],
        }

    def export_for_wandb(self) -> Dict[str, Any]:
        """导出 Weights & Biases 格式"""
        return {
            "train/loss": self.history["loss"],
            "train/learning_rate": self.history["learning_rate"],
            "train/grad_norm": self.history["grad_norm"],
        }


class SampleQualityEvaluator:
    """样本质量评估器

    评估训练样本的质量：
    - 格式正确性
    - 长度合理性
    - 推理清晰度
    """

    def __init__(self):
        self.evaluation_history = []

    def evaluate_sample(self, sample: Dict[str, Any]) -> Dict[str, float]:
        """
        评估单个样本

        Returns:
            质量分数 (0-1)
        """
        scores = {}

        # 1. 格式检查
        has_prompt = "prompt" in sample and sample["prompt"]
        has_completion = "completion" in sample and sample["completion"]
        scores["format"] = 1.0 if (has_prompt and has_completion) else 0.0

        # 2. 长度检查
        length = len(sample.get("completion", "").split())
        if length < 10:
            scores["length"] = 0.3
        elif length > 500:
            scores["length"] = 0.5
        else:
            scores["length"] = 1.0

        # 3. 推理清晰度（检查关键词）
        completion = sample.get("completion", "")
        has_steps = "Step" in completion or "step" in completion
        has_answer = "Final Answer" in completion or "answer" in completion.lower()
        scores["reasoning"] = 1.0 if (has_steps and has_answer) else 0.5

        # 4. 数学符号检查
        has_math = any(c in completion for c in ["+", "-", "*", "/", "="])
        scores["math"] = 1.0 if has_math else 0.0

        # 总分
        scores["total"] = np.mean(list(scores.values()))

        self.evaluation_history.append(scores)

        return scores

    def evaluate_dataset(self, dataset: Dataset) -> Dict[str, Any]:
        """
        评估整个数据集

        Returns:
            统计信息
        """
        all_scores = [self.evaluate_sample(ex) for ex in dataset]

        return {
            "num_samples": len(all_scores),
            "avg_format": np.mean([s["format"] for s in all_scores]),
            "avg_length": np.mean([s["length"] for s in all_scores]),
            "avg_reasoning": np.mean([s["reasoning"] for s in all_scores]),
            "avg_math": np.mean([s["math"] for s in all_scores]),
            "avg_total": np.mean([s["total"] for s in all_scores]),
        }

    def get_quality_report(self) -> str:
        """生成质量报告"""
        if not self.evaluation_history:
            return "无评估数据"

        stats = self.evaluate_dataset.__self__

        report = """
===========================================
训练样本质量评估报告
===========================================

格式正确率: {avg_format:.1%}
长度合理性: {avg_length:.1%}
推理清晰度: {avg_reasoning:.1%}
数学符号使用: {avg_math:.1%}
总体质量: {avg_total:.1%}
===========================================
        """.format(**stats)

        return report


# ============================================================================
# 便捷函数
# ============================================================================


def create_multi_turn_dataset(
    data: List[Dict[str, Any]],
    format_type: str = "sharegpt",
    tokenizer=None,
    max_turns: int = 5,
) -> Dataset:
    """
    创建多轮对话数据集

    Args:
        data: 对话数据列表
        format_type: 数据格式
        tokenizer: tokenizer
        max_turns: 最大轮数

    Returns:
        HuggingFace Dataset
    """
    formatter = ConversationFormatter()

    if format_type == "sharegpt":
        ds = Dataset.from_list(data)
        converted = formatter.from_sharegpt(ds, tokenizer)
        return converted
    else:
        raise ValueError(f"不支持的格式: {format_type}")


def augment_math_dataset(
    dataset: Dataset,
    augmentation_types: List[str] = None,
    samples_per_example: int = 2,
    seed: int = 42,
) -> Dataset:
    """
    增强数学数据集

    Args:
        dataset: 原始数据集
        augmentation_types: 增强类型
        samples_per_example: 每个样本生成的增强样本数
        seed: 随机种子

    Returns:
        增强后的数据集
    """
    if augmentation_types is None:
        augmentation_types = ["paraphrase_numbers", "rewrite_question"]

    augmented_data = []

    for i, example in enumerate(dataset):
        # 保留原始样本
        augmented_data.append(example)

        # 生成增强样本
        for aug_type in augmentation_types[:samples_per_example]:
            seed_offset = i * 100 + seed
            if aug_type == "paraphrase_numbers":
                aug_ex = DataAugmentation.paraphrase_numbers(example, seed_offset)
            elif aug_type == "rewrite_question":
                aug_ex = DataAugmentation.rewrite_question(example, seed_offset)
            else:
                continue
            augmented_data.append(aug_ex)

    return Dataset.from_list(augmented_data)


def create_training_monitor() -> TrainingMonitor:
    """创建训练监控器"""
    return TrainingMonitor()


def create_quality_evaluator() -> SampleQualityEvaluator:
    """创建质量评估器"""
    return SampleQualityEvaluator()


# ============================================================================
# 示例用法
# ============================================================================

if __name__ == "__main__":
    # 示例1: 多轮对话数据
    print("=" * 60)
    print("1. 多轮对话数据示例")
    print("=" * 60)

    # 模拟多轮对话
    conversation = [
        {"role": "user", "content": "问题: 50 + 30 等于多少?"},
        {"role": "assistant", "content": "我们可以用加法: 50 + 30 = 80"},
        {"role": "user", "content": "那 80 减 20 呢?"},
        {"role": "assistant", "content": "80 - 20 = 60"},
        {"role": "user", "content": "最终答案是什么?"},
        {"role": "assistant", "content": "答案是 60"},
    ]

    # 使用 MultiTurnConversationDataset 格式化
    conv_dataset = MultiTurnConversationDataset(tokenizer=None)
    formatted = conv_dataset.format_conversation(conversation[:4])
    print(f"Prompt:\n{formatted['prompt'][:200]}...")
    print(f"\nCompletion:\n{formatted['completion']}")

    # 示例2: 数据增强
    print("\n" + "=" * 60)
    print("2. 数据增强示例")
    print("=" * 60)

    example = {
        "question": "Natalia sold 48 clips in April, then half as many in May. How many in total?",
        "answer": " Natalia sold 48/2 = 24 clips in May. Total = 48 + 24 = 72. #### 72",
    }

    augmented1 = DataAugmentation.paraphrase_numbers(example, seed=42)
    augmented2 = DataAugmentation.rewrite_question(example, seed=42)

    print("原始问题:", example["question"])
    print("数字改写:", augmented1["question"])
    print("问题改写:", augmented2["question"])

    # 示例3: 难度评估
    print("\n" + "=" * 60)
    print("3. 难度评估示例")
    print("=" * 60)

    difficulty = DifficultyAdjuster.estimate_difficulty(example)
    print(f"问题难度: {difficulty:.2f} (0-1)")

    # 示例4: 质量评估
    print("\n" + "=" * 60)
    print("4. 样本质量评估")
    print("=" * 60)

    evaluator = SampleQualityEvaluator()
    scores = evaluator.evaluate_sample(
        {
            "question": "What is 2+2?",
            "completion": "Step 1: Calculate 2+2 = 4\nFinal Answer: 4",
        }
    )
    print(f"质量分数: {scores['total']:.2f}")
    print(f"  - 格式: {scores['format']:.2f}")
    print(f"  - 长度: {scores['length']:.2f}")
    print(f"  - 推理: {scores['reasoning']:.2f}")

    print("\n" + "=" * 60)
    print("✅ 扩展功能测试完成")
    print("=" * 60)
