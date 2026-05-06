"""三层评估报告生成器"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def _get_grade(value: float) -> str:
    if value >= 0.9:
        return "优秀"
    if value >= 0.8:
        return "良好"
    if value >= 0.7:
        return "一般"
    return "待改进"


def _bar(value: float, width: int = 30) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _metric_card(name: str, value: float, threshold: float = 0.9) -> str:
    emoji = "✅" if value >= threshold else ("⚠️" if value >= threshold * 0.85 else "❌")
    return f"  {emoji} **{name}**: {value:.1%}"


def report_for_developer(data: Dict[str, Any]) -> str:
    """开发者报告 - 技术深度版"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = ["# 开发者评估报告", "", f"**生成时间**: {now}", ""]

    # 版本信息
    lines.append("## 版本信息")
    lines.append(f"- **Agent 版本**: {data.get('agent_version', 'N/A')}")
    lines.append(f"- **评估层级**: {data.get('level', 'N/A')}")
    lines.append(f"- **总耗时分**: {data.get('duration_min', 'N/A')}")
    lines.append("")

    # 指标总览
    metrics = data.get("metrics", {})
    lines.append("## 指标总览")
    lines.append("| 指标 | 当前值 | 基线(7d) | 变化 | 评级 |")
    lines.append("|------|--------|----------|------|------|")
    baseline = data.get("baseline", {})
    for key, val in sorted(metrics.items()):
        if isinstance(val, (int, float)) and key.endswith("accuracy"):
            base = baseline.get(key) if isinstance(baseline, dict) else None
            base_str = f"{base:.1%}" if base else "N/A"
            diff = f"{val - base:+.1%}" if base else "N/A"
            grade = _get_grade(val)
            lines.append(f"| {key} | {val:.1%} | {base_str} | {diff} | {grade} |")
    lines.append("")

    # 失败样本
    details = data.get("details", {}).get("bfcl_details", [])
    failed = [d for d in details if not d.get("success", True)]
    if failed:
        lines.append(f"## 失败样本 ({len(failed)})")
        for d in failed[:10]:
            lines.append(f"### {d.get('sample_id', 'N/A')}")
            q = d.get("question", "")
            lines.append(f"- **输入**: {str(q)[:80]}")
            lines.append(f"- **预测**: {str(d.get('predicted', ''))[:80]}")
            lines.append(f"- **期望**: {str(d.get('expected', ''))[:80]}")
        if len(failed) > 10:
            lines.append(f"\n*仅显示前10个，共{len(failed)}个失败*")
        lines.append("")

    # 错误类型
    lines.append("## 错误类型分布")
    error_types = data.get("details", {}).get("error_types", {})
    if error_types:
        total = sum(error_types.values())
        for etype, count in sorted(error_types.items(), key=lambda x: -x[1]):
            pct = count / total if total else 0
            lines.append(f"- **{etype}**: {count}次 ({pct:.1%}) {_bar(pct)}")
    lines.append("")

    # 建议
    acc = metrics.get("bfcl_simple_accuracy", 0)
    lines.append("## 修复建议")
    if acc < 0.7:
        lines.append("- ❌ **优先处理**: 整体准确率偏低")
        lines.append("  - 检查工具调用 prompt 格式")
        lines.append("  - 检查 LLM 是否理解函数签名")
    elif acc < 0.9:
        lines.append("- ⚠️ **局部优化**: 针对失败样本调优")
        lines.append("  - 查看失败样本中的共性错误模式")
        lines.append("  - 考虑增加 few-shot 示例")
    else:
        lines.append("- ✅ **表现稳定**: 可直接发布")
    lines.append("")

    return "\n".join(lines)


