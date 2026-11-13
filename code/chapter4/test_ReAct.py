import sys
import types
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent))
llm_client = types.ModuleType("llm_client")
llm_client.HelloAgentsLLM = object
sys.modules["llm_client"] = llm_client
tools = types.ModuleType("tools")
tools.ToolExecutor = object
tools.search = lambda query: query
sys.modules["tools"] = tools

from ReAct import ReActAgent


def agent():
    return ReActAgent.__new__(ReActAgent)


def test_parse_single_action():
    assert agent()._parse_action("Search[query]") == ("Search", "query")


def test_parse_only_first_action():
    action = "Search[first query]\nAction: Search[second query]"

    assert agent()._parse_action(action) == ("Search", "first query")


def test_parse_multiline_and_bracketed_input_and_reject_malformed_action():
    action = "Search[line one\nline two [with brackets]]"

    assert agent()._parse_action(action) == (
        "Search",
        "line one\nline two [with brackets]",
    )
    assert agent()._parse_action("Search[unfinished") == (None, None)


def test_parse_finish_only_first_answer():
    action = "Finish[final answer]\nAction: Search[ignored]"

    assert agent()._parse_action_input(action) == "final answer"

    llm_client = Mock()
    llm_client.think.return_value = f"Thought: done\nAction: {action}"
    tool_executor = Mock()
    tool_executor.getAvailableTools.return_value = ""

    assert ReActAgent(llm_client, tool_executor).run("question") == "final answer"
    tool_executor.getTool.assert_not_called()
