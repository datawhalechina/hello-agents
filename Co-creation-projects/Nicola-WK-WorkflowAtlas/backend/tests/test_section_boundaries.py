"""An unnamed peer heading must end a known project's context."""
import pytest

from app.extraction.contextual import extract_messages
from app.schemas import StandardMessage


@pytest.mark.parametrize("text", [
    "本周项目安排\n1.星澜采集项目\n准备采集设备\n2.校园事项\n制作宣传物料\n3.内部资源搭建\n开始接口开发",
    "本周项目安排\nA.星澜采集项目\n1.准备采集设备\nB.其他主题\n1.制作宣传物料\n2.开始接口开发",
])
def test_unnamed_peer_section_does_not_inherit_previous_project(text):
    message = StandardMessage(id="boundaries", source_id="synthetic", text=text, timestamp="2026-01-01T09:00:00+08:00")
    facts = extract_messages([message])
    equipment = next(f for f in facts if "准备采集设备" in f.summary)
    assert equipment.project_hint == "星澜采集项目"
    for fact in facts:
        if "宣传物料" in fact.summary or "接口开发" in fact.summary:
            assert fact.project_hint is None
