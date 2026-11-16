"""Independently invented examples; never copies enterprise export content."""
from datetime import datetime, timedelta, timezone

from app.extraction.contextual import extract_messages
from app.schemas import StandardMessage
from app.workflow.verifier import verify_evidence
from app.workflow.builder import build_workflow


def message(text, id="m1", *, parent=None, source="fiction", chat="room", minute=0, mentions=None):
    raw = {"parent_id": parent, "mentions": mentions or []}
    return StandardMessage(id=id, source_id=source, chat_id=chat, sender="speaker", text=text,
                           timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minute), metadata={"raw": raw})


def test_natural_schedule_preserves_each_section_and_literal_header_evidence():
    source = message("本周安排\nA.青禾采集项目\n1.准备采集设备\n2.确认试采方案\nB.镜湖标注项目\n1.开始标注测试\n2.提交验收报告")
    facts = extract_messages([source])
    assert len(facts) == 4
    assert {f.project_hint for f in facts[:2]} == {"青禾采集项目"}
    assert {f.project_hint for f in facts[2:]} == {"镜湖标注项目"}
    assert all(verify_evidence(f.evidence, [source]) for f in facts)
    assert all(f.attributes["project_attribution"]["method"] == "section" for f in facts)


def test_html_assignments_use_mentions_without_replacing_raw_text():
    mentions = [{"key": "@_user_1", "id": "person-1", "name": "虚构甲"}]
    source = message("<p>本周安排</p><p>1.青禾采集项目</p><p>准备设备 @_user_1</p><p>2.镜湖标注项目</p><p>开始标注测试</p>", mentions=mentions)
    facts = extract_messages([source])
    assert len(facts) == 2 and facts[0].actor == "虚构甲"
    assert facts[1].actor is None
    assert facts[0].attributes["assigned_actor_ids"] == ["person-1"]
    assert source.text.startswith("<p>") and all(verify_evidence(f.evidence, [source]) for f in facts)


def test_reply_inherits_only_a_unique_same_source_same_chat_past_project():
    root = message("青禾采集项目开始准备设备", id="root")
    reply = message("今天开始测试采样设备", id="reply", parent="root", minute=1)
    facts = extract_messages([reply, root])
    child = next(f for f in facts if f.evidence[0].message_id == "reply")
    assert child.project_hint == "青禾采集项目"
    assert child.attributes["project_attribution"]["method"] == "reply"
    assert {e.message_id for e in child.evidence} == {"root", "reply"}
    wrong_room = reply.model_copy(update={"chat_id": "different"})
    wrong_source = reply.model_copy(update={"source_id": "different"})
    future = root.model_copy(update={"timestamp": reply.timestamp + timedelta(minutes=1)})
    for originals in ([root, wrong_room], [root, wrong_source], [future, reply]):
        child = next(f for f in extract_messages(originals) if f.evidence[0].message_id == "reply")
        assert child.project_hint is None


def test_mixed_projects_and_templates_never_force_an_assignment():
    mixed = message("青禾采集项目与镜湖标注项目同时开始测试")
    template = message("项目名称：中文 / 英文\n项目简介：中英文各一段\n代表图片：横版", id="template")
    facts = extract_messages([mixed, template])
    assert facts and all(f.project_hint is None for f in facts)
    assert not any(f.evidence[0].message_id == template.id and f.summary.startswith("项目名称") for f in facts)


def test_reply_cannot_inherit_a_multi_project_parent_or_acknowledgement_fact():
    root = message("A.青禾采集项目\n准备设备\nB.镜湖标注项目\n开始标注测试", id="root")
    reply = message("今天开始测试设备", id="reply", parent="root", minute=1)
    acknowledgement = message("收到，谢谢", id="ack", parent="root", minute=2)
    facts = extract_messages([root, reply, acknowledgement])
    child = next(f for f in facts if f.evidence[0].message_id == "reply")
    assert child.project_hint is None
    assert not any(f.evidence[0].message_id == "ack" for f in facts)


def test_actionable_project_row_does_not_claim_unrelated_following_items():
    source = message("@_user_1\n1.准备渠道资料\n2.青禾采集项目技术优化\n3.另一个未命名主题对接\n@_user_2\n1.采购资源")
    facts = extract_messages([source])
    assert len(facts) == 4
    assert [fact.project_hint for fact in facts] == [None, "青禾采集项目", None, None]


def test_unassigned_topics_make_parent_unsuitable_for_reply_project_inheritance():
    root = message("A.青禾采集项目\n准备设备\n其他工作：\n准备招聘资料", id="root")
    child = message("今天开始测试设备", id="child", parent="root", minute=1)
    facts = extract_messages([root, child])
    assert next(f for f in facts if f.evidence[0].message_id == "child").project_hint is None


def test_personal_leave_context_is_not_a_work_plan():
    source = message("我明天要去看病，先说一下安排。\nA.青禾采集项目\n准备设备")
    facts = extract_messages([source])
    assert len(facts) == 1 and "看病" not in facts[0].summary


def test_legacy_multiclause_project_tag_remains_verified_for_every_clause():
    source = message("【青禾】[任务:接口]已完成接口；开始测试；提交验收报告")
    facts = extract_messages([source])
    graph = build_workflow(facts, [source])
    assert len(graph.facts) == 3 and all(f.verified for f in graph.facts)
    assert len(graph.nodes) == 3
    assert all(any(e.quote == "【青禾】" for e in f.evidence) for f in facts)


def test_explicit_project_label_opens_a_supported_section():
    source = message("项目名称：青禾校验\n准备设备\n提交验收报告")
    facts = extract_messages([source])
    assert len(facts) == 2 and all(f.project_hint == "青禾校验" for f in facts)
    assert all(f.verified for f in build_workflow(facts, [source]).facts)


def test_polite_report_request_does_not_turn_the_recipient_into_assignee():
    source = message("青禾采集项目请向 @_user_1 汇报测试结果", mentions=[{"key": "@_user_1", "id": "person-1", "name": "虚构甲"}])
    facts = extract_messages([source])
    assert len(facts) == 1 and facts[0].actor is None and facts[0].attributes["assignees"] == []
