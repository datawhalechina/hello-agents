# ResumeAgent Mentor Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline-testable mentor interview and multi-version core that turns confirmed career evidence into isolated, stale-aware resume versions.

**Architecture:** Add a `resume_agent` Python package beside the existing notebook. Pydantic domain models enforce evidence and version invariants; deterministic services score experience quality, choose the next evidence gap, orchestrate specialized agent ports, and persist aggregate snapshots through repository interfaces. SQLite adapters store JSON snapshots locally without coupling the domain to SQL.

**Tech Stack:** Python 3.10+, Pydantic 2, pytest, standard-library `sqlite3`, existing HelloAgents integration in a later plan.

## Global Constraints

- Production logic must not be added to `main.ipynb`; the notebook remains a client of the package.
- No network or LLM credentials are required by the default test suite.
- LLM-originated facts remain proposals until explicitly confirmed.
- Confidence status and sensitivity are independent fields.
- Resume versions reference canonical experience IDs and never copy or mutate canonical facts.
- Ask one question per interview turn and stop re-asking a skipped gap.
- A quality gate requires four present dimensions, a nonempty action, and a nonempty result or evidence.
- Work only inside `Co-creation-projects/shiyuanyeming-hub-ResumeAgent` except for this plan and its design document.

---

## File map

- `pyproject.toml`: package metadata, runtime dependency, and pytest configuration.
- `resume_agent/domain/models.py`: evidence, experience, target, fact-base, session, proposal, and resume-version models.
- `resume_agent/domain/quality.py`: six-dimensional scoring and gate rules.
- `resume_agent/application/question_planner.py`: deterministic gap ranking.
- `resume_agent/application/ports.py`: repository and specialized-agent protocols.
- `resume_agent/application/interview_service.py`: interview state transitions and proposal confirmation.
- `resume_agent/application/version_service.py`: version lifecycle and stale detection.
- `resume_agent/infrastructure/sqlite_repositories.py`: SQLite snapshot persistence.
- `resume_agent/__init__.py`: stable public imports.
- `tests/`: unit and persistence tests mirroring those responsibilities.

### Task 1: Package and evidence domain

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/pyproject.toml`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/domain/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/domain/models.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_models.py`

**Interfaces:**
- Produces: `FactValue`, `Experience`, `CareerTarget`, `CareerFactBase`, `InterviewSession`, `FactProposal`, `ResumeVersion`, `ConfidenceStatus`, `Specificity`, `QualityDimension`, `InterviewPhase`, and `VersionStatus`.
- Invariant: `CareerFactBase.confirm(proposal)` increments `revision` once and only accepts a proposal whose `fact_base_revision` matches.

- [ ] **Step 1: Write model tests first**

```python
from uuid import uuid4

import pytest
from pydantic import ValidationError

from resume_agent.domain.models import (
    CareerFactBase,
    ConfidenceStatus,
    FactProposal,
    FactValue,
    QualityDimension,
    Specificity,
)


def test_sensitive_confirmed_fact_keeps_both_attributes():
    fact = FactValue(
        text="Managed a six-person team",
        confidence=ConfidenceStatus.CONFIRMED,
        specificity=Specificity.CONCRETE,
        sensitive=True,
    )
    assert fact.confidence is ConfidenceStatus.CONFIRMED
    assert fact.sensitive is True


def test_empty_fact_text_is_rejected():
    with pytest.raises(ValidationError):
        FactValue(text="   ")


def test_confirming_proposal_updates_experience_and_revision():
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Data Analyst")
    proposal = FactProposal(
        fact_base_revision=0,
        experience_id=experience.id,
        dimension=QualityDimension.ACTION,
        values=[FactValue(text="Built an automated dashboard")],
    )
    base.confirm(proposal)
    assert base.revision == 1
    assert base.get_experience(experience.id).statements[QualityDimension.ACTION][0].text == "Built an automated dashboard"


def test_stale_proposal_is_rejected():
    base = CareerFactBase(revision=2)
    experience = base.add_experience("Yunshu", "Data Analyst")
    proposal = FactProposal(
        fact_base_revision=1,
        experience_id=experience.id,
        dimension=QualityDimension.ACTION,
        values=[FactValue(text="Built an automated dashboard")],
    )
    with pytest.raises(ValueError, match="revision conflict"):
        base.confirm(proposal)
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `python -m pytest tests/test_models.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'resume_agent'`.

- [ ] **Step 3: Add package metadata and minimal domain implementation**

`pyproject.toml` declares `pydantic>=2.7,<3`, `requires-python = ">=3.10"`, package discovery for `resume_agent*`, and pytest `testpaths = ["tests"]`.

`models.py` defines string enums for confidence, specificity, dimension, phase,
and version status. `FactValue` strips and rejects empty text. `Experience`
initializes all six dimension keys with empty lists. `CareerFactBase` provides:

```python
def add_experience(self, organization: str, role: str) -> Experience: ...
def get_experience(self, experience_id: UUID) -> Experience: ...
def confirm(self, proposal: FactProposal) -> None: ...
```

`confirm` validates the revision and experience ID, appends the proposed values,
records the proposal ID in `confirmed_proposal_ids`, and increments the revision.

- [ ] **Step 4: Run model tests and verify GREEN**

Run: `python -m pytest tests/test_models.py -q`

Expected: `4 passed`.

- [ ] **Step 5: Commit the domain slice**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/pyproject.toml \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_models.py
git commit -m "feat: add ResumeAgent evidence domain"
```

