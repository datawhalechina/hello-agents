"""Offline integration coverage for bundled, on-demand paper skills.

The scripted LLM tests the real Reader tool plumbing, not model skill selection.
"""

from __future__ import annotations

from copy import deepcopy
import json
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from hello_agents.skills import SkillLoader
from hello_agents.tools.builtin.skill_tool import SkillTool
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.response import ToolStatus

from app.agents.support.paper_skill_tool import PaperSkillTool


PAPER_SKILLS = {
    "paper-reading",
    "paper-comparison",
    "literature-review",
    "reproducibility-check",
}


@pytest.fixture(autouse=True)
def offline_data_dir(tmp_path, monkeypatch):
    from app.settings import get_settings

    def no_network(*args, **kwargs):
        raise AssertionError("Paper skill tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(get_settings(), "data_dir", str(tmp_path))
    monkeypatch.setattr(get_settings(), "tavily_api_key", "")


class RecordingLLM:
    """Only the model response boundary is scripted; tools execute normally."""

    model = "offline-paper-skills-test"

    def __init__(self, responses=()):
        self.responses = iter(responses)
        self.calls = []

    def invoke_with_tools(self, messages, tools, **kwargs):
        # SimpleAgent mutates messages in place after each response.
        self.calls.append({"messages": deepcopy(messages), "tools": deepcopy(tools)})
        return next(self.responses)

    def invoke(self, *args, **kwargs):
        raise AssertionError("Unexpected plain LLM call")


def model_response(*, tool_name=None, arguments=None, call_id=None, content=None):
    tool_calls = []
    if tool_name:
        tool_calls.append(SimpleNamespace(
            id=call_id,
            function=SimpleNamespace(name=tool_name, arguments=json.dumps(arguments or {})),
        ))
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def reader_factory(monkeypatch):
    from app.agents import base, paper_analysis_agent
    from app.services.llm.agent_config import papergraph_agent_config

    def make_reader(llm=None, **config_overrides):
        def focused_config():
            config = papergraph_agent_config()
            # Keep skill behavior and configured paths; omit unrelated services.
            config.trace_enabled = False
            config.session_enabled = False
            config.subagent_enabled = False
            config.todowrite_enabled = False
            config.devlog_enabled = False
            for name, value in config_overrides.items():
                setattr(config, name, value)
            return config

        monkeypatch.setattr(base, "get_llm", lambda: llm if llm is not None else RecordingLLM())
        monkeypatch.setattr(paper_analysis_agent, "papergraph_agent_config", focused_config)
        return paper_analysis_agent.PaperAnalysisAgent()

    return make_reader


def test_bundled_skills_discovered_and_loaded_by_native_tool_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tool = PaperSkillTool()
    assert isinstance(tool, SkillTool)
    assert isinstance(tool.skill_loader, SkillLoader)
    assert tool.name == "PaperSkill"
    assert tool.skill_loader.skills_dir == BACKEND_ROOT / "skills"
    assert set(tool.skill_loader.list_skills()) == PAPER_SKILLS
    assert tool.skill_loader.skills_cache == {}

    for name in sorted(PAPER_SKILLS):
        metadata = tool.skill_loader.metadata_cache[name]
        assert metadata["description"]
        assert name in tool.description
        assert metadata["description"] in tool.description
        response = tool.run({"skill": name})
        skill = tool.skill_loader.get_skill(name)
        assert response.status == ToolStatus.SUCCESS
        assert response.data["loaded"] is True
        assert response.data["name"] == name
        assert skill is not None and skill.body
        assert skill.body in response.text
        assert skill.body not in tool.description
        assert skill.path == BACKEND_ROOT / "skills" / name / "SKILL.md"

    assert set(tool.skill_loader.skills_cache) == PAPER_SKILLS
    assert not (tmp_path / "skills").exists()


@pytest.mark.parametrize("requested_name", ["unknown-paper-skill", "../outside/SKILL.md", "paper-reading/../../outside"])
def test_unknown_and_traversal_skill_names_fail_without_loading(requested_name):
    tool = PaperSkillTool()
    response = tool.run({"skill": requested_name})
    assert response.status == ToolStatus.ERROR
    assert response.error_info["code"] == ToolErrorCode.NOT_FOUND
    assert response.data.get("loaded") is not True
    assert tool.skill_loader.skills_cache == {}


def test_absolute_path_does_not_load_an_arbitrary_skill_file(tmp_path):
    outside = tmp_path / "SKILL.md"
    outside.write_text(
        "---\nname: outside\ndescription: external fixture\n---\nPRIVATE_OUTSIDE_SKILL_BODY",
        encoding="utf-8",
    )
    tool = PaperSkillTool()
    response = tool.run({"skill": str(outside)})
    assert response.status == ToolStatus.ERROR
    assert response.error_info["code"] == ToolErrorCode.NOT_FOUND
    assert "PRIVATE_OUTSIDE_SKILL_BODY" not in response.text
    assert tool.skill_loader.skills_cache == {}


@pytest.mark.parametrize("requested_name", ["UNRECOGNIZED_NAME_" * 1000, None, 123, ["paper-reading"]])
def test_invalid_skill_arguments_return_bounded_errors(requested_name):
    tool = PaperSkillTool()
    response = tool.run({"skill": requested_name})
    assert response.status == ToolStatus.ERROR
    assert len(response.text) < 256
    assert "UNRECOGNIZED_NAME_" not in response.text
    assert "UNRECOGNIZED_NAME_" not in json.dumps(response.error_info)
    assert tool.skill_loader.skills_cache == {}
    assert [parameter.name for parameter in tool.get_parameters()] == ["skill"]


def test_reader_preserves_native_custom_skill_and_its_files(reader_factory, tmp_path):
    # A same-name user skill must still be independently available via Skill.
    custom_root = tmp_path / "memory" / "skills"
    custom_file = custom_root / "paper-reading" / "SKILL.md"
    custom_file.parent.mkdir(parents=True)
    custom_file.write_text(
        "---\nname: paper-reading\ndescription: Personal reading routine\n---\n"
        "CUSTOM_READING_ROUTINE $ARGUMENTS\n",
        encoding="utf-8",
    )
    reference = custom_file.parent / "references" / "notes.txt"
    reference.parent.mkdir()
    reference.write_text("Unmodified personal reference", encoding="utf-8")
    original_files = {path.relative_to(custom_root): path.read_bytes() for path in custom_root.rglob("*") if path.is_file()}

    agent = reader_factory()
    native = agent._reader.tool_registry.get_tool("Skill")
    bundled = agent._reader.tool_registry.get_tool("PaperSkill")
    assert type(native) is SkillTool
    assert isinstance(bundled, PaperSkillTool)
    assert native.skill_loader is agent._reader.skill_loader
    assert native.skill_loader.skills_dir == custom_root
    assert set(native.skill_loader.list_skills()) == {"paper-reading"}
    assert native.skill_loader is not bundled.skill_loader

    custom_result = native.run({"skill": "paper-reading", "args": "USER_SUPPLIED_ARGUMENT"})
    bundled_result = bundled.run({"skill": "paper-reading"})
    assert custom_result.status == bundled_result.status == ToolStatus.SUCCESS
    assert "CUSTOM_READING_ROUTINE USER_SUPPLIED_ARGUMENT" in custom_result.text
    assert "notes.txt" in custom_result.text
    assert "CUSTOM_READING_ROUTINE" not in bundled_result.text
    assert {path.relative_to(custom_root): path.read_bytes() for path in custom_root.rglob("*") if path.is_file()} == original_files


@pytest.mark.parametrize("enabled,auto_register", [(False, True), (True, False), (False, False)])
def test_reader_respects_skill_config_switches(reader_factory, enabled, auto_register):
    agent = reader_factory(skills_enabled=enabled, skills_auto_register=auto_register)
    registry = agent._reader.tool_registry
    assert registry.get_tool("PaperSkill") is None
    assert registry.get_tool("Skill") is None
    assert registry.get_tool("reader_pdf_structure") is not None
    assert (agent._reader.skill_loader is not None) is enabled


def test_reader_run_loads_skill_then_executes_real_pdf_tool(reader_factory):
    llm = RecordingLLM([
        model_response(tool_name="PaperSkill", arguments={"skill": "paper-reading"}, call_id="load-paper-skill"),
        model_response(tool_name="reader_pdf_structure", call_id="read-paper-pdf"),
        model_response(content="The method uses a sparse attention mask."),
    ])
    agent = reader_factory(llm)
    agent._reader_snap = {
        "paper_id": 17,
        "title": "Offline sparse attention study",
        "_pdf_merged_for_structure": (
            "1 Introduction\n"
            "We evaluate sparse attention using a fixed train and test split. " * 4
            + "\n2 Method\nMETHOD_EVIDENCE_MARKER: The method uses a sparse attention mask.\n"
            + "\n3 Results\nRESULT_EVIDENCE_MARKER: Runtime was measured on a fixed device.\n"
            + "\nReferences\n[1] Doe J. A reproducible attention benchmark. Test Conference, 2024.\n"
        ),
    }
    tool = agent._reader.tool_registry.get_tool("PaperSkill")
    assert tool.skill_loader.skills_cache == {}

    result = agent._reader.run("Read this paper and explain its method using its PDF evidence.")

    assert result == "The method uses a sparse attention mask."
    assert len(llm.calls) == 3
    skill = tool.skill_loader.get_skill("paper-reading")
    first, after_skill, after_pdf = [call["messages"] for call in llm.calls]
    schemas = {item["function"]["name"]: item["function"] for item in llm.calls[0]["tools"]}
    assert {"PaperSkill", "Skill", "reader_pdf_structure"} <= schemas.keys()
    assert "paper-reading" in schemas["PaperSkill"]["description"]
    assert skill.body not in json.dumps(llm.calls[0], ensure_ascii=False)
    assert not any(message["role"] == "tool" for message in first)

    skill_results = [message for message in after_skill if message["role"] == "tool"]
    assert len(skill_results) == 1
    assert skill_results[0]["tool_call_id"] == "load-paper-skill"
    assert skill.body in skill_results[0]["content"]
    assert "METHOD_EVIDENCE_MARKER" not in skill_results[0]["content"]
    for messages in (after_skill, after_pdf):
        assert all(skill.body not in (message.get("content") or "") for message in messages if message["role"] != "tool")
        assert [message for message in messages if message["role"] == "system"] == [message for message in first if message["role"] == "system"]

    pdf_results = [message for message in after_pdf if message.get("tool_call_id") == "read-paper-pdf"]
    assert len(pdf_results) == 1
    assert pdf_results[0]["role"] == "tool"
    parsed = json.loads(pdf_results[0]["content"].split("\n", 1)[1])
    assert any("METHOD_EVIDENCE_MARKER" in chapter["text"] for chapter in parsed["chapters"])
    assert any("RESULT_EVIDENCE_MARKER" in chapter["text"] for chapter in parsed["chapters"])
    assert parsed["references"]["entry_count"] == 1
    assert agent._reader_snap["references_from_structure"] == parsed["references"]["entries"]
