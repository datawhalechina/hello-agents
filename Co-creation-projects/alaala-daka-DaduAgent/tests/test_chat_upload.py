"""
对话内文件上传测试
==================
覆盖：
  1. build_file_note / strip_file_note 注释块协议（前后端共用）
  2. Agent.stream 的 file_paths 隐式注入（不联网，用 FakeGraph 替换真实 graph）
  3. POST /api/files/chat-upload 端点的正常/超限/扩展名/同名去重分支
  4. api/chat.py _coerce_files 入站 files 字段规整
"""
import asyncio
import io

import pytest
from fastapi import UploadFile
from fastapi.exceptions import HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from Agent import Agent, build_file_note, strip_file_note
from api.files import api_chat_upload_file
from api.chat import _coerce_files


# ── 注释块协议 ──

def test_build_and_strip_file_note_roundtrip():
    note = build_file_note(["uploads/a.txt"])
    assert note == "[已上传文件]\n- uploads/a.txt\n[/已上传文件]"
    assert strip_file_note(note) == ""


def test_strip_file_note_removes_block_from_text():
    text = "read this\n\n[已上传文件]\n- uploads/a.txt\n[/已上传文件]"
    assert strip_file_note(text) == "read this"


# ── Agent.stream file_paths 注入 ──

class CaptureGraph:
    """记录 stream() 传入的 messages 快照，并 yield 一个带 AI 回复的快照"""

    def __init__(self):
        self.seen: list[list] = []

    def stream(self, state, stream_mode="values"):
        msgs = list(state["messages"])
        self.seen.append(msgs)
        yield {"messages": msgs + [AIMessage(content="好的，我来处理。")]}


def test_stream_injects_file_note_with_query():
    a = Agent()
    g = CaptureGraph()
    a.agent = g

    outputs = list(a.stream("请读取", file_paths=["uploads/a.txt"]))
    assert outputs == ["好的，我来处理。\n"]

    human = g.seen[0][-1]
    assert isinstance(human, HumanMessage)
    assert "请读取" in human.content
    assert "[已上传文件]" in human.content
    assert "uploads/a.txt" in human.content


def test_stream_attachment_only_builds_bare_note():
    a = Agent()
    g = CaptureGraph()
    a.agent = g

    list(a.stream("", file_paths=["uploads/a.txt"]))
    human = g.seen[0][-1]
    assert human.content == "[已上传文件]\n- uploads/a.txt\n[/已上传文件]"


def test_stream_empty_noop_regression():
    a = Agent()
    g = CaptureGraph()
    a.agent = g

    assert list(a.stream("   ")) == []
    assert a.messages == []
    assert g.seen == []


def test_stream_filters_blank_file_paths():
    a = Agent()
    g = CaptureGraph()
    a.agent = g

    list(a.stream("x", file_paths=["uploads/a.txt", "   ", ""]))
    human = g.seen[0][-1]
    assert "uploads/a.txt" in human.content
    assert "uploads/b.txt" not in human.content


# ── POST /api/files/chat-upload 端点 ──

def test_chat_upload_saves_copy_without_rag(tmp_path, monkeypatch):
    monkeypatch.setattr("api.files.UPLOAD_DIR", str(tmp_path))
    resp = asyncio.run(api_chat_upload_file(
        UploadFile(file=io.BytesIO(b"hello"), filename="note.txt")
    ))
    assert resp["file_name"] == "note.txt"
    assert resp["path"] == "uploads/note.txt"      # 项目根相对，沙箱内
    assert resp["size"] == 5
    assert "chunks" not in resp                      # 未进 RAG
    assert (tmp_path / "note.txt").read_bytes() == b"hello"


def test_chat_upload_rejects_over_10mb(tmp_path, monkeypatch):
    monkeypatch.setattr("api.files.UPLOAD_DIR", str(tmp_path))
    uf = UploadFile(file=io.BytesIO(b"x" * (10 * 1024 * 1024)), filename="big.txt")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(api_chat_upload_file(uf))
    assert ei.value.status_code == 400
    assert "10MB" in ei.value.detail


def test_chat_upload_rejects_bad_extension(tmp_path, monkeypatch):
    monkeypatch.setattr("api.files.UPLOAD_DIR", str(tmp_path))
    uf = UploadFile(file=io.BytesIO(b"evil"), filename="evil.exe")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(api_chat_upload_file(uf))
    assert ei.value.status_code == 400


def test_chat_upload_dedups_same_name(tmp_path, monkeypatch):
    monkeypatch.setattr("api.files.UPLOAD_DIR", str(tmp_path))
    r1 = asyncio.run(api_chat_upload_file(
        UploadFile(file=io.BytesIO(b"one"), filename="note.txt")))
    r2 = asyncio.run(api_chat_upload_file(
        UploadFile(file=io.BytesIO(b"two"), filename="note.txt")))
    assert r1["path"] == "uploads/note.txt"
    assert r2["path"].startswith("uploads/note_")
    assert r1["path"] != r2["path"]
    names = {p.name for p in tmp_path.iterdir()}
    assert "note.txt" in names
    assert any(n.startswith("note_") for n in names)


# ── WS files 字段规整 ──

def test_coerce_files_filters_blanks_and_errors():
    assert _coerce_files(["a.txt", " ", "b.txt", 3, None]) == ["a.txt", "b.txt"]
    assert _coerce_files("notalist") == []
    assert _coerce_files(None) == []


def test_coerce_files_caps_at_10():
    assert len(_coerce_files([f"f{i}.txt" for i in range(15)])) == 10
