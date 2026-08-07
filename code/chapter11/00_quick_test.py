"""
快速实验测试

使用少量数据快速测试SFT和GRPO训练流程
"""

import sys
from pathlib import Path
import json

# 添加项目路径
project_root = Path(__file__).parent.parent / "HelloAgents"
sys.path.insert(0, str(project_root))

from hello_agents.tools import RLTrainingTool


def quick_test():
    """
    快速实验测试
    
    配置:
    - 模型: Qwen/Qwen3-0.6B
    - 样本数: 10个
    - 训练轮数: 1轮
    - 预计时间: ~2-3分钟
    """
    tool = RLTrainingTool()
    
    print("="*80)
    print("快速实验测试")
    print("="*80)
    
    # ========================================================================
    # 测试1: 数据加载
    # ========================================================================
    print("\n测试1: 数据加载")
    print("-"*80)
    
    data_config = {
        "action": "load_dataset",
        "format_type": "sft",
        "split": "train",
        "max_samples": 5
    }
    
    print("加载数据集...")
    result = tool.run(data_config)
    data = json.loads(result)
    print(f"✅ 数据集加载成功: {data['dataset_size']} 样本")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # ========================================================================
    # 测试2: SFT训练
    # ========================================================================
    print("\n测试2: SFT训练")
    print("-"*80)
    
    sft_config = {
        "action": "train",
        "algorithm": "sft",
        "model_name": "Qwen/Qwen3-0.6B",
        "output_dir": "./output/quick_test/sft",
        "max_samples": 10,
        "num_epochs": 1,
        "batch_size": 2,
        "use_lora": True,
        "lora_r": 8,
        "lora_alpha": 16,
    }
    
    print("SFT配置:")
    print(json.dumps(sft_config, indent=2, ensure_ascii=False))
    
    print("\n⏳ 开始SFT训练...")
    sft_result = tool.run(sft_config)
    sft_data = json.loads(sft_result)
    print("\n✅ SFT训练结果:")
    print(json.dumps(sft_data, indent=2, ensure_ascii=False))
    
    # ========================================================================
    # 测试3: GRPO训练
    # ========================================================================
    print("\n测试3: GRPO训练")
    print("-"*80)

    # 注意：GRPO 对学习率比较敏感，默认 5e-5 在小模型（如 Qwen3-0.6B）上
    # 可能导致策略坍塌（准确率大幅下降），如需更稳定可显式设置 learning_rate=1e-6。
    
    grpo_config = {
        "action": "train",
        "algorithm": "grpo",
        "model_name": "Qwen/Qwen3-0.6B",
        "output_dir": "./output/quick_test/grpo",
        "max_samples": 10,
        "num_epochs": 1,
        "batch_size": 2,
        "use_lora": True,
        "lora_r": 8,
        "lora_alpha": 16,
    }
    
    print("GRPO配置:")
    print(json.dumps(grpo_config, indent=2, ensure_ascii=False))
    
    print("\n⏳ 开始GRPO训练...")
    grpo_result = tool.run(grpo_config)
    grpo_data = json.loads(grpo_result)
    print("\n✅ GRPO训练结果:")
    print(json.dumps(grpo_data, indent=2, ensure_ascii=False))
    
    # ========================================================================
    # 测试4: 奖励函数
    # ========================================================================
    print("\n测试4: 奖励函数")
    print("-"*80)
    
    reward_config = {
        "action": "create_reward",
        "reward_type": "accuracy"
    }
    
    print("创建奖励函数...")
    reward_result = tool.run(reward_config)
    reward_data = json.loads(reward_result)
    print("✅ 奖励函数创建成功:")
    print(json.dumps(reward_data, indent=2, ensure_ascii=False))
    
    # ========================================================================
    # 总结
    # ========================================================================
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    print("\n✅ 所有测试通过!")
    print("\n测试项目:")
    print("  1. ✅ 数据加载")
    print("  2. ✅ SFT训练")
    print("  3. ✅ GRPO训练")
    print("  4. ✅ 奖励函数创建")
    
    print("\n模型路径:")
    print(f"  SFT模型: {sft_config['output_dir']}")
    print(f"  GRPO模型: {grpo_config['output_dir']}")


if __name__ == "__main__":
    quick_test()

