# ResumeAgent Public MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the usable workbench, deepen the evidence mentor, document it in three languages, and publish it as a standalone public GitHub project.

**Architecture:** Preserve FastAPI, SQLite, deterministic planning, HelloAgents adapters, and same-origin ES modules. Add only bounded mentor-state and UI improvements, then export the project subdirectory with `git subtree split` so the monorepo is not exposed.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2, SQLite, HelloAgents, vanilla JavaScript ES modules, CSS, Node test runner, pytest, Playwright CLI, GitHub CLI.

## Global Constraints

- Keep the original white two-column workbench and restrained navy/gray visual language.
- Do not add gradients, glow, glass effects, AI marketing cards, or a frontend build step.
- Only user-confirmed facts may enter generated resumes.
- Browser storage may contain selection IDs but not answers, facts, drafts, API keys, or resume HTML.
- The standalone public default branch is `main`; do not rewrite or remove the tutorial fork history.

---

### Task 1: Mentor follow-up progression

**Files:**
- Modify: `resume_agent/application/interview_service.py`
- Modify: `resume_agent/agents/mentor.py`
- Test: `tests/test_interview_service.py`
- Test: `tests/test_mentor_agents.py`

**Interfaces:**
- Consumes: `InterviewSession.current_question`, `InterviewSession.attempts`, `QuestionPlan.dimension`, and `QuestionPlan.escalation`.
- Produces: dimension-specific deterministic recall questions and persisted attempt state when an answer addresses a different dimension.

- [ ] Add a failing service test: ask for `context`, return an `action` proposal, confirm it, and assert the next `context` question uses `recall_anchors` rather than the direct wording.
- [ ] Run `.venv/bin/python -m pytest tests/test_interview_service.py tests/test_mentor_agents.py -q` and confirm the new assertion fails.
- [ ] In `answer`, retain the asked dimension before clearing `current_question`; after proposal validation, increment that dimension's attempt only when the proposal dimension differs.
- [ ] Replace the single generic recall/alternative strings in `DeterministicQuestionWriter` with mappings for all six dimensions, each containing exactly one question mark.
- [ ] Run the focused tests and commit `feat: improve mentor follow-up progression`.

### Task 2: Usability-first workbench polish

**Files:**
- Modify: `resume_agent/web/index.html`
- Modify: `resume_agent/web/app.js`
- Modify: `resume_agent/web/styles.css`
- Modify: `tests/test_web_entry.py`

**Interfaces:**
- Consumes: existing `bases`, `currentBase`, `experienceQuality`, tab state, and session state.
- Produces: `renderBaseSwitcher()`, `renderInterviewProgress()`, clearer action state, and accessible responsive controls.

- [ ] Add static contract assertions for the file selector and interview-progress region, then run `tests/test_web_entry.py` to verify failure.
- [ ] Add a compact header selector that lists existing files by target role and switches through `activateBase`; keep “示例档案” available only when no file exists and expose “新建档案” otherwise.
- [ ] Add an evidence-progress row to the interview tab using the existing quality report: show completed dimensions out of six and the current focus without introducing a second scoring model.
- [ ] Improve disabled/action labels and mobile header/toolbars while keeping all four tabs and the composer visible.
- [ ] Verify at 1440×900, 1024×768, and 390×844 with no page-level horizontal overflow or console errors; commit `feat: polish public workbench flow`.

### Task 3: Chinese, Japanese, and English project guides

**Files:**
- Modify: `README.md`
- Create: `README.ja.md`
- Create: `README.en.md`
- Create: `docs/assets/resume-agent-workbench.png`

**Interfaces:**
- Produces three equivalent entry documents linking to one another and describing only behavior verified in the default FastAPI workbench.

- [ ] Capture the current 1440×900 workbench screenshot into `docs/assets/resume-agent-workbench.png`.
- [ ] Rewrite `README.md` as the concise Chinese landing page with product flow, verified features, architecture, quick start, LLM variables, tests, privacy, limitations, and language links.
- [ ] Create equivalent natural Japanese and English guides; keep commands and limitation statements identical across languages.
- [ ] Scan all guides for obsolete Streamlit-default instructions and unsupported product claims; run the documented install/start/test commands available locally.
- [ ] Commit `docs: add trilingual project guides`.

### Task 4: Standalone GitHub publication

**Files:**
- Verify: `.gitignore`
- Verify: repository tracked-file list and generated subtree

**Interfaces:**
- Produces: public `https://github.com/shiyuanyeming-hub/ResumeAgent` with default branch `main` and project-only history.

- [ ] Run `.venv/bin/python -m pytest -q`, `node --test tests/web/api.test.mjs`, `.venv/bin/python -m compileall -q resume_agent`, and `git diff --check`; require zero failures.
- [ ] Confirm `.env`, SQLite databases, virtual environments, caches, and local outputs are not newly tracked.
- [ ] Create a subtree branch from `Co-creation-projects/shiyuanyeming-hub-ResumeAgent` and inspect its root tree before any remote write.
- [ ] Create the public GitHub repository with description “Evidence-first multilingual resume mentor for Chinese, Japanese, and English resumes”.
- [ ] Push the subtree branch to standalone `main`, set repository topics, and verify README rendering and remote default branch through `gh repo view`.
- [ ] Push the updated tutorial branch to its existing `origin` and report both remote URLs and final verification evidence.
