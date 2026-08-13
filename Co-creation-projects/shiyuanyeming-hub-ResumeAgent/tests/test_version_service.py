from resume_agent.application.version_service import VersionService
from resume_agent.domain.models import CareerFactBase, VersionStatus
from tests.fakes import InMemoryVersionRepository


def make_version_service():
    base = CareerFactBase()
    experience = base.add_experience("Yunshu", "Analyst")
    return VersionService(InMemoryVersionRepository()), base, experience


def test_two_versions_reference_same_fact_without_copying():
    service, base, experience = make_version_service()

    first = service.create(
        base,
        "Data Analyst",
        selected_experience_ids=[experience.id],
    )
    second = service.clone(first.id, "Product Analyst")

    assert first.selected_experience_ids == second.selected_experience_ids
    assert first.id != second.id


def test_base_revision_change_marks_affected_versions_stale():
    service, base, experience = make_version_service()
    service.create(
        base,
        "Data Analyst",
        selected_experience_ids=[experience.id],
    )

    base.revision += 1
    refreshed = service.refresh_staleness(base)

    assert refreshed[0].status is VersionStatus.STALE


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

    service.activate(first.id)
    service.activate(second.id)

    assert service.get(first.id).is_active is False
    assert service.get(second.id).is_active is True


def test_clone_changes_do_not_mutate_original_overlay():
    service, base, experience = make_version_service()
    original = service.create(
        base,
        "Original",
        selected_experience_ids=[experience.id],
    )
    clone = service.clone(original.id, "Clone")

    clone.emphasis[experience.id] = ["SQL"]
    service.save(clone)

    assert service.get(original.id).emphasis == {}


def test_create_rejects_unknown_experience_reference():
    service, base, experience = make_version_service()

    try:
        service.create(base, "Broken", selected_experience_ids=[base.id])
    except ValueError as error:
        assert "unknown experience" in str(error)
    else:
        raise AssertionError("unknown experience reference must be rejected")


def test_rename_preserves_version_identity():
    service, base, experience = make_version_service()
    version = service.create(base, "Before")

    renamed = service.rename(version.id, "After")

    assert renamed.id == version.id
    assert renamed.name == "After"