### Task 2: Quality gate and question planner

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/domain/quality.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application/question_planner.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_quality.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_question_planner.py`

**Interfaces:**
- Consumes: `Experience`, `QualityDimension`, and `Specificity` from Task 1.
- Produces: `QualityReport`, `evaluate_experience(experience)`, `PlanningSignals`, `QuestionHistory`, `QuestionPlan`, and `QuestionPlanner.plan(...)`.

- [ ] **Step 1: Write failing quality-gate tests**

```python
from resume_agent.domain.models import Experience, FactValue, QualityDimension, Specificity
from resume_agent.domain.quality import evaluate_experience


def put(exp, dimension, text, specificity=Specificity.PRESENT):
    exp.statements[dimension].append(FactValue(text=text, specificity=specificity))


def test_gate_requires_action_even_with_four_other_dimensions():
    exp = Experience(organization="A", role="Analyst")
    for dim in [QualityDimension.CONTEXT, QualityDimension.RESPONSIBILITY,
                QualityDimension.METHOD, QualityDimension.RESULT]:
        put(exp, dim, dim.value)
    assert evaluate_experience(exp).passes_gate is False


def test_gate_passes_with_four_dimensions_action_and_result():
    exp = Experience(organization="A", role="Analyst")
    for dim in [QualityDimension.CONTEXT, QualityDimension.RESPONSIBILITY,
                QualityDimension.ACTION, QualityDimension.RESULT]:
        put(exp, dim, dim.value)
    report = evaluate_experience(exp)
    assert report.passes_gate is True
    assert report.scores[QualityDimension.ACTION] == 1


def test_concrete_fact_scores_two():
    exp = Experience(organization="A", role="Analyst")
    put(exp, QualityDimension.EVIDENCE, "Saved four hours weekly", Specificity.CONCRETE)
    assert evaluate_experience(exp).scores[QualityDimension.EVIDENCE] == 2
```

- [ ] **Step 2: Run quality tests and verify RED**

Run: `python -m pytest tests/test_quality.py -q`

Expected: import fails because `resume_agent.domain.quality` does not exist.

- [ ] **Step 3: Implement scoring and gate rules**

`evaluate_experience` assigns 0 to an empty dimension, 1 when its highest
specificity is `present`, and 2 when it is `concrete`. It returns immutable
`QualityReport(scores, present_dimensions, total, passes_gate)`.

- [ ] **Step 4: Verify quality tests GREEN**

Run: `python -m pytest tests/test_quality.py -q`

Expected: `3 passed`.

- [ ] **Step 5: Write failing planner tests**

```python
from resume_agent.application.question_planner import PlanningSignals, QuestionHistory, QuestionPlanner
from resume_agent.domain.models import Experience, FactValue, QualityDimension


def test_planner_selects_highest_value_missing_dimension():
    exp = Experience(organization="A", role="Analyst")
    exp.statements[QualityDimension.ACTION].append(FactValue(text="Built a dashboard"))
    signals = PlanningSignals(
        target_relevance={QualityDimension.RESULT: 1.0, QualityDimension.METHOD: 0.2},
        differentiating_value={QualityDimension.RESULT: 1.0},
        answerability={QualityDimension.RESULT: 0.8},
    )
    plan = QuestionPlanner().plan(exp, signals, QuestionHistory())
    assert plan.dimension is QualityDimension.RESULT


