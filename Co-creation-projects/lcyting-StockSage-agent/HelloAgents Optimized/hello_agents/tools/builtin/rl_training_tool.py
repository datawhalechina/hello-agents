"""RL训练工具

提供强化学习训练功能，包括SFT、GRPO、PPO等算法。
"""

from typing import Dict, Any, List, Optional
import json

from ..base import Tool, ToolParameter


class RLTrainingTool(Tool):
    """RL训练工具

    支持的训练算法：
    - SFT: Supervised Fine-Tuning (监督微调)
    - GRPO: Group Relative Policy Optimization (群体相对策略优化)

    支持的功能：
    - 训练模型 (train)
    - 加载数据集 (load_dataset)
    - 创建奖励函数 (create_reward)
    - 评估模型 (evaluate)
    """

    def __init__(self):
        super().__init__(
            name="rl_training",
            description=(
                "强化学习训练工具。支持SFT、GRPO等算法，"
                "用于训练和优化语言模型的推理能力。"
                "也支持数据集加载、奖励函数创建、模型评估等功能。"
                "支持自定义数据集和奖励函数。"
            ),
        )

        # 检查TRL是否可用
        try:
            from hello_agents.rl import TRL_AVAILABLE

            self.trl_available = TRL_AVAILABLE
        except ImportError:
            self.trl_available = False

        # 存储自定义数据集和奖励函数
        self.custom_datasets = {}
        self.custom_reward_functions = {}

    def register_dataset(self, name: str, dataset) -> None:
        """
        注册自定义数据集

        Args:
            name: 数据集名称
            dataset: 数据集对象(HuggingFace Dataset)
        """
        self.custom_datasets[name] = dataset
        print(f"✅ 已注册自定义数据集: {name}")

    def register_reward_function(self, name: str, reward_fn) -> None:
        """
        注册自定义奖励函数

        Args:
            name: 奖励函数名称
            reward_fn: 奖励函数(接受completions和kwargs,返回rewards列表)
        """
        self.custom_reward_functions[name] = reward_fn
        print(f"✅ 已注册自定义奖励函数: {name}")

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行RL相关操作

        Args:
            parameters: 操作参数，包括：
                - action: 操作类型 ("train", "load_dataset", "create_reward", "evaluate")

                训练参数 (action="train"):
                - algorithm: 训练算法 ("sft", "grpo")
                - model_name: 模型名称（默认: "Qwen/Qwen2-0.5B-Instruct"）
                - dataset: 数据集名称（默认: "gsm8k"）
                - max_samples: 最大样本数（用于快速测试）
                - num_epochs: 训练轮数（默认: 3）
                - output_dir: 输出目录（默认: "./output"）
                - use_lora: 是否使用LoRA（默认: True）
                - batch_size: 批次大小（默认: 4）

                数据集加载参数 (action="load_dataset"):
                - format: 数据格式 ("sft", "rl")
                - split: 数据集划分 ("train", "test")
                - max_samples: 最大样本数

                奖励函数参数 (action="create_reward"):
                - reward_type: 奖励类型 ("accuracy", "length_penalty", "step")
                - penalty_weight: 长度惩罚权重（仅length_penalty）
                - step_bonus: 步骤奖励（仅step）

        Returns:
            操作结果的JSON字符串
        """
        # 检查TRL是否可用
        if not self.trl_available:
            return json.dumps(
                {
                    "status": "error",
                    "message": (
                        "TRL未安装。请使用以下命令安装：\n"
                        "pip install hello-agents[rl]\n"
                        "或\n"
                        "pip install trl"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )

        # 获取操作类型
        action = parameters.get("action", "train").lower()

        try:
            if action == "train":
                return self._handle_train(parameters)
            elif action == "load_dataset":
                return self._handle_load_dataset(parameters)
            elif action == "create_reward":
                return self._handle_create_reward(parameters)
            elif action == "evaluate":
                return self._handle_evaluate(parameters)
            else:
                result = {
                    "status": "error",
                    "message": f"不支持的操作: {action}。支持的操作: train, load_dataset, create_reward, evaluate",
                }
                return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            import traceback

            error_result = {
                "status": "error",
                "message": f"操作失败: {str(e)}",
                "traceback": traceback.format_exc(),
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)

    def _handle_train(self, parameters: Dict[str, Any]) -> str:
        """处理训练操作"""
        algorithm = parameters.get("algorithm", "sft").lower()
        model_name = parameters.get("model_name", "Qwen/Qwen2-0.5B-Instruct")
        dataset_name = parameters.get("dataset", "gsm8k")
        max_samples = parameters.get("max_samples", None)
        num_epochs = parameters.get("num_epochs", 3)
        output_dir = parameters.get("output_dir", "./output")
        use_lora = parameters.get("use_lora", True)
        batch_size = parameters.get("batch_size", 4)

        # 支持自定义数据集
        custom_dataset = parameters.get("custom_dataset", None)
        # 支持自定义奖励函数
        custom_reward = parameters.get("custom_reward", None)

        # 支持训练监控配置
        use_wandb = parameters.get("use_wandb", False)
        use_tensorboard = parameters.get("use_tensorboard", True)
        wandb_project = parameters.get("wandb_project", None)

        print(f"\n{'=' * 60}")
        print(f"🚀 开始 {algorithm.upper()} 训练")
        print(f"{'=' * 60}")
        print(f"📦 模型: {model_name}")
        if custom_dataset:
            print("📊 数据集: 自定义数据集")
        else:
            print(f"📊 数据集: {dataset_name}")
        print(f"🔄 训练轮数: {num_epochs}")
        print(f"💾 输出目录: {output_dir}")
        print(f"🎯 算法: {algorithm.upper()}")
        if custom_reward:
            print("🎁 奖励函数: 自定义奖励函数")

        # 打印监控配置
        monitoring = []
        if use_wandb:
            monitoring.append(f"wandb (项目: {wandb_project or 'default'})")
        if use_tensorboard:
            monitoring.append("tensorboard")
        if monitoring:
            print(f"📊 训练监控: {', '.join(monitoring)}")

        print(f"{'=' * 60}\n")

        if algorithm == "sft":
            result = self._train_sft(
                model_name=model_name,
                dataset_name=dataset_name,
                max_samples=max_samples,
                num_epochs=num_epochs,
                output_dir=output_dir,
                use_lora=use_lora,
                batch_size=batch_size,
                custom_dataset=custom_dataset,
                use_wandb=use_wandb,
                use_tensorboard=use_tensorboard,
                wandb_project=wandb_project,
            )
        elif algorithm == "grpo":
            result = self._train_grpo(
                model_name=model_name,
                dataset_name=dataset_name,
                max_samples=max_samples,
                num_epochs=num_epochs,
                output_dir=output_dir,
                use_lora=use_lora,
                batch_size=batch_size,
                custom_dataset=custom_dataset,
                custom_reward=custom_reward,
                use_wandb=use_wandb,
                use_tensorboard=use_tensorboard,
                wandb_project=wandb_project,
            )
        else:
            result = {
                "status": "error",
                "message": f"不支持的算法: {algorithm}。支持的算法: sft, grpo",
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def _handle_load_dataset(self, parameters: Dict[str, Any]) -> str:
        """处理数据集加载操作"""
        from hello_agents.rl import create_sft_dataset, create_rl_dataset

        format_type = parameters.get("format", "sft").lower()
        split = parameters.get("split", "train")
        max_samples = parameters.get("max_samples", 100)
        model_name = parameters.get("model_name", "Qwen/Qwen3-0.6B")

        if format_type == "sft":
            dataset = create_sft_dataset(split=split, max_samples=max_samples)
        elif format_type == "rl":
            dataset = create_rl_dataset(
                split=split, max_samples=max_samples, model_name=model_name
            )
        else:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"不支持的数据格式: {format_type}。支持的格式: sft, rl",
                },
                ensure_ascii=False,
                indent=2,
            )

        result = {
            "status": "success",
            "format": format_type,
            "split": split,
            "dataset_size": len(dataset),
            "sample_keys": list(dataset[0].keys()) if len(dataset) > 0 else [],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _handle_create_reward(self, parameters: Dict[str, Any]) -> str:
        """处理奖励函数创建操作"""
        from hello_agents.rl import (
            create_accuracy_reward,
            create_length_penalty_reward,
            create_step_reward,
        )

        reward_type = parameters.get("reward_type", "accuracy").lower()

        if reward_type == "accuracy":
            _ = create_accuracy_reward()
            result = {
                "status": "success",
                "reward_type": "accuracy",
                "description": "准确性奖励函数: 答案正确=1.0, 错误=0.0",
            }
        elif reward_type == "length_penalty":
            penalty_weight = parameters.get("penalty_weight", 0.001)
            max_length = parameters.get("max_length", 1024)
            # 创建基础奖励函数
            base_reward_fn = create_accuracy_reward()
            _reward_fn = create_length_penalty_reward(
                base_reward_fn=base_reward_fn,
                max_length=max_length,
                penalty_weight=penalty_weight,
            )
            result = {
                "status": "success",
                "reward_type": "length_penalty",
                "penalty_weight": penalty_weight,
                "max_length": max_length,
                "description": f"长度惩罚奖励函数: 基础奖励 - {penalty_weight} * (长度 / {max_length})",
            }
        elif reward_type == "step":
            step_bonus = parameters.get("step_bonus", 0.1)
            # 创建基础奖励函数
            base_reward_fn = create_accuracy_reward()
            create_step_reward(base_reward_fn=base_reward_fn, step_bonus=step_bonus)
            result = {
                "status": "success",
                "reward_type": "step",
                "step_bonus": step_bonus,
                "description": f"步骤奖励函数: 基础奖励 + {step_bonus} * 步骤数",
            }
        else:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"不支持的奖励类型: {reward_type}。支持的类型: accuracy, length_penalty, step",
                },
                ensure_ascii=False,
                indent=2,
            )

        return json.dumps(result, ensure_ascii=False, indent=2)

    def _handle_evaluate(self, parameters: Dict[str, Any]) -> str:
        """处理模型评估操作"""
        try:
            from hello_agents.rl import (
                create_rl_dataset,
                create_accuracy_reward,
            )
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_path = parameters.get("model_path")
            max_samples = parameters.get("max_samples", 100)

            if not model_path:
                return json.dumps(
                    {"status": "error", "message": "缺少必需参数: model_path"},
                    ensure_ascii=False,
                    indent=2,
                )

            # 加载测试数据
            print(f"📥 加载测试数据集 (max_samples={max_samples})...")
            dataset = create_rl_dataset(
                split="test", max_samples=max_samples, model_name=model_path
            )

            # 加载模型和tokenizer
            print(f"📥 加载模型: {model_path}...")
            try:
                model = AutoModelForCausalLM.from_pretrained(model_path)
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model = model.to(device)
                model.eval()
            except Exception as e:
                return json.dumps(
                    {"status": "error", "message": f"模型加载失败: {str(e)}"},
                    ensure_ascii=False,
                    indent=2,
                )

            # 生成预测
            print("🔮 生成预测...")
            completions = []
            ground_truths = []

            # 导入tqdm用于进度条
            try:
                from tqdm import tqdm

                use_tqdm = True
            except ImportError:
                use_tqdm = False
                print("  提示: 安装tqdm可显示进度条 (pip install tqdm)")

            # 创建迭代器
            iterator = range(min(max_samples, len(dataset)))
            if use_tqdm:
                iterator = tqdm(iterator, desc="  评估进度", unit="样本")

            for i in iterator:
                prompt = dataset[i]["prompt"]
                ground_truth = dataset[i]["ground_truth"]

                # 生成回答
                inputs = tokenizer(prompt, return_tensors="pt").to(device)
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=128,  # 减少生成长度加快速度
                        temperature=0.7,
                        do_sample=False,  # 使用贪婪解码加快速度
                        pad_token_id=tokenizer.pad_token_id,
                    )
                # 只取生成的部分,不包括输入
                completion = tokenizer.decode(
                    outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
                )

                completions.append(completion)
                ground_truths.append(ground_truth)

                # 如果没有tqdm,每10个样本打印一次进度
                if not use_tqdm and (i + 1) % 10 == 0:
                    print(f"  进度: {i + 1}/{max_samples}")

            # 计算奖励
            print("📊 计算评估指标...")
            reward_fn = create_accuracy_reward()
            rewards = reward_fn(completions, ground_truth=ground_truths)

            # 计算统计信息
            avg_reward = sum(rewards) / len(rewards)
            accuracy = avg_reward  # 对于准确性奖励,平均奖励就是准确率

            result = {
                "status": "success",
                "model_path": model_path,
                "num_samples": len(completions),
                "accuracy": f"{accuracy:.2%}",
                "average_reward": f"{avg_reward:.4f}",
                "device": device,
            }

            print("\n✅ 评估完成!")
            print(f"  准确率: {accuracy:.2%}")
            print(f"  平均奖励: {avg_reward:.4f}")

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"评估失败: {str(e)}"},
                ensure_ascii=False,
                indent=2,
            )

    def _train_sft(
        self,
        model_name: str,
        dataset_name: str,
        max_samples: Optional[int],
        num_epochs: int,
        output_dir: str,
        use_lora: bool,
        batch_size: int,
        custom_dataset=None,
        use_wandb: bool = False,
        use_tensorboard: bool = True,
        wandb_project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行SFT训练"""
        from hello_agents.rl import (
            SFTTrainerWrapper,
            TrainingConfig,
            create_sft_dataset,
            setup_training_environment,
        )

        # 创建配置
        config = TrainingConfig(
            model_name=model_name,
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            use_lora=use_lora,
            use_wandb=use_wandb,
            use_tensorboard=use_tensorboard,
            wandb_project=wandb_project,
        )

        # 设置环境
        setup_training_environment(config)

        # 加载数据集
        if custom_dataset is not None:
            # 使用自定义数据集
            dataset = custom_dataset
            print(f"✅ 使用自定义数据集: {len(dataset)} 个样本")
        elif dataset_name in self.custom_datasets:
            # 使用注册的自定义数据集
            dataset = self.custom_datasets[dataset_name]
            print(f"✅ 使用注册的数据集 '{dataset_name}': {len(dataset)} 个样本")
        else:
            # 使用默认数据集
            dataset = create_sft_dataset(max_samples=max_samples)

        # 创建训练器
        trainer_wrapper = SFTTrainerWrapper(config=config, dataset=dataset)

        # 开始训练
        trainer_wrapper.train()

        # 保存模型
        trainer_wrapper.save_model()

        return {
            "status": "success",
            "algorithm": "SFT",
            "model": model_name,
            "output_dir": output_dir,
            "num_epochs": num_epochs,
            "dataset_size": len(dataset),
        }

    def _train_grpo(
        self,
        model_name: str,
        dataset_name: str,
        max_samples: Optional[int],
        num_epochs: int,
        output_dir: str,
        use_lora: bool,
        batch_size: int,
        custom_dataset=None,
        custom_reward=None,
        use_wandb: bool = False,
        use_tensorboard: bool = True,
        wandb_project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行GRPO训练"""
        from hello_agents.rl import (
            GRPOTrainerWrapper,
            TrainingConfig,
            create_rl_dataset,
            create_accuracy_reward,
            setup_training_environment,
        )

        # 创建配置
        config = TrainingConfig(
            model_name=model_name,
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            use_lora=use_lora,
            use_wandb=use_wandb,
            use_tensorboard=use_tensorboard,
            wandb_project=wandb_project,
        )

        # 设置环境
        setup_training_environment(config)

        # 加载数据集
        if custom_dataset is not None:
            # 使用自定义数据集
            dataset = custom_dataset
            print(f"✅ 使用自定义数据集: {len(dataset)} 个样本")
        elif dataset_name in self.custom_datasets:
            # 使用注册的自定义数据集
            dataset = self.custom_datasets[dataset_name]
            print(f"✅ 使用注册的数据集 '{dataset_name}': {len(dataset)} 个样本")
        else:
            # 使用默认数据集
            dataset = create_rl_dataset(max_samples=max_samples, model_name=model_name)

        # 创建奖励函数
        if custom_reward is not None:
            # 使用自定义奖励函数
            reward_fn = custom_reward
            print("✅ 使用自定义奖励函数")
        elif dataset_name in self.custom_reward_functions:
            # 使用注册的奖励函数
            reward_fn = self.custom_reward_functions[dataset_name]
            print(f"✅ 使用注册的奖励函数 '{dataset_name}'")
        else:
            # 使用默认奖励函数
            reward_fn = create_accuracy_reward()

        # 创建训练器
        trainer_wrapper = GRPOTrainerWrapper(
            config=config, dataset=dataset, reward_fn=reward_fn
        )

        # 开始训练
        trainer_wrapper.train()

        # 保存模型
        trainer_wrapper.save_model()

        return {
            "status": "success",
            "algorithm": "GRPO",
            "model": model_name,
            "output_dir": output_dir,
            "num_epochs": num_epochs,
            "dataset_size": len(dataset),
        }

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: train (训练), load_dataset (加载数据集), create_reward (创建奖励函数), evaluate (评估模型)",
                required=False,
                default="train",
            ),
            ToolParameter(
                name="algorithm",
                type="string",
                description="训练算法 (仅train): sft (监督微调), grpo (群体相对策略优化)",
                required=False,
                default="sft",
            ),
            ToolParameter(
                name="model_name",
                type="string",
                description="模型名称 (仅train)，例如: Qwen/Qwen2-0.5B-Instruct",
                required=False,
                default="Qwen/Qwen2-0.5B-Instruct",
            ),
            ToolParameter(
                name="dataset",
                type="string",
                description="数据集名称 (仅train)，目前支持: gsm8k",
                required=False,
                default="gsm8k",
            ),
            ToolParameter(
                name="format",
                type="string",
                description="数据格式 (仅load_dataset): sft, rl",
                required=False,
                default="sft",
            ),
            ToolParameter(
                name="split",
                type="string",
                description="数据集划分 (仅load_dataset): train, test",
                required=False,
                default="train",
            ),
            ToolParameter(
                name="reward_type",
                type="string",
                description="奖励类型 (仅create_reward): accuracy, length_penalty, step",
                required=False,
                default="accuracy",
            ),
            ToolParameter(
                name="max_samples",
                type="integer",
                description="最大样本数（用于快速测试），None表示使用全部数据",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="num_epochs",
                type="integer",
                description="训练轮数 (仅train)",
                required=False,
                default=3,
            ),
            ToolParameter(
                name="output_dir",
                type="string",
                description="输出目录 (仅train)",
                required=False,
                default="./output",
            ),
            ToolParameter(
                name="use_lora",
                type="boolean",
                description="是否使用LoRA进行参数高效微调 (仅train)",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="batch_size",
                type="integer",
                description="批次大小 (仅train)",
                required=False,
                default=4,
            ),
        ]


# 便捷函数
def train_with_sft(
    model_name: str = "Qwen/Qwen2-0.5B-Instruct",
    max_samples: Optional[int] = 100,
    num_epochs: int = 3,
    output_dir: str = "./output/sft",
) -> str:
    """
    使用SFT训练模型（便捷函数）

    Args:
        model_name: 模型名称
        max_samples: 最大样本数
        num_epochs: 训练轮数
        output_dir: 输出目录

    Returns:
        训练结果JSON字符串
    """
    tool = RLTrainingTool()
    return tool.run(
        {
            "action": "train",
            "algorithm": "sft",
            "model_name": model_name,
            "max_samples": max_samples,
            "num_epochs": num_epochs,
            "output_dir": output_dir,
        }
    )


def train_with_grpo(
    model_name: str = "Qwen/Qwen2-0.5B-Instruct",
    max_samples: Optional[int] = 100,
    num_epochs: int = 3,
    output_dir: str = "./output/grpo",
) -> str:
    """
    使用GRPO训练模型（便捷函数）

    Args:
        model_name: 模型名称
        max_samples: 最大样本数
        num_epochs: 训练轮数
        output_dir: 输出目录

    Returns:
        训练结果JSON字符串
    """
    tool = RLTrainingTool()
    return tool.run(
        {
            "action": "train",
            "algorithm": "grpo",
            "model_name": model_name,
            "max_samples": max_samples,
            "num_epochs": num_epochs,
            "output_dir": output_dir,
        }
    )


def load_dataset(
    format_type: str = "sft", split: str = "train", max_samples: int = 100
) -> str:
    """
    加载数据集（便捷函数）

    Args:
        format_type: 数据格式 ("sft", "rl")
        split: 数据集划分 ("train", "test")
        max_samples: 最大样本数

    Returns:
        数据集信息JSON字符串
    """
    tool = RLTrainingTool()
    return tool.run(
        {
            "action": "load_dataset",
            "format": format_type,
            "split": split,
            "max_samples": max_samples,
        }
    )


def create_reward_function(reward_type: str = "accuracy", **kwargs) -> str:
    """
    创建奖励函数（便捷函数）

    Args:
        reward_type: 奖励类型 ("accuracy", "length_penalty", "step")
        **kwargs: 其他参数
            - penalty_weight: 长度惩罚权重（仅length_penalty）
            - step_bonus: 步骤奖励（仅step）

    Returns:
        奖励函数信息JSON字符串
    """
    tool = RLTrainingTool()
    params = {"action": "create_reward", "reward_type": reward_type}
    params.update(kwargs)
    return tool.run(params)


def evaluate_model(model_path: str, max_samples: int = 100) -> str:
    """
    评估模型性能（便捷函数）

    Args:
        model_path: 模型路径
        max_samples: 评估样本数

    Returns:
        评估结果JSON字符串
    """
    tool = RLTrainingTool()
    return tool.run(
        {"action": "evaluate", "model_path": model_path, "max_samples": max_samples}
    )
