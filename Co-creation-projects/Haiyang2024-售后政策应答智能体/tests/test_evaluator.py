# -*- coding: utf-8 -*-
"""评测层测试：打分判定、汇总指标、报告生成与样本数据一致性。

全部离线：用假的执行结果（RunResult）驱动打分逻辑，不调用模型。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_run_result

from src.evaluator import (
    CaseResult,
    _mean,
    _pct,
    judge,
    load_samples,
    render_report,
    resolve_out_dir,
    summarize,
)

KNOWN_RULES = {"LOG-001", "LOG-002", "PAY-001", "PAY-002", "RET-001", "LIM-001"}


class Test打分:
    def test_命中禁止表述(self) -> None:
        case = {"id": "c1", "must_not_contain": ["一定到账", "明天到"]}
        result = judge(case, "A", make_run_result("您的退款明天到"), KNOWN_RULES)
        assert result.violated is True
        assert result.violations == ["明天到"]

    def test_未命中禁止表述(self) -> None:
        case = {"id": "c1", "must_not_contain": ["一定到账"]}
        result = judge(case, "A", make_run_result("退款一般 1-3 个工作日到账"), KNOWN_RULES)
        assert result.violated is False
        assert result.violations == []

    def test_缺失禁止字段不报错(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("任意回复"), KNOWN_RULES)
        assert result.violated is False

    def test_编造编号被识别(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("依据 XYZ-999 的规定"), KNOWN_RULES)
        assert result.fabricated_rules == ["XYZ-999"]
        assert result.cited_rules == ["XYZ-999"]

    def test_真实编号不算编造(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("依据 LOG-001 与 PAY-002"), KNOWN_RULES)
        assert result.fabricated_rules == []
        assert result.cited_rules == ["LOG-001", "PAY-002"]

    def test_混编造与真实都能分开(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("LOG-001 与 ABC-123"), KNOWN_RULES)
        assert result.cited_rules == ["ABC-123", "LOG-001"]
        assert result.fabricated_rules == ["ABC-123"]

    # 期望规则有两条，因此引用一条为 0.5、两条齐全为 1.0
    @pytest.mark.parametrize(
        ("answer", "expected"),
        [
            ("依据 LOG-001 和 PAY-001", 1.0),
            ("依据 LOG-001 处理", 0.5),
            ("我们会尽快处理", 0.0),
        ],
    )
    def test_依据覆盖率(self, answer: str, expected: float) -> None:
        case = {"id": "c1", "expected_rules": ["LOG-001", "PAY-001"]}
        result = judge(case, "A", make_run_result(answer), KNOWN_RULES)
        assert result.coverage == expected

    def test_无期望规则时覆盖率为空(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("任意回复"), KNOWN_RULES)
        assert result.coverage is None

    def test_应追问且确实追问(self) -> None:
        case = {"id": "c1", "should_ask": True}
        result = judge(case, "A", make_run_result("麻烦您提供一下订单号"), KNOWN_RULES)
        assert result.asked is True

    def test_应追问但没追问(self) -> None:
        case = {"id": "c1", "should_ask": True}
        result = judge(case, "A", make_run_result("已为您处理完毕"), KNOWN_RULES)
        assert result.asked is False

    def test_未标注追问则不参与判定(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("如需协助可随时联系我们"), KNOWN_RULES)
        assert result.asked is None

    def test_普通服务用语不算追问(self) -> None:
        case = {"id": "c1", "should_ask": True}
        result = judge(case, "A", make_run_result("感谢理解，如需协助可随时联系我们"), KNOWN_RULES)
        assert result.asked is False

    def test_达到步数上限视为未完成(self) -> None:
        answer = "抱歉，我无法在限定步数内完成这个任务。"
        result = judge({"id": "c1"}, "C", make_run_result(answer), KNOWN_RULES)
        assert result.completed is False

    def test_空回答视为未完成(self) -> None:
        result = judge({"id": "c1"}, "C", make_run_result(""), KNOWN_RULES)
        assert result.completed is False

    def test_正常回答视为完成(self) -> None:
        result = judge({"id": "c1"}, "A", make_run_result("已为您处理"), KNOWN_RULES)
        assert result.completed is True

    def test_规则化复核独立于数据集断言(self) -> None:
        """数据集没列出的红线，规则化复核也应能抓到。"""
        case = {"id": "c1", "must_not_contain": []}
        result = judge(case, "A", make_run_result("保证明天到账"), KNOWN_RULES)
        assert result.violated is False
        assert result.redline_hits, "规则化复核应命中时效类红线"

    def test_评测集里的期望编号都真实存在(self, eval_samples_path, retriever) -> None:
        """数据一致性：样本期望引用的规则编号必须在知识库里真实存在。"""
        known = retriever.rule_ids
        for case in load_samples(eval_samples_path):
            for rule in case.get("expected_rules") or []:
                assert rule in known, f"{case['id']} 引用了不存在的规则 {rule}"


class Test均值与格式化:
    def test_空列表返回None(self) -> None:
        assert _mean([]) is None

    def test_正常求均值(self) -> None:
        assert _mean([1.0, 0.0]) == 0.5

    def test_格式化空值为破折号(self) -> None:
        assert _pct(None) == "—"

    def test_格式化百分比(self) -> None:
        assert _pct(0.125) == "12.5%"


class Test输出目录保护:
    def test_全量模式不变(self, tmp_path: Path) -> None:
        assert resolve_out_dir(tmp_path / "outputs", limited=False) == tmp_path / "outputs"

    def test_试跑隔离到子目录(self, tmp_path: Path) -> None:
        assert resolve_out_dir(tmp_path / "outputs", limited=True) == tmp_path / "outputs" / "limit-demo"


class Test汇总:
    def _result(self, **kwargs) -> CaseResult:
        data = {
            "case_id": "c1",
            "mode": "A",
            "tags": [],
            "answer_chars": 100,
            "llm_calls": 1,
            "tool_calls": 0,
            "elapsed_ms": 1000,
        }
        data.update(kwargs)
        return CaseResult(**data)

    def test_空结果集不崩溃(self) -> None:
        summary = summarize("A", [])
        assert summary["样本数"] == 0
        assert summary["红线违规率"] is None
        assert summary["依据覆盖率"] is None
        assert summary["追问触发率"] is None

    def test_指标计算正确(self) -> None:
        results = [
            self._result(violated=True, coverage=1.0, asked=True, completed=True),
            self._result(violated=False, coverage=0.0, asked=False, completed=False),
        ]
        summary = summarize("A", results)
        assert summary["样本数"] == 2
        assert summary["红线违规率"] == 0.5
        assert summary["依据覆盖率"] == 0.5
        assert summary["追问触发率"] == 0.5
        assert summary["未完成率"] == 0.5

    def test_无追问样本时指标为空而非零(self) -> None:
        summary = summarize("A", [self._result(asked=None)])
        assert summary["追问触发率"] is None, "没有样本时应显示为空，不能显示成 0%"
        assert summary["应追问样本数"] == 0

    def test_异常数统计(self) -> None:
        summary = summarize("A", [self._result(error="boom"), self._result()])
        assert summary["异常数"] == 1


class Test报告:
    def _summary(self) -> dict:
        return summarize(
            "A",
            [
                CaseResult(
                    case_id="c1",
                    mode="A",
                    tags=[],
                    answer_chars=10,
                    llm_calls=1,
                    tool_calls=0,
                    elapsed_ms=100,
                )
            ],
        )

    def test_无问题时给出正面结论(self) -> None:
        report = render_report([self._summary()], [])
        assert "本轮没有出现红线违规" in report

    def test_有问题时列出明细(self) -> None:
        result = CaseResult(
            case_id="c9",
            mode="B",
            tags=["物流"],
            answer_chars=10,
            llm_calls=2,
            tool_calls=1,
            elapsed_ms=200,
            violated=True,
            violations=["一定到账"],
        )
        report = render_report([self._summary()], [result])
        assert "c9" in report and "一定到账" in report

    def test_空汇总不崩溃(self) -> None:
        report = render_report([], [])
        assert "三种模式的对比报告" in report

    def test_包含判定口径说明(self) -> None:
        assert "判定口径说明" in render_report([self._summary()], [])


class Test样本加载:
    def test_全部样本(self, eval_samples_path: Path) -> None:
        samples = load_samples(eval_samples_path)
        assert len(samples) == 30

    def test_limit生效(self, eval_samples_path: Path) -> None:
        assert len(load_samples(eval_samples_path, 5)) == 5

    def test_limit为None等价于全部(self, eval_samples_path: Path) -> None:
        assert load_samples(eval_samples_path, None) == load_samples(eval_samples_path)

    def test_样本必要字段齐全(self, eval_samples_path: Path) -> None:
        for case in load_samples(eval_samples_path):
            assert case.get("id"), "样本缺少 id"
            assert case.get("input", "").strip(), f"{case['id']} 缺少 input"
            assert isinstance(case.get("must_not_contain", []), list)

    def test_不含升级通道样本(self, eval_samples_path: Path) -> None:
        for case in load_samples(eval_samples_path):
            assert "升级通道" not in (case.get("tags") or []), f"{case['id']} 不该出现在本工程样本中"
