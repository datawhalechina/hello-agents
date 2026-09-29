# -*- coding: utf-8 -*-
"""共享测试夹具。

设计原则：**默认全部离线**。除 `test_online_smoke.py` 里标记为 slow 的用例之外，
其余测试不调用模型、不访问网络，保证任何环境都能一条命令跑完。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agents import RunResult
from src.retriever import PolicyRetriever

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "data" / "knowledge_base"
EVAL_SAMPLES = ROOT / "data" / "eval" / "eval_samples.yaml"


@pytest.fixture(scope="session")
def knowledge_dir() -> Path:
    return KNOWLEDGE_DIR


@pytest.fixture(scope="session")
def retriever() -> PolicyRetriever:
    """整轮测试共用一个检索器（建索引有开销，且它只读）。"""
    return PolicyRetriever(KNOWLEDGE_DIR)


@pytest.fixture(scope="session")
def eval_samples_path() -> Path:
    return EVAL_SAMPLES


@pytest.fixture
def sample_ticket() -> str:
    """取自评测集 case_001 的真实工单。"""
    return "我买的蓝牙耳机订单 20260709001，到现在三天还没发货，客服也没人回。我现在很着急，能不能赶紧发货？"


def make_run_result(answer: str = "", **kwargs) -> RunResult:
    """构造一个假的执行结果，用于离线测试打分逻辑，不触发任何模型调用。"""
    data = {
        "mode": "A",
        "ticket": "测试工单",
        "answer": answer,
        "llm_calls": 1,
        "tool_calls": 0,
        "elapsed_ms": 100,
    }
    data.update(kwargs)
    return RunResult(**data)
