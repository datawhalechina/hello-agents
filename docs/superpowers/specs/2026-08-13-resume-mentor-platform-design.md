# ResumeAgent Mentor Platform Design

**Date:** 2026-08-13

**Status:** Approved for implementation

**Project:** `Co-creation-projects/shiyuanyeming-hub-ResumeAgent`

## 1. Product intent

ResumeAgent will evolve from a notebook-based resume generator into a standalone,
open-source resume mentoring product. Its primary job is not to ask users to fill
in a template. It should act like a patient career mentor: discover experiences
the user may have overlooked, ask increasingly concrete follow-up questions, and
turn only user-confirmed evidence into targeted Chinese, Japanese, and English
resumes.

The product has two connected outcomes:

1. Build a reusable, evidence-backed career fact base through mentor-led
   interviewing.
2. Create multiple job-specific resume versions from that fact base without
   changing or inventing the underlying facts.

## 2. Scope

### 2.1 First product release

- A multi-agent, stateful interview that discovers and deepens experiences.
- A deterministic quality gate that decides which evidence gap to address next.
- Explicit handling of confirmed facts, estimates, unknowns, and sensitive data.
- A canonical career fact base shared by all resume versions.
- Create, list, switch, clone, rename, and delete job-specific versions.
- JD analysis and version-specific experience selection, ordering, and emphasis.
- Chinese, Japanese, and English generation using the existing renderers.
- FastAPI endpoints and a Streamlit web application.
- A compatibility notebook that demonstrates the public Python API.
- Automated unit and API tests that do not require an LLM or network access.

### 2.2 Deferred work

- Parsing uploaded PDF or DOCX resumes.
- Authentication, teams, cloud synchronization, and billing.
- Job-board scraping or automatic job applications.
- Collaborative editing.
- Production deployment infrastructure.
- A custom React front end. The API boundary will allow one later.

## 3. Architectural principles

1. **Evidence before prose.** Agents collect and confirm facts before any writer
   turns them into resume language.
2. **Deterministic control, generative language.** Python controls state,
   scoring, persistence, version isolation, and validation. LLMs understand free
   text, formulate natural questions, analyze JDs, and draft prose.
3. **One canonical truth.** Job-specific versions reference facts; they do not
   copy and silently mutate them.
4. **Structured agent boundaries.** Every agent accepts and returns validated
   Pydantic models. Free-form LLM text never writes directly to persistence.
5. **Framework isolation.** HelloAgents is used through an adapter so the domain
   and application layers do not depend on a particular LLM framework.
6. **Offline-testable core.** Question planning, quality scoring, versioning,
   validation, and storage work without API credentials.

## 4. System architecture

The notebook will no longer contain the production implementation. The project
will use the following package boundaries:

```text
resume_agent/
  domain/          # Models, enums, quality rubric, invariants
  application/     # Interview and version use cases
  agents/          # Specialized agents and prompts
  infrastructure/  # SQLite repositories and HelloAgents adapter
  api/             # FastAPI routes and schemas
  ui/              # Streamlit application
  renderers/       # Chinese, Japanese, English, HTML and PDF output
tests/
main.ipynb          # Teaching/demo client of the public API
```

The first release uses SQLite through a repository interface. SQLite provides
safe local persistence and queryable version history while keeping installation
simple. A later PostgreSQL repository can implement the same interfaces.

## 5. Multi-agent team

### 5.1 Mentor orchestrator

Owns the interview phase and selects the next specialist. It cannot edit facts.
Its decisions are constrained by the deterministic interview state machine.

### 5.2 Career-target agent

Clarifies target role, seniority, industry, country, language, and constraints.
It creates a target profile used to score the relevance of later questions.

### 5.3 Experience-discovery agent

Helps users recall employment, internships, projects, research, coursework,
volunteering, leadership, competitions, and independent work. It is especially
important for students and career changers who may not recognize an activity as
resume-worthy.

### 5.4 Evidence-deepening agent

Asks one focused question at a time about context, responsibility, action,
method, result, or evidence. It uses examples and recall anchors but never
suggests facts as if the user had already supplied them.

### 5.5 Fact-audit agent

Extracts proposed facts from an answer and labels each value as `confirmed`,
`estimated`, or `unverified`. Sensitivity is a separate flag because a value can
be both confirmed and sensitive. The user confirms proposed changes before they
enter the canonical fact base.

