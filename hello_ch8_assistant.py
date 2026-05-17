#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hello-Agents Chapter 8 学习问答助手（双引擎正式版）

默认路线：local
- 稳定可用
- 不依赖 Hermes
- 不依赖 hello-agents 官方 RAG 内部缺陷被修完
- 保留 chapter8 的结构映射、学习模式、问答模式、笔记与报告

可选路线：official
- 尽量走 hello-agents==0.2.9 的官方 RAGTool / MemoryTool 思路
- 仅用于研究 chapter8 官方链路，不保证当前版本完整可用

推荐：先用 local 把系统真正跑起来；需要对照 chapter8 官方实现时再切 official。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from hello_rag_tutor import (
    PROJECT_ROOT,
    DATA_DIR as LOCAL_DATA_DIR,
    SESSION_DIR as LOCAL_SESSION_DIR,
    DEFAULT_GLOBS,
    CHAPTER8_MODULE_GUIDE,
    LocalKnowledgeBase,
    LearningAssistant,
)


DATA_DIR = PROJECT_ROOT / "hello_ch8_data"
SESSION_DIR = DATA_DIR / "sessions"
ENV_PATH = PROJECT_ROOT / ".env.ch8"
FALLBACK_MEMORY_PATH = DATA_DIR / "fallback_memory.json"
QDRANT_LOCAL_DIR = DATA_DIR / "qdrant_local"
KB_DIR = DATA_DIR / "knowledge_base"
DEFAULT_ENGINE = os.getenv("HELLO_CH8_ENGINE", "local").strip().lower() or "local"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SESSION_DIR.mkdir(exist_ok=True)
    QDRANT_LOCAL_DIR.mkdir(exist_ok=True)
    KB_DIR.mkdir(exist_ok=True)


def write_env_if_missing() -> None:
    if ENV_PATH.exists():
        return
    content = "\n".join([
        "# Hello-Agents chapter8 dual-engine config",
        "HELLO_CH8_ENGINE=local",
        "",
        "# official 引擎相关（只有研究官方链路时才需要）",
        "EMBED_MODEL_TYPE=tfidf",
        f"QDRANT_LOCAL_PATH={QDRANT_LOCAL_DIR.as_posix()}",
        "# LLM_MODEL_ID=",
        "# LLM_API_KEY=",
        "# LLM_BASE_URL=",
        "",
    ])
    ENV_PATH.write_text(content, encoding="utf-8")


class LocalFallbackMemoryTool:
    def __init__(self, store_path: Path):
        self.store_path = store_path
        if not self.store_path.exists():
            self.store_path.write_text("[]", encoding="utf-8")

    def _read(self):
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write(self, data):
        self.store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(self, parameters: Dict[str, Any]) -> str:
        action = parameters.get("action")
        data = self._read()
        if action == "add":
            item = {
                "content": parameters.get("content", ""),
                "memory_type": parameters.get("memory_type", "working"),
                "importance": parameters.get("importance", 0.5),
                "timestamp": datetime.now().isoformat(),
            }
            data.append(item)
            self._write(data)
            return "✅ fallback memory add success"
        if action == "search":
            query = str(parameters.get("query", "")).lower()
            limit = int(parameters.get("limit", 5))
            hits = [x for x in data if query in x.get("content", "").lower()]
            return json.dumps(hits[:limit], ensure_ascii=False, indent=2)
        if action == "stats":
            return json.dumps({"count": len(data), "store_path": str(self.store_path)}, ensure_ascii=False)
        if action == "summary":
            return json.dumps(data[-10:], ensure_ascii=False, indent=2)
        return f"⚠️ fallback memory unsupported action: {action}"


