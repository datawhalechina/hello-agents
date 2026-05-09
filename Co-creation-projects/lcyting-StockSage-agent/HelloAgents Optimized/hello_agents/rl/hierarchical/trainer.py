"""分层 GRPO 训练器 (Hierarchical GRPO Trainer)

实现两阶段训练流程：
阶段1: 分别预训练高层（SFT）+ 低层（SFT）
阶段2: 联合 GRPO 训练（交替更新两层）

训练协调：
- 高层更新时冻结低层，反之亦然
- 使用协调器在两层之间传递奖励信号
"""

import json
import os
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

from .high_level_policy import HighLevelPolicy
from .low_level_policy import LowLevelPolicy
from .reward import HierarchicalReward, HierarchicalRewardResult
from .coordinator import PolicyCoordinator, ExecutionReport


@dataclass
class HierarchicalTrainingConfig:
    """分层训练配置"""

    # 高层配置
    high_model_name: str = "Qwen/Qwen3-0.6B"
    high_output_dir: str = "./models/high_policy"
    high_learning_rate: float = 5e-5
    high_num_epochs: int = 3
    high_batch_size: int = 4

    # 低层配置
    low_model_name: str = "Qwen/Qwen3-0.6B"
    low_output_dir: str = "./models/low_policy"
    low_learning_rate: float = 5e-5
    low_num_epochs: int = 3
    low_batch_size: int = 4

    # 联合训练配置
    joint_learning_rate: float = 1e-5
    joint_num_epochs: int = 3
    joint_batch_size: int = 4
    joint_output_dir: str = "./models/joint_policy"

    # GRPO参数
    num_generations: int = 4
    kl_coef: float = 0.05
    temperature: float = 0.8
    max_new_tokens: int = 512

    # 训练策略
    freeze_low_during_high: bool = True
    freeze_high_during_low: bool = True
    high_update_frequency: int = 1  # 每N个低层batch更新一次高层

    # 通用
    use_lora: bool = True
    lora_rank: int = 16
    lora_alpha: int = 32
    seed: int = 42


