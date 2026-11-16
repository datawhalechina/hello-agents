"""Run `python -m evaluation.run --output evaluation/latest_report.json`."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path

from app.agents.orchestrator import WorkflowOrchestrator
from app.connectors.local import parse_messages
from app.extraction.local import classify_message
from app.workflow.verifier import verify_evidence

ROOT = Path(__file__).resolve().parents[1]


def metrics(expected: set, actual: set) -> dict:
    matched = len(expected & actual)
    precision = matched / len(actual) if actual else int(not expected)
    recall = matched / len(expected) if expected else int(not actual)
    return {"expected": len(expected), "predicted": len(actual), "matched": matched,
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0}


def evaluate() -> dict:
    fixtures = ROOT / "data" / "fixtures"
    messages = parse_messages((fixtures / "demo_messages.json").read_text(encoding="utf-8"), "demo-feishu")
    gold = json.loads((fixtures / "gold_standard.json").read_text(encoding="utf-8"))
    with redirect_stdout(io.StringIO()):
        result = WorkflowOrchestrator(provider="local-demo").analyze(messages)
    graph = result.proposal
    expected_work = {row["message_id"] for row in gold["facts"]}
    actual_work = {message.id for message in messages if classify_message(message) == "work"}
    expected_facts = {(row["message_id"], row["kind"], row["project"], row["entity"]) for row in gold["facts"]}
    actual_facts = {(fact.evidence[0].message_id, str(fact.kind), fact.project_hint, fact.entity_key) for fact in graph.facts}
    expected_relations = {(row["message_id"], row["relation"], row["target_entity"]) for row in gold["relations"]}
    node_facts = {node.id: next(fact for fact in graph.facts if fact.id == node.fact_ids[0]) for node in graph.nodes}
    actual_relations = {(node_facts[edge.source].evidence[0].message_id, edge.relation, node_facts[edge.target].entity_key)
                        for edge in graph.edges if edge.relation != "precedes"}
    reference_count = sum(len(fact.evidence) for fact in graph.facts)
    verified_count = sum(verify_evidence(reference, messages) for fact in graph.facts for reference in fact.evidence)
    return {
        "scope": gold["scope"], "provider": result.provider, "messages": len(messages),
        "work_classification": metrics(expected_work, actual_work),
        "atomic_fact_fields": metrics(expected_facts, actual_facts),
        "explicit_relations": metrics(expected_relations, actual_relations),
        "evidence_integrity": {"references": reference_count, "valid": verified_count,
                               "ratio": verified_count / reference_count if reference_count else 0},
        "unassigned_facts": sum(fact.project_id is None for fact in graph.facts),
        "stage_count": len(result.agent_results), "warnings": graph.warnings,
        "limitations": ["Handwritten project/entity tags and explicit relation phrases make this a controlled acceptance fixture.",
                        "No live Feishu data, remote LLM calls or semantic causality benchmark is included.",
                        "Literal evidence integrity does not establish semantic truth or trusted training labels."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Fail when the controlled acceptance fixture is imperfect")
    args = parser.parse_args()
    report = evaluate()
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
    print(content)
    if args.strict and (any(report[key]["f1"] < 1 for key in ["work_classification", "atomic_fact_fields", "explicit_relations"]) or report["evidence_integrity"]["ratio"] < 1):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