class LocalEngineAdapter:
    def __init__(self):
        ensure_dirs()
        self.kb = LocalKnowledgeBase(PROJECT_ROOT)
        self.app = LearningAssistant(self.kb)
        self.memory_tool = LocalFallbackMemoryTool(FALLBACK_MEMORY_PATH)
        self.memory_backend = "fallback_json"
        self.engine_name = "local"

    def build(self, limit: Optional[int] = None) -> Dict[str, Any]:
        stats = self.kb.build_index(patterns=DEFAULT_GLOBS)
        self.memory_tool.run({
            "action": "add",
            "content": f"local engine build: files={stats['files']} chunks={stats['chunks']}",
            "memory_type": "episodic",
            "importance": 0.9,
        })
        return stats

    def learn(self, rebuild: bool = False) -> str:
        self.memory_tool.run({
            "action": "add",
            "content": "运行了 local 学习模式",
            "memory_type": "episodic",
            "importance": 0.8,
        })
        return self.app.run_learning_mode(rebuild=rebuild)

    def ask(self, question: str, top_k: int = 5) -> str:
        self.memory_tool.run({
            "action": "add",
            "content": f"提问: {question}",
            "memory_type": "working",
            "importance": 0.6,
        })
        return self.app.interactive_qa(question, top_k=top_k)

    def search(self, query: str, top_k: int = 5) -> str:
        if not self.kb.index and not self.kb.load():
            self.kb.build_index(patterns=DEFAULT_GLOBS)
        result = self.kb.ask(query, top_k=top_k)
        lines = [
            "Hello-Agents 检索预览",
            "=" * 72,
            result["answer"],
            "",
            "引用来源：",
        ]
        for citation in result["citations"]:
            lines.append(f"- {citation}")
        return "\n".join(lines)

    def recall(self, query: str, limit: int = 5) -> str:
        return self.memory_tool.run({"action": "search", "query": query, "limit": limit})

    def note(self, content: str, concept: Optional[str] = None) -> str:
        payload = content if not concept else f"[{concept}] {content}"
        return self.memory_tool.run({
            "action": "add",
            "content": payload,
            "memory_type": "semantic",
            "importance": 0.8,
        })

    def stats(self) -> Dict[str, Any]:
        if not self.kb.index and not self.kb.load():
            self.kb.build_index(patterns=DEFAULT_GLOBS)
        return {
            "engine": self.engine_name,
            "memory_backend": self.memory_backend,
            "kb_stats": self.kb.stats(),
            "memory_stats": json.loads(self.memory_tool.run({"action": "stats"})),
            "index_path": str((LOCAL_DATA_DIR / "index.json").relative_to(PROJECT_ROOT)),
        }

    def report(self) -> Dict[str, Any]:
        path = SESSION_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "engine": self.engine_name,
            "created_at": datetime.now().isoformat(),
            "memory_backend": self.memory_backend,
            "stats": self.stats(),
            "module_guide": CHAPTER8_MODULE_GUIDE,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_file"] = str(path.relative_to(PROJECT_ROOT))
        return payload


