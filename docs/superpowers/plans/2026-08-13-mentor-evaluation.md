# ResumeAgent Mentor Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, versioned benchmark and CLI for measuring mentor question quality and evidence extraction safety.

**Architecture:** Validated JSONL cases feed pure scorers and a port-based runner. The CLI uses the configured stateless mentor runtime, aggregates repeatable metrics, applies a strict threshold, and writes secret-safe JSON/Markdown reports.

**Tech Stack:** Python 3.10+, Pydantic 2, argparse, JSONL, pytest, existing HelloAgents ports.

## Global Constraints

- The bundled dataset contains synthetic data only.
- Reports never contain raw prompts, user answers, model outputs, API keys, or base URLs.
- Deterministic hallucination/privacy/schema failures cannot be overridden by semantic scoring.
- A single case error does not abort remaining cases.
- Degraded runtime exits without writing a success report.

---

### Task 1: Evaluation models, dataset, and pure scoring

**Files:**
- Create: `resume_agent/evaluation/__init__.py`
- Create: `resume_agent/evaluation/models.py`
- Create: `resume_agent/evaluation/dataset.py`
- Create: `resume_agent/evaluation/scoring.py`
- Create: `evaluation/datasets/mentor_v1.jsonl`
- Test: `tests/test_evaluation_dataset.py`
- Test: `tests/test_evaluation_scoring.py`

**Interfaces:**
- Produces: `QuestionEvaluationCase`, `AuditEvaluationCase`, `EvaluationCase` discriminated union.
- Produces: `load_dataset(path) -> MentorDataset` with unique IDs.
- Produces: `score_question(case, question) -> CaseScore` and `score_proposal(case, proposal) -> CaseScore`.

- [ ] Write failing schema/load/scoring tests for valid cases, duplicates, malformed JSONL, multiple questions, forbidden wording, wrong dimension, required/forbidden fact fragments, estimates, sensitive labels, and source linkage.
- [ ] Verify RED because `resume_agent.evaluation` does not exist.
- [ ] Implement focused Pydantic models, line-numbered dataset errors, and pure named checks.
- [ ] Add at least 18 synthetic cases covering all six dimensions and adversarial situations.
- [ ] Run targeted/full tests and commit `feat: add mentor evaluation dataset and scorers`.

### Task 2: Benchmark runner and secret-safe reports

**Files:**
- Create: `resume_agent/evaluation/runner.py`
- Create: `resume_agent/evaluation/reporting.py`
- Test: `tests/test_evaluation_runner.py`
- Test: `tests/test_evaluation_reporting.py`

**Interfaces:**
- Produces: `MentorBenchmark(question_writer, fact_auditor).run(dataset, repeats, metadata) -> BenchmarkReport`.
- Produces: `write_report(report, output_dir) -> ReportFiles`.

- [ ] Write failing tests for mixed cases, repeat accounting, isolated runtime errors, exact aggregate metrics, safe metadata, JSON/Markdown output, and absence of raw case content.
- [ ] Verify RED for missing runner/reporting modules.
- [ ] Implement case-state construction, port invocation, aggregation, error categories, and atomic report writes.
- [ ] Run targeted/full tests and commit `feat: run repeatable mentor benchmarks`.

### Task 3: Configured CLI, documentation, and real smoke

**Files:**
- Create: `resume_agent/evaluation/cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Test: `tests/test_evaluation_cli.py`

**Interfaces:**
- Produces: console script `resume-agent-eval` and module entry `python -m resume_agent.evaluation.cli`.
- Consumes: `build_mentor_runtime`, bundled dataset, benchmark runner, and reporting.

- [ ] Write failing CLI tests for ready runtime, degraded runtime, invalid repeats/threshold, threshold exit code, and output file paths.
- [ ] Verify RED for missing CLI.
- [ ] Implement argparse without hidden network calls, load `.env` with exported-environment precedence, and return exit codes 0 (pass), 1 (quality threshold), 2 (configuration/input error).
- [ ] Document benchmark purpose, commands, metrics, privacy behavior, and model-comparison workflow.
- [ ] Run full tests, compileall, `git diff --check`, and a real local fake OpenAI-compatible HelloAgents smoke benchmark.
- [ ] Commit `feat: add mentor quality benchmark CLI`.
