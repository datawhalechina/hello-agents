"""Lifecycle management for job-specific resume overlays."""

from typing import List, Optional
from uuid import UUID, uuid4

from resume_agent.application.ports import VersionRepository
from resume_agent.domain.models import (
    CareerFactBase,
    ResumeVersion,
    VersionStatus,
    utc_now,
)
from resume_agent.rendering.styles import STYLE_CATALOG


class VersionService:
    def __init__(self, repository: VersionRepository) -> None:
        self.repository = repository

    def create(
        self,
        base: CareerFactBase,
        name: str,
        *,
        selected_experience_ids: Optional[List[UUID]] = None,
        target_role: str = "",
        company: str = "",
        raw_jd: str = "",
        locale: str = "zh",
    ) -> ResumeVersion:
        selected = list(selected_experience_ids or [])
        known_ids = {experience.id for experience in base.experiences}
        unknown = set(selected) - known_ids
        if unknown:
            raise ValueError(f"unknown experience references: {sorted(map(str, unknown))}")

        version = ResumeVersion(
            fact_base_id=base.id,
            name=name,
            target_role=target_role or name,
            company=company,
            raw_jd=raw_jd,
            locale=locale,
            selected_experience_ids=selected,
            ordering=selected,
            base_revision=base.revision,
        )
        self.repository.save(version)
        return version.model_copy(deep=True)

    def get(self, version_id: UUID) -> ResumeVersion:
        return self.repository.get(version_id)

    def list(self, fact_base_id: UUID) -> List[ResumeVersion]:
        return sorted(
            self.repository.list(fact_base_id),
            key=lambda version: version.created_at,
        )

    def save(self, version: ResumeVersion) -> ResumeVersion:
        version.updated_at = utc_now()
        self.repository.save(version)
        return self.repository.get(version.id)

    def clone(self, version_id: UUID, name: str) -> ResumeVersion:
        original = self.repository.get(version_id)
        now = utc_now()
        clone = original.model_copy(
            deep=True,
            update={
                "id": uuid4(),
                "name": name,
                "status": VersionStatus.DRAFT,
                "is_active": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self.repository.save(clone)
        return self.repository.get(clone.id)

    def rename(self, version_id: UUID, name: str) -> ResumeVersion:
        version = self.repository.get(version_id)
        version.name = name
        return self.save(version)

    def set_style(self, version_id: UUID, style: str) -> ResumeVersion:
        normalized = style.strip()
        if not normalized:
            raise ValueError("style must not be empty")
        version = self.repository.get(version_id)
        if normalized not in STYLE_CATALOG.get(version.locale, {}):
            raise ValueError(
                f"unsupported style for {version.locale}: {normalized}"
            )
        version.styles = {**version.styles, version.locale: normalized}
        return self.save(version)

    def activate(self, version_id: UUID) -> ResumeVersion:
        target = self.repository.get(version_id)
        for version in self.repository.list(target.fact_base_id):
            should_be_active = version.id == target.id
            if version.is_active != should_be_active:
                version.is_active = should_be_active
                version.updated_at = utc_now()
                self.repository.save(version)
        return self.repository.get(version_id)

    def delete(self, version_id: UUID) -> None:
        self.repository.delete(version_id)

    def refresh_staleness(self, base: CareerFactBase) -> List[ResumeVersion]:
        refreshed = []
        for version in self.repository.list(base.id):
            if version.base_revision != base.revision:
                version.status = VersionStatus.STALE
                version.updated_at = utc_now()
                self.repository.save(version)
            refreshed.append(self.repository.get(version.id))
        return sorted(refreshed, key=lambda version: version.created_at)
