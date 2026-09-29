# -*- coding: utf-8 -*-
"""智能体编排层测试（离线部分）。

这里只测不需要模型的纯逻辑：答案整理、轨迹兜底、限流重试与模式定义。
真正调用模型的部分放在 `test_online_smoke.py`。
"""

from __future__ import annotations

import pytest

from src.agents import (
    MODES,
    RETRY_ATTEMPTS,
    _Counters,
    _recover_from_trace,
    _tidy_answer,
    _with_retry,
)


class Test模式定义:
    def test_三种模式齐全(self) -> None:
        assert set(MODES) == {"A", "B", "C"}

    def test_每种模式字段完整(self) -> None:
        for mode, info in MODES.items():
            assert set(info) == {"label", "agent", "capability"}, mode
            assert all(value.strip() for value in info.values()), mode

    def test_模式之间描述不同(self) -> None:
        labels = [info["label"] for info in MODES.values()]
        assert len(labels) == len(set(labels))


class Test答案整理:
    def test_单行字段展开为多段(self) -> None:
        raw = "客户回复：正文｜依据规则：LOG-001｜内部建议：催发｜风险提醒：不承诺"
        result = _tidy_answer(raw)
        assert result.count("\n\n") == 3
        assert result.startswith("客户回复：正文")

    def test_普通文本保持不变(self) -> None:
        text = "您好，我们已为您加急催发，请放心。"
        assert _tidy_answer(text) == text

    def test_单个分隔符不展开(self) -> None:
        text = "甲｜乙"
        assert _tidy_answer(text) == text

    def test_空文本(self) -> None:
        assert _tidy_answer("") == ""

    def test_去掉空段(self) -> None:
        result = _tidy_answer("甲｜｜乙｜丙")
        assert "｜" not in result


class Test轨迹兜底:
    def test_提取最后一次草稿(self) -> None:
        trace = (
            "--- 第 1 步 ---\n"
            "🎬 行动: search_policy[发货时效]\n"
            "👀 观察: 命中 1 条\n"
            "--- 第 2 步 ---\n"
            "🎬 行动: check_compliance[第一版草稿]\n"
            "--- 第 3 步 ---\n"
            "🎬 行动: check_compliance[第二版草稿]\n"
        )
        assert _recover_from_trace(trace) == "第二版草稿"

    def test_没有合规动作时返回空(self) -> None:
        assert _recover_from_trace("🎬 行动: search_policy[查询]") == ""

    def test_空轨迹返回空(self) -> None:
        assert _recover_from_trace("") == ""

    def test_草稿自带方括号也能完整取回(self) -> None:
        trace = "🎬 行动: check_compliance[请参考 [LOG-001] 的规定]\n"
        assert _recover_from_trace(trace) == "请参考 [LOG-001] 的规定"


class Test限流重试:
    def test_一次成功不重试(self, monkeypatch) -> None:
        monkeypatch.setattr("src.agents.time.sleep", lambda *_: None)
        calls = []

        def ok():
            calls.append(1)
            return "结果"

        assert _with_retry(ok) == "结果"
        assert len(calls) == 1

    def test_限流后重试成功(self, monkeypatch) -> None:
        monkeypatch.setattr("src.agents.time.sleep", lambda *_: None)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("Error code: 429 - rate limit exceeded")
            return "结果"

        assert _with_retry(flaky) == "结果"
        assert len(calls) == 3

    def test_超过次数仍失败则抛出(self, monkeypatch) -> None:
        monkeypatch.setattr("src.agents.time.sleep", lambda *_: None)
        calls = []

        def always():
            calls.append(1)
            raise RuntimeError("429 too many requests")

        with pytest.raises(RuntimeError):
            _with_retry(always)
        assert len(calls) == RETRY_ATTEMPTS

    def test_非限流异常不重试(self, monkeypatch) -> None:
        monkeypatch.setattr("src.agents.time.sleep", lambda *_: None)
        calls = []

        def bad():
            calls.append(1)
            raise ValueError("参数不合法")

        with pytest.raises(ValueError):
            _with_retry(bad)
        assert len(calls) == 1

    def test_超时类错误也会重试(self, monkeypatch) -> None:
        monkeypatch.setattr("src.agents.time.sleep", lambda *_: None)
        calls = []

        def timeout_once():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("Request timed out")
            return "结果"

        assert _with_retry(timeout_once) == "结果"
        assert len(calls) == 2


class Test计数器:
    def test_重置清空(self) -> None:
        counters = _Counters()
        counters.llm.append(1)
        counters.tool.append(1)
        counters.reset()
        assert counters.llm == [] and counters.tool == []


class Test构建模式:
    def test_未知模式抛出明确异常(self, retriever, monkeypatch) -> None:
        from src.agents import AgentRunner

        runner = AgentRunner(retriever)
        # 替换掉模型创建，避免离线环境因缺少密钥而失败
        monkeypatch.setattr(runner, "_new_llm", lambda: object())
        with pytest.raises(ValueError, match="未知模式"):
            runner._build("X", _Counters())

    def test_三种模式都能构建(self, retriever, monkeypatch) -> None:
        from src.agents import AgentRunner

        runner = AgentRunner(retriever)
        monkeypatch.setattr(runner, "_new_llm", lambda: object())
        for mode in MODES:
            agent = runner._build(mode, _Counters())
            assert agent is not None
