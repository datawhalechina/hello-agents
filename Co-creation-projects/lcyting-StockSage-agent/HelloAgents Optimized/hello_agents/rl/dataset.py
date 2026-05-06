"""RL训练数据集"""

from typing import Dict, Any, Optional
from datasets import load_dataset, Dataset
from transformers import AutoTokenizer


class GSM8KDataset:
    """GSM8K数学推理数据集

    GSM8K (Grade School Math 8K) 是一个包含8500个高质量小学数学问题的数据集。
    每个问题都需要2-8步的推理过程来解决。
    """

    def __init__(
        self,
        split: str = "train",
        max_samples: Optional[int] = None,
        format_type: str = "sft",  # "sft" or "rl"
        tokenizer=None,  # 用于RL格式应用chat template
    ):
        """
        初始化GSM8K数据集

        Args:
            split: 数据集分割 ("train" 或 "test")
            max_samples: 最大样本数（用于快速测试）
            format_type: 数据格式类型 ("sft" 用于监督学习, "rl" 用于强化学习)
            tokenizer: Tokenizer对象,用于RL格式应用chat template
        """
        self.split = split
        self.max_samples = max_samples
        self.format_type = format_type
        self.tokenizer = tokenizer

        print(f"📥 加载 GSM8K 数据集 (split={split})...")
        self.dataset = load_dataset("openai/gsm8k", "main", split=split)

        if max_samples:
            self.dataset = self.dataset.select(
                range(min(max_samples, len(self.dataset)))
            )
            print(f"   使用 {len(self.dataset)} 个样本（限制：{max_samples}）")
        else:
            print(f"   加载了 {len(self.dataset)} 个样本")

    def format_for_sft(self, example: Dict[str, Any]) -> Dict[str, str]:
        """
        格式化为SFT训练格式

        Args:
            example: 原始数据样本

        Returns:
            格式化后的样本，包含 "prompt" 和 "completion"
        """
        question = example["question"]
        answer = example["answer"]

        # 提取最终答案（GSM8K的答案格式为：推理过程\n#### 最终答案）
        if "####" in answer:
            reasoning, final_answer = answer.split("####")
            reasoning = reasoning.strip()
            final_answer = final_answer.strip()
        else:
            reasoning = answer
            final_answer = ""

        # 构造prompt和completion
        prompt = f"Question: {question}\n\nLet's solve this step by step:\n"
        completion = f"{reasoning}\n\nFinal Answer: {final_answer}"

        return {
            "prompt": prompt,
            "completion": completion,
            "text": prompt + completion,  # 用于某些trainer
        }

    def format_for_rl(self, example: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化为RL训练格式(Standard Format with Chat Template Applied)

        Args:
            example: 原始数据样本

        Returns:
            格式化后的样本，使用standard format (已应用chat template)
            - prompt: 应用chat template后的文本字符串
            - ground_truth: 正确答案
            - question: 原始问题
            - full_answer: 完整答案
        """
        question = example["question"]
        answer = example["answer"]

        # 提取最终答案
        if "####" in answer:
            _, final_answer = answer.split("####")
            final_answer = final_answer.strip()
        else:
            final_answer = answer.strip()

        # 构造prompt内容
        prompt_content = f"Question: {question}\n\nLet's solve this step by step:"

        # 如果提供了tokenizer,应用chat template
        if self.tokenizer:
            messages = [{"role": "user", "content": prompt_content}]
            prompt_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            # 如果没有tokenizer,直接使用原始文本
            prompt_text = prompt_content

        return {
            "prompt": prompt_text,  # Standard format (string)
            "ground_truth": final_answer,
            "question": question,
            "full_answer": answer,
        }

    def get_dataset(self) -> Dataset:
        """
        获取格式化后的数据集

        Returns:
            HuggingFace Dataset对象
        """
        if self.format_type == "sft":
            formatted_dataset = self.dataset.map(
                self.format_for_sft, remove_columns=self.dataset.column_names
            )
        elif self.format_type == "rl":
            formatted_dataset = self.dataset.map(
                self.format_for_rl, remove_columns=self.dataset.column_names
            )
        else:
            raise ValueError(f"不支持的格式类型: {self.format_type}")

        return formatted_dataset

    def __len__(self) -> int:
        """返回数据集大小"""
        return len(self.dataset)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """获取单个样本"""
        example = self.dataset[idx]
        if self.format_type == "sft":
            return self.format_for_sft(example)
        else:
            return self.format_for_rl(example)


def create_math_dataset(
    dataset_name: str = "gsm8k",
    split: str = "train",
    max_samples: Optional[int] = None,
    format_type: str = "sft",
    tokenizer=None,
) -> Dataset:
    """
    创建数学推理数据集

    Args:
        dataset_name: 数据集名称（目前仅支持 "gsm8k"）
        split: 数据集分割
        max_samples: 最大样本数
        format_type: 数据格式类型
        tokenizer: Tokenizer对象,用于RL格式应用chat template

    Returns:
        格式化后的数据集
    """
    if dataset_name.lower() == "gsm8k":
        dataset_wrapper = GSM8KDataset(
            split=split,
            max_samples=max_samples,
            format_type=format_type,
            tokenizer=tokenizer,
        )
        return dataset_wrapper.get_dataset()
    else:
        raise ValueError(f"不支持的数据集: {dataset_name}")


def format_math_dataset(
    dataset: Dataset, format_type: str = "sft", model_name: str = "Qwen/Qwen3-0.6B"
) -> Dataset:
    """
    将自定义数据集转换为训练格式

    Args:
        dataset: 原始数据集,必须包含 'question' 和 'answer' 字段
        format_type: 格式类型 ("sft" 或 "rl")
        model_name: 模型名称,用于加载tokenizer

    Returns:
        格式化后的数据集
    """
    from transformers import AutoTokenizer

    # 加载tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    # 定义格式化函数
    def format_sft_sample(example: Dict[str, Any]) -> Dict[str, str]:
        """格式化为SFT格式"""
        question = example["question"]
        answer = example["answer"]

        # 提取最终答案
        if "####" in answer:
            reasoning, final_answer = answer.split("####")
            reasoning = reasoning.strip()
            final_answer = final_answer.strip()
        else:
            reasoning = answer
            final_answer = ""

        # 构造prompt和completion
        prompt = f"Question: {question}\n\nLet's solve this step by step:\n"
        completion = f"{reasoning}\n\nFinal Answer: {final_answer}"

        return {"prompt": prompt, "completion": completion, "text": prompt + completion}

    def format_rl_sample(example: Dict[str, Any]) -> Dict[str, Any]:
        """格式化为RL格式"""
        question = example["question"]
        answer = example["answer"]

        # 提取最终答案
        if "####" in answer:
            _, final_answer = answer.split("####")
            final_answer = final_answer.strip()
        else:
            final_answer = answer.strip()

        # 构造prompt内容
        prompt_content = f"Question: {question}\n\nLet's solve this step by step:"

        # 应用chat template
        messages = [{"role": "user", "content": prompt_content}]
        prompt_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        return {
            "prompt": prompt_text,
            "ground_truth": final_answer,
            "question": question,
            "full_answer": answer,
        }

    # 格式化数据集
    if format_type == "sft":
        formatted_dataset = dataset.map(
            format_sft_sample, remove_columns=dataset.column_names
        )
    elif format_type == "rl":
        formatted_dataset = dataset.map(
            format_rl_sample, remove_columns=dataset.column_names
        )
    else:
        raise ValueError(f"不支持的格式类型: {format_type}")

    return formatted_dataset


def create_sft_dataset(
    max_samples: Optional[int] = 1000, split: str = "train"
) -> Dataset:
    """
    创建SFT训练数据集（便捷函数）

    Args:
        max_samples: 最大样本数
        split: 数据集分割

    Returns:
        SFT格式的数据集
    """
    return create_math_dataset(
        dataset_name="gsm8k", split=split, max_samples=max_samples, format_type="sft"
    )


def create_rl_dataset(
    max_samples: Optional[int] = 500,
    split: str = "train",
    model_name: str = "Qwen/Qwen3-0.6B",
) -> Dataset:
    """
    创建RL训练数据集（便捷函数）

    Args:
        max_samples: 最大样本数
        split: 数据集分割
        model_name: 模型名称,用于应用chat template

    Returns:
        RL格式的数据集（已应用chat template）
    """
    # 加载tokenizer
    print(f"📝 加载tokenizer (model={model_name})...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    return create_math_dataset(
        dataset_name="gsm8k",
        split=split,
        max_samples=max_samples,
        format_type="rl",
        tokenizer=tokenizer,
    )


def preview_dataset(dataset: Dataset, num_samples: int = 3) -> None:
    """
    预览数据集样本

    Args:
        dataset: 数据集
        num_samples: 预览样本数
    """
    print(f"\n📋 数据集预览（前 {num_samples} 个样本）:")
    print("=" * 80)

    for i in range(min(num_samples, len(dataset))):
        sample = dataset[i]
        print(f"\n样本 {i + 1}:")
        print("-" * 80)
        for key, value in sample.items():
            # 限制显示长度
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            print(f"{key}: {value_str}")

    print("=" * 80 + "\n")


# 示例用法
if __name__ == "__main__":
    # 创建SFT数据集
    sft_dataset = create_sft_dataset(max_samples=10)
    preview_dataset(sft_dataset, num_samples=2)

    # 创建RL数据集
    rl_dataset = create_rl_dataset(max_samples=10)
    preview_dataset(rl_dataset, num_samples=2)