def report_for_product(data: Dict[str, Any]) -> str:
    """产品经理报告 - 业务视角版"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metrics = data.get("metrics", {})
    baseline = data.get("baseline", {})

    # 计算核心指标
    acc_keys = [
        k
        for k in metrics
        if k.endswith("accuracy") and isinstance(metrics[k], (int, float))
    ]
    avg_acc = sum(metrics[k] for k in acc_keys) / len(acc_keys) if acc_keys else 0
    prev_avg = (
        sum(baseline.get(k, 0) for k in acc_keys) / len(acc_keys) if acc_keys else 0
    )

    lines = ["# 产品评估报告", "", f"**生成时间**: {now}", ""]

    # 一句话结论
    direction = (
        "✅ 建议发布"
        if avg_acc >= 0.85
        else ("⚠️ 建议暂缓" if avg_acc >= 0.7 else "❌ 不建议发布")
    )
    lines.append("## 核心结论")
    lines.append(f"> {direction} (平均准确率 {avg_acc:.1%}，上一版本 {prev_avg:.1%})")
    lines.append("")

    # 核心指标卡片
    lines.append("## 核心指标")
    lines.append(_metric_card("整体准确率", avg_acc, 0.85))
    for k in acc_keys:
        label = k.replace("bfcl_", "").replace("_accuracy", "")
        lines.append(_metric_card(label, metrics[k], 0.85))
    lines.append("")

    # 版本对比
    if baseline:
        lines.append("## 版本对比")
        lines.append("| 指标 | 当前 | 上一版本 | 变化 |")
        lines.append("|------|------|----------|------|")
        for k in acc_keys:
            cur = metrics.get(k, 0)
            prev = baseline.get(k, 0)
            arrow = "↑" if cur > prev else ("↓" if cur < prev else "→")
            lines.append(
                f"| {k.replace('bfcl_', '').replace('_accuracy', '')} | {cur:.1%} | {prev:.1%} | {arrow} {abs(cur - prev):.1%} |"
            )
        lines.append("")

    # 风险评估
    regressions = [
        (k, metrics[k] - baseline[k])
        for k in acc_keys
        if baseline.get(k) and metrics[k] < baseline[k] - 0.05
    ]
    lines.append("## 风险评估")
    if regressions:
        for k, diff in regressions:
            label = k.replace("bfcl_", "").replace("_accuracy", "")
            lines.append(f"- ⚠️ **{label}**: 下降 {abs(diff):.1%} - 已记录 Issue 待优化")
    else:
        lines.append("- ✅ 无显著退化")
    lines.append("")

    # 发布建议
    lines.append("## 发布建议")
    if avg_acc >= 0.85:
        lines.append("✅ **批准** - 整体质量达标，可以发布")
    elif avg_acc >= 0.7:
        lines.append("⏸ **暂缓** - 需修复退化项后再发布")
    else:
        lines.append("❌ **拒绝** - 质量不达标，需重新开发")
    lines.append("")

    return "\n".join(lines)


def report_for_user(data: Dict[str, Any]) -> str:
    """用户报告 - 极简可视化版"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metrics = data.get("metrics", {})
    acc_keys = [
        k
        for k in metrics
        if k.endswith("accuracy") and isinstance(metrics[k], (int, float))
    ]
    avg_acc = sum(metrics[k] for k in acc_keys) / len(acc_keys) if acc_keys else 0

    # 健康状态
    if avg_acc >= 0.9:
        status, emoji = "运行正常", "🟢"
    elif avg_acc >= 0.7:
        status, emoji = "部分波动", "🟡"
    else:
        status, emoji = "需要关注", "🔴"

    lines = ["# 智能体健康报告", "", f"**更新时间**: {now}", ""]

    # 状态卡片
    lines.append(f"## {emoji} 当前状态: {status}")
    lines.append(f"在过去评估周期内，智能体正确率 **{avg_acc:.0%}**。")
    lines.append("")

    # 能力雷达图（ASCII简化版）
    lines.append("## 能力概览")
    labels = {
        "工具调用": "bfcl_simple_accuracy",
        "多函数": "bfcl_multiple_accuracy",
        "并行": "bfcl_parallel_accuracy",
        "无关检测": "bfcl_irrelevance_accuracy",
    }
    for label, key in labels.items():
        val = metrics.get(key, avg_acc)
        lines.append(f"  {label}: {_bar(val)} {val:.0%}")
    lines.append("")

    # 一句话说明
    lines.append("## 说明")
    lines.append(f"在过去7天，智能体正确回答了 **{avg_acc:.0%}** 的问题。")
    if avg_acc >= 0.9:
        lines.append("所有核心功能运行正常，可放心使用。")
    elif avg_acc >= 0.7:
        lines.append("部分复杂场景有波动，持续优化中。")
    else:
        lines.append("团队正在排查问题，预计将在下次更新中修复。")
    lines.append("")

    # 常见问题
    lines.append("## 常见问题正确率")
    samples = data.get("details", {}).get("sample_summary", {})
    if samples:
        for q, correct in list(samples.items())[:5]:
            em = "✅" if correct else "❌"
            lines.append(f"  {em} {q}")
    lines.append("")

    return "\n".join(lines)


class ReportGenerator:
    """报告生成器 - 根据受众自动选择模板"""

    def __init__(self, output_dir: str = "data/eval_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self, data: Dict[str, Any], audience: str = "developer", save: bool = True
    ) -> str:
        generators = {
            "developer": report_for_developer,
            "product": report_for_product,
            "user": report_for_user,
        }
        fn = generators.get(audience, report_for_developer)
        report = fn(data)

        if save:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.output_dir / f"report_{audience}_{now}.md"
            path.write_text(report, encoding="utf-8")
            print(f"[报告] {audience} 报告已保存: {path}")

        return report

    def generate_all(self, data: Dict[str, Any]) -> Dict[str, str]:
        return {
            "developer": self.generate(data, "developer"),
            "product": self.generate(data, "product"),
            "user": self.generate(data, "user"),
        }