### 5.6 JD-analysis agent

Extracts responsibilities, hard requirements, preferred qualifications,
keywords, and implied capabilities from a job description.

### 5.7 Version-strategy agent

Selects relevant confirmed experiences, proposes their order and emphasis, and
identifies missing evidence. It may ask the orchestrator to reopen a targeted
interview, but it may not invent a capability to satisfy a JD.

### 5.8 Language-writer agents

Independent Chinese, Japanese, and English writers apply their own resume
conventions. Japanese output retains the two-document format and era rules;
English remains ATS-safe; Chinese remains concise and role-focused.

### 5.9 HR/ATS-review agent

Reviews a generated version for evidence strength, relevance, clarity, language,
and ATS compatibility. Its feedback becomes either a prose revision or a
targeted evidence request.

## 6. Career fact model

Every durable entity has a stable UUID and timestamps. The canonical fact base
contains profile details, education, experiences, projects, skills, and target
preferences.

An experience contains:

- organization, role, location, and dates;
- `context`: the problem or situation;
- `responsibility`: the user's personal ownership;
- `actions`: concrete steps the user performed;
- `methods`: tools, techniques, and professional methods;
- `results`: observed outcomes;
- `evidence`: numbers, scale, frequency, artifacts, adoption, or feedback;
- linked skills and source answer identifiers;
- per-value confidence status and sensitivity flag.

The system distinguishes team outcomes from individual contributions. Estimated
numbers remain visibly marked and are never silently upgraded to confirmed.

## 7. Mentor interview algorithm

### 7.1 Phases

1. **Orient:** understand the user's goal and preferred interview language.
2. **Discover:** build a broad inventory before deciding that the user lacks
   experience.
3. **Deepen:** improve one high-value experience at a time.
4. **Confirm:** show a concise summary and ask the user to accept or correct the
   proposed facts.
5. **Synthesize:** show the evidence portfolio and remaining optional gaps.
6. **Revisit:** reopen a targeted gap when a selected JD requires it.

### 7.2 Six-dimensional quality rubric

Each experience is scored from 0 to 2 on:

- context;
- responsibility;
- action;
- method;
- result;
- evidence.

`0` means absent, `1` means present but vague, and `2` means concrete. An
experience passes the initial quality gate when:

- at least four dimensions score 1 or more;
- action scores at least 1; and
- result or evidence scores at least 1.

The system may continue improving a passing experience when the target-role
relevance is high and a concrete gap remains.

### 7.3 Question selection

The deterministic planner generates candidate gaps and ranks each candidate:

```text
priority =
    0.30 * missing_information
  + 0.25 * target_relevance
  + 0.20 * differentiating_value
  + 0.15 * estimated_answerability
  + 0.10 * freshness
  - repetition_penalty
  - fatigue_penalty
```

The highest-ranked eligible gap becomes the single topic for the next question.
The evidence-deepening agent turns that topic into conversational language.

Question escalation has three levels:

1. Direct question.
2. Recall anchors, such as time saved, people served, frequency, before/after,
   deliverables, adoption, or feedback.
3. Alternative evidence when a numeric result is unavailable.

After the user twice states that they do not know, or explicitly asks to skip,
the gap is marked `skipped` for the current session. This prevents an aggressive
or infinite interview while preserving the quality-driven stopping rule.

### 7.4 Language and safety behavior

- Ask one question per turn.
- Explain why a difficult question matters when useful.
- Prefer concrete prompts over generic requests such as “tell me more.”
- Do not pressure users to disclose protected or sensitive information.
- Never fabricate numbers. Ranges supplied by the user are stored as estimates.
- Allow corrections, deletion, and sensitivity marking at any time.
- Summarize each experience for confirmation before advancing.

## 8. Resume version model

A resume version stores only a job-specific overlay:

- stable version ID, display name, status, and timestamps;
- target role, company, locale, and raw JD;
- structured JD analysis;
- referenced experience and project IDs;
- ordering, emphasis, selected skills, and optional exclusion rules;
- language and style choices;
- generation and review metadata;
- the canonical fact-base revision used to generate it.

