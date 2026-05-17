#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hello-Agents 知识库问答系统（独立版）

目标：
1. 不依赖 Hermes
2. 不依赖 hello-agents Python 包
3. 尽量按 chapter8 的四个核心示例来组织结构
4. 同时提供：
   - 学习模式：展示“现在用了 chapter8 哪个模块、用了哪些函数、输出什么、有什么用”
   - 问答模式：针对 hello-agents 仓库内容进行本地检索问答

映射关系：
- 04_RAGTool_MarkItDown_Pipeline.py  -> 文档扫描、读取、标准化、分块
- 05_RAGTool_Advanced_Search.py      -> 查询扩展、关键词/语义混合召回、重排
- 10_RAG_Pipeline_Complete.py        -> ingest / build / search / stats 全链路
- 11_Q&A_Assistant.py                -> 应用层封装、CLI 交互、学习报告
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "hello_rag_data"
INDEX_PATH = DATA_DIR / "index.json"
SESSION_DIR = DATA_DIR / "sessions"
DEFAULT_GLOBS = [
    "_index.md",
    "docs/**/*.md",
    "Extra-Chapter/**/*.md",
    "code/chapter8/**/*.py",
    "code/chapter7/**/*.py",
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by",
    "is", "are", "was", "were", "be", "this", "that", "it", "as", "from", "at",
    "我们", "你", "我", "他", "她", "它", "的", "了", "和", "与", "或", "及", "在", "是",
    "就", "都", "而", "及其", "一个", "一种", "可以", "通过", "使用", "进行", "其中", "以及",
    "什么", "哪些", "如何", "怎么", "有没有", "是否", "一个", "用于", "主要", "相关",
}

CHAPTER8_MODULE_GUIDE = {
    "ingest": {
        "chapter8_file": "04_RAGTool_MarkItDown_Pipeline.py",
        "functions": ["scan_source_files", "read_text", "normalize_text", "chunk_markdown"],
        "purpose": "把仓库文档统一读入，保留标题结构，再切成可检索片段。",
    },
    "search": {
        "chapter8_file": "05_RAGTool_Advanced_Search.py",
        "functions": ["expand_query", "search", "rerank_results"],
        "purpose": "对用户问题做查询扩展，再混合关键词和字符级相似度召回，提高命中率。",
    },
    "pipeline": {
        "chapter8_file": "10_RAG_Pipeline_Complete.py",
        "functions": ["build_index", "stats", "ask"],
        "purpose": "把 ingest、索引构建、检索、问答串成完整主流程。",
    },
    "assistant": {
        "chapter8_file": "11_Q&A_Assistant.py",
        "functions": ["run_learning_mode", "interactive_qa", "save_session_report"],
        "purpose": "把底层能力封装成一个你可以直接运行、学习、提问的应用。",
    },
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SESSION_DIR.mkdir(exist_ok=True)


@dataclass
class ChunkRecord:
    chunk_id: str
    source_path: str
    title: str
    section_path: str
    chapter: str
    category: str
    text: str
    tokens: List[str]
    token_counts: Dict[str, int]
    char_ngrams: Dict[str, int]
    length: int


class SimpleTokenizer:
    token_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]*|[\u4e00-\u9fff]{1,}|\d+")

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        raw = [m.group(0).lower() for m in cls.token_pattern.finditer(text)]
        return [tok for tok in raw if tok not in STOPWORDS and len(tok.strip()) > 0]

    @staticmethod
    def char_ngrams(text: str, n: int = 2) -> Dict[str, int]:
        compact = re.sub(r"\s+", "", text.lower())
        grams = Counter()
        if len(compact) < n:
            return grams
        for i in range(len(compact) - n + 1):
            grams[compact[i:i+n]] += 1
        return dict(grams)