class HierarchicalGRPOTrainer:
    """分层 GRPO 训练器

    训练流程:
    1. 高层 SFT: 学习将任务分解为子目标
    2. 低层 SFT: 学习执行具体工具调用
    3. 联合 GRPO: 交替优化两层策略
    """

    def __init__(
        self,
        config: Optional[HierarchicalTrainingConfig] = None,
        high_policy: Optional[HighLevelPolicy] = None,
        low_policy: Optional[LowLevelPolicy] = None,
        reward: Optional[HierarchicalReward] = None,
        tool_executor: Optional[Callable] = None,
    ):
        self.config = config or HierarchicalTrainingConfig()
        self.reward = reward or HierarchicalReward()
        self.tool_executor = tool_executor

        # 初始化策略
        self.high_policy = high_policy or HighLevelPolicy()
        self.low_policy = low_policy or LowLevelPolicy(
            tool_executor=tool_executor,
        )

        # 初始化协调器
        self.coordinator = PolicyCoordinator(
            high_policy=self.high_policy,
            low_policy=self.low_policy,
            tool_executor=tool_executor,
        )

        # 训练状态
        self.training_log: List[Dict] = []

    def setup_models(self):
        """初始化模型和分词器"""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        # 高层模型
        print(f"📦 Loading high-level policy model: {self.config.high_model_name}")
        self.high_tokenizer = AutoTokenizer.from_pretrained(
            self.config.high_model_name, trust_remote_code=True
        )
        if self.high_tokenizer.pad_token is None:
            self.high_tokenizer.pad_token = self.high_tokenizer.eos_token
        self.high_model = AutoModelForCausalLM.from_pretrained(
            self.config.high_model_name, trust_remote_code=True
        )
        self.high_policy.model = self.high_model
        self.high_policy.tokenizer = self.high_tokenizer

        # 低层模型
        print(f"📦 Loading low-level policy model: {self.config.low_model_name}")
        self.low_tokenizer = AutoTokenizer.from_pretrained(
            self.config.low_model_name, trust_remote_code=True
        )
        if self.low_tokenizer.pad_token is None:
            self.low_tokenizer.pad_token = self.low_tokenizer.eos_token
        self.low_model = AutoModelForCausalLM.from_pretrained(
            self.config.low_model_name, trust_remote_code=True
        )
        self.low_policy.model = self.low_model
        self.low_policy.tokenizer = self.low_tokenizer

    def stage1_pretrain_high_with_sft(
        self,
        dataset: List[Dict],
        **kwargs,
    ):
        """阶段1.1: SFT 预训练高层策略

        数据集格式: [{"task": "...", "subgoals": [...]}, ...]
        """
        from trl import SFTConfig, SFTTrainer
        from datasets import Dataset

        print("\n" + "=" * 60)
        print("Stage 1.1: SFT Pretraining High-Level Policy")
        print("=" * 60)

        # 格式化数据
        formatted_data = []
        for item in dataset:
            formatted_data.append(
                {
                    "prompt": self.high_policy.format_prompt(
                        item["task"],
                        item.get("tool_descriptions", ""),
                    ),
                    "completion": self.high_policy.encode_subgoals(item["subgoals"]),
                }
            )

        hf_dataset = Dataset.from_list(formatted_data)

        # SFT 配置
        sft_config = SFTConfig(
            output_dir=self.config.high_output_dir,
            num_train_epochs=self.config.high_num_epochs,
            per_device_train_batch_size=self.config.high_batch_size,
            learning_rate=self.config.high_learning_rate,
            logging_steps=10,
            save_steps=100,
            fp16=True,
        )

        trainer = SFTTrainer(
            model=self.high_model,
            args=sft_config,
            train_dataset=hf_dataset,
            processing_class=self.high_tokenizer,
        )

        print("\n🚀 Training high-level policy...")
        trainer.train()
        trainer.save_model(self.config.high_output_dir)
        print(f"✅ High-level policy saved to {self.config.high_output_dir}")

    def stage2_pretrain_low_with_sft(
        self,
        dataset: List[Dict],
        **kwargs,
    ):
        """阶段1.2: SFT 预训练低层策略

        数据集格式: [{"subgoal": "...", "tool_calls": [...]}, ...]
        """
        from trl import SFTConfig, SFTTrainer
        from datasets import Dataset

        print("\n" + "=" * 60)
        print("Stage 1.2: SFT Pretraining Low-Level Policy")
        print("=" * 60)

        formatted_data = []
        for item in dataset:
            calls_str = "\n".join(
                tc.to_string() if hasattr(tc, "to_string") else str(tc)
                for tc in item["tool_calls"]
            )
            full_output = f"{calls_str}\nFinish[done]"
            formatted_data.append(
                {
                    "prompt": self.low_policy.format_prompt(
                        item.get("subgoal_obj", item["subgoal"]),
                        item.get("tool_descriptions", ""),
                    ),
                    "completion": full_output,
                }
            )

        hf_dataset = Dataset.from_list(formatted_data)

        sft_config = SFTConfig(
            output_dir=self.config.low_output_dir,
            num_train_epochs=self.config.low_num_epochs,
            per_device_train_batch_size=self.config.low_batch_size,
            learning_rate=self.config.low_learning_rate,
            logging_steps=10,
            save_steps=100,
            fp16=True,
        )

        trainer = SFTTrainer(
            model=self.low_model,
            args=sft_config,
            train_dataset=hf_dataset,
            processing_class=self.low_tokenizer,
        )

        print("\n🚀 Training low-level policy...")
        trainer.train()
        trainer.save_model(self.config.low_output_dir)
        print(f"✅ Low-level policy saved to {self.config.low_output_dir}")

    def stage3_joint_grpo(
        self,
        tasks: List[str],
        tool_descriptions: str = "",
        **kwargs,
    ):
        """阶段2: 联合 GRPO 训练（交替优化两层）

        训练循环:
        1. 对每个任务：
           a. 高层生成子目标
           b. 低层执行每个子目标
           c. 计算高层和低层奖励
           d. 交替更新两层策略
        """
        print("\n" + "=" * 60)
        print("Stage 2: Joint GRPO Training")
        print("=" * 60)

        # 准备 LoRA
        if self.config.use_lora:
            self._apply_lora()

        # 训练循环
        for epoch in range(self.config.joint_num_epochs):
            print(f"\n--- Joint Epoch {epoch + 1}/{self.config.joint_num_epochs} ---")
            epoch_rewards = []

            for task_idx, task in enumerate(tasks):
                # 1. 执行任务（规划 + 执行）
                report = self.coordinator.execute_task(
                    task, tool_descriptions, **kwargs
                )

                # 2. 计算两层奖励
                high_rewards = self.coordinator.compute_high_reward_from_report(report)
                low_rewards = self.coordinator.compute_low_reward_from_report(report)
                reward_result = self.reward.compute_total_reward(
                    high_rewards, low_rewards
                )

                epoch_rewards.append(reward_result.total)

                # 3. 更新高层策略
                if task_idx % self.config.high_update_frequency == 0:
                    if self.config.freeze_low_during_high:
                        self._freeze_model(self.low_model)
                    self._update_high_policy(report, reward_result)
                    if self.config.freeze_low_during_high:
                        self._unfreeze_model(self.low_model)

                # 4. 更新低层策略
                if self.config.freeze_high_during_low:
                    self._freeze_model(self.high_model)
                self._update_low_policy(report, reward_result)
                if self.config.freeze_high_during_low:
                    self._unfreeze_model(self.high_model)

                # 记录日志
                if task_idx % 5 == 0:
                    print(
                        f"  Task {task_idx}/{len(tasks)} | "
                        f"Reward: {reward_result.total:.3f} | "
                        f"High: {reward_result.high_level.get('completeness', 0):.2f} | "
                        f"Low tool: {reward_result.low_level.get('tool_correctness', 0):.2f}"
                    )

            # Epoch 汇总
            avg_epoch_reward = sum(epoch_rewards) / max(len(epoch_rewards), 1)
            success_rate = sum(1 for r in epoch_rewards if r > 1.0) / max(
                len(epoch_rewards), 1
            )
            print(f"\nEpoch {epoch + 1} Summary:")
            print(f"  Avg Reward: {avg_epoch_reward:.3f}")
            print(f"  Success Rate: {success_rate:.2%}")

            self.training_log.append(
                {
                    "epoch": epoch + 1,
                    "avg_reward": avg_epoch_reward,
                    "success_rate": success_rate,
                }
            )

        # 保存联合模型
        self._save_joint_model()
        print(f"\n✅ Joint model saved to {self.config.joint_output_dir}")

    def _update_high_policy(
        self,
        report: ExecutionReport,
        reward: HierarchicalRewardResult,
    ):
        """更新高层策略（简化版：使用 GRPO 风格更新）"""
        from transformers import AdamW

        optimizer = AdamW(
            [p for p in self.high_model.parameters() if p.requires_grad],
            lr=self.config.joint_learning_rate,
        )

        # 构造训练样本
        prompt = self.high_policy.format_prompt(report.task, "")
        subgoals = [
            f"{sg.index}: {sg.description} [{sg.status.value}]"
            for sg in report.subgoals
        ]
        completion = "\n".join(subgoals)

        # 计算优势
        high_score = sum(reward.high_level.values()) / max(len(reward.high_level), 1)

        # 前向 + 反向（简化版）
        inputs = self.high_tokenizer(prompt + completion, return_tensors="pt")
        labels = self.high_tokenizer(completion, return_tensors="pt").input_ids

        outputs = self.high_model(**inputs, labels=labels)
        loss = outputs.loss * (1.0 - high_score * 0.5)  # 奖励加权的损失

        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

    def _update_low_policy(
        self,
        report: ExecutionReport,
        reward: HierarchicalRewardResult,
    ):
        """更新低层策略（简化版）"""
        from transformers import AdamW

        optimizer = AdamW(
            [p for p in self.low_model.parameters() if p.requires_grad],
            lr=self.config.joint_learning_rate,
        )

        low_score = sum(reward.low_level.values()) / max(len(reward.low_level), 1)

        for sg in report.subgoals:
            if not sg.trajectory:
                continue

            trajectory_text = "\n".join(str(step) for step in sg.trajectory)
            prompt = self.low_policy.format_prompt(sg.description, "", "")

            inputs = self.low_tokenizer(prompt + trajectory_text, return_tensors="pt")
            labels = self.low_tokenizer(trajectory_text, return_tensors="pt").input_ids

            outputs = self.low_model(**inputs, labels=labels)
            loss = outputs.loss * (1.0 - low_score * 0.5)

            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

    def _apply_lora(self):
        """对两层模型应用 LoRA"""
        from peft import LoraConfig, get_peft_model

        lora_config = LoraConfig(
            r=self.config.lora_rank,
            lora_alpha=self.config.lora_alpha,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )

        self.high_model = get_peft_model(self.high_model, lora_config)
        self.low_model = get_peft_model(self.low_model, lora_config)
        self.high_policy.model = self.high_model
        self.low_policy.model = self.low_model

        print(f"✅ LoRA applied (rank={self.config.lora_rank})")

    def _freeze_model(self, model):
        """冻结模型参数"""
        for param in model.parameters():
            param.requires_grad = False

    def _unfreeze_model(self, model):
        """解冻模型参数"""
        for param in model.parameters():
            param.requires_grad = True

    def _save_joint_model(self):
        """保存联合训练后的模型"""
        os.makedirs(self.config.joint_output_dir, exist_ok=True)

        # 保存高层
        self.high_model.save_pretrained(
            os.path.join(self.config.joint_output_dir, "high_policy")
        )
        self.high_tokenizer.save_pretrained(
            os.path.join(self.config.joint_output_dir, "high_policy")
        )

        # 保存低层
        self.low_model.save_pretrained(
            os.path.join(self.config.joint_output_dir, "low_policy")
        )
        self.low_tokenizer.save_pretrained(
            os.path.join(self.config.joint_output_dir, "low_policy")
        )

        # 保存训练日志
        with open(
            os.path.join(self.config.joint_output_dir, "training_log.json"), "w"
        ) as f:
            json.dump(self.training_log, f, indent=2)