class OfficialEngineStub:
    def __init__(self):
        ensure_dirs()
        load_dotenv(ENV_PATH, override=False)
        self.engine_name = "official"
        self.memory_backend = "fallback_json"
        self.memory_tool = LocalFallbackMemoryTool(FALLBACK_MEMORY_PATH)

    def _msg(self) -> str:
        return (
            "official 引擎目前保留为 chapter8 官方链路对照入口。\n"
            "你前面已经看到，hello-agents 0.2.9 的 TF-IDF / Qdrant / MemoryTool 链路还存在实现缺口。\n"
            "因此这版双引擎默认推荐使用 local。\n"
            "如果你后续要继续修官方链路，我们再在这个入口上补。"
        )

    def build(self, limit: Optional[int] = None) -> Dict[str, Any]:
        return {"engine": self.engine_name, "status": "not_ready", "message": self._msg()}

    def learn(self, rebuild: bool = False) -> str:
        return self._msg()

    def ask(self, question: str, top_k: int = 5) -> str:
        return self._msg()

    def search(self, query: str, top_k: int = 5) -> str:
        return self._msg()

    def recall(self, query: str, limit: int = 5) -> str:
        return self.memory_tool.run({"action": "search", "query": query, "limit": limit})

    def note(self, content: str, concept: Optional[str] = None) -> str:
        payload = content if not concept else f"[{concept}] {content}"
        return self.memory_tool.run({"action": "add", "content": payload, "memory_type": "semantic", "importance": 0.8})

    def stats(self) -> Dict[str, Any]:
        return {
            "engine": self.engine_name,
            "status": "not_ready",
            "memory_backend": self.memory_backend,
            "message": self._msg(),
        }

    def report(self) -> Dict[str, Any]:
        path = SESSION_DIR / f"report_official_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "engine": self.engine_name,
            "created_at": datetime.now().isoformat(),
            "status": "not_ready",
            "message": self._msg(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_file"] = str(path.relative_to(PROJECT_ROOT))
        return payload


class HelloCh8Assistant:
    def __init__(self, engine: str = DEFAULT_ENGINE):
        ensure_dirs()
        write_env_if_missing()
        self.engine = (engine or DEFAULT_ENGINE).strip().lower()
        if self.engine == "official":
            self.backend = OfficialEngineStub()
        else:
            self.engine = "local"
            self.backend = LocalEngineAdapter()

    def run_learning_mode(self, rebuild: bool = False) -> str:
        return self.backend.learn(rebuild=rebuild)

    def build(self, limit: Optional[int] = None) -> Dict[str, Any]:
        return self.backend.build(limit=limit)

    def ask(self, question: str, top_k: int = 5) -> str:
        return self.backend.ask(question, top_k=top_k)

    def search_preview(self, query: str, top_k: int = 5) -> str:
        return self.backend.search(query, top_k=top_k)

    def recall(self, query: str, limit: int = 5) -> str:
        return self.backend.recall(query, limit=limit)

    def add_note(self, content: str, concept: Optional[str] = None) -> str:
        return self.backend.note(content, concept=concept)

    def get_stats(self) -> Dict[str, Any]:
        return self.backend.stats()

    def generate_report(self) -> Dict[str, Any]:
        return self.backend.report()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hello-Agents Chapter 8 双引擎学习问答助手")
    parser.add_argument("--engine", choices=["local", "official"], default=DEFAULT_ENGINE)
    sub = parser.add_subparsers(dest="command")

    p_learn = sub.add_parser("learn", help="运行学习模式")
    p_learn.add_argument("--rebuild", action="store_true")

    p_build = sub.add_parser("build", help="构建知识库")
    p_build.add_argument("--limit", type=int, default=None)

    p_ask = sub.add_parser("ask", help="向知识库提问")
    p_ask.add_argument("question")
    p_ask.add_argument("--top-k", type=int, default=5)

    p_search = sub.add_parser("search", help="只看检索结果预览")
    p_search.add_argument("query")
    p_search.add_argument("--top-k", type=int, default=5)

    p_recall = sub.add_parser("recall", help="回顾学习记录")
    p_recall.add_argument("query")
    p_recall.add_argument("--limit", type=int, default=5)

    p_note = sub.add_parser("note", help="添加学习笔记")
    p_note.add_argument("content")
    p_note.add_argument("--concept", default=None)

    sub.add_parser("stats", help="查看当前统计")
    sub.add_parser("report", help="生成会话报告")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    assistant = HelloCh8Assistant(engine=args.engine)

    if args.command == "learn":
        print(assistant.run_learning_mode(rebuild=args.rebuild))
        return
    if args.command == "build":
        print(json.dumps(assistant.build(limit=args.limit), ensure_ascii=False, indent=2))
        return
    if args.command == "ask":
        print(assistant.ask(args.question, top_k=args.top_k))
        return
    if args.command == "search":
        print(assistant.search_preview(args.query, top_k=args.top_k))
        return
    if args.command == "recall":
        print(assistant.recall(args.query, limit=args.limit))
        return
    if args.command == "note":
        print(assistant.add_note(args.content, concept=args.concept))
        return
    if args.command == "stats":
        print(json.dumps(assistant.get_stats(), ensure_ascii=False, indent=2))
        return
    if args.command == "report":
        print(json.dumps(assistant.generate_report(), ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
