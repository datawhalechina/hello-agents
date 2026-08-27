"""
ProjectAssistant._retrieve_relevant_notes() 的回归测试（Issue #846）

覆盖场景：
1. action 笔记与 query 无关键词重叠时，仍被显式检索并出现在结果中
2. blocker、action、search 返回相同笔记时不产生重复
3. 最终结果数量不超过 limit
4. NoteTool 返回空值/非法结果/抛异常时不会崩溃

说明：
- 本文件通过 stub 掉第三方依赖（hello_agents、dotenv）来导入被测模块，
  不需要真实安装这些包，也不会发起任何 LLM 调用。
- 既支持 pytest 运行（python -m pytest test_04_note_tool_integration.py -v），
  也支持直接运行（python test_04_note_tool_integration.py）。
"""
import importlib.util
import sys
import types
from pathlib import Path

# === 1. Stub 掉被测模块的第三方依赖 ===
if "dotenv" not in sys.modules:
    _dotenv = types.ModuleType("dotenv")
    _dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = _dotenv

if "hello_agents" not in sys.modules:
    _hello_agents = types.ModuleType("hello_agents")

    class _SimpleAgent:
        def __init__(self, name, llm=None, **kwargs):
            self.name = name
            self.llm = llm

    _hello_agents.SimpleAgent = _SimpleAgent
    _hello_agents.HelloAgentsLLM = type("HelloAgentsLLM", (), {"__init__": lambda self, *a, **k: None})
    sys.modules["hello_agents"] = _hello_agents

    _context = types.ModuleType("hello_agents.context")
    _context.ContextBuilder = type("ContextBuilder", (), {})
    _context.ContextConfig = type("ContextConfig", (), {"__init__": lambda self, **k: None})
    _context.ContextPacket = type("ContextPacket", (), {"__init__": lambda self, **k: None})
    sys.modules["hello_agents.context"] = _context

    _tools = types.ModuleType("hello_agents.tools")
    _tools.MemoryTool = type("MemoryTool", (), {})
    _tools.RAGTool = type("RAGTool", (), {})
    _tools.NoteTool = type("NoteTool", (), {})
    sys.modules["hello_agents.tools"] = _tools

    _message = types.ModuleType("hello_agents.core.message")
    _message.Message = type("Message", (), {"__init__": lambda self, **k: None})
    sys.modules["hello_agents.core.message"] = _message


