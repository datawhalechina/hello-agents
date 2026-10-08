# -*- coding: utf-8 -*-
"""构建本工程专用评测集：从 golden_v1 中裁出主链路样本。

为什么需要裁剪：
    源评测集 36 条中有 6 条是"升级通道"样本，判定的是"该不该从确定性流程升级到
    自治通道"。那批样本依赖"确定性流程与自治通道并存"的编排与 `should_escalate`
    变量；而本工程三种模式都是自治路径，没有"升级"这个动作，
    保留它们只会产生一批无判定结果的记录。

保留的 30 条覆盖五类：正常诉求 12、边界 6、信息缺失 4、知识库未覆盖 4、失败样本固化 4。
这五类正好对应本工程的四个可判定指标：红线违规、依据覆盖、编号编造、追问触发。
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "eval" / "golden_v1.yaml"
TARGET = ROOT / "data" / "eval" / "eval_samples.yaml"

#: 与本工程无对应变量的类别，整类剔除
EXCLUDED_LABEL = "升级通道"

HEADER = """# 评测样本（本工程专用，由 scripts/build_eval_set.py 生成，请勿手工编辑）
#
# 来源：data/eval/golden_v1.yaml（共 36 条）
# 裁剪：保留主链路 30 条 —— 正常诉求 12 + 边界 6 + 信息缺失 4 + 未覆盖 4 + 失败样本 4
#       剔除 6 条「升级通道」样本：那批判定的是"该不该升级到自治通道"，
#       依赖"确定性流程与自治通道并存"的编排与 should_escalate 变量，
#       而本工程三种模式均为自治路径，没有对应变量，保留会产生无判定结果的空记录。
#
# 列定义：
#   input            客户诉求原文（必填）
#   expected_intent  期望的问题类型（供人工复核，不参与自动打分）
#   expected_rules   期望引用的规则编号（必须在知识库中真实存在）
#   must_not_contain 回复中禁止出现的表述 —— 红线违规率的直接判据
#   should_ask       是否应先向客户追问缺失信息 —— 追问触发率的判据
#   tags             分类标签，用于分组统计
#
# 约定：expected_rules 写的是理想答案，不是现状；达不到就如实标红。
"""


def main() -> None:
    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    cases = data.get("cases", [])

    kept = [c for c in cases if EXCLUDED_LABEL not in (c.get("tags") or [])]
    dropped = [c for c in cases if EXCLUDED_LABEL in (c.get("tags") or [])]

    body = yaml.safe_dump(
        {"name": "eval_samples", "version": "1.0.0", "cases": kept},
        allow_unicode=True,
        sort_keys=False,
        width=200,
    )
    TARGET.write_text(HEADER + "\n" + body, encoding="utf-8")

    print(f"源样本：{len(cases)} 条")
    print(f"保留：{len(kept)} 条 -> {TARGET.relative_to(ROOT)}")
    print(f"剔除：{len(dropped)} 条（{'、'.join(c['id'] for c in dropped)}）")

    labeled = [c for c in kept if c.get("expected_rules")]
    asking = [c for c in kept if c.get("should_ask")]
    print(f"其中：有期望规则 {len(labeled)} 条，应触发追问 {len(asking)} 条")


if __name__ == "__main__":
    main()
