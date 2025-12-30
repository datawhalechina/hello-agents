from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    GROUP = "group"
    PERSON = "person"
    EVENT = "event"
    LOCATION = "location"
    ORG = "org"
    OTHER = "other"


class Entity(BaseModel):
    id: str
    type: EntityType
    name: str
    props: Dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    source: str
    target: str
    type: str
    props: Dict[str, Any] = Field(default_factory=dict)


class ExtractedGraph(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None


class CommunityResult(BaseModel):
    communities: List[List[str]]
    node_to_community: Dict[str, int]
    summary_by_community: Dict[str, str] = Field(default_factory=dict)
