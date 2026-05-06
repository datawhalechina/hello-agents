"""
防御奖励机制
用于防止奖励黑客（Reward Hacking）
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AntiGamingConfig:
    """防御配置"""

    # 最小推理长度（字符数）
    min_reasoning_length: int = 30

    # 是否强制要求 Step 标记
    require_step_markers: bool = True

    # 最小 step 数量
    min_steps: int = 1

    # 禁用直接答案输出（无推理过程）
    disallow_direct_answer: bool = True

    # 可疑模式检测阈值
    suspicious_pattern_threshold: float = 0.3

    # 异常模式惩罚分数
    anomaly_penalty: float = 0.5

    # 启用过程奖励
    enable_process_reward: bool = True

    # 过程奖励权重（答对但无推理时扣分）
    no_reasoning_penalty: float = 0.3

    # 重复字符检测
    enable_repetition_check: bool = True
    max_repetition_ratio: float = 0.3


@dataclass
class DefenseResult:
    """防御结果"""

    # 最终奖励（应用防御后）
    final_reward: float

    # 原始奖励（应用防御前）
    raw_reward: float

    # 防御标记
    defense_applied: bool

    # 检测到的问题
    issues: List[str] = field(default_factory=list)

    # 各组件分数
    components: Dict[str, float] = field(default_factory=dict)


def check_suspicious_patterns(text: str) -> tuple[float, List[str]]:
    """
    检测可疑模式，返回(惩罚分数, 问题列表)
    """
    penalty = 0.0
    issues = []

    text_lower = text.lower()

    # 1. 检测直接输出答案（无任何推理）
    # 匹配整个文本只有一个数字的情况
    numbers = re.findall(r"-?\d+\.?\d*", text)
    if len(numbers) == 1:
        # 检查是否只有答案，没有其他内容
        answer_part = numbers[0]
        # 去掉空格和标点后的纯文本长度
        pure_text = re.sub(r"[\d\s\.\-+eE]+", "", text).strip()
        if len(pure_text) < 5 and abs(float(answer_part) - float(numbers[0])) == 0:
            penalty += 0.4
            issues.append("直接输出答案，无推理过程")

    # 2. 检测重复字符（可能是 token 循环）
    if len(text) > 20:
        # 统计连续重复
        repeats = re.findall(r"(.)\1{5,}", text)
        if repeats:
            repeat_ratio = sum(len(r) + 1 for r in repeats) / len(text)
            if repeat_ratio > 0.2:
                penalty += 0.3
                issues.append(f"检测到重复字符模式，重复率 {repeat_ratio:.1%}")

    # 3. 检测过短但声称有推理
    if len(text) < 30 and ("step" in text_lower or "because" in text_lower):
        penalty += 0.2
        issues.append("文本过短但声称有推理")

    # 4. 检测无意义的标记堆砌
    step_markers = re.findall(r"(?i)step\s*\d+", text)
    if len(step_markers) > 10:
        penalty += 0.2
        issues.append("Step 标记数量异常，可能伪造")

    # 5. 检测乱码或无意义字符
    # 检查可读字符比例
    readable = len(re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]", text))
    if len(text) > 0 and readable / len(text) < 0.5:
        penalty += 0.3
        issues.append("可读字符比例过低")

    # 6. 检测模板填充（只是填充关键词，无实质内容）
    template_words = ["therefore", "thus", "hence", "consequently", "根据", "因此"]
    filler_count = sum(1 for w in template_words if w in text_lower)
    if filler_count > 0 and len(text) < 50:
        penalty += 0.1

    return min(penalty, 1.0), issues


def check_reasoning_structure(
    text: str, config: AntiGamingConfig
) -> tuple[float, List[str]]:
    """
    检查推理结构，返回(分数, 问题列表)
    1=完整推理，0=无推理
    """
    score = 1.0
    issues = []

    # 1. 检查是否有 Step 标记
    step_matches = re.findall(r"(?i)step\s*\d+[:：]", text)

    if config.require_step_markers:
        if len(step_matches) < config.min_steps:
            score -= 0.3
            issues.append(f"Step 标记不足 (需要≥{config.min_steps})")

    # 2. 检查推理长度
    if len(text) < config.min_reasoning_length:
        score -= 0.2
        issues.append(f"推理长度不足 (需要≥{config.min_reasoning_length}字符)")

    # 3. 检查是否有中间计算过程
    has_intermediate = re.search(r"\d+\s*[\+\-\*/÷]\s*\d+", text) is not None
    if not has_intermediate:
        score -= 0.1
        issues.append("缺少中间计算过程")

    # 4. 检查等式的使用
    equal_signs = text.count("=")
    if equal_signs < 1:
        score -= 0.1
        issues.append("缺少等式连接")

    return max(0.0, score), issues


def compute_defense_reward(
    completion: str, raw_reward: float, config: AntiGamingConfig
) -> DefenseResult:
    """
    计算防御后的奖励

    Args:
        completion: 模型输出
        raw_reward: 原始奖励（防御前）
        config: 防御配置

    Returns:
        DefenseResult: 包含最终奖励和各组件
    """
    issues = []
    components = {}

    # 1. 可疑模式检测
    anomaly_penalty, anomaly_issues = check_suspicious_patterns(completion)
    if anomaly_penalty > config.suspicious_pattern_threshold:
        issues.extend(anomaly_issues)

    # 2. 推理结构检查
    structure_score, structure_issues = check_reasoning_structure(completion, config)
    if structure_score < 0.8:
        issues.extend(structure_issues)

    # 3. 重复字符检测
    if config.enable_repetition_check:
        repeats = re.findall(r"(.)\1{5,}", completion)
        if repeats:
            repeat_ratio = sum(len(r) + 1 for r in repeats) / max(1, len(completion))
            if repeat_ratio > config.max_repetition_ratio:
                issues.append(f"重复字符过多 ({repeat_ratio:.1%})")
                # 应用惩罚
                structure_score *= 1.0 - repeat_ratio

    # 4. 计算最终奖励
    final_reward = raw_reward

    # 应用可疑模式惩罚
    if anomaly_penalty > 0:
        final_reward *= 1.0 - anomaly_penalty * config.anomaly_penalty

    # 应用推理结构惩罚（答对但无推理）
    has_steps = len(re.findall(r"(?i)step\s*\d+", completion)) > 0
    has_reasoning = len(completion) > config.min_reasoning_length

    if raw_reward > 0.9 and config.enable_process_reward:
        # 答案对了，但检查推理过程
        if not has_steps or not has_reasoning:
            # 应用过程惩罚
            penalty = config.no_reasoning_penalty
            final_reward *= 1.0 - penalty
            issues.append(f"答案正确但缺少推理过程，扣 {penalty:.0%}")
            components["process_penalty_applied"] = True

    # 应用结构分数
    if structure_score < 1.0:
        final_reward *= structure_score

    # 确保奖励在 [0, 1] 范围内
    final_reward = max(0.0, min(1.0, final_reward))

    # 构建结果
    defense_applied = len(issues) > 0

    result = DefenseResult(
        final_reward=final_reward,
        raw_reward=raw_reward,
        defense_applied=defense_applied,
        issues=issues,
        components={
            "anomaly_penalty": anomaly_penalty,
            "structure_score": structure_score,
        },
    )

    return result


# ============================================================
# 整合示例：带防御的 GSM8K 奖励
# ============================================================


def compute_gsm8k_reward_with_defense(
    completion: str, ground_truth: str, config: Optional[AntiGamingConfig] = None
) -> Dict[str, float]:
    """
    带防御的 GSM8K 奖励计算（整合版）
    """
    from .fine_grained_reward import FineGrainedRewardFunction, RewardConfig

    if config is None:
        config = AntiGamingConfig()

    # 1. 原始奖励计算
    gsm8k_config = RewardConfig()
    reward_fn = FineGrainedRewardFunction(gsm8k_config)
    raw_result = reward_fn.compute_reward(completion, ground_truth)
    raw_reward = raw_result["total"]

    # 2. 防御处理
    defense_result = compute_defense_reward(completion, raw_reward, config)

    # 3. 返回结果
    return {
        "total": defense_result.final_reward,
        "raw_total": defense_result.raw_reward,
        "defense_applied": defense_result.defense_applied,
        "issues": defense_result.issues,
        "accuracy": raw_result["accuracy"],
        "reasoning": raw_result["reasoning"],
        "efficiency": raw_result["efficiency"],
    }


# ============================================================
# 测试示例
# ============================================================


def test_defense():
    """测试防御机制"""
    print("=" * 60)
    print("防御机制测试")
    print("=" * 60)

    config = AntiGamingConfig()

    test_cases = [
        # 好案例
        ("Step 1: 48/2 = 24\nStep 2: 48 + 24 = 72\nFinal Answer: 72", "72", "完整推理"),
        # 坏案例：直接输出答案
        ("72", "72", "直接输出答案"),
        # 坏案例：答案正确但无推理
        ("The answer is 72", "72", "答案正确但无推理"),
        # 坏案例：重复字符
        ("aaaaa aaaaa aaaaa 72", "72", "重复字符"),
        # 坏案例：伪造推理
        ("Step 1: Step 2: Step 3: 72", "72", "伪造推理"),
    ]

    for completion, truth, desc in test_cases:
        result = compute_gsm8k_reward_with_defense(completion, truth, config)

        print(f"\n[{desc}]")
        print(f"  输入: {repr(completion[:50])}...")
        print(f"  原始奖励: {result['raw_total']:.3f}")
        print(f"  最终奖励: {result['total']:.3f}")
        print(f"  防御生效: {result['defense_applied']}")
        if result["issues"]:
            print(f"  问题: {result['issues']}")


if __name__ == "__main__":
    test_defense()
