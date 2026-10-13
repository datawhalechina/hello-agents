# -*- coding: utf-8 -*-
"""在线冒烟测试：真正调用模型，验证三种模式端到端可用。

默认跳过（未配置密钥时），需要真实模型：
    pytest -m slow

为什么保留在线测试：
    离线测试能保证逻辑正确，但保证不了"模型能不能按预期格式输出"。
    例如 ReAct 的动作格式、原生函数调用的返回结构，只有真跑一次才发现问题。
"""

from __future__ import annotations

import os

import pytest
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not os.environ.get("LLM_API_KEY"), reason="未配置 LLM_API_KEY，跳过在线测试"),
]

TICKET = "我买的蓝牙耳机订单 20260709001，到现在三天还没发货，客服也没人回，我很着急。"


@pytest.fixture(scope="module")
def runner(retriever):
    from src.agents import AgentRunner

    return AgentRunner(retriever, quiet=True)


@pytest.mark.parametrize("mode", ["A", "B", "C"])
def test_每种模式都能给出回复(runner, mode: str) -> None:
    result = runner.run(TICKET, mode)
    assert not result.error, f"模式 {mode} 报错：{result.error}"
    assert result.answer.strip(), f"模式 {mode} 返回空回复"
    assert result.llm_calls >= 1, f"模式 {mode} 没有产生模型调用"


def test_模式B会调用检索工具(runner) -> None:
    result = runner.run(TICKET, "B")
    assert result.tool_calls >= 1, "检索增强模式应当调用过工具"


def test_模式C会调用工具且给出依据(runner) -> None:
    result = runner.run(TICKET, "C")
    assert result.tool_calls >= 1, "自治模式应当调用过工具"
    assert "LOG-" in result.answer or "GEN-" in result.answer, "回复中应引用政策规则编号"


def test_模式C不产生越界承诺(runner) -> None:
    from src.tools import check_red_lines

    result = runner.run(TICKET, "C")
    violations = check_red_lines(result.answer)
    assert not violations, f"自治模式仍产生了越界承诺：{violations}"
