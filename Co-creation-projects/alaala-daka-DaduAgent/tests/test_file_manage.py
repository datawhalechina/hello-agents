"""
文件管理工具单元测试

测试 file_safety 模块、file_manage 工具和 ask_for_answer 工具。
使用 pytest + tempfile。

注意: LangChain 的 @tool 装饰器产生 StructuredTool 对象，
必须通过 .invoke({"param": "value"}) 调用，不能直接当作函数调用。
"""
import os
import sys
import tempfile
import pytest
from unittest.mock import patch

# 确保项目根在 path 中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_tools.file_safety import (
    resolve_safe_path,
    is_within_sandbox,
    is_blocked_pattern,
    is_allowed_write_extension,
    check_file_size,
    is_risky_auto_operation,
    check_max_depth,
    is_manual_mode,
    is_auto_mode,
    get_mode,
    _format_size,
    _get_project_root,
)
from agent_tools.file_manage_tools import (
    file_manage,
    ask_for_answer,
)
from tool.config_handler import FileManage_Config


# ---- 辅助函数 ----

def fm(cmd: str) -> str:
    """便捷调用 file_manage StructuredTool"""
    return file_manage.invoke({"command": cmd})


def afa(question: str) -> str:
    """便捷调用 ask_for_answer StructuredTool"""
    return ask_for_answer.invoke({"question": question})


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_workspace():
    """创建临时工作目录作为测试沙箱"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_allowed = list(FileManage_Config.get("allowed_paths", ["."]))
        FileManage_Config["allowed_paths"] = [tmpdir]
        yield tmpdir
        FileManage_Config["allowed_paths"] = original_allowed


@pytest.fixture
def temp_text_file(temp_workspace):
    """在临时工作区创建一个文本文件"""
    filepath = os.path.join(temp_workspace, "test.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("line 1: hello\nline 2: world\nline 3: foo\nline 4: bar\nline 5: baz\n")
    return filepath


@pytest.fixture
def temp_python_file(temp_workspace):
    """在临时工作区创建一个 Python 文件"""
    filepath = os.path.join(temp_workspace, "script.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\nprint('hello world')\n")
    return filepath


# ============================================================
# _format_size 测试
# ============================================================

def test_format_size_bytes():
    assert _format_size(500) == "500 B"


def test_format_size_kb():
    assert "KB" in _format_size(2048)


def test_format_size_mb():
    assert "MB" in _format_size(3_145_728)


# ============================================================
# resolve_safe_path 测试
# ============================================================

def test_resolve_empty_path():
    abs_path, err = resolve_safe_path("")
    assert abs_path is None
    assert err is not None


def test_resolve_path_traversal():
    abs_path, err = resolve_safe_path("../etc/passwd")
    assert abs_path is None
    assert ".." in err.lower() or "路径遍历" in err


def test_resolve_path_traversal_encoded():
    abs_path, err = resolve_safe_path("foo/../../etc/passwd")
    assert abs_path is None
    assert ".." in err


def test_resolve_normal_relative_path(temp_workspace):
    # 使用临时工作区内的绝对路径测试
    abs_path, err = resolve_safe_path(os.path.join(temp_workspace, "subdir/file.txt"))
    assert abs_path is not None, f"Error was: {err}"
    assert err is None
    assert temp_workspace in abs_path


# ============================================================
# is_within_sandbox 测试
# ============================================================

def test_sandbox_allows_path_within():
    project_root = _get_project_root()
    # 沙箱默认为 uploads/（用户上传文件目录）
    within = os.path.join(project_root, "uploads", "note.txt")
    allowed, _ = is_within_sandbox(within)
    assert allowed is True


def test_default_sandbox_is_uploads_only():
    """安全默认：allowed_paths 仅含 uploads/，不含项目根 '.'"""
    allowed = FileManage_Config.get("allowed_paths", ["."])
    assert "uploads" in allowed
    assert "." not in allowed


def test_file_manage_rejects_outside_sandbox():
    """加固：uploads/ 之外的项目文件（如 config/）必须被 file_manage 拒绝"""
    result = fm("read config/AgentConfig.yml")
    assert "允许的目录" in result or "安全校验" in result


def test_sandbox_rejects_path_outside():
    outside = "C:\\Windows\\System32\\drivers\\etc\\hosts" if os.name == "nt" else "/etc/hosts"
    allowed, _ = is_within_sandbox(outside)
    assert allowed is False


# ============================================================
# is_blocked_pattern 测试
# ============================================================

def test_blocked_pattern_env():
    blocked, pattern = is_blocked_pattern("/some/path/.env")
    assert blocked is True
    assert ".env" in pattern


def test_blocked_pattern_git():
    blocked, _ = is_blocked_pattern("/some/path/.git/config")
    assert blocked is True


def test_blocked_pattern_exe():
    blocked, _ = is_blocked_pattern("/some/path/program.exe")
    assert blocked is True


def test_blocked_pattern_normal_file():
    project_root = _get_project_root()
    normal = os.path.join(project_root, "README.md")
    blocked, _ = is_blocked_pattern(normal)
    assert blocked is False


# ============================================================
# is_allowed_write_extension 测试
# ============================================================

def test_allowed_extension_py():
    ok, ext = is_allowed_write_extension("/path/to/script.py")
    assert ok is True
    assert ext == ".py"


def test_allowed_extension_txt():
    ok, ext = is_allowed_write_extension("/path/to/notes.txt")
    assert ok is True


def test_blocked_extension_exe():
    ok, detail = is_allowed_write_extension("/path/to/virus.exe")
    assert ok is False
    assert ".exe" in detail


def test_blocked_extension_dll():
    ok, _ = is_allowed_write_extension("/path/to/library.dll")
    assert ok is False


# ============================================================
# check_file_size 测试
# ============================================================

def test_file_size_nonexistent():
    ok, detail = check_file_size("/nonexistent/file.txt", 1024)
    assert ok is True


def test_file_size_within_limit(temp_text_file):
    ok, detail = check_file_size(temp_text_file, 1_048_576)
    assert ok is True


def test_file_size_exceeds_limit(temp_text_file):
    ok, detail = check_file_size(temp_text_file, 1)
    assert ok is False


# ============================================================
# is_risky_auto_operation 测试
# ============================================================

def test_risky_auto_delete_directory():
    risky, reason = is_risky_auto_operation("/some/dir", "delete", is_directory=True)
    assert risky is True


def test_risky_auto_delete_file():
    risky, _ = is_risky_auto_operation("/some/file.txt", "delete", is_directory=False)
    assert risky is False


def test_risky_auto_system_prefix():
    risky, _ = is_risky_auto_operation(
        "C:\\Windows\\System32\\file.txt", "write", is_directory=False
    )
    assert risky is True


# ============================================================
# file_manage: read
# ============================================================

def test_file_manage_read_success(temp_text_file):
    result = fm(f"read {temp_text_file}")
    assert "line 1" in result
    assert "line 5" in result


def test_file_manage_read_with_offset(temp_text_file):
    result = fm(f"read {temp_text_file} 2")
    assert "line 3" in result


def test_file_manage_read_with_offset_and_limit(temp_text_file):
    result = fm(f"read {temp_text_file} 1 2")
    assert "line 2" in result
    assert "line 3" in result
    assert "line 4" not in result


def test_file_manage_read_nonexistent(temp_workspace):
    result = fm(f"read {os.path.join(temp_workspace, 'noexist.txt')}")
    assert "不存在" in result


def test_file_manage_read_blocked_path(temp_workspace):
    # 在沙箱内放一个 .env，验证 glob 模式拦截（与沙箱位置无关）
    env = os.path.join(temp_workspace, ".env")
    with open(env, "w", encoding="utf-8") as f:
        f.write("SECRET=1\n")
    result = fm(f"read {env}")
    assert "禁止" in result or "拦截" in result or "被阻止" in result


# ============================================================
# file_manage: write
# ============================================================

def test_file_manage_write_manual_mode_no_approval(temp_workspace):
    """手动模式下不加 --approved 应返回要求批准的信息"""
    target = os.path.join(temp_workspace, "output.txt")
    result = fm(f"write {target} | hello world")
    if is_manual_mode():
        assert (
            "需要用户批准" in result
            or "ask_for_answer" in result
            or "批准" in result
        )


def test_file_manage_write_manual_mode_with_approval(temp_workspace):
    target = os.path.join(temp_workspace, "output_approved.txt")
    result = fm(f"write --approved {target} | hello world")
    # 在 manual 或 auto 模式下都应成功
    assert "成功" in result or "已写入" in result or "写入" in result
    assert os.path.exists(target)


def test_file_manage_write_creates_file(temp_workspace):
    target = os.path.join(temp_workspace, "new_file.md")
    result = fm(f"write --approved {target} | # Hello Markdown")
    assert os.path.exists(target)
    with open(target, "r", encoding="utf-8") as f:
        assert f.read() == "# Hello Markdown"


def test_file_manage_write_blocked_extension(temp_workspace):
    target = os.path.join(temp_workspace, "program.exe")
    result = fm(f"write --approved {target} | fake content")
    # .exe is both blocked in patterns AND not in allowed extensions
    error_found = any(
        word in result for word in ["扩展名", "禁止", "允许", "拦截", "阻止"]
    )
    assert error_found, f"Expected error message, got: {result[:200]}"


def test_file_manage_write_content_too_large(temp_workspace):
    target = os.path.join(temp_workspace, "large.txt")
    huge_content = "x" * 10_000_000  # 10 MB exceeds 5 MB limit
    result = fm(f"write --approved {target} | {huge_content}")
    error_found = any(
        word in result for word in ["超过", "上限", "太大"]
    )
    assert error_found, f"Expected size error, got: {result[:200]}"


# ============================================================
# file_manage: append
# ============================================================

def test_file_manage_append(temp_text_file):
    result = fm(f"append --approved {temp_text_file} | line 6: appended")
    assert "成功" in result or "已追加" in result or "追加" in result
    with open(temp_text_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "line 6: appended" in content
        assert "line 1: hello" in content


# ============================================================
# file_manage: delete
# ============================================================

def test_file_manage_delete_file(temp_workspace):
    target = os.path.join(temp_workspace, "to_delete.txt")
    with open(target, "w", encoding="utf-8") as f:
        f.write("delete me")
    assert os.path.exists(target)

    result = fm(f"delete --approved {target}")
    assert not os.path.exists(target)


def test_file_manage_delete_nonexistent(temp_workspace):
    target = os.path.join(temp_workspace, "noexist.txt")
    result = fm(f"delete --approved {target}")
    assert "不存在" in result


def test_file_manage_delete_directory_rejected(temp_workspace):
    subdir = os.path.join(temp_workspace, "subdir")
    os.makedirs(subdir, exist_ok=True)
    result = fm(f"delete --approved {subdir}")
    assert "目录" in result or "禁止" in result
    assert os.path.exists(subdir)


# ============================================================
# file_manage: mkdir
# ============================================================

def test_file_manage_mkdir_creates_directory(temp_workspace):
    newdir = os.path.join(temp_workspace, "created_dir")
    result = fm(f"mkdir --approved {newdir}")
    assert os.path.isdir(newdir)


def test_file_manage_mkdir_already_exists(temp_workspace):
    subdir = os.path.join(temp_workspace, "existing")
    os.makedirs(subdir, exist_ok=True)
    result = fm(f"mkdir --approved {subdir}")
    assert "已存在" in result


def test_file_manage_mkdir_manual_no_approval(temp_workspace):
    newdir = os.path.join(temp_workspace, "need_approval_dir")
    result = fm(f"mkdir {newdir}")
    if is_manual_mode():
        assert (
            "需要用户批准" in result
            or "ask_for_answer" in result
            or "批准" in result
        )
        assert not os.path.exists(newdir)


# ============================================================
# file_manage: list
# ============================================================

def test_file_manage_list_directory(temp_text_file):
    result = fm(f"list {os.path.dirname(temp_text_file)}")
    assert "test.txt" in result


def test_file_manage_list_with_pattern(temp_text_file, temp_python_file):
    d = os.path.dirname(temp_text_file)
    result = fm(f"list {d} *.py")
    assert "script.py" in result
    assert "test.txt" not in result


# ============================================================
# file_manage: info
# ============================================================

def test_file_manage_info_file(temp_text_file):
    result = fm(f"info {temp_text_file}")
    assert "文件" in result or "类型" in result


def test_file_manage_info_nonexistent(temp_workspace):
    result = fm(f"info {os.path.join(temp_workspace, 'ghost.txt')}")
    assert "不存在" in result


# ============================================================
# file_manage: exists
# ============================================================

def test_file_manage_exists_true(temp_text_file):
    result = fm(f"exists {temp_text_file}")
    assert "存在" in result


def test_file_manage_exists_false(temp_workspace):
    result = fm(f"exists {os.path.join(temp_workspace, 'ghost.txt')}")
    assert "不存在" in result


# ============================================================
# file_manage: search
# ============================================================

def test_file_manage_search_py_files(temp_text_file, temp_python_file):
    d = os.path.dirname(temp_text_file)
    result = fm(f"search *.py {d}")
    assert "script.py" in result


def test_file_manage_search_no_matches(temp_text_file):
    d = os.path.dirname(temp_text_file)
    result = fm(f"search *.rs {d}")
    assert "未找到" in result


# ============================================================
# file_manage: 未知命令 & 空命令
# ============================================================

def test_file_manage_unknown_command():
    result = fm("unknown_cmd arg")
    assert "未知操作" in result


def test_file_manage_empty_command():
    result = fm("")
    assert "用法" in result or "read" in result


# ============================================================
# ask_for_answer 工具测试
# ============================================================

def test_ask_for_answer_returns_input():
    with patch("builtins.input", return_value="yes"):
        result = afa("test question?")
        assert "yes" in result


def test_ask_for_answer_handles_no():
    with patch("builtins.input", return_value="no"):
        result = afa("confirm delete?")
        assert "no" in result


def test_ask_for_answer_handles_eof():
    with patch("builtins.input", side_effect=EOFError):
        result = afa("test?")
        assert "取消" in result or "拒绝" in result


# ============================================================
# 集成测试: 完整的手动模式批准流程
# ============================================================

def test_manual_mode_approval_flow(temp_workspace):
    """模拟完整的批准流程"""
    if not is_manual_mode():
        pytest.skip("仅在手动模式下运行此测试")

    target = os.path.join(temp_workspace, "integration_test.txt")

    # 步骤 1: 不加 --approved 尝试写入
    result1 = fm(f"write {target} | integration content")
    assert (
        "需要用户批准" in result1
        or "ask_for_answer" in result1
        or "批准" in result1
    )
    assert not os.path.exists(target)

    # 步骤 2: 模拟 ask_for_answer
    with patch("builtins.input", return_value="yes"):
        answer = afa(f"Allow write to {target}?")
    assert "yes" in answer

    # 步骤 3: 带 --approved 重试
    result2 = fm(f"write --approved {target} | integration content")
    assert os.path.exists(target)

    # 验证内容
    with open(target, "r", encoding="utf-8") as f:
        assert f.read() == "integration content"


# ============================================================
# 安全测试: 路径遍历攻击
# ============================================================

def test_path_traversal_in_read():
    result = fm("read ../../../etc/passwd")
    error_keywords = ["阻止", "遍历", "..", "禁止", "拦截", "不允许"]
    assert any(kw in result for kw in error_keywords), f"Got: {result[:200]}"


def test_path_traversal_in_write():
    result = fm("write --approved ../../../etc/hosts | evil")
    error_keywords = ["阻止", "遍历", "..", "禁止", "拦截", "不允许"]
    assert any(kw in result for kw in error_keywords), f"Got: {result[:200]}"


# ============================================================
# 配置模式检测
# ============================================================

def test_get_mode_returns_valid_mode():
    mode = get_mode()
    assert mode in ("manual", "auto")


def test_is_manual_and_auto_are_exclusive():
    assert is_manual_mode() != is_auto_mode()
