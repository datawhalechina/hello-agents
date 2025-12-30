from __future__ import annotations

import re
from typing import Dict, List

from pydantic import TypeAdapter

from .llm import LLMConfig, chat_json
from .schema import Entity, EntityType, ExtractedGraph, Relation


_SYSTEM = """你是一个信息抽取助手。你需要从文本中抽取知识图谱（LPG）：实体（团体/人/事件/位置/组织等）与关系。\n\n输出必须是 JSON，包含：\n- entities: [{id,type,name,props}]\n- relations: [{source,target,type,props}]\n\n规则：\n- id 使用稳定字符串（推荐：type:name 的 slug 形式）\n- type 只能是: group/person/event/location/org/other\n- 关系类型用简短英文动词短语（例如 hosted_by, held_at, attended_by, organized_by, announces, next_event_at）\n- props 里可以放 time/date、source_sentence 等\n"""


def _slug(entity_type: EntityType, name: str) -> str:
    safe = re.sub(r"\s+", "_", name.strip())
    safe = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff-]", "", safe)
    return f"{entity_type.value}:{safe}".lower()


def extract_graph(text: str, llm: LLMConfig) -> ExtractedGraph:
    if llm.backend != "none":
        payload = chat_json(
            llm,
            system=_SYSTEM,
            user=f"请从下面文本抽取图谱：\n\n{text}",
        )
        return TypeAdapter(ExtractedGraph).validate_python(payload)

    return heuristic_extract(text)


def heuristic_extract(text: str) -> ExtractedGraph:
    """No-LLM fallback: minimal regex-based extraction for the demo article."""

    entities: Dict[str, Entity] = {}
    relations: List[Relation] = []

    def add_entity(entity_type: EntityType, name: str, **props):
        eid = _slug(entity_type, name)
        if eid not in entities:
            entities[eid] = Entity(id=eid, type=entity_type, name=name, props={})
        entities[eid].props.update({k: v for k, v in props.items() if v is not None})
        return eid

    group_names = ["星火读书会"]
    for g in group_names:
        add_entity(EntityType.GROUP, g)

    org_candidates = ["华东理工大学AI实验室", "上海交通大学"]
    for org in org_candidates:
        if org in text:
            add_entity(EntityType.ORG, org)

    person_candidates = ["张伟", "李娜", "王强", "赵敏"]
    for p in person_candidates:
        if p in text:
            add_entity(EntityType.PERSON, p)

    loc_candidates = ["上海市徐汇区", "上海交通大学闵行校区"]
    for loc in loc_candidates:
        if loc in text:
            add_entity(EntityType.LOCATION, loc)

    if "分享会" in text:
        event_name = "线下分享会"
        event_id = add_entity(EntityType.EVENT, event_name)

        if "2025年12月28日" in text:
            entities[event_id].props["date"] = "2025-12-28"

        g_id = _slug(EntityType.GROUP, "星火读书会")
        relations.append(Relation(source=g_id, target=event_id, type="hosted", props={}))

        if "上海市徐汇区" in text:
            l_id = _slug(EntityType.LOCATION, "上海市徐汇区")
            relations.append(Relation(source=event_id, target=l_id, type="held_at", props={}))

        if "主持人是张伟" in text:
            p_id = _slug(EntityType.PERSON, "张伟")
            relations.append(Relation(source=p_id, target=event_id, type="hosted_by", props={"role": "host"}))

        if "主讲人是李娜" in text:
            p_id = _slug(EntityType.PERSON, "李娜")
            relations.append(Relation(source=p_id, target=event_id, type="speaker_at", props={"role": "speaker"}))

        for p in ["王强", "赵敏"]:
            if p in text:
                p_id = _slug(EntityType.PERSON, p)
                relations.append(Relation(source=p_id, target=event_id, type="attended", props={}))

        if "联合组织" in text and "华东理工大学AI实验室" in text:
            org_id = _slug(EntityType.ORG, "华东理工大学AI实验室")
            relations.append(Relation(source=org_id, target=event_id, type="co_organized", props={}))

    if "下一次活动" in text and "2026年1月10日" in text:
        next_event = add_entity(EntityType.EVENT, "下一次活动", date="2026-01-10")
        if "上海交通大学闵行校区" in text:
            loc_id = _slug(EntityType.LOCATION, "上海交通大学闵行校区")
            relations.append(Relation(source=next_event, target=loc_id, type="held_at", props={}))
        g_id = _slug(EntityType.GROUP, "星火读书会")
        relations.append(Relation(source=g_id, target=next_event, type="announces", props={}))

    return ExtractedGraph(entities=list(entities.values()), relations=relations, evidence={"mode": "heuristic"})
