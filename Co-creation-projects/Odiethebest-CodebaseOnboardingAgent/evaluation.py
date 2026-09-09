"""Dependency-free parsing, strict-anchor metrics and citation-ID checks.

Protocol v2: only exact (file, symbol, start_line) matches earn credit.
An enclosing class is not a substitute for a method. Repeated results earn no
additional credit. The metrics evaluate retrieved evidence, not answer quality.
"""
import ast
import math
import re
import textwrap


def parse_chunk(content):
    # Keep CodeChunk.content intact for source display and original line numbers.
    # A parse failure must surface rather than silently erase call sites.
    return ast.parse(textwrap.dedent(content))


def anchor_match(chunk, gold):
    return (chunk.file_path, chunk.symbol_name, chunk.start_line) == (
        gold["file"], gold["symbol"], gold["start_line"])


def validate_questions(questions, chunks):
    if not questions:
        raise ValueError("Empty question set")
    ids = set()
    for q in questions:
        if q["id"] in ids:
            raise ValueError(f"Duplicate question ID: {q['id']}")
        ids.add(q["id"])
        if q["taxonomy"] not in {"L1", "L2", "L3"}:
            raise ValueError(f"Unknown stratum: {q['taxonomy']}")
        golds = q["gt_targets"]
        keys = [(g["file"], g["symbol"], g["start_line"]) for g in golds]
        if not keys or len(set(keys)) != len(keys):
            raise ValueError(f"Empty or duplicate gold anchors: {q['id']}")
        for g in golds:
            if sum(anchor_match(c, g) for c in chunks) != 1:
                raise ValueError(f"Gold must resolve to exactly one chunk: {q['id']} {g}")


def ranked_metrics(ranked_ids, golds, by_id, k=5):
    keys = {(g["file"], g["symbol"], g["start_line"]) for g in golds}
    covered, gains = set(), []
    first = 0.0
    for rank, cid in enumerate(ranked_ids[:k], 1):
        c = by_id.get(cid)
        key = (c.file_path, c.symbol_name, c.start_line) if c else None
        hit = key in keys and key not in covered
        gains.append(float(hit))
        if hit:
            covered.add(key)
            if not first:
                first = 1.0 / rank
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(keys), k)))
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    return {"recall@5": len(covered) / len(keys) if keys else 0.0,
            "mrr@5": first, "ndcg@5": dcg / ideal if ideal else 0.0}


CITE_RE = re.compile(r"\[([^\]\n]*#[^\]\n]*)\]")


def verify_citations(answer, by_id, allowed_ids=None):
    """Count distinct ID claims before filtering; never infer semantic support.

    allowed_ids optionally limits citations to evidence observed in this run.
    Malformed IDs containing # count as invalid instead of escaping the denominator.
    """
    raw = list(dict.fromkeys(CITE_RE.findall(answer)))
    allowed = set(by_id) if allowed_ids is None else set(allowed_ids)
    verified = [cid for cid in raw if cid in by_id and cid in allowed]
    cleaned = CITE_RE.sub(lambda m: m.group(0) if m.group(1) in verified else "", answer)
    return {"cited_before_filter": raw, "verified": verified, "answer": cleaned,
            "citation_id_validity": len(verified) / len(raw) if raw else 0.0}


def decide(stratum_scores, rule):
    """Use full-precision means. Missing strata fail loudly, not as a result."""
    checks = []
    for st in rule["strata"]:
        values = stratum_scores[st]
        for ctrl in rule["controls"]:
            margin = values[rule["treatment"]] - values[ctrl]
            checks.append({"stratum": st, "comparison": f"{rule['treatment']} vs {ctrl}",
                           "margin": margin, "threshold": rule["min_margin"],
                           "passed": margin >= rule["min_margin"]})
    return checks, "supported" if all(c["passed"] for c in checks) else "unsupported"
