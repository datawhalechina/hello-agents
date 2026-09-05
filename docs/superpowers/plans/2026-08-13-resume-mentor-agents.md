# ResumeAgent Mentor Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the mentor core to specialized, structured-output agents while preserving an offline deterministic question path.

**Architecture:** An `AgentRunner` port hides HelloAgents. A reusable structured-output executor extracts and validates one JSON object, retries once with validation feedback, and raises a recoverable typed error. Fact-audit and question-writer adapters inject authoritative IDs and revisions in Python so LLM output can never select persistence targets.

**Tech Stack:** Python 3.10+, Pydantic 2, HelloAgents-compatible `run(str) -> str` adapter, pytest.

## Global Constraints

- LLM output never writes directly to the fact base.
- The fact-base revision and active experience ID come from application state, not model output.
- Invalid structured output retries exactly once.
- A question-writer response contains exactly one nonempty question.
- Tests use fake runners and require no API key or network.
- Deterministic question templates remain available when no LLM is configured.

---

### Task 1: Structured agent execution

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/agents/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/agents/structured.py`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_structured_agent.py`

**Interfaces:**
- Produces: `AgentRunner`, `AgentOutputError`, `extract_json_object(text)`, and `run_structured(runner, prompt, response_model)`.

- [ ] Write tests proving fenced JSON extraction, surrounding-text extraction, one retry after validation failure, and a typed error after two failures.
- [ ] Run `python -m pytest tests/test_structured_agent.py -q` and verify import failure.
- [ ] Implement brace-aware JSON extraction using `json.JSONDecoder.raw_decode`; do not use a greedy regular expression.
- [ ] Validate with `response_model.model_validate`; on failure append the validation message and exact schema to a single retry prompt.
- [ ] Run the test file and verify all cases pass.
- [ ] Commit with `git commit -m "feat: validate structured agent output"`.

### Task 2: Fact-audit and mentor-question agents

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/agents/prompts.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/agents/mentor.py`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_mentor_agents.py`

**Interfaces:**
- Consumes: `AgentRunner`, `FactAuditAgent`, `QuestionWriterAgent`, and domain models.
- Produces: `StructuredFactAuditAgent`, `StructuredQuestionWriterAgent`, and `DeterministicQuestionWriter`.

- [ ] Write a failing fact-audit test where the runner returns `dimension`, `values`, and `rationale`; assert the persisted target IDs and revision come from the supplied session and base.
- [ ] Write a failing audit test proving `estimated` remains estimated and `sensitive` remains an independent flag.
- [ ] Write failing question tests for direct, recall-anchor, and alternative-evidence escalation, plus rejection of two questions in one response.
- [ ] Run `python -m pytest tests/test_mentor_agents.py -q` and verify import failure.
- [ ] Implement Chinese prompts that forbid invented facts, distinguish personal from team outcomes, label estimates, and request one question per turn.
- [ ] Implement structured adapters and deterministic per-dimension templates.
- [ ] Run mentor-agent tests and the full suite.
- [ ] Commit with `git commit -m "feat: add evidence mentor specialist agents"`.

### Task 3: HelloAgents bridge and public assembly

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/agents/hello_agents_adapter.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/__init__.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/README.md`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_agent_public_api.py`

**Interfaces:**
- Produces: `HelloAgentsRunner(agent)`, `build_mentor_agents(audit_agent, question_agent)`, and stable public imports for all three mentor adapters.

- [ ] Write a failing smoke test using fake objects whose `run` method records prompts and returns valid JSON.
- [ ] Run `python -m pytest tests/test_agent_public_api.py -q` and verify missing imports.
- [ ] Implement a dependency-light bridge that wraps existing `SimpleAgent` instances without importing or constructing them at module import time.
- [ ] Add `build_mentor_agents` returning a `StructuredFactAuditAgent` and `StructuredQuestionWriterAgent` from two wrapped agents.
- [ ] Document how the notebook passes its existing `SimpleAgent` instances into the package.
- [ ] Run the full test suite, compile the package, and check whitespace.
- [ ] Commit with `git commit -m "docs: expose ResumeAgent mentor adapters"`.

