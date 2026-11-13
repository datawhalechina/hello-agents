"""Recover complete parameters without inventing code or bypassing review."""
from __future__ import annotations

import asyncio
import json
from collections import deque

import pytest

from backend.model import ActionFormatError, parse_action, tool_messages
from backend.runtime import Runtime
from backend.settings import Settings
from backend.skills import ANNOTATION_SKILL, annotation_read_hints, load_skill
from backend.store import Store, identifier, now
from backend.workspace import digest


@pytest.mark.parametrize("nested_summary", [False, True])
def test_only_missing_outer_brace_is_completed_without_changing_patch_strings(nested_summary):
    changes = [{"path": "backend/run.py", "base_hash": "real-hash", "edits": [
        {"old": 'print("{} [] \\\\path")\r\n',
         "new": '# 中文说明：引号 "、括号 {} []、反斜杠 \\ 和换行\r\nprint("{} [] \\\\path")\r\n'}]}]
    action = {"action": "propose_patch", "args": {"changes": changes}}
    if nested_summary:
        action["args"]["summary"] = "准备注释补丁"
    else:
        action["summary"] = "准备注释补丁"
    broken = json.dumps(action, ensure_ascii=False)[:-1]
    diagnostics = []
    normalized = parse_action(broken, diagnostics=diagnostics)
    assert normalized == {"action": "propose_patch", "args": {"changes": changes}, "summary": "准备注释补丁"}
    assert len(diagnostics) == (2 if nested_summary else 1)


@pytest.mark.parametrize("broken", [
    '{"action":"propose_patch","args":{"changes":[',
    '{"action":"propose_patch","args":{"changes":[]',
    '{"action":"propose_patch","args":{},"summary":"incomplete',
    '{"action":"propose_patch","args":{},',
    '{"action":"propose_patch","args":{"changes":]}',
    '{"action":"propose_patch","args":{"path":"bad\\q"}',
    '{"action":"propose_patch","args":{} "summary":"missing comma"',
    '[{"action":"propose_patch","args":{}}',
])
def test_ambiguous_or_incomplete_values_are_never_repaired(broken):
    diagnostics = []
    with pytest.raises(ActionFormatError):
        parse_action(broken, diagnostics=diagnostics)
    assert not diagnostics


def test_summary_relocation_does_not_modify_action_parameters():
    action = {"action": "read", "args": {"path": "main.py", "summary": "读取入口"}}
    diagnostics = []
    normalized = parse_action(json.dumps(action), diagnostics=diagnostics)
    assert normalized == {"action": "read", "args": {"path": "main.py"}, "summary": "读取入口"}
    assert len(diagnostics) == 1


@pytest.mark.parametrize("duplicate_closing_brace", [False, True])
async def test_normalized_native_arguments_round_trip_with_automatic_annotation(tmp_path, duplicate_closing_brace):
    before = '#!/usr/bin/env python3\n"""Entry documentation."""\nimport os\n'
    header = ('# 代码用途：保留入口模块的导入行为。\n# 输入文件：无。\n'
              '# 输入说明：无。\n# 输出文件：无。\n# 输出说明：不写入文件。\n')
    after = before.replace('import os\n', header + 'import os\n')
    root = tmp_path / "workspace"
    root.mkdir()
    source = root / "run.py"
    source.write_bytes(before.encode())
    store = Store(tmp_path / "data/state.sqlite3")
    workspace_id, task_id = identifier(), identifier()
    store.execute("INSERT INTO workspaces VALUES(?,?,?)", (workspace_id, str(root), "workspace"))
    store.execute("INSERT INTO tasks(id,session_id,workspace_id,prompt,status,skill,skill_instructions,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                  (task_id, identifier(), workspace_id, "注释整个项目", "queued", ANNOTATION_SKILL,
                   load_skill(ANNOTATION_SKILL), now(), now()))
    responses = deque([
        json.dumps({"action": "read", "args": {"path": "run.py", "summary": "读取入口"}})[:-1],
        json.dumps({"action": "propose_patch", "args": {"changes": [{"path": "run.py", "base_hash": digest(before),
                    "edits": [{"old": "import os\n", "new": header + "import os\n"}]}], "summary": "准备注释补丁"}}) + "}" if duplicate_closing_brace else
        json.dumps({"action": "propose_patch", "args": {"changes": [{"path": "run.py", "base_hash": digest(before),
                    "edits": [{"old": "import os\n", "new": header + "import os\n"}]}], "summary": "准备注释补丁"}})[:-1],
        json.dumps({"action": "final", "args": {"message": "注释已应用。"}, "summary": "完成"}),
    ])
    seen = []

    class NativeModel:
        async def generate(self, messages, emit):
            seen.append(messages)
            response = responses.popleft()
            self.last_tool_call = {"id": f"call-{len(seen)}", "type": "function", "function": {
                "name": "submit_action", "arguments": response}}
            return response

        def close(self):
            pass

    runtime = Runtime(store, Settings(store, persist_secrets=False), NativeModel)
    try:
        await runtime.run(task_id)
        assert store.one("tasks", task_id)["status"] == "completed"
        assert source.read_bytes() == after.encode()
        wire = tool_messages(seen[1])
        assert wire[-1]["role"] == "tool" and wire[-1]["tool_call_id"] == "call-1"
        observation = json.loads(wire[-1]["content"])
        assert observation["content"] == before and observation["hash"] == digest(before)
        assert json.loads(wire[-2]["tool_calls"][0]["function"]["arguments"]) == {
            "action": "read", "args": {"path": "run.py"}, "summary": "读取入口"}
        persisted = json.loads(store.one("tasks", task_id)["messages"])
        for message in persisted:
            if message.get("tool_calls"):
                assert json.loads(message["tool_calls"][0]["function"]["arguments"]) == json.loads(message["content"])
        events = store.events(task_id)
        assert len([e for e in events if e["kind"] == "model.normalized"]) == 2
        assert not any(e["kind"] == "tool.error" for e in events)
        wire = tool_messages(seen[2])
        assert wire[-1]["role"] == "tool" and wire[-1]["tool_call_id"] == "call-2"
        assert json.loads(wire[-1]["content"])["status"] == "applied"
        patch = store.rows("SELECT id FROM patches WHERE task_id=?", (task_id,))[0]
        runtime.patches.apply(patch["id"], undo=True)
        assert source.read_bytes() == before.encode()
    finally:
        await runtime.close()


@pytest.mark.parametrize("tail", ['} {}', '} {"action":"test","args":{}}', '} extra', '}}', ']'])
def test_write_tail_with_anything_beyond_one_redundant_brace_stays_invalid(tail):
    action = {"action": "propose_patch", "args": {"changes": [{"content": "literal } braces"}]}}
    with pytest.raises(ActionFormatError):
        parse_action(json.dumps(action) + tail)


def test_read_hints_locate_each_function_separately_before_its_decorators():
    source = ('"""Module documentation."""\n'
              '@cached()\ndef get_settings():\n    return 1\n\n'
              'def validate_config():\n    return True\n')
    hints = annotation_read_hints("config.py", source)
    assert hints["function_comment_positions"] == [
        {"name": "get_settings", "definition_line": 3, "comment_before_line": 2, "parameters": []},
        {"name": "validate_config", "definition_line": 6, "comment_before_line": 6, "parameters": []},
    ]
