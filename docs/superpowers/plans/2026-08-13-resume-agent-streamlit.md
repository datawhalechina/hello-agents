# ResumeAgent Streamlit Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a tested Streamlit product shell where new users are led by a mentor conversation, can inspect confirmed evidence, manage job-specific versions, and see honest preview capability status.

**Architecture:** First make the FastAPI contract rerun-safe and recoverable. A Streamlit-independent HTTP client maps API responses to the existing Pydantic models and typed errors. A single Streamlit entry point uses four sidebar-selected workspaces and stores only resource identifiers plus transient UI selections in session state; the API remains authoritative.

**Tech Stack:** Streamlit 1.50+, HTTPX, FastAPI, Pydantic 2, pytest, Streamlit AppTest.

## Global Constraints

- The mentor conversation is the default workspace.
- Streamlit never opens SQLite, imports Notebook functions, or computes interview quality and skip rules.
- No mutation happens during passive page rendering or rerun.
- The current question endpoint is idempotent.
- Pending proposals require explicit confirm or reject.
- UI session state stores IDs, not mutable copies of fact bases or versions.
- HTTP mutations are not automatically retried.
- Preview and review show capability-aware empty states until renderer APIs exist.
- Sensitive facts are collapsed by default.

---

### Task 1: Rerun-safe interview read model

**Files:**
- Modify domain models, interview service, repository protocols, SQLite repositories, API schemas/routes.
- Test: `tests/test_api_ui_contract.py`

**Deliverable:** list fact bases; list/recover sessions by fact base and experience; server-side experience quality endpoint; persisted idempotent current question; reject proposal.

- [ ] Write failing tests covering all five operations and proving two current-question GETs return the same question without adding duplicate messages.
- [ ] Verify RED.
- [ ] Implement repository list operations, `InterviewQuestion` persistence, session recovery, quality read model, and rejection.
- [ ] Verify targeted and full tests; commit `feat: make mentor API UI-ready`.

### Task 2: Typed HTTP client

**Files:**
- Add HTTPX runtime dependency and Streamlit web optional dependencies.
- Create: `resume_agent/ui/client.py`, `resume_agent/ui/state.py`.
- Test: `tests/test_ui_client.py`, `tests/test_ui_state.py`.

**Deliverable:** `HttpResumeAgentClient`, typed error mapping, and serializable `WorkspaceState` with query-param helpers.

- [ ] Write failing MockTransport tests for model parsing, 404/409/422/502/503 mapping, network failures, and no retry of POST.
- [ ] Write failing state tests for ID-only serialization and recovery.
- [ ] Implement the client protocol and state helpers without importing Streamlit.
- [ ] Verify targeted/full tests; commit `feat: add ResumeAgent web client`.

### Task 3: Streamlit four-workspace application

**Files:**
- Create: `resume_agent/ui/app.py`, `resume_agent/ui/components.py`, `resume_agent/ui/theme.py`.
- Test: `tests/test_streamlit_app.py`.

**Deliverable:** default mentor chat, evidence portfolio, resume versions, and preview/review empty state.

- [ ] Write AppTest smoke tests for page title, four navigation choices, onboarding form, API-offline state, and preview empty state.
- [ ] Verify RED.
- [ ] Implement onboarding, sidebar context, explicit form/button mutations, proposal cards, read-only evidence accordions, version forms/cards, delete confirmation, and disabled preview controls.
- [ ] Use injectable/fake client construction for AppTest; never launch a real API in tests.
- [ ] Verify AppTest and full suite; commit `feat: add ResumeAgent Streamlit workspace`.

### Task 4: Runtime entry point and documentation

**Files:**
- Create: `streamlit_app.py`.
- Modify: `README.md`, `pyproject.toml`, public exports.
- Test: import/runtime smoke.

**Deliverable:** documented two-process local startup and tested Streamlit entry point.

- [ ] Add `RESUME_AGENT_API_URL` configuration and document starting API then UI.
- [ ] Document recovery URL/query behavior and current offline/LLM capability limitations.
- [ ] Run all tests, compileall, Streamlit AppTest, and whitespace checks.
- [ ] Commit `docs: add ResumeAgent web app entry point`.

