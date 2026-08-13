from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from resume_agent.application.ports import RevisionConflict
from resume_agent.domain.models import (
    CareerFactBase,
    InterviewSession,
    ResumeVersion,
)
from resume_agent.infrastructure.sqlite_repositories import (
    SQLiteFactBaseRepository,
    SQLiteSessionRepository,
    SQLiteStore,
    SQLiteVersionRepository,
)


def test_fact_base_survives_repository_restart(tmp_path):
    database = tmp_path / "resume-agent.db"
    first = SQLiteFactBaseRepository(SQLiteStore(database))
    base = CareerFactBase()
    base.add_experience("Yunshu", "Analyst")
    first.create(base)

    second = SQLiteFactBaseRepository(SQLiteStore(database))
    loaded = second.get(base.id)

    assert loaded.experiences[0].organization == "Yunshu"


def test_optimistic_revision_rejects_stale_save(tmp_path):
    repository = SQLiteFactBaseRepository(
        SQLiteStore(tmp_path / "resume-agent.db")
    )
    base = CareerFactBase()
    repository.create(base)
    base.revision = 1

    with pytest.raises(RevisionConflict):
        repository.save(base, expected_revision=9)


def test_fact_base_guarded_save_persists_new_revision(tmp_path):
    repository = SQLiteFactBaseRepository(
        SQLiteStore(tmp_path / "resume-agent.db")
    )
    base = CareerFactBase()
    repository.create(base)
    base.revision = 1

    repository.save(base, expected_revision=0)

    assert repository.get(base.id).revision == 1


def test_session_survives_repository_restart(tmp_path):
    database = tmp_path / "resume-agent.db"
    session = InterviewSession(fact_base_id=uuid4())
    SQLiteSessionRepository(SQLiteStore(database)).create(session)

    loaded = SQLiteSessionRepository(SQLiteStore(database)).get(session.id)

    assert loaded.fact_base_id == session.fact_base_id


def test_version_clone_is_independent_after_restart(tmp_path):
    store = SQLiteStore(tmp_path / "resume-agent.db")
    repository = SQLiteVersionRepository(store)
    base = CareerFactBase()
    original = ResumeVersion(
        name="Analyst",
        fact_base_id=base.id,
        base_revision=0,
    )
    clone = original.model_copy(
        deep=True,
        update={"id": uuid4(), "name": "Analyst Tokyo"},
    )
    repository.save(original)
    repository.save(clone)

    loaded = SQLiteVersionRepository(SQLiteStore(store.path)).list(base.id)

    assert {item.id for item in loaded} == {original.id, clone.id}


def test_deleting_version_does_not_touch_fact_base(tmp_path):
    store = SQLiteStore(tmp_path / "resume-agent.db")
    bases = SQLiteFactBaseRepository(store)
    versions = SQLiteVersionRepository(store)
    base = CareerFactBase()
    version = ResumeVersion(name="Analyst", fact_base_id=base.id, base_revision=0)
    bases.create(base)
    versions.save(version)

    versions.delete(version.id)

    assert bases.get(base.id).id == base.id
    with pytest.raises(KeyError):
        versions.get(version.id)


def test_concurrent_version_activation_keeps_exactly_one_active(tmp_path):
    database = tmp_path / "resume-agent.db"
    repository = SQLiteVersionRepository(SQLiteStore(database))
    base = CareerFactBase()
    first = ResumeVersion(name="First", fact_base_id=base.id, base_revision=0)
    second = ResumeVersion(name="Second", fact_base_id=base.id, base_revision=0)
    repository.save(first)
    repository.save(second)
    barrier = Barrier(2)

    def activate(version_id):
        local_repository = SQLiteVersionRepository(SQLiteStore(database))
        barrier.wait()
        local_repository.activate(version_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(activate, first.id),
            executor.submit(activate, second.id),
        ]
        for future in futures:
            future.result()

    active = [version for version in repository.list(base.id) if version.is_active]
    assert len(active) == 1
