"""
会话管理测试
===========
测试 session_store（持久化）、session 工具、以及 Agent 会话集成。
遵循 tests/test_file_manage.py 的测试模式。
"""
import pytest
import tempfile
import os
import json

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from session.session_store import (
    serialize_message, deserialize_message,
    save_session_messages, load_session_messages,
    list_sessions, delete_session, get_session_info, session_exists,
    save_session_todos, load_session_todos,
    save_session_title, load_session_title, truncate_title,
    _sanitize_session_id
)
from tool.config_handler import Session_Config, System_Config


# ═══════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def temp_sessions_dir():
    """将会话目录指向临时目录，测试结束后恢复"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = Session_Config.get("sessions_dir", "sessions")
        Session_Config["sessions_dir"] = tmpdir
        yield tmpdir
        Session_Config["sessions_dir"] = original_dir


# ═══════════════════════════════════════════════════════════
#  序列化测试
# ═══════════════════════════════════════════════════════════

class TestSerialization:
    """消息序列化/反序列化测试"""

    def test_serialize_human_dict(self):
        """用户 dict 消息序列化"""
        msg = {"role": "user", "content": "你好"}
        record = serialize_message(msg)
        assert record["type"] == "human"
        assert record["content"] == "你好"

    def test_serialize_human_message(self):
        """HumanMessage 对象序列化"""
        msg = HumanMessage(content="你好世界")
        record = serialize_message(msg)
        assert record["type"] == "human"
        assert record["content"] == "你好世界"

    def test_serialize_ai_message(self):
        """AIMessage 对象序列化"""
        msg = AIMessage(content="这是回复")
        record = serialize_message(msg)
        assert record["type"] == "ai"
        assert record["content"] == "这是回复"

    def test_serialize_ai_message_with_tool_calls(self):
        """带 tool_calls 的 AIMessage 序列化"""
        msg = AIMessage(content="", tool_calls=[{"name": "search", "args": {"query": "test"}, "id": "call_1"}])
        record = serialize_message(msg)
        assert record["type"] == "ai"
        assert "tool_calls" in record
        assert len(record["tool_calls"]) == 1

    def test_serialize_tool_message(self):
        """ToolMessage 对象序列化"""
        msg = ToolMessage(content="搜索结果", tool_call_id="call_1", name="search")
        record = serialize_message(msg)
        assert record["type"] == "tool"
        assert record["content"] == "搜索结果"
        assert record["tool_call_id"] == "call_1"
        assert record["name"] == "search"

    def test_serialize_system_message(self):
        """SystemMessage 对象序列化"""
        msg = SystemMessage(content="系统提示")
        record = serialize_message(msg)
        assert record["type"] == "system"
        assert record["content"] == "系统提示"

    def test_deserialize_human(self):
        """反序列化为用户 dict"""
        record = {"type": "human", "content": "问题"}
        msg = deserialize_message(record)
        assert isinstance(msg, dict)
        assert msg["role"] == "user"
        assert msg["content"] == "问题"

    def test_deserialize_ai(self):
        """反序列化为 AIMessage"""
        record = {"type": "ai", "content": "回答"}
        msg = deserialize_message(record)
        assert isinstance(msg, AIMessage)
        assert msg.content == "回答"

    def test_deserialize_tool(self):
        """反序列化为 ToolMessage"""
        record = {"type": "tool", "content": "结果", "tool_call_id": "call_x", "name": "calculator"}
        msg = deserialize_message(record)
        assert isinstance(msg, ToolMessage)
        assert msg.content == "结果"
        assert msg.tool_call_id == "call_x"

    def test_deserialize_system(self):
        """反序列化为 SystemMessage"""
        record = {"type": "system", "content": "提示"}
        msg = deserialize_message(record)
        assert isinstance(msg, SystemMessage)
        assert msg.content == "提示"

    def test_deserialize_unknown_type_fallback(self):
        """未知类型回退为 human dict"""
        record = {"type": "unknown_type", "content": "something"}
        msg = deserialize_message(record)
        assert isinstance(msg, dict)
        assert msg["role"] == "user"

    def test_deserialize_todo_returns_none(self):
        """__todo__ 记录反序列化为 None（非对话消息，不应被加载为消息）"""
        record = {"type": "__todo__", "todos": [], "todo_counter": 0}
        msg = deserialize_message(record)
        assert msg is None

    def test_roundtrip_mixed_messages(self, temp_sessions_dir):
        """混合消息类型保存-加载往返测试"""
        messages = [
            {"role": "user", "content": "查询"},
            AIMessage(content="思考", tool_calls=[{"name": "search", "args": {"query": "x"}, "id": "c1"}]),
            ToolMessage(content="搜索结果", tool_call_id="c1", name="search"),
            AIMessage(content="最终回答"),
        ]
        save_session_messages("test_roundtrip", messages)
        loaded = load_session_messages("test_roundtrip")
        assert loaded is not None
        assert len(loaded) == 4
        assert loaded[0]["content"] == "查询"
        assert isinstance(loaded[1], AIMessage)
        assert isinstance(loaded[2], ToolMessage)
        assert isinstance(loaded[3], AIMessage)


# ═══════════════════════════════════════════════════════════
#  会话存储 CRUD 测试
# ═══════════════════════════════════════════════════════════

class TestSessionStore:
    """会话文件 CRUD 测试"""

    def test_save_and_load(self, temp_sessions_dir):
        """保存和加载会话消息"""
        messages = [{"role": "user", "content": "hello"}]
        save_session_messages("test_session", messages)

        loaded = load_session_messages("test_session")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]["content"] == "hello"

    def test_load_nonexistent(self, temp_sessions_dir):
        """加载不存在的会话返回 None"""
        result = load_session_messages("nonexistent")
        assert result is None

    def test_list_sessions(self, temp_sessions_dir):
        """列出所有会话"""
        save_session_messages("session_a", [{"role": "user", "content": "a"}])
        save_session_messages("session_b", [{"role": "user", "content": "b"}])

        sessions = list_sessions()
        assert len(sessions) >= 2
        ids = [s["session_id"] for s in sessions]
        assert "session_a" in ids
        assert "session_b" in ids

    def test_delete_session(self, temp_sessions_dir):
        """删除会话"""
        save_session_messages("to_delete", [{"role": "user", "content": "x"}])
        assert session_exists("to_delete")

        result = delete_session("to_delete")
        assert result is True
        assert not session_exists("to_delete")

    def test_delete_nonexistent(self, temp_sessions_dir):
        """删除不存在的会话返回 False"""
        result = delete_session("no_such_session")
        assert result is False

    def test_session_exists(self, temp_sessions_dir):
        """检查会话是否存在"""
        assert not session_exists("new_one")
        save_session_messages("new_one", [])
        assert session_exists("new_one")

    def test_get_session_info(self, temp_sessions_dir):
        """获取会话信息"""
        save_session_messages("info_test", [{"role": "user", "content": "x"}])
        info = get_session_info("info_test")
        assert info is not None
        assert info["session_id"] == "info_test"
        assert info["message_count"] == 1
        assert "created_at" in info
        assert "updated_at" in info
        assert "size_bytes" in info

    def test_get_session_info_nonexistent(self, temp_sessions_dir):
        """获取不存在的会话信息返回 None"""
        info = get_session_info("no_info")
        assert info is None

    def test_sanitize_session_id(self):
        """session_id 清洁化"""
        assert _sanitize_session_id("normal_id") == "normal_id"
        assert _sanitize_session_id("path/traversal") == "path_traversal"
        assert _sanitize_session_id("special:chars*test") == "special_chars_test"
        assert _sanitize_session_id("") == "default"  # 空字符串回退

    def test_empty_session_loads_empty_list(self, temp_sessions_dir):
        """空会话文件加载为 []"""
        save_session_messages("empty_session", [])
        loaded = load_session_messages("empty_session")
        assert loaded == []

    def test_user_message_count_counts_nonempty_human_only(self, temp_sessions_dir):
        """user_message_count 只统计内容非空的用户消息；message_count 仍为原始记录数"""
        save_session_messages("user_count", [
            {"role": "user", "content": "q1"},
            {"type": "human", "role": "user", "content": ""},  # 历史遗留空记录，不计入
            AIMessage(content="这是回复"),
            {"role": "user", "content": "q2"},
        ])
        info = get_session_info("user_count")
        assert info["message_count"] == 4
        assert info["user_message_count"] == 2

    def test_list_sessions_title_fallback_truncated(self, temp_sessions_dir):
        """无存储标题时，title 回退为第一条用户消息的截断（且不含哈希）"""
        first = "帮我写一个Python爬虫脚本抓取网页数据并输出到Excel文件"
        save_session_messages("fallback_sess", [{"role": "user", "content": first}])
        sessions = list_sessions()
        entry = next(s for s in sessions if s["session_id"] == "fallback_sess")
        assert entry["title"] == truncate_title(first)
        assert entry["user_message_count"] == 1
        assert all(ch not in entry["title"] for ch in "fallback_sess")

    def test_title_uses_stored_title_over_truncation(self, temp_sessions_dir):
        """存储标题优先于截断回退"""
        save_session_messages("titled", [{"role": "user", "content": "很长的一条消息" * 10}])
        save_session_title("titled", "已存标题")
        info = get_session_info("titled")
        assert info["title"] == "已存标题"
        sessions = list_sessions()
        entry = next(s for s in sessions if s["session_id"] == "titled")
        assert entry["title"] == "已存标题"

    def test_title_empty_for_empty_session(self, temp_sessions_dir):
        """空会话（无用户消息）title 为 ''"""
        save_session_messages("empty_title", [])
        info = get_session_info("empty_title")
        assert info["title"] == ""

    def test_save_and_load_title_roundtrip(self, temp_sessions_dir):
        """标题 sidecar 保存/加载往返；缺失返回空字符串"""
        assert load_session_title("missing_meta") == ""
        save_session_title("meta_sess", "Python 爬虫")
        assert load_session_title("meta_sess") == "Python 爬虫"

    def test_truncate_title(self):
        """truncate_title 截断、压平空白、空输入返回 ''"""
        assert truncate_title("中" * 25) == "中" * 20
        assert truncate_title("多  个空格\n换行") == "多 个空格 换行"
        assert truncate_title("") == ""
        assert truncate_title("   \n ") == ""

    def test_meta_sidecar_not_listed_as_session(self, temp_sessions_dir):
        """只有 sidecar 文件不构成会话"""
        save_session_title("orphan_meta", "孤立标题")
        ids = [s["session_id"] for s in list_sessions()]
        assert "orphan_meta" not in ids

    def test_delete_session_removes_meta_sidecar(self, temp_sessions_dir):
        """删除会话同时清理标题 sidecar"""
        save_session_messages("del_meta", [{"role": "user", "content": "x"}])
        save_session_title("del_meta", "要删的标题")
        assert delete_session("del_meta")
        assert load_session_title("del_meta") == ""


# ═══════════════════════════════════════════════════════════
#  Todo 状态持久化测试
# ═══════════════════════════════════════════════════════════

class TestTodoPersistence:
    """Todo 状态与会话关联持久化测试"""

    def test_save_and_load_todos(self, temp_sessions_dir):
        """保存和加载 todo 状态"""
        todos = [
            {"id": 1, "title": "任务1", "desc": "", "status": "pending",
             "created_at": "07-30 14:00", "done_at": None},
        ]
        save_session_messages("todo_session", [{"role": "user", "content": "hi"}])
        save_session_todos("todo_session", todos, 5)

        result = load_session_todos("todo_session")
        assert result is not None
        loaded_todos, counter = result
        assert len(loaded_todos) == 1
        assert loaded_todos[0]["title"] == "任务1"
        assert counter == 5

    def test_load_todos_nonexistent(self, temp_sessions_dir):
        """加载不存在会话的 todo 返回 None"""
        result = load_session_todos("no_todos")
        assert result is None

    def test_todos_not_affect_message_count(self, temp_sessions_dir):
        """__todo__ 记录不计入消息计数"""
        save_session_messages("count_test", [
            {"role": "user", "content": "msg1"},
            {"role": "user", "content": "msg2"},
        ])
        save_session_todos("count_test", [{"id": 1, "title": "t"}], 1)

        info = get_session_info("count_test")
        assert info["message_count"] == 2  # 不包括 __todo__ 行

    def test_load_skips_todo_and_empty_human(self, temp_sessions_dir):
        """加载时跳过 __todo__ 记录与历史遗留的空用户消息，避免产生空气泡"""
        save_session_messages("legacy", [
            {"role": "user", "content": "真实问题"},
            {"type": "human", "role": "user", "content": ""},  # 历史遗留空记录
        ])
        save_session_todos("legacy", [{"id": 1, "title": "t"}], 1)

        loaded = load_session_messages("legacy")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]["content"] == "真实问题"


# ═══════════════════════════════════════════════════════════
#  Session Tool 测试（通过 Agent 集成）
# ═══════════════════════════════════════════════════════════

class TestSessionTool:
    """session 工具子命令分发测试"""

    @pytest.fixture(autouse=True)
    def setup_agent(self, temp_sessions_dir):
        """为工具测试创建 Agent 实例"""
        from Agent import Agent
        self.agent = Agent()
        # 确保有活跃会话
        if not self.agent.session_id:
            self.agent.new_session("tool_test")

    def _sess(self, cmd: str) -> str:
        """便捷调用 session 工具"""
        from agent_tools.session_tool import session
        return session.invoke({"command": cmd})

    def test_list_empty(self):
        """列出会话 — 应该至少有当前会话"""
        result = self._sess("list")
        assert "会话" in result
        assert self.agent.session_id in result

    def test_info_current(self):
        """查看当前会话信息"""
        result = self._sess("info")
        assert self.agent.session_id in result
        assert "消息数" in result

    def test_info_specific(self):
        """查看指定会话信息"""
        result = self._sess(f"info {self.agent.session_id}")
        assert self.agent.session_id in result

    def test_current(self):
        """显示当前会话 ID"""
        result = self._sess("current")
        assert self.agent.session_id in result

    def test_create(self):
        """创建新会话"""
        result = self._sess("create 测试创建")
        assert "已创建" in result

    def test_save(self):
        """手动保存"""
        result = self._sess("save")
        assert "已保存" in result

    def test_delete_rejects_current(self):
        """不能删除当前活跃会话"""
        result = self._sess(f"delete {self.agent.session_id}")
        assert "无法删除" in result or "不存在" in result

    def test_switch_nonexistent(self):
        """切换到不存在的会话"""
        result = self._sess("switch no_such_session_xyz")
        assert "不存在" in result

    def test_unknown_command(self):
        """未知命令返回错误"""
        result = self._sess("invalid_cmd")
        assert "未知操作" in result

    def test_empty_command(self):
        """空命令返回帮助"""
        result = self._sess("")
        assert "会话" in result


# ═══════════════════════════════════════════════════════════
#  会话标题生成测试（不发起真实 LLM 调用）
# ═══════════════════════════════════════════════════════════

class _FailingModel:
    """模拟 LLM 故障的假模型"""
    def invoke(self, *args, **kwargs):
        raise RuntimeError("模拟 LLM 故障")


class _FakeGraph:
    """模拟 langchain graph：stream() 产出 messages 快照"""
    def __init__(self, messages):
        self._messages = messages

    def stream(self, messages, stream_mode="values"):
        yield {"messages": self._messages}


class TestAgentTitle:
    """会话标题生成与持久化测试"""

    @pytest.fixture(autouse=True)
    def setup_agent(self, temp_sessions_dir, monkeypatch):
        """创建 Agent 实例，并用故障模型替代 chatmodel（不发真实请求）"""
        from Agent import Agent
        monkeypatch.setattr("Agent.chatmodel", _FailingModel())
        self.agent = Agent()
        if not self.agent.session_id:
            self.agent.new_session("title_test")

    def test_ensure_session_title_falls_back_to_truncation(self):
        """LLM 失败时回退为截断标题，且重复调用不改变已存标题"""
        self.agent.messages = [{"role": "user", "content": "帮我写一个Python爬虫脚本抓取网页数据"}]
        self.agent._ensure_session_title()
        title = load_session_title(self.agent.session_id)
        assert title == truncate_title("帮我写一个Python爬虫脚本抓取网页数据")
        assert len(title) <= 20
        # 幂等：再次调用不改变标题
        self.agent._ensure_session_title()
        assert load_session_title(self.agent.session_id) == title

    def test_stream_generates_title_on_first_turn(self):
        """stream() 首轮对话完成后生成并持久化标题"""
        first_msg = "帮我写爬虫"
        self.agent.agent = _FakeGraph([
            HumanMessage(content=first_msg),
            AIMessage(content="好的，我来帮你。"),
        ])
        outputs = list(self.agent.stream(first_msg))
        assert outputs  # 有产出
        assert load_session_title(self.agent.session_id) == truncate_title(first_msg)
