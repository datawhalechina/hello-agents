# ResumeAgent FastAPI Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the tested ResumeAgent mentor core as a local-first HTTP API suitable for Streamlit and future front ends.

**Architecture:** A `create_app` factory builds SQLite repositories and application services, while injectable fact-audit and question-writer ports keep tests offline. Thin FastAPI routes validate transport schemas and delegate all stateful operations to services. Typed exception handlers translate domain failures into stable HTTP errors.

**Tech Stack:** FastAPI, Pydantic 2, SQLite, HTTPX-backed `TestClient`, pytest, Uvicorn.

## Global Constraints

- Python 3.10+ and Pydantic 2.
- No model or API key is loaded during module import.
- The API is created through `create_app(database_path, ...)`; tests use a temporary database.
- Default API tests require no network.
- Unknown resources return 404, stale revisions return 409, invalid state returns 422, and unavailable/invalid agent output returns 503/502.
- Route code does not mutate aggregate internals directly; application services own mutations.

---

### Task 1: App factory and fact-base service

**Files:**
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/pyproject.toml`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application/fact_base_service.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/app.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/schemas.py`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_api_fact_bases.py`

**Interfaces:**
- Produces: `FactBaseService.create`, `get`, `add_experience`; `ServiceContainer`; `create_app`; `GET /health`; `POST/GET /fact-bases`; `POST /fact-bases/{id}/experiences`.

- [ ] Add `fastapi>=0.115,<1` and `uvicorn>=0.30,<1` runtime dependencies, plus `httpx>=0.27,<1` to the dev extra; install the editable project.
- [ ] Write failing TestClient tests for health, fact-base creation, persistence-backed fetch, adding an experience, and 404 lookup.
- [ ] Verify RED because `resume_agent.api` does not exist.
- [ ] Implement `FactBaseService` so adding an experience increments the canonical revision and saves with the prior revision.
- [ ] Implement request schemas and the app factory with repository objects stored in a typed container on `app.state`.
- [ ] Add a `KeyError` handler returning `{"detail": "..."}` with HTTP 404.
- [ ] Verify the API fact-base tests pass and commit `feat: expose ResumeAgent fact bases API`.

### Task 2: Mentor interview endpoints

**Files:**
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/app.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/schemas.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/agents/unavailable.py`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_api_interviews.py`

**Interfaces:**
- Produces: `POST /sessions`; `POST /sessions/{id}/answers`; `POST /sessions/{id}/proposals/{proposal_id}/confirm`; `POST /sessions/{id}/unknown`; `GET /sessions/{id}/next-question`.

- [ ] Write failing tests using injected stub agents for session creation, proposal-without-mutation, confirmation, one-question response, and two-unknown skip behavior.
- [ ] Write a failing test proving an app without an LLM audit agent returns HTTP 503 for `/answers` while preserving other endpoints.
- [ ] Verify RED for missing routes.
- [ ] Add `UnavailableFactAuditAgent` and build `InterviewService` in the app container, defaulting only the question writer to `DeterministicQuestionWriter`.
- [ ] Implement transport routes that delegate to `InterviewService` and never confirm proposals automatically.
- [ ] Map `AgentUnavailableError` to 503, `AgentOutputError` to 502, and invalid state `ValueError` to 422.
- [ ] Verify interview tests and full suite pass; commit `feat: expose ResumeAgent mentor interview API`.

### Task 3: Resume-version endpoints

**Files:**
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/app.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/schemas.py`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_api_versions.py`

**Interfaces:**
- Produces: create/list/get/clone/rename/activate/delete and refresh-staleness endpoints for resume versions.

- [ ] Write failing tests that create two versions from one base, clone one, activate exactly one, rename, delete the clone without deleting the original, and mark versions stale after a base revision change.
- [ ] Verify RED for missing routes.
- [ ] Implement thin routes around `VersionService`; return HTTP 204 for successful deletion.
- [ ] Verify version endpoint tests and the full suite pass; commit `feat: expose resume version API`.

### Task 4: Runtime entry point and documentation

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/api/main.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/__init__.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/README.md`
- Test: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_api_openapi.py`

**Interfaces:**
- Produces: importable default `app`, public `create_app`, and documented local launch command.

- [ ] Write a failing test asserting OpenAPI contains fact-base, session, and version tags and all required paths.
- [ ] Verify RED for absent default entry point or metadata.
- [ ] Add a default local SQLite path configurable through `RESUME_AGENT_DB` without reading any LLM key.
- [ ] Document `uvicorn resume_agent.api.main:app --reload`, `/docs`, database location, and offline limitations.
- [ ] Run the full suite, `compileall`, `git diff --check`, and an import smoke test.
- [ ] Commit `docs: add ResumeAgent API entry point`.

