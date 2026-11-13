"""Check the PDF-loading example and both tutorial snippets without services.

Run with the chapter's hello-agents==0.2.0 dependency:
    python -m unittest discover -s code/chapter8/tests -v
"""

import ast
import os
import re
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import Mock

from hello_agents.tools import RAGTool


ROOT = Path(__file__).resolve().parents[3]


def load_examples():
    """Extract the actual methods without importing the Gradio UI."""
    source = ROOT / "code/chapter8/11_Q&A_Assistant.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    assistant = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                     and node.name == "PDFLearningAssistant")
    method = next(node for node in assistant.body if isinstance(node, ast.FunctionDef)
                  and node.name == "load_document")
    methods = {source.name: method}
    for name in ("第八章 记忆与检索.md", "Chapter8-Memory-and-Retrieval.md"):
        text = (ROOT / "docs/chapter8" / name).read_text(encoding="utf-8")
        snippet = next(block for block in re.findall(r"```python\n(.*?)```", text, re.S)
                       if block.startswith("def load_document("))
        methods[name] = ast.parse(snippet).body[0]
    examples = {}
    for name, method in methods.items():
        namespace = {"os": os, "time": time, "Dict": Dict, "Any": Any}
        module = ast.Module(body=[method], type_ignores=[])
        exec(compile(module, name, "exec"), namespace)
        examples[name] = namespace["load_document"]
    return examples


def make_rag(mode):
    """Use real RAG dispatch/results with a controlled ingestion boundary."""
    rag = RAGTool.__new__(RAGTool)
    rag.initialized = mode != "uninitialized"
    rag.init_error = "test initialization failure"
    rag.rag_namespace = "default"

    def add_documents(**kwargs):
        if mode == "pipeline_error":
            raise ValueError("test ingestion failure")
        return 0 if mode == "zero_chunks" else 2

    rag._pipelines = {"default": {"add_documents": add_documents, "namespace": "default"}}
    return rag


class PDFLoadResultTests(unittest.TestCase):
    def test_load_results_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "new.pdf"
            pdf.write_bytes(b"fixture: ingestion is controlled by the test")
            for name, load_document in load_examples().items():
                for mode in ("uninitialized", "pipeline_error", "zero_chunks", "success", "missing"):
                    for previous in (None, "previous.pdf"):
                        with self.subTest(example=name, mode=mode, previous=previous):
                            memory = Mock()
                            initial_count = 1 if previous else 0
                            app = SimpleNamespace(
                                rag_tool=make_rag(mode), memory_tool=memory,
                                current_document=previous,
                                stats={"documents_loaded": initial_count}, session_id="test",
                            )
                            path = str(pdf) if mode != "missing" else str(pdf.with_name("missing.pdf"))
                            result = load_document(app, path)
                            self.assertEqual(result["success"], mode == "success")
                            if mode == "success":
                                self.assertEqual(app.current_document, pdf.name)
                                self.assertEqual(app.stats["documents_loaded"], initial_count + 1)
                                self.assertEqual(len(memory.mock_calls), 1)
                            else:
                                self.assertEqual(app.current_document, previous)
                                self.assertEqual(app.stats["documents_loaded"], initial_count)
                                self.assertEqual(memory.mock_calls, [])
                                self.assertTrue(result["message"])
                                if mode == "uninitialized":
                                    self.assertIn("test initialization failure", result["message"])
                                elif mode == "pipeline_error":
                                    self.assertIn("test ingestion failure", result["message"])
                                elif mode == "zero_chunks":
                                    self.assertIn("⚠️", result["message"])


if __name__ == "__main__":
    unittest.main()
