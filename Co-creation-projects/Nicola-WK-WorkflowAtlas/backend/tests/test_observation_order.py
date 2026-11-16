from app.extraction.contextual import extract_messages
from app.ordering import fact_order_key
from app.schemas import StandardMessage
from app.workflow.builder import build_workflow


def test_same_message_tasks_keep_literal_order_in_graph_and_memory():
    message = StandardMessage(id="order", source_id="synthetic", timestamp="2026-01-01T09:00:00+08:00", text="A.星澜项目\n先准备设备\n再开始测试设备\n最后提交验收报告")
    facts = extract_messages([message])
    assert len(facts) == 3
    expected = [fact.summary for fact in sorted(facts, key=lambda f: f.attributes["source_span"]["start"])]
    # Adversarial IDs establish that identifier order cannot reorder source clauses.
    for fact, name in zip(facts, ["z-last", "m-middle", "a-first"]):
        fact.id = name
    graph = build_workflow(facts, [message])
    assert [node.label for node in graph.nodes] == expected
    assert [f.summary for f in sorted(graph.facts, key=fact_order_key)] == expected
    from app.retrieval.memory import build_working_memory
    memory = build_working_memory(graph.facts)
    assert [item["summary"] for item in memory["recent_facts"]] == list(reversed(expected))
