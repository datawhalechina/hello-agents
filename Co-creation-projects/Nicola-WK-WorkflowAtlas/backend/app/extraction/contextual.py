"""Bounded local observations from explicit natural names, sections and replies.

The rules intentionally retain unresolved information. Context is only a source
of attribution evidence, never a license to infer completion or causal links.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import html
import re

from ..connectors.context import build_identity_map, message_segments, reply_references, resolve_sender_name
from ..schemas import EvidenceReference, StandardMessage, WorkFact
from .local import INJECTION, PROJECT, ENTITY, WORK, classify_message, explicit_relations, extract_local, infer_kind, infer_status, project_hints, stable_fact_id

ACTION = re.compile(r"准备|确认|采购|对接|推进|采集|录制|审核|安排|需求|计划|提交|修改|制作|完成|更新|同步|试标|试采|标注|调试|报价|汇报|统计|收购|搭建|授权|规范|招聘|渠道|拓展|交付|上线|优化|编写|校验|测试|部署|执行|修复|选择|解决|负责人|阻塞|卡点|卡住|风险|逾期|开始|开发|验收|失败|决定|决策|返工|依赖|task|project|start|test|deliver|prepare|review", re.I)
ACK = re.compile(r"^(?:收到|好的|好哒|好|了解|明白|谢谢|辛苦了|赞|ok|okay|thanks)[！!。，,\s]*$", re.I)
BACKGROUND = re.compile(r"项目(?:名称|名)\s*[:：]\s*(?:中文|英文)|项目简介\s*[:：].{0,15}(?:中英文|中文|英文)|诚邀.{0,15}(?:调研|填写)|请根据自身实际情况填写|核心创始团队|龙头企业|行业领先|数据集构建服务|覆盖.{0,30}为.{0,20}(?:训练|评测)", re.I)
LIST_PREFIX = re.compile(r"^\s*(?:(?:[A-Z]|\d+|[一二三四五六七八九十]+)[.、．）)]|[-•])\s*", re.I)
NATURAL = re.compile(r"[A-Za-z\u3400-\u9fff0-9][A-Za-z\u3400-\u9fff0-9_ /+\-]{0,28}?项目", re.I)
GENERIC = {"本", "该", "此", "这", "这个", "那个", "每个", "各个", "多个", "所有", "全部", "其他", "对应", "具体", "正式", "目前", "目前的", "之前", "之前的", "新", "旧", "当前", "一个", "两个", "三个", "四个", "五个", "项目", "执行", "本周", "本次", "此次", "我们", "目前负责的", "目前的各个"}
PREFIXES = re.compile(r"^(?:各位|我们(?:正在|已经|计划|将)?|正在|已经|开展(?:一项)?|推进|负责(?:的)?|安排|启动|关于|有关|确认|完成|接着|接下来|本周|本次|此次|之前的|目前的|目前|一个|一项|对应|具体|正式|之前|汇报)")
CLAUSE = re.compile(r"(?:&(?:\#x[\da-fA-F]+|\#\d+|[A-Za-z]+);|[^；;。！？!?\n])+", re.I)
SUBSTANTIVE = re.compile(r"准备|确认|采购|对接|推进|审核|安排|计划|提交|修改|制作|已完成|完成了|更新|同步|试标|试采|调试|报价|汇报|统计|收购|搭建|拓展|交付|上线|优化|编写|校验|测试|部署|执行|修复|选择|解决|负责人|阻塞|卡点|卡住|风险|逾期|开始|开发|验收|失败|决定|决策|返工|依赖|需要|必须|需|将|拟|预计|要求|缺失|缺少|负责人|负责|招募|邀请|产出|收音|分辨率|报名|终止|录制|采集|start|test|deliver|prepare|review", re.I)
PERSONAL = re.compile(r"(?:我|本人).{0,16}(?:去医院|看病|请假|家里有事|身体不舒服)")


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", "", value)).strip()


def _clean_name(value: str) -> str | None:
    value = LIST_PREFIX.sub("", value).strip()
    for _ in range(6):
        changed = PREFIXES.sub("", value, count=1).strip()
        if changed == value:
            break
        value = changed
    stem = value[:-2].strip() if value.endswith("项目") else value
    if stem in GENERIC or len(stem) < 2 or len(stem) > 26 or re.search(r"(?:多少|什么|几个|所有|每个|各个|五个|四个|项目部|项目执行|项目安排|目前负责|如果|这个|那个)", stem):
        return None
    return value


def natural_projects(text: str) -> list[str]:
    """Only names literally present in this clause; no fuzzy alias merging."""
    if BACKGROUND.search(text):
        return []
    # Mention transport keys are identity tokens, not natural project names.
    analysis_text = re.sub(r"@[_A-Za-z0-9]+", " ", text)
    values = []
    label = re.search(r"(?:项目名称|项目名)\s*[:：]\s*([^，,。；;\n]{2,30})", text)
    if label:
        value = label.group(1).strip()
        if value not in {"中文 / 英文", "中文/英文", "中文", "英文"} and not any(c in value for c in "<>@"):
            values.append(value)
    for match in NATURAL.finditer(analysis_text):
        value = _clean_name(match.group())
        if value and value in text and value not in values:
            values.append(value)
    return values[:12]


def classify_local_message(message: StandardMessage) -> str:
    """Classify substantive work, acknowledgements, templates and resource data."""
    text = "\n".join(segment.display_text for segment in message_segments(message.text))
    if INJECTION.search(text):
        return "uncertain"
    raw = message.metadata.get("raw", {})
    msg_type = raw.get("msg_type", raw.get("message_type", "text")) if isinstance(raw, dict) else "text"
    if msg_type not in {"text", "post"} or text.startswith(("[recalled message]", "[post without text]")):
        return "background"
    if ACK.fullmatch(text) or (re.search(r"祝福|注意身体|生日快乐|节日快乐", text) and not re.search(r"(?:本周|下周|工作|计划)安排", text)):
        return "chitchat"
    if BACKGROUND.search(text) or re.fullmatch(r"(?:\[[^\]]*\]\()?https?://[^\s]+\)?", text):
        return "background"
    return "work" if ACTION.search(text) or WORK.search(text) else classify_message(message)


@dataclass(frozen=True)
class ProjectSupport:
    name: str
    reference: EvidenceReference


def _reference(message: StandardMessage, quote: str) -> EvidenceReference:
    return EvidenceReference(source_id=message.source_id, message_id=message.id, quote=quote)


def _is_header(text: str, names: list[str]) -> bool:
    if len(names) != 1:
        return False
    remaining = LIST_PREFIX.sub("", text)
    remaining = re.sub(r"^项目(?:名称|名)?\s*[:：]\s*", "", remaining)
    remaining = remaining.replace(names[0], "", 1)
    remaining = re.sub(r"@_user_\d+", "", remaining).strip(" \t：:，,（）()")
    return remaining in {"", "后续安排", "工作安排", "后续工作", "本周安排", "进度", "进度安排"}


def _section_marker(text: str) -> tuple[str, int] | None:
    """Recognize list families without treating numbered task rows as names.

    Family is an explicit structural cue: A/B may contain numeric tasks, while
    1/2 are peers when the project heading itself used a numeric marker.
    """
    match = re.match(r"^(?P<space>\s*)(?:(?P<alpha>[A-Z])|(?P<numeric>\d+)|(?P<chinese>[一二三四五六七八九十]+))[.、．）)]\s*", text, re.I)
    if match is not None:
        family = next(name for name in ("alpha", "numeric", "chinese") if match.group(name) is not None)
        return family, len(match.group("space").expandtabs(4))
    bullet = re.match(r"^(?P<space>\s*)[-•]\s*", text)
    return ("bullet", len(bullet.group("space").expandtabs(4))) if bullet else None


def _ends_section(current: tuple[str, int], parent: tuple[str, int] | None) -> bool:
    # Without an enumerated parent there is no positive structural evidence
    # that a new list belongs below it, so stop inherited project/actor scope.
    if parent is None:
        return True
    family, indent = current
    parent_family, parent_indent = parent
    if indent > parent_indent:
        return False
    hierarchy = {"alpha": 0, "chinese": 1, "numeric": 2, "bullet": 3}
    return hierarchy[family] <= hierarchy[parent_family]


def _assignees(message: StandardMessage, quote: str, identities: dict, carry: list[dict], *, section_task: bool = False) -> tuple[list[dict], str | None]:
    raw = message.metadata.get("raw", {})
    mentions = raw.get("mentions", []) if isinstance(raw, dict) else []
    if not isinstance(mentions, list):
        mentions = []
    matched = []
    for mention in mentions:
        if not isinstance(mention, dict) or not isinstance(mention.get("key"), str) or mention["key"] not in quote:
            continue
        identifier = mention.get("id")
        if not isinstance(identifier, str) or not identifier:
            continue
        prefix = quote[:quote.find(mention["key"])]
        if re.search(r"(?:向|给|找|与|和|咨询|联系)\s*$", _plain(prefix)):
            continue
        name = identities.get((message.source_id, identifier), identifier)
        matched.append({"id": identifier, "name": name})
    text = _plain(quote)
    explicit = bool(re.search(r"负责人|负责|执行人|请|安排.{0,12}@|由.{0,12}@", text))
    mention_only = bool(re.fullmatch(r"(?:@_user_\d+\s*)+", text))
    trailing_task = section_task and ACTION.search(text) and re.search(r"@_user_\d+[\s，,。]*$", text)
    if matched and not (explicit or mention_only or trailing_task):
        matched = []
    selected = matched or carry
    return selected, "、".join(item["name"] for item in selected) if selected else None


def _catalog_matches(text: str, catalog: list[ProjectSupport]) -> list[ProjectSupport]:
    matched = {}
    for support in catalog:
        alias = support.name[:-2] if support.name.endswith("项目") else support.name
        if len(alias) < 2:
            continue
        pattern = re.escape(alias)
        if alias.isascii():
            pattern = r"(?<![a-zA-Z0-9])" + pattern + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text, re.I):
            matched[support.name.casefold()] = support
    # More specific explicit names can contain another known project; leaving
    # both candidates visible is safer than guessing they denote one entity.
    return list(matched.values())[:12]


def extract_messages(messages: list[StandardMessage], selected_messages: list[StandardMessage] | None = None) -> list[WorkFact]:
    """Extract bounded observations, preserving literal evidence and scope.

    Project context is scoped to source+chat. Replies may inherit only a unique
    project from a recorded ancestor that is not in the future. No neighboring
    messages or similarity scores create project ownership.
    """
    ordered = sorted(messages, key=lambda item: (item.timestamp, item.source_id, item.id))
    eligible = {(m.source_id, m.id) for m in selected_messages} if selected_messages is not None else None
    index = {(m.source_id, m.id): m for m in ordered}
    catalogs: dict[tuple[str, str], list[ProjectSupport]] = defaultdict(list)
    # Names are discovered only in substantive work observations, not imported
    # company descriptions, recruitment copy or file-name placeholders.
    for message in ordered:
        if classify_local_message(message) != "work":
            continue
        scope = (message.source_id, message.chat_id)
        for segment in message_segments(message.text):
            for name in natural_projects(segment.display_text):
                if len(catalogs[scope]) < 64 and not any(item.name.casefold() == name.casefold() for item in catalogs[scope]):
                    catalogs[scope].append(ProjectSupport(name, _reference(message, segment.quote)))
    identities = build_identity_map(ordered)
    project_by_message: dict[tuple[str, str], dict[str, ProjectSupport]] = {}
    ambiguous_messages: set[tuple[str, str]] = set()
    result = []
    for message in ordered:
        key = (message.source_id, message.id)
        scope = (message.source_id, message.chat_id)
        if classify_local_message(message) != "work":
            continue
        selected = eligible is None or key in eligible
        legacy_hints = project_hints(message.text)
        if legacy_hints and not any(re.search(r"招募|调研|注意事项|公告", hint) for hint in legacy_hints):
            legacy = extract_local(message)
            for fact in legacy:
                supports = []
                if fact.project_hint:
                    for tag in PROJECT.finditer(message.text):
                        label = (tag.group(1) or tag.group(2)).strip()
                        if label == fact.project_hint:
                            reference = _reference(message, tag.group())
                            supports.append(reference.model_dump())
                            if reference not in fact.evidence:
                                fact.evidence.append(reference)
                            break
                fact.attributes["project_attribution"] = {"method": "explicit" if fact.project_hint else "unassigned", "support": supports, "evidence": supports, "review_required": True}
                fact.attributes["reported_by"] = {"id": message.sender, "name": resolve_sender_name(message, identities)}
                fact.attributes["sender_id"] = message.sender
                fact.attributes["sender_name"] = resolve_sender_name(message, identities)
                fact.attributes["assignees"] = []
                fact.attributes["actor_role"] = "reporter"
            if selected:
                result.extend(legacy)
            project_by_message[key] = {f.project_hint.casefold(): ProjectSupport(f.project_hint, f.evidence[0]) for f in legacy if f.project_hint}
            if any(f.project_hint is None for f in legacy):
                ambiguous_messages.add(key)
            continue

        parent_supports = []
        for parent_id in reply_references(message)[:8]:
            parent = index.get((message.source_id, parent_id))
            if parent is None or parent.chat_id != message.chat_id or parent.timestamp > message.timestamp:
                continue
            if (parent.source_id, parent.id) in ambiguous_messages:
                parent_supports = []
                break
            known = project_by_message.get((parent.source_id, parent.id), {})
            if len(known) == 1:
                parent_supports.extend(known.values())
            elif len(known) > 1:
                parent_supports = []
                break
        parent_unique = {support.name.casefold(): support for support in parent_supports}
        parent_context = next(iter(parent_unique.values())) if len(parent_unique) == 1 else None
        section: ProjectSupport | None = None
        section_marker: tuple[str, int] | None = None
        carried_assignees: list[dict] = []
        carried_assignment_support: EvidenceReference | None = None
        seen: dict[str, ProjectSupport] = {}
        facts = []
        for segment in message_segments(message.text):
            text = segment.display_text
            names = natural_projects(text)
            marker = _section_marker(text)
            if section is not None and marker is not None and _ends_section(marker, section_marker):
                section = None
                section_marker = None
                carried_assignees = []
                carried_assignment_support = None
            if _is_header(text, names):
                section = ProjectSupport(names[0], _reference(message, segment.quote))
                section_marker = marker
                seen[section.name.casefold()] = section
                carried_assignees, _ = _assignees(message, segment.quote, identities, [])
                carried_assignment_support = _reference(message, segment.quote) if carried_assignees else None
                continue
            if re.fullmatch(r"(?:项目执行|对外沟通|其他工作|工作安排|本周安排|下周安排|本周工作安排|下周工作安排)(?:部分)?\s*[:：]?", LIST_PREFIX.sub("", text)):
                section = None
                section_marker = None
                carried_assignees = []
                carried_assignment_support = None
                continue
            if re.fullmatch(r"(?:@_user_\d+\s*)+", text):
                carried_assignees, _ = _assignees(message, segment.quote, identities, [])
                carried_assignment_support = _reference(message, segment.quote) if carried_assignees else None
                continue
            if LIST_PREFIX.match(text) and names:
                # Mentioning a project in an actionable numbered item is not a
                # section declaration. Following items can concern other work.
                section = None
                section_marker = None
                carried_assignees = []
                carried_assignment_support = None
            for match in CLAUSE.finditer(segment.quote):
                quote = match.group().strip()
                plain = _plain(quote)
                summary = LIST_PREFIX.sub("", plain).strip(" \t,，:：")
                if not quote or not summary or ACK.fullmatch(summary) or not ACTION.search(summary) or BACKGROUND.search(summary):
                    continue
                # A bare project label is context, not a completed task.
                direct = natural_projects(summary)
                if PERSONAL.search(summary) and not direct:
                    continue
                if _is_header(summary, direct):
                    continue
                support = None
                method = "unassigned"
                if len(direct) == 1:
                    support = ProjectSupport(direct[0], _reference(message, quote)); method = "explicit"
                elif not direct:
                    matches = _catalog_matches(summary, catalogs[scope])
                    if len(matches) == 1:
                        original = matches[0]
                        # No future message is used to establish project identity.
                        origin = index.get((original.reference.source_id, original.reference.message_id))
                        if origin and origin.timestamp <= message.timestamp:
                            support = original; method = "catalog"
                    elif not matches:
                        if section is not None:
                            support = section; method = "section"
                        elif parent_context is not None:
                            support = parent_context; method = "reply"
                actionable = re.sub(r"https?://\S+|@[_A-Za-z0-9]+", "", summary)
                for name in direct:
                    actionable = actionable.replace(name, "")
                for known in _catalog_matches(summary, catalogs[scope]):
                    alias = known.name[:-2] if known.name.endswith("项目") else known.name
                    actionable = re.sub(re.escape(alias), "", actionable, flags=re.I)
                if not SUBSTANTIVE.search(actionable):
                    continue
                evidence = [_reference(message, quote)]
                if support and support.reference not in evidence:
                    evidence.append(support.reference)
                assignments, actor = _assignees(message, quote, identities, carried_assignees, section_task=section is not None)
                raw_data = message.metadata.get("raw", {})
                raw_mentions = raw_data.get("mentions", []) if isinstance(raw_data, dict) else []
                if not isinstance(raw_mentions, list):
                    raw_mentions = []
                has_inline_mention = any(isinstance(item.get("key"), str) and bool(item["key"]) and item["key"] in quote for item in raw_mentions if isinstance(item, dict))
                if assignments and carried_assignment_support and not has_inline_mention and carried_assignment_support not in evidence:
                    evidence.append(carried_assignment_support)
                assignment_ids = list(dict.fromkeys(item["id"] for item in assignments))
                assignment_names = list(dict.fromkeys(item["name"] for item in assignments))
                cleaned = re.sub(r"@_user_\d+|@_all", "", summary).strip()
                if not cleaned:
                    continue
                kind = infer_kind(cleaned)
                attribution_evidence = [support.reference.model_dump()] if support else []
                offset = segment.start + match.start() + len(match.group()) - len(match.group().lstrip())
                attributes = {"provider": "local-demo", "classification": "work", "reported_by": {"id": message.sender, "name": resolve_sender_name(message, identities)}, "sender_id": message.sender, "sender_name": resolve_sender_name(message, identities), "assignees": assignments, "assigned_actor_ids": assignment_ids, "assigned_actor_names": assignment_names, "actor_role": "explicit_assignee" if assignments else "unspecified", "project_attribution": {"method": method, "support": attribution_evidence, "evidence": attribution_evidence, "review_required": True}, "relations": explicit_relations(quote), "source_span": {"start": offset, "end": offset + len(quote)}}
                if len(direct) > 1:
                    attributes["project_candidates"] = direct
                entity = ENTITY.search(quote)
                entity_key = entity.group(1).strip() if entity else None
                facts.append(WorkFact(id=stable_fact_id(message, kind.value, f"{offset}:{quote}", cleaned), kind=kind, summary=cleaned, project_hint=support.name if support else None, entity_key=entity_key, actor=actor, status=infer_status(cleaned), occurred_at=message.timestamp, evidence=evidence, confidence=0.7 if support else 0.6, attributes=attributes))
                if support:
                    seen[support.name.casefold()] = support
        project_by_message[key] = seen
        if any(fact.project_hint is None for fact in facts):
            ambiguous_messages.add(key)
        if selected:
            result.extend(facts)
    return result
