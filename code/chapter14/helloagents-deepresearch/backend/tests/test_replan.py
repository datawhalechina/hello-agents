"""Unit tests for wave-based re-planning in the deep research workflow."""

from types import SimpleNamespace

from agent import DeepResearchAgent
from config import Configuration
from models import SummaryState, TodoItem
from prompts import replan_instructions
from services.planner import PlanningService


class _StubPlannerAgent:
    """Duck-typed planner agent returning a canned response."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.history_cleared = False

    def run(self, prompt: str) -> str:
        return self._response

    def clear_history(self) -> None:
        self.history_cleared = True


def _make_wave_agent(max_waves: int, execute, replan):
    """Build a DeepResearchAgent without __init__ side effects (LLM/NoteTool)."""

    agent = object.__new__(DeepResearchAgent)
    agent.config = Configuration(max_web_research_loops=max_waves)
    agent.planner = SimpleNamespace(replan_todo_list=replan)
    agent._set_tool_event_sink = lambda sink: None
    agent._execute_task = execute
    agent._serialize_task = lambda t: {"id": t.id, "title": t.title, "status": t.status}
    return agent


def _task(task_id: int, status: str = "pending", summary: str | None = None) -> TodoItem:
    return TodoItem(
        id=task_id,
        title=f"任务{task_id}",
        intent="意图",
        query=f"q{task_id}",
        status=status,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# _collect_gaps
# ---------------------------------------------------------------------------
def test_collect_gaps_keeps_only_skipped_failed_or_empty_summary() -> None:
    tasks = [
        _task(1, status="completed", summary="有内容"),
        _task(2, status="skipped"),
        _task(3, status="failed"),
        _task(4, status="completed", summary=None),
        _task(5, status="completed", summary="暂无可用信息"),
        _task(6, status="pending"),
    ]

    gaps = DeepResearchAgent._collect_gaps(tasks)

    assert [t.id for t in gaps] == [2, 3, 4, 5]


# ---------------------------------------------------------------------------
# PlanningService.replan_todo_list
# ---------------------------------------------------------------------------
def test_replan_todo_list_parses_response_and_continues_ids() -> None:
    stub = _StubPlannerAgent('{"tasks": [{"title": "补做", "intent": "补齐缺口", "query": "新关键词"}]}')
    service = PlanningService(stub, Configuration())

    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1, status="completed", summary="ok"), _task(2, status="skipped")]
    gaps = [state.todo_items[1]]

    result = service.replan_todo_list(state, gaps)

    assert len(result) == 1
    assert result[0].id == 3  # continues after max existing id
    assert result[0].title == "补做"
    assert result[0].query == "新关键词"
    assert stub.history_cleared


def test_replan_todo_list_returns_empty_on_unparsable_response() -> None:
    stub = _StubPlannerAgent("no json here at all")
    service = PlanningService(stub, Configuration())

    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1, status="skipped")]

    assert service.replan_todo_list(state, state.todo_items) == []


def test_format_completed_skips_non_completed_tasks() -> None:
    tasks = [_task(1, status="completed", summary="总结A"), _task(2, status="skipped")]

    rendered = PlanningService._format_completed(tasks)

    assert "任务 1" in rendered and "总结A" in rendered
    assert "任务 2" not in rendered


def test_format_gaps_renders_gap_tasks() -> None:
    rendered = PlanningService._format_gaps([_task(7, status="skipped")])

    assert "任务 7" in rendered and "skipped" in rendered


# ---------------------------------------------------------------------------
# Wave loop (_run_waves)
# ---------------------------------------------------------------------------
def test_run_waves_replans_gaps_and_appends_followup_tasks() -> None:
    replan_calls = {"n": 0}
    executed = []

    def execute(state, task, emit_stream=False, step=None):
        executed.append(task.id)
        if task.id == 2:
            task.status = "skipped"
        else:
            task.status = "completed"
            task.summary = "ok"
        return []

    def replan(state, gaps):
        replan_calls["n"] += 1
        assert [g.id for g in gaps] == [2]
        return [_task(3)]

    agent = _make_wave_agent(max_waves=3, execute=execute, replan=replan)
    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1), _task(2)]

    events = list(agent._run_waves(state, emit_stream=False))

    assert events == []
    assert executed == [1, 2, 3]  # every pending task runs in every wave
    assert [t.id for t in state.todo_items] == [1, 2, 3]
    assert state.todo_items[2].status == "completed"
    assert replan_calls["n"] == 1  # already re-planned gaps are not re-collected


def test_run_waves_isolates_task_exceptions() -> None:
    executed = []

    def execute(state, task, emit_stream=False, step=None):
        executed.append(task.id)
        if task.id == 2:
            raise RuntimeError("search backend down")
        task.status = "completed"
        task.summary = "ok"
        return []

    def replan(state, gaps):
        return [_task(3)]

    agent = _make_wave_agent(max_waves=3, execute=execute, replan=replan)
    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1), _task(2)]

    events = list(agent._run_waves(state, emit_stream=False))

    assert events == []
    assert executed == [1, 2, 3]  # a crashing task must not abort the run
    assert state.todo_items[1].status == "failed"  # crash -> gap
    assert [t.id for t in state.todo_items] == [1, 2, 3]  # re-planned follow-up
    assert state.todo_items[2].status == "completed"


def test_run_waves_respects_wave_cap() -> None:
    replan_calls = {"n": 0}

    def execute(state, task, emit_stream=False, step=None):
        task.status = "skipped"  # always a gap
        return []

    def replan(state, gaps):
        replan_calls["n"] += 1
        return [_task(len(state.todo_items) + 1)]

    agent = _make_wave_agent(max_waves=2, execute=execute, replan=replan)
    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1)]

    list(agent._run_waves(state, emit_stream=False))

    assert replan_calls["n"] == 1  # wave 0 re-plans, wave 1 hits the cap
    assert len(state.todo_items) == 2


def test_run_waves_stops_when_replan_returns_empty() -> None:
    def execute(state, task, emit_stream=False, step=None):
        task.status = "skipped"
        return []

    def replan(state, gaps):
        return []

    agent = _make_wave_agent(max_waves=3, execute=execute, replan=replan)
    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1)]

    list(agent._run_waves(state, emit_stream=False))

    assert len(state.todo_items) == 1  # no follow-up wave appended


def test_run_waves_skips_replan_when_no_gaps() -> None:
    replan_calls = {"n": 0}

    def execute(state, task, emit_stream=False, step=None):
        task.status = "completed"
        task.summary = "ok"
        return []

    def replan(state, gaps):
        replan_calls["n"] += 1
        return [_task(99)]

    agent = _make_wave_agent(max_waves=3, execute=execute, replan=replan)
    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1)]

    list(agent._run_waves(state, emit_stream=False))

    assert replan_calls["n"] == 0
    assert len(state.todo_items) == 1


def test_run_waves_stream_yields_second_todo_list_event() -> None:
    def execute(state, task, emit_stream=False, step=None):
        if task.id == 99:
            task.status = "completed"
            task.summary = "ok"
        else:
            task.status = "skipped"  # leave a gap so re-planning triggers
        if emit_stream:
            return [{"type": "task_status", "task_id": task.id, "status": task.status}]
        return []

    def replan(state, gaps):
        return [_task(99)]

    agent = _make_wave_agent(max_waves=3, execute=execute, replan=replan)
    state = SummaryState(research_topic="测试主题")
    state.todo_items = [_task(1)]

    events = list(agent._run_waves(state, emit_stream=True))
    types = [e["type"] for e in events]

    assert types[0] == "todo_list"
    assert types.count("todo_list") == 2  # wave 0 + re-planned wave broadcast
    assert types.count("task_status") >= 1
    assert any(e["status"] == "skipped" for e in events if e["type"] == "task_status")


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
def test_replan_instructions_contains_expected_placeholders() -> None:
    for placeholder in ("{current_date}", "{research_topic}", "{completed}", "{gaps}"):
        assert placeholder in replan_instructions
