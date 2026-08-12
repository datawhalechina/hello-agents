"""显式启用后才调用真实 LLM 的冒烟测试。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.agents import build_agent_team
from src.config import LLMSettings
from src.tools import REQUIRED_REPORT_HEADINGS, create_tool_registry
from src.workflow import RequirementClarifierWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.live
def test_live_multi_agent_workflow() -> None:
    if os.getenv("RUN_LIVE_TESTS") != "1":
        pytest.skip("设置 RUN_LIVE_TESTS=1 后才运行真实 LLM 冒烟测试")

    load_dotenv(PROJECT_ROOT / ".env")
    settings = LLMSettings.from_env()
    registry = create_tool_registry()
    workflow = RequirementClarifierWorkflow(
        build_agent_team(settings, registry), registry
    )

    result = workflow.run(
        "面向社区居民开发一个活动报名工具，希望一个月内完成首版。"
    )

    assert all(f"## {heading}" in result.report for heading in REQUIRED_REPORT_HEADINGS)
    assert result.quality["missing_headings"] == []
    assert result.quality["score"] >= 90