class CorpusIngestor:
    def __init__(self, root: Path):
        self.root = root

    def scan_source_files(self, patterns: Sequence[str]) -> List[Path]:
        files: List[Path] = []
        for pattern in patterns:
            files.extend(self.root.glob(pattern))
        unique = sorted({p.resolve() for p in files if p.is_file()})
        return [Path(p) for p in unique]

    def read_text(self, path: Path) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return path.read_text(errors="ignore")

    def normalize_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\t", "    ")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def infer_metadata(self, path: Path) -> Tuple[str, str, str]:
        rel = path.relative_to(self.root).as_posix()
        chapter_match = re.search(r"chapter(\d+)", rel, flags=re.IGNORECASE)
        chapter = f"chapter{chapter_match.group(1)}" if chapter_match else "general"
        if rel.startswith("docs/"):
            category = "docs"
        elif rel.startswith("Extra-Chapter/"):
            category = "extra"
        elif rel.startswith("code/"):
            category = "code"
        else:
            category = "root"
        title = path.stem
        return title, chapter, category

    def chunk_markdown(self, path: Path, text: str, chunk_size: int = 1200, chunk_overlap: int = 180) -> List[ChunkRecord]:
        title, chapter, category = self.infer_metadata(path)
        sections = self._split_by_headings(text)
        chunks: List[ChunkRecord] = []
        for sec_idx, section in enumerate(sections):
            section_text = section["content"].strip()
            if not section_text:
                continue
            windows = self._window_text(section_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for win_idx, window in enumerate(windows):
                chunk_id = f"{path.relative_to(self.root).as_posix()}::s{sec_idx}::c{win_idx}"
                tokens = SimpleTokenizer.tokenize(window)
                record = ChunkRecord(
                    chunk_id=chunk_id,
                    source_path=path.relative_to(self.root).as_posix(),
                    title=title,
                    section_path=section["heading_path"] or title,
                    chapter=chapter,
                    category=category,
                    text=window,
                    tokens=tokens,
                    token_counts=dict(Counter(tokens)),
                    char_ngrams=SimpleTokenizer.char_ngrams(window),
                    length=len(window),
                )
                chunks.append(record)
        return chunks

    def _split_by_headings(self, text: str) -> List[Dict[str, str]]:
        lines = text.split("\n")
        sections: List[Dict[str, str]] = []
        heading_stack: List[str] = []
        buffer: List[str] = []

        def flush() -> None:
            if not buffer:
                return
            content = "\n".join(buffer).strip()
            if content:
                sections.append({
                    "heading_path": " > ".join(heading_stack) if heading_stack else "",
                    "content": content,
                })
            buffer.clear()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped[level:].strip()
                if level <= 0:
                    level = 1
                heading_stack[:] = heading_stack[: max(level - 1, 0)]
                heading_stack.append(title)
            else:
                buffer.append(line)
        flush()
        if not sections:
            sections.append({"heading_path": "", "content": text})
        return sections

    def _window_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paras:
            return []
        chunks: List[str] = []
        current = ""
        for para in paras:
            candidate = para if not current else current + "\n\n" + para
            if len(candidate) <= chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                start = 0
                while start < len(para):
                    end = min(start + chunk_size, len(para))
                    piece = para[start:end]
                    chunks.append(piece)
                    if end >= len(para):
                        current = ""
                        break
                    start = max(end - chunk_overlap, start + 1)
                else:
                    current = ""
        if current:
            chunks.append(current)
        return chunks


class LocalKnowledgeBase:
    def __init__(self, root: Path):
        self.root = root
        self.ingestor = CorpusIngestor(root)
        self.index: List[ChunkRecord] = []
        self.df: Counter[str] = Counter()
        self.avg_doc_len = 0.0

    def build_index(self, patterns: Sequence[str] = DEFAULT_GLOBS, chunk_size: int = 1200, chunk_overlap: int = 180) -> Dict[str, int]:
        files = self.ingestor.scan_source_files(patterns)
        chunks: List[ChunkRecord] = []
        for path in files:
            text = self.ingestor.normalize_text(self.ingestor.read_text(path))
            chunks.extend(self.ingestor.chunk_markdown(path, text, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
        self.index = chunks
        self.df = Counter()
        total_len = 0
        for chunk in chunks:
            total_len += max(1, len(chunk.tokens))
            for tok in set(chunk.tokens):
                self.df[tok] += 1
        self.avg_doc_len = total_len / max(1, len(chunks))
        self._save_index()
        return {
            "files": len(files),
            "chunks": len(chunks),
            "avg_chunk_chars": int(sum(c.length for c in chunks) / max(1, len(chunks))),
        }

    def load(self) -> bool:
        if not INDEX_PATH.exists():
            return False
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        self.index = [ChunkRecord(**item) for item in data["chunks"]]
        self.df = Counter(data["df"])
        self.avg_doc_len = data.get("avg_doc_len", 0.0)
        return True

    def _save_index(self) -> None:
        ensure_dirs()
        payload = {
            "created_at": datetime.now().isoformat(),
            "avg_doc_len": self.avg_doc_len,
            "df": dict(self.df),
            "chunks": [asdict(c) for c in self.index],
        }
        INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def stats(self) -> Dict[str, object]:
        by_category = Counter(c.category for c in self.index)
        by_chapter = Counter(c.chapter for c in self.index)
        return {
            "chunk_count": len(self.index),
            "categories": dict(by_category),
            "chapters": dict(by_chapter),
            "index_path": str(INDEX_PATH.relative_to(PROJECT_ROOT)) if INDEX_PATH.exists() else "not_built",
        }

    def expand_query(self, query: str) -> List[str]:
        expansions = [query]
        lower = query.lower()
        alias_pairs = [
            ("记忆", ["memory", "工作记忆", "情景记忆", "语义记忆"]),
            ("检索", ["rag", "搜索", "召回", "search"]),
            ("上下文", ["context", "gssc", "压缩", "context engineering"]),
            ("mcp", ["model context protocol", "工具协议"]),
            ("helloagents", ["hello-agents", "hello agents", "框架"]),
            ("函数", ["代码", "方法", "脚本"]),
            ("chapter8", ["记忆与检索", "第八章"]),
        ]
        for key, vals in alias_pairs:
            if key in lower:
                expansions.extend(vals)
        if "问答" in query:
            expansions.extend(["assistant", "qa", "Q&A", "ask"])
        return list(dict.fromkeys(expansions))

    def search(self, query: str, top_k: int = 6) -> List[Dict[str, object]]:
        if not self.index:
            raise RuntimeError("索引为空，请先 build")
        queries = self.expand_query(query)
        query_tokens = []
        for q in queries:
            query_tokens.extend(SimpleTokenizer.tokenize(q))
        q_counter = Counter(query_tokens)
        q_ngrams = SimpleTokenizer.char_ngrams(query)
        results = []
        N = max(1, len(self.index))
        for chunk in self.index:
            bm25_score = self._bm25(q_counter, chunk, N)
            char_score = self._cosine_dict(q_ngrams, chunk.char_ngrams)
            title_bonus = 0.0
            section_blob = f"{chunk.title} {chunk.section_path} {chunk.source_path}".lower()
            for tok in set(query_tokens):
                if tok and tok in section_blob:
                    title_bonus += 0.15
            score = bm25_score + char_score * 1.2 + title_bonus
            if score <= 0:
                continue
            results.append({
                "score": score,
                "bm25": bm25_score,
                "char": char_score,
                "chunk": chunk,
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return self.rerank_results(query, results[: max(top_k * 2, 10)])[:top_k]

    def rerank_results(self, query: str, candidates: List[Dict[str, object]]) -> List[Dict[str, object]]:
        q = query.lower()
        boosted = []
        for item in candidates:
            chunk: ChunkRecord = item["chunk"]
            extra = 0.0
            text_blob = (chunk.section_path + "\n" + chunk.text[:500]).lower()
            if any(word in text_blob for word in ["chapter8", "第八章", "记忆", "检索", "rag", "memory"]):
                extra += 0.2
            if q in text_blob:
                extra += 0.3
            item = dict(item)
            item["score"] = item["score"] + extra
            boosted.append(item)
        boosted.sort(key=lambda x: x["score"], reverse=True)
        return boosted

    def ask(self, question: str, top_k: int = 5) -> Dict[str, object]:
        results = self.search(question, top_k=top_k)
        answer = self._synthesize_answer(question, results)
        citations = [self._format_citation(item["chunk"], idx + 1) for idx, item in enumerate(results)]
        return {
            "question": question,
            "answer": answer,
            "citations": citations,
            "results": results,
        }

    def _synthesize_answer(self, question: str, results: List[Dict[str, object]]) -> str:
        if not results:
            return "我在当前索引里没有找到足够相关的内容。你可以换个问法，或者先 rebuild 把更多目录纳入索引。"
        snippets = []
        for item in results[:4]:
            chunk: ChunkRecord = item["chunk"]
            snippet = self._trim_text(chunk.text, 220)
            snippets.append(f"- 来自 {chunk.source_path} / {chunk.section_path}: {snippet}")
        intro = [
            f"问题：{question}",
            "基于当前仓库内容，我先给你一个 grounded answer：",
        ]
        heuristics = self._question_style_hint(question, results)
        body = [heuristics, "证据摘录：", *snippets]
        return "\n".join(intro + body)

    def _question_style_hint(self, question: str, results: List[Dict[str, object]]) -> str:
        q = question.lower()
        top_chunks = [item["chunk"] for item in results[:3]]
        chapters = [c.chapter for c in top_chunks]
        files = [c.source_path for c in top_chunks]
        if "第八章" in question or "chapter8" in q or "记忆" in question or "rag" in q:
            return f"这类问题主要落在 {', '.join(dict.fromkeys(chapters))}，尤其是 {files[0]} 这类文件。"
        if "代码" in question or "函数" in question or "脚本" in question:
            return f"如果你想看可执行实现，优先读：{files[0]}；它在检索结果里最相关。"
        return f"最相关的材料集中在：{', '.join(dict.fromkeys(files[:3]))}。"

    def _format_citation(self, chunk: ChunkRecord, rank: int) -> str:
        return f"[{rank}] {chunk.source_path} | {chunk.section_path}"

    def _bm25(self, q_counter: Counter[str], chunk: ChunkRecord, N: int, k1: float = 1.5, b: float = 0.75) -> float:
        score = 0.0
        dl = max(1, len(chunk.tokens))
        for tok, qf in q_counter.items():
            tf = chunk.token_counts.get(tok, 0)
            if tf == 0:
                continue
            df = self.df.get(tok, 0)
            idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
            denom = tf + k1 * (1 - b + b * dl / max(self.avg_doc_len, 1.0))
            score += idf * (tf * (k1 + 1) / max(denom, 1e-9)) * qf
        return score

    def _cosine_dict(self, a: Dict[str, int], b: Dict[str, int]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[k] * b[k] for k in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _trim_text(self, text: str, limit: int) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact if len(compact) <= limit else compact[: limit - 1] + "…"


class LearningAssistant:
    def __init__(self, kb: LocalKnowledgeBase):
        self.kb = kb
        self.session = {
            "started_at": datetime.now().isoformat(),
            "questions": [],
            "mode_history": [],
        }

    def run_learning_mode(self, rebuild: bool = False) -> str:
        logs: List[str] = []
        logs.append("Hello-Agents 学习模式")
        logs.append("=" * 72)
        if rebuild or not self.kb.load():
            stats = self.kb.build_index()
            logs.append("[pipeline] 首次构建索引完成")
            logs.append(f"  files={stats['files']}  chunks={stats['chunks']}  avg_chunk_chars={stats['avg_chunk_chars']}")
        else:
            logs.append("[pipeline] 已加载现有索引，无需重新构建")

        logs.append("")
        logs.append("一、这次运行对应 chapter8 哪几个必看模块")
        logs.append("-" * 72)
        for key in ["ingest", "search", "pipeline", "assistant"]:
            info = CHAPTER8_MODULE_GUIDE[key]
            logs.append(f"[{key}] 对应 {info['chapter8_file']}")
            logs.append(f"  用到的函数职责: {', '.join(info['functions'])}")
            logs.append(f"  有什么用: {info['purpose']}")

        logs.append("")
        logs.append("二、现在真的做了什么")
        logs.append("-" * 72)
        files = self.kb.ingestor.scan_source_files(DEFAULT_GLOBS)
        sample_files = [str(p.relative_to(PROJECT_ROOT)) for p in files[:8]]
        logs.append("[04 ingest] scan_source_files() 扫到了这些文件：")
        for path in sample_files:
            logs.append(f"  - {path}")
        logs.append("[04 ingest] normalize_text() 把换行、空白、编码差异统一。")
        logs.append("[04 ingest] chunk_markdown() 按标题层级 + 段落窗口切块。")

        kb_stats = self.kb.stats()
        logs.append("")
        logs.append("三、索引统计")
        logs.append("-" * 72)
        logs.append(json.dumps(kb_stats, ensure_ascii=False, indent=2))

        demo_query = "chapter8 里 RAG 是怎么组织成完整管道的"
        answer = self.kb.ask(demo_query, top_k=4)
        logs.append("")
        logs.append("四、用一个真实问题演示检索和问答")
        logs.append("-" * 72)
        logs.append(f"示例问题: {demo_query}")
        logs.append("[05 search] expand_query() 会把问题扩成 RAG / 检索 / 第八章 / 管道 等信号。")
        logs.append("[05 search] search() 混合 BM25 + 字符级相似度召回。")
        logs.append("[05 search] rerank_results() 会把标题、章节、显式命中再加权。")
        logs.append("")
        logs.append("输出示例：")
        logs.append(answer["answer"])
        logs.append("")
        logs.append("引用来源：")
        for citation in answer["citations"]:
            logs.append(f"  {citation}")

        logs.append("")
        logs.append("五、你能从这次输出学到什么")
        logs.append("-" * 72)
        logs.append("1. chapter8 的重点不只是问答，而是 ingest -> index -> search -> assistant 这条主链。")
        logs.append("2. 04 负责文档怎么进库；05 负责怎么搜得更稳；10 负责完整骨架；11 负责变成一个应用。")
        logs.append("3. 你现在运行的这个脚本，就是按这个结构复刻出来的独立版本。")
        self.session["mode_history"].append({"mode": "learn", "at": datetime.now().isoformat()})
        self.save_session_report()
        return "\n".join(logs)

    def interactive_qa(self, question: str, top_k: int = 5) -> str:
        if not self.kb.index and not self.kb.load():
            self.kb.build_index()
        result = self.kb.ask(question, top_k=top_k)
        self.session["questions"].append({
            "question": question,
            "at": datetime.now().isoformat(),
            "citations": result["citations"],
        })
        self.session["mode_history"].append({"mode": "ask", "at": datetime.now().isoformat()})
        self.save_session_report()
        lines = [
            "Hello-Agents 问答结果",
            "=" * 72,
            result["answer"],
            "",
            "引用来源：",
        ]
        for citation in result["citations"]:
            lines.append(f"- {citation}")
        lines.append("")
        lines.append("如果你要继续深挖，优先打开排名最前的那几个文件。")
        return "\n".join(lines)

    def save_session_report(self) -> str:
        ensure_dirs()
        path = SESSION_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(self.session, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hello-Agents 独立问答/学习系统")
    sub = parser.add_subparsers(dest="command")

    p_build = sub.add_parser("build", help="重建索引")
    p_build.add_argument("--chunk-size", type=int, default=1200)
    p_build.add_argument("--chunk-overlap", type=int, default=180)

    p_learn = sub.add_parser("learn", help="运行学习模式")
    p_learn.add_argument("--rebuild", action="store_true")

    p_ask = sub.add_parser("ask", help="提问")
    p_ask.add_argument("question", help="你的问题")
    p_ask.add_argument("--top-k", type=int, default=5)

    sub.add_parser("stats", help="查看索引统计")
    sub.add_parser("shell", help="进入交互式问答")
    return parser


def run_shell(app: LearningAssistant) -> None:
    print("进入 Hello-Agents 交互问答模式。输入 exit 退出，输入 /learn 查看学习模式。")
    if not app.kb.index and not app.kb.load():
        print("正在构建索引，请稍候…")
        app.kb.build_index()
    while True:
        try:
            q = input("\nhello-rag> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            print("退出。")
            break
        if q == "/learn":
            print(app.run_learning_mode(rebuild=False))
            continue
        print(app.interactive_qa(q))


def main() -> None:
    ensure_dirs()
    parser = build_arg_parser()
    args = parser.parse_args()
    kb = LocalKnowledgeBase(PROJECT_ROOT)
    app = LearningAssistant(kb)

    if args.command == "build":
        stats = kb.build_index(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return
    if args.command == "learn":
        print(app.run_learning_mode(rebuild=args.rebuild))
        return
    if args.command == "ask":
        print(app.interactive_qa(args.question, top_k=args.top_k))
        return
    if args.command == "stats":
        if not kb.load():
            kb.build_index()
        print(json.dumps(kb.stats(), ensure_ascii=False, indent=2))
        return
    if args.command == "shell":
        run_shell(app)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
