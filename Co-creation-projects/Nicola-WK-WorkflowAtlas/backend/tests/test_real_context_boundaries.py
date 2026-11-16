"""Independent synthetic boundaries for source-backed natural context.

Examples are invented and contain no supplied enterprise text or identities.
"""
from datetime import datetime, timedelta, timezone
import pytest

from app.extraction.contextual import extract_messages
from app.agents.orchestrator import WorkflowOrchestrator
from app.schemas import EvidenceReference, StandardMessage
from app.workflow.builder import build_workflow
from app.workflow.verifier import verify_evidence


def record(text, identifier="m1", *, source="fiction-source", chat="fiction-room", minute=0, parent=None, root=None, mentions=None, kind="text"):
    return StandardMessage(
        id=identifier, source_id=source, chat_id=chat, sender="fiction-author", text=text,
        timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc) + timedelta(minutes=minute),
        metadata={"raw": {"sender": {"id": "fiction-author", "name": "虚构记录人"}, "msg_type": kind,
                          "parent_id": parent, "root_id": root, "mentions": mentions or []}},
    )


def from_message(facts, identifier):
    return [fact for fact in facts if fact.evidence[0].message_id == identifier]


def test_html_sections_have_literal_project_support_without_mutating_source():
    source = record("<p>本周安排</p><p>A.琉光采样项目</p><p>准备传感设备&nbsp;并确认采样方案</p><p>B.山岚校验项目</p><p>提交测试结果</p>")
    original = source.model_dump(mode="json")
    facts = extract_messages([source])
    assert len(facts) == 2
    assert [fact.project_hint for fact in facts] == ["琉光采样项目", "山岚校验项目"]
    assert all(fact.review_status == "pending" for fact in facts)
    for fact in facts:
        attribution = fact.attributes["project_attribution"]
        support = [EvidenceReference.model_validate(item) for item in attribution.get("support", attribution.get("evidence", []))]
        assert attribution["method"] == "section" and support
        assert verify_evidence(support, [source]) and verify_evidence(fact.evidence, [source])
        assert any(fact.project_hint in item.quote for item in support)
    assert source.model_dump(mode="json") == original


def test_same_message_ids_do_not_leak_catalog_between_sources_or_chats():
    prior = record("琉光采样项目开始准备设备", "shared-id")
    foreign_source = record("琉光采样开始测试设备", "child", source="other-source", minute=1)
    foreign_room = record("琉光采样开始测试设备", "room-child", chat="other-room", minute=1)
    facts = extract_messages([prior, foreign_source, foreign_room])
    assert from_message(facts, "child")[0].project_hint is None
    assert from_message(facts, "room-child")[0].project_hint is None


def test_reply_parent_root_conflict_stays_unassigned():
    first = record("琉光采样项目开始准备设备", "root")
    second = record("山岚校验项目开始准备设备", "parent", minute=1)
    reply = record("今天提交测试结果", "reply", minute=2, parent="parent", root="root")
    facts = extract_messages([first, second, reply])
    child = from_message(facts, "reply")[0]
    assert child.project_hint is None
    assert child.attributes["project_attribution"]["method"] == "unassigned"


def test_reply_context_cannot_be_supplied_by_future_or_other_chat_message():
    reply = record("今天开始测试设备", "reply", minute=1, parent="root")
    for parent in (
        record("琉光采样项目开始准备设备", "root", minute=2),
        record("琉光采样项目开始准备设备", "root", chat="other-room"),
        record("琉光采样项目开始准备设备", "root", source="other-source"),
    ):
        child = from_message(extract_messages([parent, reply]), "reply")[0]
        assert child.project_hint is None
        assert len(child.evidence) == 1


def test_mention_of_report_recipient_is_not_a_task_assignment():
    mentions = [{"key": "@_user_1", "id": "fiction-recipient", "name": "虚构收件人"}]
    source = record("琉光采样项目已完成设备测试，向 @_user_1 汇报结果", mentions=mentions)
    facts = extract_messages([source])
    assert facts
    assert all(fact.actor is None and fact.attributes["actor_role"] != "explicit_assignee" for fact in facts)
    assert all(not fact.attributes.get("assigned_actor_ids") for fact in facts)


def test_explicit_assignment_keeps_reporter_separate_from_assignee():
    mentions = [{"key": "@_user_1", "id": "fiction-owner", "name": "虚构执行者"}]
    source = record("琉光采样项目请由 @_user_1 负责准备传感设备", mentions=mentions)
    facts = extract_messages([source])
    assert facts and facts[0].actor == "虚构执行者"
    assert facts[0].attributes["actor_role"] == "explicit_assignee"
    assert facts[0].attributes["reported_by"]["id"] == "fiction-author"
    assert facts[0].attributes["assigned_actor_ids"] == ["fiction-owner"]
    assert verify_evidence(facts[0].evidence, [source])


