"""
RAG 知识库上传管道单元测试

测试 file_handler 的扩展名支持判断、load_document 分发，以及 file_uploader
的分批生成器。全部无网络：加载器通过 monkeypatch 替换，或使用真实临时文本文件。

注意: 不要直接构造 File_Uploader()（会触发 __init__ 连接 Chroma、创建模型），
一律使用 File_Uploader.__new__(File_Uploader) 绕过构造。导入本模块会构建
模块级单例 _file_upload_service（本地 SQLite，无网络），属预期行为。
"""
import os
import sys

import pytest
from langchain_core.documents import Document

# 确保项目根在 path 中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tool import file_handler
from tool.config_handler import Rag_Config
from tool.file_handler import (
    get_supported_extensions,
    is_supported_extension,
    load_document,
)
from vector_uploader_service import file_uploader
from vector_uploader_service.file_uploader import File_Uploader


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def rag_extensions():
    """快照并恢复 Rag_Config 的 support_extensions 配置"""
    had_key = "support_extensions" in Rag_Config
    original = list(Rag_Config.get("support_extensions", []))
    yield
    if had_key:
        Rag_Config["support_extensions"] = original
    else:
        Rag_Config.pop("support_extensions", None)


def make_uploader():
    """绕过 __init__ 构造 File_Uploader（避免连接 Chroma / 创建模型）"""
    return File_Uploader.__new__(File_Uploader)


# ============================================================
# get_supported_extensions / is_supported_extension
# ============================================================

def test_get_supported_extensions_normalizes(rag_extensions):
    Rag_Config["support_extensions"] = [".TXT", "md", ".md", ".py"]
    assert get_supported_extensions() == [".txt", ".md", ".py"]


def test_get_supported_extensions_missing_key(rag_extensions):
    Rag_Config.pop("support_extensions", None)
    assert get_supported_extensions() == [".txt", ".pdf"]


def test_is_supported_extension_case_insensitive(rag_extensions):
    Rag_Config["support_extensions"] = [".txt", ".md", ".pdf", ".docx"]
    assert is_supported_extension("README.MD")
    assert is_supported_extension("notes.TXT")
    assert not is_supported_extension("virus.exe")
    assert not is_supported_extension("noextension")


# ============================================================
# load_document 分发
# ============================================================

def test_load_document_text_family_real_files(rag_extensions, tmp_path):
    Rag_Config["support_extensions"] = [".txt", ".md", ".py"]
    cases = {
        "note.txt": "hello world",
        "doc.md": "# Title\nbody",
        "main.py": "print('hi')",
    }
    for fname, content in cases.items():
        p = tmp_path / fname
        p.write_text(content, encoding="utf-8")
        docs = load_document(str(p))
        assert docs is not None
        assert docs[0].page_content == content


def test_load_document_pdf_dispatch(rag_extensions, monkeypatch):
    sentinel = [Document(page_content="pdf-content")]
    monkeypatch.setattr(file_handler, "pdfloader", lambda p: sentinel)
    assert load_document("doc.pdf") is sentinel


def test_load_document_docx_dispatch(rag_extensions, monkeypatch):
    sentinel = [Document(page_content="docx-content")]
    monkeypatch.setattr(file_handler, "docxloader", lambda p: sentinel)
    assert load_document("doc.docx") is sentinel


def test_load_document_unsupported_returns_none(rag_extensions):
    Rag_Config["support_extensions"] = [".txt"]
    assert load_document("foo.exe") is None
    assert load_document("foo.pdf") is None  # 配置把关覆盖硬编码扩展名分支
    assert load_document("foo.md") is None


# ============================================================
# 分批生成器
# ============================================================

def test_iter_txt_batches(tmp_path):
    uploader = make_uploader()
    content = "\n".join(f"line {i}" for i in range(50))
    p = tmp_path / "big.txt"
    p.write_text(content, encoding="utf-8")
    batches = list(uploader._iter_txt_batches(str(p), chars_per_batch=100))
    assert batches
    assert "".join(batches) == content


def test_iter_docx_batches(monkeypatch):
    uploader = make_uploader()
    sentinel = [Document(page_content="a" * 5000)]
    monkeypatch.setattr(file_uploader, "docxloader", lambda p: sentinel)
    batches = list(uploader._iter_docx_batches("doc.docx", chars_per_batch=1000))
    assert len(batches) == 5
    assert all(len(b) == 1000 for b in batches)
    assert "".join(batches) == "a" * 5000


def test_iter_pdf_batches(monkeypatch):
    uploader = make_uploader()
    pages = [Document(page_content=f"page {i}") for i in range(7)]
    monkeypatch.setattr(file_uploader, "pdfloader", lambda p: pages)
    batches = list(uploader._iter_pdf_batches("doc.pdf", pages_per_batch=3))
    assert len(batches) == 3
    assert batches[0] == "page 0\npage 1\npage 2"
    assert batches[1] == "page 3\npage 4\npage 5"
    assert batches[2] == "page 6"
