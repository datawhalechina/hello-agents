from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from rich.console import Console

from .community import build_hierarchy_summary, detect_communities, dump_communities
from .extract import extract_graph
from .gleaning import apply_gleaning
from .graph_store import GraphStore
from .llm import load_llm_config
from .ocr import extract_ocr_spans, spans_to_debug_json, spans_to_text
from .query import QueryEngine

console = Console()


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def cmd_demo(args: argparse.Namespace) -> None:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = load_llm_config(enable_llm=bool(args.llm))
    text = _read_text(args.input)

    console.print(f"[bold]Extracting graph[/bold] (llm_backend={llm.backend})")
    extracted = extract_graph(text, llm)

    store = GraphStore.from_extracted(extracted)
    glean_logs = apply_gleaning(store.g)

    graph_path = str(out_dir / "graph.json")
    store.dump_json(graph_path)
    console.print(f"Wrote {graph_path}")

    console.print(f"Gleaning inferred edges: {len(glean_logs)}")

    console.print("[bold]Community detection[/bold]")
    communities = detect_communities(store.g)
    node_to_comm = {}
    for idx, nodes in enumerate(communities):
        for n in nodes:
            node_to_comm[n] = idx

    comm_path = str(out_dir / "communities.json")
    dump_communities(comm_path, communities, node_to_comm)
    console.print(f"Wrote {comm_path}")

    console.print("[bold]Hierarchy summary[/bold]")
    summaries = build_hierarchy_summary(store.g, communities, llm)
    summary_path = out_dir / "hierarchy_summary.md"
    summary_path.write_text(summaries.get("_top", ""), encoding="utf-8")
    console.print(f"Wrote {summary_path}")

    console.print("[bold]Query demo[/bold]")
    q = QueryEngine(store)
    hits = q.semantic_search_nodes("读书会 上海", top_k=5)
    console.print("semantic_search_nodes('读书会 上海'):")
    for nid, score in hits:
        console.print(f"- {nid}  score={score:.3f}  name={store.g.nodes[nid].get('name')}")


def cmd_ocr(args: argparse.Namespace) -> None:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    spans = extract_ocr_spans(args.image)
    text = spans_to_text(spans)

    (out_dir / "ocr_text.txt").write_text(text, encoding="utf-8")
    with open(out_dir / "ocr_debug.json", "w", encoding="utf-8") as f:
        json.dump(spans_to_debug_json(spans), f, ensure_ascii=False, indent=2)

    console.print(f"Wrote {out_dir / 'ocr_text.txt'}")
    console.print(f"Wrote {out_dir / 'ocr_debug.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_demo = sub.add_parser("demo", help="Run end-to-end demo: text -> graph -> communities -> summary -> query")
    p_demo.add_argument("--input", required=True)
    p_demo.add_argument("--out", default="outputs")
    p_demo.add_argument("--llm", action="store_true", help="Enable LLM-based extraction if configured")
    p_demo.set_defaults(func=cmd_demo)

    p_ocr = sub.add_parser("ocr", help="Run OCR on an image")
    p_ocr.add_argument("--image", required=True)
    p_ocr.add_argument("--out", default="outputs")
    p_ocr.set_defaults(func=cmd_ocr)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