def test_carried_assignment_includes_the_original_mention_line_evidence():
    mentions = [{"key": "@_user_1", "id": "fiction-owner", "name": "虚构执行者"}]
    source = record("A.琉光采样项目\n@_user_1\n1.准备传感设备", mentions=mentions)
    facts = extract_messages([source])
    assert len(facts) == 1 and facts[0].actor == "虚构执行者"
    assert any("@_user_1" in evidence.quote for evidence in facts[0].evidence)
    assert verify_evidence(facts[0].evidence, [source])


def test_nonvisible_scripts_templates_links_and_attachments_do_not_create_facts():
    messages = [
        record("<script>琉光采样项目开始准备设备</script><p>收到，谢谢</p>", "script"),
        record("项目名称：中文 / 英文\n项目简介：中英文各一段\n代表图片：横版", "template"),
        record("诚邀大家参与本项目调研，请根据自身实际情况填写", "advertisement"),
        record("https://example.invalid/project/task/review", "link"),
        record("琉光采样项目开始准备设备", "unread-file", kind="file"),
    ]
    assert extract_messages(messages) == []


def test_repeated_processing_is_stable_and_never_auto_approves_labels():
    messages = [record("琉光采样项目开始准备设备", "root"), record("今天提交测试结果", "reply", minute=1, parent="root")]
    first = extract_messages(messages)
    second = extract_messages(list(reversed(messages)))
    assert [fact.model_dump(mode="json") for fact in first] == [fact.model_dump(mode="json") for fact in second]
    first_graph = build_workflow(first, messages)
    second_graph = build_workflow(second, list(reversed(messages)))
    assert first_graph.model_dump(mode="json") == second_graph.model_dump(mode="json")
    assert all(fact.review_status == "pending" for fact in first_graph.facts)
    assert all(verify_evidence(fact.evidence, messages) for fact in first_graph.facts)


def test_identical_task_text_in_different_sections_keeps_two_supported_facts():
    source = record("A.琉光采样项目\n准备设备\nB.山岚校验项目\n准备设备")
    facts = extract_messages([source])
    assert len(facts) == 2 and len({fact.id for fact in facts}) == 2
    graph = build_workflow(facts, [source])
    assert len(graph.facts) == len(graph.nodes) == 2
    assert all(fact.verified for fact in graph.facts)
    assert not any("conflicting duplicate fact" in warning for warning in graph.warnings)


def test_reply_attribution_support_does_not_copy_parent_dependency_to_child():
    target = record("【琉光采样项目】[任务:基础接口] 开始开发接口", "target")
    parent = record("琉光采样项目联调测试依赖「基础接口」", "parent", minute=1)
    child = record("今天提交测试报告", "child", parent="parent", minute=2)
    graph = WorkflowOrchestrator(provider="local-demo").analyze([target, parent, child]).proposal
    child_fact = from_message(graph.facts, "child")[0]
    assert child_fact.project_hint == "琉光采样项目"
    facts_by_id = {fact.id: fact for fact in graph.facts}
    node_facts = {node.id: facts_by_id[node.fact_ids[0]] for node in graph.nodes}
    assert any(edge.relation == "depends_on" and node_facts[edge.source].evidence[0].message_id == "parent" for edge in graph.edges)
    assert not any(edge.relation == "depends_on" and node_facts[edge.source].evidence[0].message_id == "child" for edge in graph.edges)


def test_actionable_project_row_does_not_open_context_for_unrelated_following_work():
    source = record("本周安排\n1.琉光采样项目开始准备设备\n2.确认薪资合规材料\n3.提交招聘资料")
    facts = extract_messages([source])
    named = next(fact for fact in facts if "琉光" in fact.summary)
    assert named.project_hint == "琉光采样项目"
    unrelated = [fact for fact in facts if "薪资" in fact.summary or "招聘" in fact.summary]
    assert len(unrelated) == 2 and all(fact.project_hint is None for fact in unrelated)


def test_reply_to_parent_with_known_and_unassigned_topics_stays_unassigned():
    parent = record("琉光采样项目开始准备设备\n确认薪资合规材料", "parent")
    child = record("今天提交测试结果", "child", minute=1, parent="parent")
    facts = extract_messages([parent, child])
    parent_facts = from_message(facts, "parent")
    assert any(fact.project_hint for fact in parent_facts) and any(fact.project_hint is None for fact in parent_facts)
    assert from_message(facts, "child")[0].project_hint is None


@pytest.mark.parametrize("text", ["琉光采样项目预计明天完成", "琉光采样项目明天开始测试"])
def test_future_plan_is_not_reported_as_completed_or_already_in_progress(text):
    facts = extract_messages([record(text)])
    assert len(facts) == 1 and facts[0].kind == "plan"
    assert facts[0].status == "planned"
