"""Known multi-conversation exports retain isolated identities and root metadata."""
import json

import pytest

from test_platform_export_compatibility import (
    commit_and_repeat,
    forbid_import_network_and_analysis,
    stored_contexts,
)


@pytest.mark.parametrize("wrapper", ["chats", "conversations", "sessions"])
def test_multi_conversation_wrappers_preserve_native_identity_domains_and_complete_context(client, wrapper):
    original = {"id": 0, "time": "2026-11-12 09:00:00", "sender": "虚构同事", "content": "接口开发安排在周三"}
    conversations = [{"id": f"chat-{name}", "name": f"虚构会话{name}", "platform": "wechat",
                      "session_note": f"SYNTHETIC_SESSION_NOTE_{name}", "messages": [dict(original)]} for name in ("A", "B")]
    preview = commit_and_repeat(client, json.dumps({wrapper: conversations}, ensure_ascii=False), expected=2)
    messages = preview["messages"]
    assert {message["chat_id"] for message in messages} == {"chat-A", "chat-B"}
    assert len({message["id"] for message in messages}) == 2
    assert all(message["source_type"] == "wechat" and message["metadata"]["raw"] == original for message in messages)
    contexts = stored_contexts(client)
    assert len(contexts) == 2
    stored = {item["context"]["conversation"]["id"]: item for item in contexts}
    for message, conversation in zip(messages, conversations):
        context = stored[conversation["id"]]
        assert message["metadata"]["import"]["source_context_hash"] == context["context_hash"]
        assert context["context"]["conversation"] == {key: value for key, value in conversation.items() if key != "messages"}


def test_single_session_wrapper_preserves_explicit_session_fields(client):
    session = {"id": "single-chat", "name": "虚构单会话", "note": "SYNTHETIC_SINGLE_SESSION_CONTEXT"}
    row = {"id": 0, "time": "2026-11-12 09:00:00", "sender": "虚构同事", "content": "接口开发安排在周三"}
    envelope = {"session": session, "platform": "wechat", "messages": [row]}
    preview = commit_and_repeat(client, json.dumps(envelope, ensure_ascii=False))
    message = preview["messages"][0]
    assert message["source_type"] == "wechat" and message["chat_id"] == "single-chat"
    assert message["metadata"]["raw"] == row
    contexts = stored_contexts(client)
    assert len(contexts) == 1 and contexts[0]["context"]["conversation"] == session
    assert message["metadata"]["import"]["source_context_hash"] == contexts[0]["context_hash"]
