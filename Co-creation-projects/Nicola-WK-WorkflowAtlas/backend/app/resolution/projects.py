"""Exact normalized aliases, stable IDs, and explicit ambiguity handling."""
from __future__ import annotations

import hashlib
import unicodedata
from collections import defaultdict
from datetime import datetime

from app.schemas import Project, WorkFact


def canonical_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split()).casefold()


def stable_id(prefix: str, *parts: str) -> str:
    # Length framing prevents concatenation collisions between different fields.
    payload = "".join(f"{len(part)}:{part}" for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def resolve_projects(
    facts: list[WorkFact], existing_projects: list[Project] | None = None
) -> tuple[list[WorkFact], list[Project], list[str]]:
    projects = {project.id: project.model_copy(deep=True) for project in existing_projects or []}
    alias_ids: dict[str, set[str]] = defaultdict(set)
    for project in projects.values():
        for alias in [project.name, *project.aliases]:
            if canonical_name(alias):
                alias_ids[canonical_name(alias)].add(project.id)
    warnings: list[str] = []
    resolved: list[WorkFact] = []
    for original in sorted(facts, key=lambda fact: (fact.occurred_at.isoformat(), fact.id)):
        fact = original.model_copy(deep=True)
        hint = canonical_name(fact.project_hint or "")
        candidate_ids = alias_ids.get(hint, set()) if hint else set()
        if len(candidate_ids) > 1:
            fact.project_id = None
            warnings.append(f"Fact {fact.id}: ambiguous project alias {fact.project_hint!r}; left unassigned")
        elif candidate_ids:
            chosen = next(iter(candidate_ids))
            if fact.project_id and fact.project_id in projects and fact.project_id != chosen:
                fact.project_id = None
                warnings.append(f"Fact {fact.id}: project ID conflicts with explicit hint; left unassigned")
            else:
                fact.project_id = chosen
        elif fact.project_id in projects and not hint:
            pass
        elif hint:
            project_id = stable_id("project", hint)
            if fact.project_id and fact.project_id in projects and fact.project_id != project_id:
                fact.project_id = None
                warnings.append(f"Fact {fact.id}: known project ID conflicts with new project hint; left unassigned")
            else:
                if project_id not in projects:
                    projects[project_id] = Project(
                        id=project_id,
                        name=" ".join((fact.project_hint or "").strip().split()),
                        created_at=fact.occurred_at,
                    )
                alias_ids[hint].add(project_id)
                fact.project_id = project_id
        else:
            fact.project_id = None
            warnings.append(f"Fact {fact.id}: no explicit project identity; left unassigned")
        resolved.append(fact)
    return resolved, sorted(projects.values(), key=lambda item: (canonical_name(item.name), item.id)), warnings