def test_planner_never_returns_skipped_dimension():
    exp = Experience(organization="A", role="Analyst")
    history = QuestionHistory(skipped={QualityDimension.RESULT})
    plan = QuestionPlanner().plan(exp, PlanningSignals(), history)
    assert plan is not None
    assert plan.dimension is not QualityDimension.RESULT


def test_planner_stops_when_gate_passes_by_default():
    exp = Experience(organization="A", role="Analyst")
    for dimension in [QualityDimension.CONTEXT, QualityDimension.RESPONSIBILITY,
                      QualityDimension.ACTION, QualityDimension.RESULT]:
        exp.statements[dimension].append(FactValue(text=dimension.value))
    assert QuestionPlanner().plan(exp, PlanningSignals(), QuestionHistory()) is None
```

- [ ] **Step 6: Run planner tests and verify RED**

Run: `python -m pytest tests/test_question_planner.py -q`

Expected: import fails because `question_planner` does not exist.

- [ ] **Step 7: Implement weighted planning**

Implement the exact formula from the design. Missing information is
`(2 - score) / 2`; absent signal values default to `0.5`; freshness is `1.0` on
the first attempt and `0.5` afterward; repetition penalty is `0.25 * attempts`;
fatigue penalty is `min(0.3, 0.03 * total_attempts)`. Exclude skipped dimensions.
Return `None` when the quality gate passes unless `continue_after_gate=True`.

- [ ] **Step 8: Verify planner and quality tests GREEN**

Run: `python -m pytest tests/test_quality.py tests/test_question_planner.py -q`

Expected: all tests pass.

- [ ] **Step 9: Commit the mentor algorithm**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_quality.py \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_question_planner.py
git commit -m "feat: add evidence quality question planner"
```

### Task 3: Multi-agent interview orchestration

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application/ports.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application/interview_service.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/fakes.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_interview_service.py`

**Interfaces:**
- Consumes: Task 1 models and Task 2 planner.
- Produces: `FactAuditAgent`, `QuestionWriterAgent`, `FactBaseRepository`, `SessionRepository`, `InterviewTurn`, and `InterviewService`.

- [ ] **Step 1: Write failing orchestration tests**

```python
from resume_agent.application.interview_service import InterviewService
from resume_agent.domain.models import CareerFactBase, InterviewSession, QualityDimension
from tests.fakes import InMemoryFactBaseRepository, InMemorySessionRepository, StubAuditAgent, StubQuestionWriter


def make_interview():
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Data Analyst")
    session = InterviewSession(fact_base_id=base.id, active_experience_id=experience.id)
    bases = InMemoryFactBaseRepository([base])
    sessions = InMemorySessionRepository([session])
    service = InterviewService(bases, sessions, StubAuditAgent(), StubQuestionWriter())
    return service, session, bases, experience


def test_answer_creates_unconfirmed_proposal_without_mutating_fact_base():
    service, session, bases, experience = make_interview()
    turn = service.answer(session.id, "I built the weekly dashboard myself")
    assert turn.proposal.dimension is QualityDimension.ACTION
    assert bases.get(session.fact_base_id).get_experience(experience.id).statements[QualityDimension.ACTION] == []


def test_confirmation_updates_base_and_returns_one_next_question():
    service, session, bases, experience = make_interview()
    turn = service.answer(session.id, "I built the weekly dashboard myself")
    result = service.confirm(session.id, turn.proposal.id)
    assert bases.get(session.fact_base_id).revision == 1
    assert len(result.questions) == 1


def test_skip_after_two_unknown_answers_prevents_same_gap():
    service, session, bases, experience = make_interview()
    first = service.record_unknown(session.id, QualityDimension.RESULT)
    second = service.record_unknown(session.id, QualityDimension.RESULT)
    assert first.skipped is False
    assert second.skipped is True
    assert service.next_question(session.id).dimension is not QualityDimension.RESULT
```

- [ ] **Step 2: Run orchestration tests and verify RED**

Run: `python -m pytest tests/test_interview_service.py -q`

Expected: import fails because `interview_service` does not exist.

- [ ] **Step 3: Define agent and repository protocols**

```python
class FactAuditAgent(Protocol):
    def propose(self, message: str, session: InterviewSession, base: CareerFactBase) -> FactProposal: ...