# === 2. 导入被测模块（文件名以数字开头，需用 importlib 加载）===
_MODULE_PATH = Path(__file__).parent / "04_note_tool_integration.py"
_spec = importlib.util.spec_from_file_location("_04_note_tool_integration", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
ProjectAssistant = _module.ProjectAssistant


# === 3. 测试用的 NoteTool 替身 ===
class StubNoteTool:
    """记录调用并按 action 返回预设结果的 NoteTool 替身"""

    def __init__(self, blockers=None, actions=None, search_results=None, error=None):
        self.blockers = blockers
        self.actions = actions
        self.search_results = search_results
        self.error = error  # 若不为 None，则 run() 抛出该异常
        self.calls = []

    def run(self, params):
        self.calls.append(dict(params))
        if self.error is not None:
            raise self.error
        action = params.get("action")
        if action == "list":
            if params.get("note_type") == "blocker":
                return self.blockers
            if params.get("note_type") == "action":
                return self.actions
            return []
        if action == "search":
            return self.search_results
        return None


def _make_assistant(note_tool):
    """绕过 __init__（避免 LLM/ContextBuilder 依赖），只注入 note_tool"""
    assistant = ProjectAssistant.__new__(ProjectAssistant)
    assistant.note_tool = note_tool
    return assistant


def _note(note_id, note_type, title, content):
    return {
        "note_id": note_id,
        "type": note_type,
        "title": title,
        "content": content,
        "updated_at": "2026-01-01T00:00:00",
    }


# === 4. 测试用例 ===
def test_action_note_retrieved_without_keyword_overlap():
    """action 笔记与 query 无关键词重叠时，仍应被显式检索到（Issue #846 核心）"""
    action_note = _note("n-action-1", "action", "部署前更新依赖版本", "执行 pip install 并验证")
    note_tool = StubNoteTool(
        blockers=[_note("n-blocker-1", "blocker", "数据库连接超时", "连接池耗尽")],
        actions=[action_note],
        search_results=[],  # 通用搜索未命中 action 笔记
    )
    assistant = _make_assistant(note_tool)

    # query 与 action 笔记标题/正文没有任何关键词重叠
    results = assistant._retrieve_relevant_notes("数据库连接超时怎么解决", limit=3)

    ids = [n["note_id"] for n in results]
    assert "n-action-1" in ids, f"action 笔记应被显式检索到, 实际: {ids}"
    # 同时确认显式调用了 list action（blocker 和 action 各一次）
    list_calls = [c for c in note_tool.calls if c.get("action") == "list"]
    assert {c.get("note_type") for c in list_calls} == {"blocker", "action"}
    assert all(c.get("limit") == 1 for c in list_calls)


def test_dedup_when_all_sources_return_same_note():
    """blocker、action、search 返回相同笔记时，不应产生重复"""
    shared = _note("n-1", "action", "重构业务逻辑层", "下一步执行计划")
    note_tool = StubNoteTool(
        blockers=[shared],
        actions=[shared],
        search_results=[shared],
    )
    assistant = _make_assistant(note_tool)

    results = assistant._retrieve_relevant_notes("重构业务逻辑层", limit=3)

    assert len(results) == 1, f"重复笔记未被去重, 实际: {results}"
    assert results[0]["note_id"] == "n-1"


def test_result_count_does_not_exceed_limit():
    """合并后的结果数量不应超过 limit"""
    search_hits = [
        _note(f"n-s-{i}", "conclusion", f"搜索结果{i}", f"内容{i}") for i in range(5)
    ]
    note_tool = StubNoteTool(
        blockers=[_note("n-b-1", "blocker", "阻塞项", "内容")],
        actions=[_note("n-a-1", "action", "行动项", "内容")],
        search_results=search_hits,
    )
    assistant = _make_assistant(note_tool)

    for limit in (1, 2, 3):
        results = assistant._retrieve_relevant_notes("搜索", limit=limit)
        assert len(results) <= limit, f"limit={limit} 时返回 {len(results)} 条"


def test_handles_none_and_invalid_results():
    """NoteTool 返回 None / 非法 JSON 字符串时不崩溃"""
    for invalid in (None, "not a json string", "", 12345):
        note_tool = StubNoteTool(
            blockers=invalid, actions=invalid, search_results=invalid
        )
        assistant = _make_assistant(note_tool)
        results = assistant._retrieve_relevant_notes("任意查询", limit=3)
        assert results == [], f"非法输入 {invalid!r} 应返回空列表, 实际: {results}"


def test_handles_note_tool_exception():
    """NoteTool 抛异常时不崩溃，返回空列表"""
    note_tool = StubNoteTool(error=RuntimeError("NoteTool 内部错误"))
    assistant = _make_assistant(note_tool)

    results = assistant._retrieve_relevant_notes("任意查询", limit=3)
    assert results == [], f"异常应被捕获并返回空列表, 实际: {results}"


if __name__ == "__main__":
    # 兼容无 pytest 环境：直接运行并逐条打印结果
    test_funcs = [
        test_action_note_retrieved_without_keyword_overlap,
        test_dedup_when_all_sources_return_same_note,
        test_result_count_does_not_exceed_limit,
        test_handles_none_and_invalid_results,
        test_handles_note_tool_exception,
    ]
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"[PASS] {func.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {func.__name__}: {e}")
    total = len(test_funcs)
    print(f"\n{total - failed}/{total} tests passed")
    sys.exit(1 if failed else 0)
