"""
Agent.stream 历史累积 + 历史清洗 + 反思触发器测试
=================================================
针对以下 bug 的回归测试：
  1. stream() 只保留 chunk["messages"][-1]，并行工具调用时丢失 N-1 条 ToolMessage，
     导致下次对话被 DeepSeek 400 拒绝（Agent 永久不可用）。
  2. _sanitize_history 修复历史遗留的 tool_calls / ToolMessage 不匹配。
  3. task_reflection_trigger 只统计本轮的工具调用，避免反射提示在历史中堆积。
"""
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import Command
import json

from Agent import Agent, _sanitize_history
from agent_tools.middleware import task_reflection_trigger, todo_continue_trigger
from agent_tools.agent_tools import restore_todo_state, reset_todo_state


class FakeGraph:
    """模拟 langgraph 编译后的 graph：按完整快照序列 yield（stream_mode='values'）"""

    def __init__(self, snapshots):
        self.snapshots = snapshots

    def stream(self, state, stream_mode="values"):
        for snap in self.snapshots:
            yield {"messages": snap}


def _ai(content="", tool_calls=None):
    return AIMessage(content=content, tool_calls=tool_calls or [])


def test_stream_accumulates_all_parallel_tool_results():
    """并行工具调用时，stream() 必须保留全部 ToolMessage（而非只有最后一条）"""
    a = Agent()
    ai1 = _ai(tool_calls=[
        {"name": "search", "args": {"query": "a"}, "id": "call_1"},
        {"name": "search", "args": {"query": "b"}, "id": "call_2"},
        {"name": "search", "args": {"query": "c"}, "id": "call_3"},
    ])
    tm1 = ToolMessage(content="r1", tool_call_id="call_1", name="search")
    tm2 = ToolMessage(content="r2", tool_call_id="call_2", name="search")
    tm3 = ToolMessage(content="r3", tool_call_id="call_3", name="search")
    ai2 = _ai(content="完成")
    snapshots = [
        [HumanMessage(content="查一下"), ai1],
        [HumanMessage(content="查一下"), ai1, tm1, tm2, tm3],
        [HumanMessage(content="查一下"), ai1, tm1, tm2, tm3, ai2],
    ]
    a.agent = FakeGraph(snapshots)

    outputs = list(a.stream("查一下"))
    assert outputs == ["完成\n"]
    # 全部 3 条 ToolMessage 都必须保留
    tool_msgs = [m for m in a.messages if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 3
    assert {t.tool_call_id for t in tool_msgs} == {"call_1", "call_2", "call_3"}


def test_stream_empty_query_noop():
    """空/空白查询不产生任何消息"""
    a = Agent()
    assert list(a.stream("   ")) == []
    assert a.messages == []


def test_sanitize_history_strips_unmatched_tool_calls():
    """被污染的历史：未匹配的 tool_call 被剥离，孤儿 ToolMessage 被删除"""
    ai = _ai(tool_calls=[
        {"name": "search", "args": {"query": "a"}, "id": "call_1"},
        {"name": "search", "args": {"query": "b"}, "id": "call_2"},
        {"name": "search", "args": {"query": "c"}, "id": "call_3"},
    ])
    tm1 = ToolMessage(content="r1", tool_call_id="call_1", name="search")  # 唯一回应
    orphan = ToolMessage(content="孤儿", tool_call_id="call_x", name="search")
    messages = [HumanMessage(content="q"), ai, tm1, orphan]

    cleaned = _sanitize_history(messages)

    ai_kept = [m for m in cleaned if isinstance(m, AIMessage) and m.tool_calls]
    assert len(ai_kept) == 1
    assert [tc["id"] for tc in ai_kept[0].tool_calls] == ["call_1"]
    tms = [m for m in cleaned if isinstance(m, ToolMessage)]
    assert len(tms) == 1
    assert tms[0].tool_call_id == "call_1"


def test_sanitize_history_drops_empty_ai_without_matches():
    """完全无匹配且无文本的 AIMessage 被整体删除"""
    ai = _ai(content="", tool_calls=[{"name": "todo", "args": {}, "id": "c9"}])
    messages = [HumanMessage(content="q"), ai]
    cleaned = _sanitize_history(messages)
    assert len(cleaned) == 1
    assert isinstance(cleaned[0], HumanMessage)


def test_sanitize_history_keeps_healthy_history():
    """健康历史（call 与 ToolMessage 一一对应）保持不变"""
    ai = _ai(tool_calls=[{"name": "search", "args": {"query": "x"}, "id": "c1"}])
    tm = ToolMessage(content="r", tool_call_id="c1", name="search")
    ai2 = _ai(content="回复")
    messages = [HumanMessage(content="q"), ai, tm, ai2]
    cleaned = _sanitize_history(messages)
    assert len(cleaned) == 4
    assert len([m for m in cleaned if isinstance(m, ToolMessage)]) == 1


def test_reflection_counts_only_current_turn():
    """反思触发器只统计最近一轮的工具调用"""
    ai1 = _ai(tool_calls=[{"name": "search", "args": {"query": "x"}, "id": "c1"}])
    tm1 = ToolMessage(content="r", tool_call_id="c1", name="search")

    # 只有历史轮次有工具调用，本轮纯聊天 → 不触发
    state_pure_chat = {
        "messages": [
            HumanMessage(content="q1"), ai1, tm1, _ai(content="回答1"),
            HumanMessage(content="q2"),
        ]
    }
    assert task_reflection_trigger.after_agent(state_pure_chat, None) is None

    # 本轮有工具调用 → 触发（返回 Command）
    tm2 = ToolMessage(content="r2", tool_call_id="c2", name="search")
    state_with_tools = {
        "messages": [
            HumanMessage(content="q1"), ai1, tm1, _ai(content="回答1"),
            HumanMessage(content="q2"),
            _ai(tool_calls=[{"name": "search", "args": {"query": "y"}, "id": "c2"}]),
            tm2,
            _ai(content="回答2"),
        ]
    }
    result = task_reflection_trigger.after_agent(state_with_tools, None)
    assert result is not None
    assert isinstance(result, Command)


# ── todo_continue_trigger + stream 的 todo 事件 ──

def _pending_todo(tid=1, title="任务"):
    return {"id": tid, "title": title, "desc": "", "status": "pending",
            "created_at": "", "done_at": None}


def test_todo_continue_trigger_nudges_once_then_dedups():
    """本轮 add 待办且未完成、最终无 tool_calls → 注入一次 Command(goto=model)；带 marker 后去重返回 None"""
    try:
        restore_todo_state([_pending_todo()], 1)
        ai1 = _ai(tool_calls=[{"name": "todo", "args": {"command": "add 搜索数据"}, "id": "c1"}])
        tm1 = ToolMessage(content="✅ 已添加任务 [1] 搜索数据", tool_call_id="c1", name="todo")
        state = {"messages": [HumanMessage(content="q"), ai1, tm1, _ai(content="计划已就绪")]}
        result = todo_continue_trigger.after_agent(state, None)
        assert result is not None and isinstance(result, Command)
        assert result.goto == "model"
        # marker 已注入后再次退出 → 去重，返回 None（防死循环）
        marker_msg = result.update["messages"][0]
        state2 = {"messages": [HumanMessage(content="q"), ai1, tm1, _ai(content="计划已就绪"), marker_msg]}
        assert todo_continue_trigger.after_agent(state2, None) is None
    finally:
        reset_todo_state()


def test_todo_continue_trigger_skips_list_only():
    """仅 todo list（非变更型调用）不触发续跑"""
    try:
        restore_todo_state([_pending_todo()], 1)
        ai1 = _ai(tool_calls=[{"name": "todo", "args": {"command": "list"}, "id": "c1"}])
        tm1 = ToolMessage(content="📋 待办清单", tool_call_id="c1", name="todo")
        state = {"messages": [HumanMessage(content="q"), ai1, tm1, _ai(content="看完了")]}
        assert todo_continue_trigger.after_agent(state, None) is None
    finally:
        reset_todo_state()


def test_stream_emits_todo_event_for_parallel_adds():
    """stream() 本轮出现 todo ToolMessage 时发出一次 todo 快照事件（并行 add 只发一条）"""
    a = Agent()
    ai1 = _ai(tool_calls=[
        {"name": "todo", "args": {"command": "add 搜索数据"}, "id": "c1"},
        {"name": "todo", "args": {"command": "add 计算同比"}, "id": "c2"},
    ])
    tm1 = ToolMessage(content="✅ 已添加任务 [1]", tool_call_id="c1", name="todo")
    tm2 = ToolMessage(content="✅ 已添加任务 [2]", tool_call_id="c2", name="todo")
    ai2 = _ai(content="完成")
    snapshots = [
        [HumanMessage(content="q"), ai1],
        [HumanMessage(content="q"), ai1, tm1, tm2],
        [HumanMessage(content="q"), ai1, tm1, tm2, ai2],
    ]
    a.agent = FakeGraph(snapshots)
    try:
        restore_todo_state([_pending_todo(1, "搜索数据"), _pending_todo(2, "计算同比")], 2)
        outputs = list(a.stream("q"))
    finally:
        reset_todo_state()
    todo_events = [o for o in outputs if '"type": "todo"' in o]
    assert len(todo_events) == 1, outputs
    assert len(json.loads(todo_events[0])["todos"]) == 2
    assert outputs[-1] == "完成\n"