Supported operations are create, list, get, switch active, clone, rename, and
delete. Deleting a version never deletes canonical facts. Deleting a referenced
fact requires an explicit warning and causes affected versions to become stale.

When canonical facts change, versions that reference the changed entities are
marked stale and can be regenerated. This avoids silent drift between a resume
and its source evidence.

## 9. Main workflows

### 9.1 Mentor interview

1. UI sends a user message to the interview API.
2. The application records the message and reads session state.
3. The orchestrator selects discovery, deepening, or confirmation.
4. The fact-audit agent produces a structured proposal.
5. The application validates the proposal and exposes it for confirmation.
6. Confirmed changes update the fact base in one transaction.
7. The quality planner selects the next gap.
8. The specialist agent asks one focused follow-up question.

### 9.2 Create a targeted version

1. User creates a version and supplies a JD or target profile.
2. JD-analysis produces structured requirements.
3. Version strategy matches requirements to confirmed evidence.
4. Missing high-value evidence optionally reopens the interview.
5. User accepts the proposed selection and ordering.
6. Language writers and deterministic renderers produce output.
7. HR/ATS review either requests prose changes or identifies a fact gap.

## 10. API and web application

The FastAPI service exposes resource-oriented endpoints for health, fact bases,
interview sessions, messages, fact proposals, resume versions, generation, and
review. Mutating endpoints return the updated resource and use clear 4xx errors
for invalid state transitions.

The Streamlit application has four primary views:

1. **Mentor chat:** conversation, current focus, and interview progress.
2. **Evidence portfolio:** confirmed experiences, quality dimensions, estimates,
   sensitive fields, and corrections.
3. **Resume versions:** JD, match status, selected evidence, and version actions.
4. **Preview and review:** Chinese, Japanese, and English previews, style choice,
   feedback, and export.

The UI must show that the mentor is collecting evidence rather than merely
chatting. It must also make estimates and unconfirmed proposals visually clear.

## 11. Error handling and resilience

- Validate all LLM outputs with Pydantic.
- Retry one time with validation feedback when structured output is invalid.
- If the retry fails, preserve the user message and return a recoverable error;
  never discard an answer.
- Use database transactions for fact confirmation and version changes.
- Use optimistic revision checks to prevent stale writes.
- Agent timeouts produce a retry option and do not corrupt session state.
- Generation failure in one language does not delete successful outputs in
  another language.
- Local deterministic features remain available without an API key.

## 12. Testing strategy

### Unit tests

- Six-dimensional quality scoring and pass conditions.
- Question ranking, repetition penalty, fatigue handling, and skip behavior.
- Confidence-status and sensitivity invariants.
- Fact confirmation and revision conflicts.
- Version CRUD, clone isolation, stale detection, and deletion behavior.
- Numeric consistency and non-fabrication validators.

### Contract and integration tests

- Each agent adapter returns validated structured output using fake LLMs.
- Full interview turn from message to proposed facts and next question.
- Targeted version creation from a known fact base and JD analysis.
- SQLite persistence across application restarts.
- FastAPI success and failure responses.

### End-to-end smoke test

A deterministic scripted user completes discovery, deepening, confirmation,
version creation, and generation without network access. Live LLM tests are
optional and excluded from the default test suite.

## 13. Migration plan

Implementation will proceed as vertical slices:

1. Create the package, domain models, quality planner, and tests.
2. Add SQLite repositories and resume-version use cases.
3. Add the multi-agent interfaces, fake agents, and interview orchestration.
4. Adapt HelloAgents and existing prompts behind the interfaces.
5. Expose FastAPI endpoints.
6. Build the Streamlit product flow.
7. Move existing renderers into the package and convert the notebook into a
   compatibility demo.

Existing generated files remain usable during migration. The current notebook
will not be removed until the package path covers its demonstrated behavior.

## 14. Acceptance criteria

The first release is complete when a new user can:

1. start an interview and identify at least one experience;
2. receive focused follow-up questions until the quality gate passes or they
   explicitly skip a gap;
3. review and confirm the extracted evidence;
4. create two resume versions from one canonical fact base;
5. change one base fact and see both affected versions marked stale;
6. clone or delete one version without changing the other;
7. generate role-targeted output while retaining numeric and factual
   consistency; and
8. complete this flow through both tested Python services and the web UI.
