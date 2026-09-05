# ResumeAgent Configured Agent Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically enable stateless HelloAgents mentor specialists from validated environment settings while retaining a safe, observable offline mode.

**Architecture:** A lazy runtime factory owns environment parsing and optional framework imports. Fresh factory-backed `SimpleAgent` instances prevent cross-session memory leakage. FastAPI publishes a secret-free capability model, and Streamlit displays that status before users submit answers.

**Tech Stack:** Python 3.10+, Pydantic 2, HelloAgents 1.x optional dependency, python-dotenv, FastAPI, HTTPX, Streamlit, pytest.

## Global Constraints

- Application import and offline startup must not require HelloAgents.
- Runtime construction must never issue an LLM request.
- Each structured Agent invocation uses a fresh `SimpleAgent` instance.
- API keys and full base URLs never appear in capability responses or errors.
- Existing direct dependency injection into `create_app` remains supported.
- Missing Agent capability never disables fact viewing, versioning, preview, or export.

---

### Task 1: Validated lazy mentor runtime

**Files:**
- Create: `resume_agent/agents/runtime.py`
- Modify: `resume_agent/agents/hello_agents_adapter.py`
- Modify: `pyproject.toml`
- Test: `tests/test_agent_runtime.py`
- Modify: `tests/test_mentor_agents.py`

**Interfaces:**
- Produces: `AgentRuntimeSettings.from_environ(environ) -> AgentRuntimeSettings`.
- Produces: `AgentCapabilityStatus` and `MentorRuntime`.
- Produces: `build_mentor_runtime(environ=None, framework_loader=None) -> MentorRuntime`.
- Produces: `FreshAgentRunner(factory).run(prompt) -> str`.

- [ ] Write failing tests for missing config, placeholder key, URL/numeric validation, lazy dependency import, exact HelloAgents constructor settings, fresh Agent instances, and safe provider errors.
- [ ] Run `.venv/bin/python -m pytest tests/test_agent_runtime.py tests/test_mentor_agents.py -q` and verify RED for missing runtime types.
- [ ] Implement environment parsing, lazy import, fresh factories, and error normalization. Add `agents = ["hello-agents>=1,<2", "python-dotenv>=1,<2"]`; include the same packages in `dev`.
- [ ] Install `.venv/bin/python -m pip install -e '.[dev]'` and run targeted/full tests.
- [ ] Commit `feat: configure stateless mentor agents`.

### Task 2: Capability-aware API entry point

**Files:**
- Modify: `resume_agent/api/app.py`
- Modify: `resume_agent/api/main.py`
- Modify: `resume_agent/__init__.py`
- Test: `tests/test_api_capabilities.py`
- Modify: `tests/test_api_openapi.py`

**Interfaces:**
- Produces: `GET /capabilities -> AgentCapabilityStatus`.
- Consumes: `create_app(..., agent_capabilities=...)`.

- [ ] Write failing tests for configured/degraded capability JSON, secret absence, healthy offline import, and OpenAPI route presence.
- [ ] Verify RED for the missing endpoint and constructor argument.
- [ ] Build runtime only in `api/main.py`, inject both ports and status, and retain existing `create_app` test injection behavior.
- [ ] Run targeted/full tests and commit `feat: expose mentor runtime capabilities`.

### Task 3: Capability-aware Web product and documentation

**Files:**
- Modify: `resume_agent/ui/client.py`
- Modify: `resume_agent/ui/app.py`
- Modify: `.env.example`
- Modify: `README.md`
- Test: `tests/test_ui_client.py`
- Modify: `tests/test_streamlit_app.py`

**Interfaces:**
- Produces: `HttpResumeAgentClient.capabilities() -> AgentCapabilityStatus`.
- Consumes: capability status in sidebar and mentor workspace.

- [ ] Write failing HTTP client and AppTest cases for enabled/degraded capability displays.
- [ ] Verify RED for the missing client method and UI copy.
- [ ] Fetch capabilities without retrying, display model-safe status, and show setup guidance before an unavailable mentor answer.
- [ ] Document `pip install -e '.[agents,web]'`, all variables, `.env` precedence, optional offline mode, and no-startup-call behavior.
- [ ] Run full tests, compileall, `git diff --check`, and real offline Uvicorn/Streamlit smoke.
- [ ] Commit `feat: surface mentor agent readiness`.