class QuestionWriterAgent(Protocol):
    def write(self, plan: QuestionPlan, experience: Experience, target: CareerTarget) -> str: ...


class FactBaseRepository(Protocol):
    def get(self, fact_base_id: UUID) -> CareerFactBase: ...
    def save(self, base: CareerFactBase, expected_revision: int) -> None: ...
```

Add equivalent `get` and `save` operations for sessions. The test fakes store
deep copies so persistence behavior cannot be bypassed through shared references.

- [ ] **Step 4: Implement interview state transitions**

`answer` records the user message, calls only the fact-audit port, stores the
proposal in the session, and leaves the base unchanged. `confirm` verifies the
pending proposal ID, confirms it on the base, saves with optimistic revision,
then calls the planner and question-writer port once. `record_unknown` increments
per-dimension attempts and skips on the second unknown. `next_question` excludes
skipped dimensions and returns a single `QuestionPlan` plus its rendered text.

- [ ] **Step 5: Run orchestration tests and verify GREEN**

Run: `python -m pytest tests/test_interview_service.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit orchestration**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests
git commit -m "feat: orchestrate evidence mentor agents"
```

### Task 4: Resume version lifecycle

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application/version_service.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_version_service.py`

**Interfaces:**
- Consumes: `CareerFactBase`, `ResumeVersion`, and `VersionRepository`.
- Produces: `VersionService.create`, `list`, `get`, `activate`, `clone`, `rename`, `delete`, and `refresh_staleness`.

- [ ] **Step 1: Write failing version tests**

```python
def make_version_service():
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Analyst")
    return VersionService(InMemoryVersionRepository()), base, experience


def test_two_versions_reference_same_fact_without_copying():
    service, base, experience = make_version_service()
    first = service.create(base, "Data Analyst", selected_experience_ids=[experience.id])
    second = service.clone(first.id, "Product Analyst")
    assert first.selected_experience_ids == second.selected_experience_ids
    assert first.id != second.id


def test_base_revision_change_marks_affected_versions_stale():
    service, base, experience = make_version_service()
    version = service.create(base, "Data Analyst", selected_experience_ids=[experience.id])
    base.revision += 1
    refreshed = service.refresh_staleness(base)
    assert refreshed[0].status.value == "stale"


def test_deleting_clone_does_not_delete_original():
    service, base, experience = make_version_service()
    original = service.create(base, "Data Analyst")
    clone = service.clone(original.id, "Data Analyst - Tokyo")
    service.delete(clone.id)
    assert service.get(original.id).name == "Data Analyst"


def test_only_one_version_is_active():
    service, base, experience = make_version_service()
    first = service.create(base, "First")
    second = service.create(base, "Second")
    service.activate(second.id)
    assert service.get(first.id).is_active is False
    assert service.get(second.id).is_active is True
```

- [ ] **Step 2: Run version tests and verify RED**

Run: `python -m pytest tests/test_version_service.py -q`

Expected: import fails because `version_service` does not exist.

- [ ] **Step 3: Implement version repository protocol and service**

`create` stores the current base revision. `clone` deep-copies only the overlay
configuration and assigns new ID and timestamps. `activate` deactivates all other
versions in the same fact base. `refresh_staleness` compares `base_revision` and
marks versions stale without changing selected IDs. `delete` removes exactly one
version and never calls a fact-base repository.

- [ ] **Step 4: Run version tests and verify GREEN**

Run: `python -m pytest tests/test_version_service.py -q`

Expected: `4 passed`.

- [ ] **Step 5: Commit version management**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/application \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_version_service.py
git commit -m "feat: add job-specific resume versions"
```

### Task 5: SQLite persistence

**Files:**
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/infrastructure/__init__.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/infrastructure/sqlite_repositories.py`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_sqlite_repositories.py`

**Interfaces:**
- Consumes: repository protocols from Task 3 and Task 4.
- Produces: `SQLiteStore`, `SQLiteFactBaseRepository`, `SQLiteSessionRepository`, and `SQLiteVersionRepository`.

- [ ] **Step 1: Write failing persistence tests**

```python
def test_fact_base_survives_repository_restart(tmp_path):
    db = tmp_path / "resume-agent.db"
    first = SQLiteFactBaseRepository(SQLiteStore(db))
    base = CareerFactBase()
    base.add_experience("Yunshu", "Analyst")
    first.create(base)
    second = SQLiteFactBaseRepository(SQLiteStore(db))
    loaded = second.get(base.id)
    assert loaded.experiences[0].organization == "Yunshu"


