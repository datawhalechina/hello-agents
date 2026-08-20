# MoneyMirrorAgent ExecPlan

## Project Goal

Build a runnable Hello-Agents graduation project that turns a user-provided CSV bill into deterministic financial facts, agent-led coaching, dynamic Money Quests, persistent Memory, monthly Reflection, and a Markdown report.

## Current State

- CLI is the product entry point: `python main.py --csv <账单CSV>`.
- Runtime uses a configured OpenAI-compatible LLM for explanations, coaching, Quest orchestration, Reflection, and Markdown reporting.
- Python tools own import normalization, calculation, anomaly detection, budget and goal projection, subscription detection, and Quest progress validation.
- SQLite stores category corrections, goals, budget snapshots, quests, achievements, reflections, and conversation records.

## Milestones

| Milestone | Status |
| --- | --- |
| CSV import, deterministic analysis, SQLite Memory | Completed |
| Multi-agent coordinator and Hello-Agents runtime integration | Completed |
| Terminal coaching and LLM-generated Markdown report | Completed |
| Dynamic Quest orchestration with Python validation | Completed |
| Configurable evidence-based persona catalog | Completed |
| Regression tests and CLI runtime audit | Completed |

## Completed

- Implemented the coordinator, TransactionAgent, PatternAgent, PersonaAgent, GoalAgent, QuestAgent, ReflectionAgent, and ConversationAgent.
- Added five sample CSV bills alongside support for arbitrary user CSV paths.
- Implemented an evidence-based persona pipeline: feature extraction, JSON scoring, threshold validation, Top-K selection, and LLM narrative.
- Expanded `src/config/personas.json` to 14 behavior-driven archetypes, including night, weekend, dining, subscriptions, learning, payday rhythm, flexible spending, saving, planning, and mindful-spending dimensions.
- Added `payday` and `impulse_inverse` to the feature contract so configuration can express paycheck-timing and restraint signals without embedding new persona labels in Python.
- Added regression tests for the expanded catalog, representative payday and dining behavior, and savings-rate feature preservation.
- Ran the complete CLI flow with `data/sample_01.csv` against the configured LLM service; it generated a JSON fact snapshot and a Markdown report with all expected report sections.
- Condensed the README Money Quest section to describe the task-generation flow and terminal usage at a high level.
- Removed the specified wording from QuestAgent copy configuration and generated project artifacts; retained numeric and currency-format validation.

## In Progress

- No high-priority implementation task is open for this persona-catalog iteration.

## Remaining

- Keep persona thresholds calibrated against additional anonymized user bills as they become available.
- Perform the final PR checklist before the user submits changes upstream.

## Decisions

- Persona identity is selected by deterministic feature scoring and evidence thresholds from `personas.json`.
- The LLM receives the selected archetype and verified evidence to write supportive narrative only.
- Persona catalog changes remain configuration-first; feature additions are limited to reusable behavior signals.
- User-supplied CSV content, rather than input filename, is the source of all analysis and persona evidence.

## Discoveries

- The README referenced this ExecPlan path, but the document was absent; this file restores the documented project artifact.
- Savings features now retain their actual percentage shape within the 0–100 scoring range, avoiding saturation for every savings rate above 30%.

## Test Results

| Command | Result |
| --- | --- |
| `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_persona_agent.py` | 8 passed |
| `PYTHONPATH=. .venv/bin/python -m pytest -q` | 28 passed |
| `.venv/bin/python -m compileall -q src main.py tests` | Passed |
| `timeout 180 .venv/bin/python main.py --csv data/sample_01.csv --reset --db <temp>/memory.db --output-dir <temp>/outputs` | Passed; JSON and LLM Markdown report generated |

## Known Issues

- A live CLI run requires a valid LLM configuration in `.env` and network access to the configured provider.

## Next Actions

1. Preserve passing tests after any persona calibration changes.
2. Use additional anonymized CSV bills to tune thresholds when broader behavior distributions are available.
3. Complete the PR review checklist before upstream submission.
