---
name: paper-innovation-designer
description: Use when deriving research gaps, innovation ideas, novelty checks, or experiment plans from several academic PDF papers, parsed paper notes, literature-review excerpts, or structured paper records; especially when the user asks to generate 2-3 feasible innovation points, compare limitations across papers, design experiments, select datasets/baselines/metrics, or write a research proposal grounded in source papers.
---

# Paper Innovation Designer

## Overview

Turn a small paper set into evidence-grounded innovation ideas and executable experiment plans. Preserve traceability: every gap, idea, and experiment choice should point back to specific source papers, sections, pages, or extracted evidence.

## Workflow

1. **Collect inputs**
   - Use the provided PDFs, paper folder, extracted notes, or structured paper records.
   - If the research direction is missing, infer a provisional direction from the papers and state it.
   - If PDFs are available locally, extract text with a PDF-capable tool before synthesizing.

2. **Extract each paper into a fixed schema**
   - `title`
   - `task_problem`
   - `method`
   - `key_contributions`
   - `datasets`
   - `metrics`
   - `results`
   - `limitations`
   - `future_work`
   - `source_sections` or source page evidence

3. **Build a cross-paper evidence matrix**
   Compare papers by task, method family, data setting, evaluation metrics, results, limitations, and future-work claims. Keep paper-specific failures isolated; do not let one weak extraction dominate the synthesis.

4. **Identify research gaps**
   Use these gap types:
   - `repeated_limitation`: multiple papers share the same unresolved limitation.
   - `method_gap`: current methods omit a plausible technique, signal, modality, constraint, or optimization target.
   - `contradictory`: papers report conflicting findings, assumptions, or tradeoffs.
   - `unfulfilled_future`: papers explicitly suggest future work that later papers still do not address.

5. **Generate candidate innovation ideas**
   Create candidates from four sources:
   - `method_combination`: combine complementary methods from different papers.
   - `limitation_fix`: directly address repeated or high-impact limitations.
   - `cross_domain`: transfer a method from an adjacent task/domain.
   - `new_scenario`: adapt the problem to a realistic but under-tested setting.

6. **Score and filter**
   Score each candidate from 0-10 on:
   - novelty
   - feasibility
   - significance

   Select 2-3 ideas with strong total score and clear evidence. If novelty cannot be checked online, mark it as "needs external novelty verification" instead of overstating originality.

7. **Design experiments for each selected idea**
   For every chosen idea, include:
   - hypothesis
   - target datasets or data collection plan
   - baselines
   - metrics
   - ablation studies
   - implementation steps
   - expected results
   - risks and mitigation

## Output Format

Use this structure unless the user requests another format:

```markdown
## Paper Evidence Matrix
| Paper | Task | Method | Data | Key Result | Limitation/Future Work |

## Research Gaps
1. Gap: ...
   Type: ...
   Evidence: ...
   Confidence: ...

## Candidate Innovations
| Idea | Source Type | Gap Origin | Novelty | Feasibility | Significance | Evidence |

## Recommended 2-3 Ideas
### Idea 1: ...
Rationale: ...
Why now: ...
Source evidence: ...
Novelty check: ...

## Experiment Plans
### Experiment Plan For Idea 1
Hypothesis:
Datasets:
Baselines:
Metrics:
Ablations:
Steps:
Expected results:
Risks:
```

## Quality Rules

- Do not invent limitations; distinguish explicit limitations from inferred ones.
- Prefer concrete ideas over broad slogans. A usable idea names the technical change, target task, expected mechanism, and evaluation path.
- Do not claim novelty from memory alone. Use current web or database search when available; otherwise mark novelty as unverified.
- Keep all recommendations feasible for a graduate-level research project unless the user asks for high-risk ideas.
- Penalize ideas that cannot be evaluated with available data, baselines, or metrics.
- Include negative evidence when a paper already solves the proposed idea.

## Common Failure Modes

| Failure | Correction |
|---|---|
| Summarizing each paper but not synthesizing across papers | Build the evidence matrix first, then derive gaps from overlaps and conflicts |
| Generating generic "improve model accuracy" ideas | Specify method, target limitation, data setting, and measurable outcome |
| Treating future work as a proven gap | Check whether another provided paper already addresses it |
| Designing experiments without baselines | Use methods from source papers as minimum baselines |
| Overclaiming novelty | Add a novelty-check note or uncertainty label |