def test_optimistic_revision_rejects_stale_save(tmp_path):
    repo = SQLiteFactBaseRepository(SQLiteStore(tmp_path / "resume-agent.db"))
    base = CareerFactBase()
    repo.create(base)
    base.revision = 1
    with pytest.raises(RevisionConflict):
        repo.save(base, expected_revision=9)


def test_version_clone_is_independent_after_restart(tmp_path):
    store = SQLiteStore(tmp_path / "resume-agent.db")
    repo = SQLiteVersionRepository(store)
    base = CareerFactBase()
    original = ResumeVersion(name="Analyst", fact_base_id=base.id, base_revision=0)
    clone = original.model_copy(deep=True, update={"id": uuid4(), "name": "Analyst Tokyo"})
    repo.save(original)
    repo.save(clone)
    loaded = SQLiteVersionRepository(SQLiteStore(store.path)).list(base.id)
    assert {item.id for item in loaded} == {original.id, clone.id}
```

- [ ] **Step 2: Run persistence tests and verify RED**

Run: `python -m pytest tests/test_sqlite_repositories.py -q`

Expected: import fails because `sqlite_repositories` does not exist.

- [ ] **Step 3: Implement schema and repositories**

Create three tables with UUID text primary keys, fact-base ID where applicable,
revision integer, and Pydantic JSON payload. Enable foreign keys and WAL mode.
Use `INSERT` for `create`, UPSERT for sessions and versions, and
`UPDATE ... WHERE id = ? AND revision = ?` for fact bases. Raise
`RevisionConflict` when the guarded update affects zero rows.

- [ ] **Step 4: Run persistence and full tests GREEN**

Run: `python -m pytest -q`

Expected: all tests pass with no network access.

- [ ] **Step 5: Commit persistence**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/infrastructure \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_sqlite_repositories.py
git commit -m "feat: persist ResumeAgent mentor state"
```

### Task 6: Public API and documentation

**Files:**
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/__init__.py`
- Modify: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/README.md`
- Create: `Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_public_api.py`

**Interfaces:**
- Consumes: all core types and services from Tasks 1–5.
- Produces: stable top-level imports for `CareerFactBase`, `InterviewService`, `QuestionPlanner`, `VersionService`, and SQLite repositories.

- [ ] **Step 1: Write failing public-import smoke test**

```python
def test_public_api_imports():
    from resume_agent import (
        CareerFactBase,
        InterviewService,
        QuestionPlanner,
        SQLiteFactBaseRepository,
        VersionService,
    )
    assert CareerFactBase is not None
    assert InterviewService is not None
    assert QuestionPlanner is not None
    assert SQLiteFactBaseRepository is not None
    assert VersionService is not None
```

- [ ] **Step 2: Run public API test and verify RED**

Run: `python -m pytest tests/test_public_api.py -q`

Expected: import error for at least one missing top-level export.

- [ ] **Step 3: Export the stable API and update README**

Export the five tested symbols plus domain enums and models. Add a “mentor core”
section to README describing the evidence quality gate, confirmation requirement,
multi-version isolation, and the exact offline test command:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

Correct the stale future-plan entry that says JD gap analysis is not implemented.
List FastAPI, Streamlit, HelloAgents adapters, and renderer migration as the next
delivery phase rather than claiming they are already complete.

- [ ] **Step 4: Run full verification**

Run: `python -m pytest -q`

Expected: all tests pass.

Run: `python -m compileall -q resume_agent`

Expected: exit status 0 with no output.

Run: `git diff --check HEAD~5..HEAD`

Expected: exit status 0 with no whitespace errors.

- [ ] **Step 5: Commit documentation and public API**

```bash
git add Co-creation-projects/shiyuanyeming-hub-ResumeAgent/resume_agent/__init__.py \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/tests/test_public_api.py \
  Co-creation-projects/shiyuanyeming-hub-ResumeAgent/README.md
git commit -m "docs: introduce ResumeAgent mentor core"
```

## Plan boundary

This plan delivers the domain, mentor algorithm, orchestration ports, version
management, and local persistence as one independently testable core. Follow-up
plans will cover: (1) HelloAgents adapters and structured prompts, (2) FastAPI
and Streamlit product surfaces, and (3) renderer extraction plus notebook
migration. Those plans depend on the stable interfaces delivered here.
