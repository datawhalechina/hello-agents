# ResumeAgent Mentor Evaluation Design

## Goal

Create a repeatable benchmark that answers whether the mentor asks useful, safe questions and extracts only evidence the candidate actually supplied. The benchmark must compare prompts or models without making an LLM judge mandatory.

## Evaluation Strategy

The first version uses deterministic contract checks over a curated synthetic dataset. These checks are the highest-value safety gates for resume mentoring because they do not vary between runs:

- one question per turn;
- question addresses the planned evidence dimension and escalation style;
- no invented premise, coercive sensitive-data request, or forbidden wording;
- fact proposal selects the expected dimension;
- required source claims are retained;
- forbidden or invented claims are absent;
- estimated numbers and sensitive flags remain correctly labelled;
- every proposal remains unconfirmed and linked to the source message.

An optional semantic judge can be added later, but it cannot override a failed hallucination, privacy, or schema gate.

## Dataset

`resume_agent/evaluation/datasets/mentor_v1.jsonl` is packaged with the CLI and contains versioned synthetic cases with stable IDs. No real candidate data is included.

Question cases contain target, experience state, requested dimension/escalation, and lexical expectations such as `must_include_any`, `must_not_include`, and `expected_question_marks`.

Audit cases contain a user answer and expected proposal behavior: dimension, required fact fragments, forbidden fragments, confidence, specificity, and sensitive flag. Cases cover all six dimensions plus:

- team result versus personal contribution;
- approximate numbers;
- confidential numbers;
- “I do not remember” uncertainty;
- prompt injection asking the Agent to invent achievements;
- answers containing both Chinese and English;
- absence of numeric evidence;
- negated capabilities.

## Architecture

`resume_agent/evaluation/models.py` defines cases, per-case results, metric totals, and benchmark report. `dataset.py` validates JSONL uniqueness and schema. `scoring.py` evaluates actual questions/proposals without calling a model. `runner.py` invokes the configured question-writer and fact-audit ports and aggregates failures while continuing after individual Agent errors.

The runner accepts the existing application ports, so tests use deterministic fakes and production runs use `build_mentor_runtime`. It repeats each case a configurable number of times to expose nondeterminism. A case passes only if every required deterministic gate passes on every repeat.

## Metrics

The report includes:

- question contract pass rate;
- audit dimension accuracy;
- evidence recall rate;
- hallucination-free rate;
- confidence/sensitivity label accuracy;
- schema/runtime success rate;
- strict case pass rate.

`strict_pass_rate` is the release gate. The CLI accepts `--fail-under` and exits nonzero when the threshold is missed.

## CLI and Reports

`python -m resume_agent.evaluation.cli` loads `.env`, builds the standard mentor runtime, runs the bundled dataset, and writes timestamped JSON plus Markdown under `evaluation/reports/`. `--dataset`, `--repeats`, `--fail-under`, and `--output-dir` are supported.

Reports include model/framework, dataset version, aggregate metrics, failed case IDs, failed check names, and safe error categories. They omit API keys, base URLs, full prompts, raw user answers, and raw model outputs.

If the mentor runtime is degraded, the CLI exits with a clear setup message and does not create a misleading report.

## Testing

- Schema tests reject duplicate IDs, unknown kinds, invalid confidence expectations, and malformed JSONL.
- Scoring tests prove hallucinated facts, wrong dimensions, multiple questions, coercive wording, and incorrect labels fail independently.
- Runner tests prove per-case errors do not abort the benchmark, repeats are counted, metrics aggregate correctly, and report serialization excludes raw input/output.
- CLI tests cover success, threshold failure, and degraded runtime without network calls.
- A local fake OpenAI-compatible server smoke test exercises the actual HelloAgents runtime and produces a benchmark report without paid API usage.
