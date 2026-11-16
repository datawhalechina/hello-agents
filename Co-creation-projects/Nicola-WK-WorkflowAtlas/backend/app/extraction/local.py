"""Conservative, deterministic Chinese/English demo extraction.

This module is deliberately labeled a demo provider. It never claims model
reasoning or resolves ambiguous references from an unbounded chat history.
"""
from __future__ import annotations

import hashlib
import re

from ..schemas import EvidenceReference, FactKind, StandardMessage, WorkFact

PROJECT = re.compile(r"【([^】\n]{1,80})】|\[(?:项目|project)\s*[:：]\s*([^\]\n]{1,80})\]", re.I)
ENTITY = re.compile(r"[\[［【](?:任务|实体|task|entity)\s*[:：]\s*([^\]］】\n]{1,120})[\]］】]", re.I)
INJECTION = re.compile(r"忽略(?:之前|上面|所有|系统)|泄露.{0,8}(?:密钥|密码)|ignore\s+(?:previous|all|system)\s+instructions|reveal\s+(?:the\s+)?(?:secret|api.?key)", re.I)
WORK = re.compile(r"任务|项目|接口|联调|测试|需求|评审|发布|上线|部署|交付|文档|报告|决定|决策|计划|安排|完成|故障|阻塞|失败|修复|返工|验收|开发|依赖|进行|提交|解决|task|project|deploy|decision|blocked|issue|deliver|complete|review|plan|release", re.I)
CHAT = re.compile(r"早上好|晚安|午饭|吃饭|奶茶|周末|哈哈|天气|早安|hello|good\s+morning|lunch", re.I)

RELATION_PATTERNS = (
    ("depends_on", r"依赖(?:于)?|取决于|depends\s+on"),
    ("blocks", r"阻塞(?:了)?|blocks?"),
    ("resolves", r"解决(?:了)?|修复(?:了)?|resolves?"),
    ("produces", r"交付(?:了)?|产出(?:了)?|produces?"),
    ("revises", r"返工|重做|修订|revises?"),
    ("branches_to", r"分支到|分支为|branch(?:es)?\s+to"),
    ("parallel_with", r"并行(?:于|执行)?|parallel\s+with"),
)


def stable_fact_id(message: StandardMessage, kind: str, quote: str, summary: str) -> str:
    material = "".join(f"{len(part)}:{part}" for part in (message.source_id, message.id, kind, quote, summary))
    return "fact_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def classify_message(message: StandardMessage) -> str:
    """Return work, chitchat, background or uncertain without executing content."""
    text = message.text
    if INJECTION.search(text):
        return "uncertain"
    if WORK.search(text):
        return "work"
    if CHAT.search(text):
        return "chitchat"
    if PROJECT.search(text):
        return "background"
    return "uncertain"


def project_hints(text: str) -> list[str]:
    values = []
    for match in PROJECT.finditer(text):
        value = (match.group(1) or match.group(2)).strip()
        if not re.match(r"(?:任务|实体|task|entity)\s*[:：]", value, re.I) and value not in values:
            values.append(value)
    return values


def infer_kind(text: str) -> FactKind:
    if re.search(r"决定|决策|改为|取消|采用|decision|decided|choose", text, re.I):
        return FactKind.decision
    if re.search(r"故障|阻塞|失败|报错|风险|问题|bug|blocked|issue|error", text, re.I) and not re.search(r"已修复|已解决|恢复正常|resolved|fixed", text, re.I):
        return FactKind.issue
    if re.search(r"交付|产出|附件|报告|交付物|artifact|delivered|提交.{0,15}(?:文档|报告|链接)", text, re.I):
        return FactKind.artifact
    if re.search(r"计划|安排|预计|准备|将于|明天|下周|plan|scheduled", text, re.I):
        return FactKind.plan
    if re.search(r"会议|评审通过|上线|发布|验收通过|恢复正常|已解决|已修复|release|meeting|resolved", text, re.I):
        return FactKind.event
    return FactKind.task


def infer_status(text: str) -> str:
    if re.search(r"取消|不再|cancel", text, re.I):
        return "cancelled"
    if re.search(r"返工|重做|修订|rework|revis", text, re.I):
        return "rework"
    future = re.search(r"预计|计划|安排|准备|将于|明天|下周|后天|plan|scheduled", text, re.I)
    observed_completion = re.search(r"已完成|已经完成|完成了|已交付|已解决|已修复|已上线|已发布|恢复正常|completed|delivered|resolved|fixed", text, re.I)
    if future and not observed_completion:
        return "planned"
    recovered = re.search(r"已修复|已解决|恢复正常|resolved|fixed", text, re.I)
    still_broken = re.search(r"仍(?:有|然|未)|尚未|未修复|未解决|还有.{0,8}(?:故障|问题|失败)|still\s+(?:blocked|broken|failing)", text, re.I)
    if recovered and not still_broken:
        return "completed"
    if re.search(r"未完成|尚未|等待|阻塞|失败|故障|报错|blocked|failed", text, re.I):
        return "blocked" if re.search(r"阻塞|失败|故障|报错|blocked|failed", text, re.I) else "pending"
    if re.search(r"已完成|完成了|完成$|已交付|交付了|已解决|已修复|通过|已上线|已发布|done|completed|delivered|resolved|fixed", text, re.I):
        return "completed"
    if re.search(r"开始|进行|开发中|处理中|in.progress|started", text, re.I):
        return "in_progress"
    if re.search(r"计划|安排|预计|准备|将于|明天|下周|plan|scheduled", text, re.I):
        return "planned"
    return "observed"


def explicit_relations(quote: str) -> list[dict[str, str]]:
    """Require a quoted target: no guessed pronouns or inferred causal links."""
    relations = []
    for relation, phrase in RELATION_PATTERNS:
        pattern = r"(?:" + phrase + r")\s*[「『“\"]([^」』”\"\n]{1,120})[」』”\"]"
        for match in re.finditer(pattern, quote, re.I):
            relations.append({"relation": relation, "target_entity_key": match.group(1).strip(), "quote": quote})
    return relations


def extract_local(message: StandardMessage) -> list[WorkFact]:
    """Extract one source-bound observation per work clause, retaining exact quote."""
    if classify_message(message) != "work":
        return []
    hints = project_hints(message.text)
    default_entity = ENTITY.search(message.text)
    facts = []
    for raw in re.split(r"[；;。\n]+", message.text):
        quote = raw.strip()
        if not quote or not WORK.search(quote) or INJECTION.search(quote):
            continue
        local_hints = project_hints(quote) or hints
        entity = ENTITY.search(quote) or default_entity
        summary = PROJECT.sub("", quote)
        summary = ENTITY.sub("", summary).strip(" ,，:：") or quote
        kind = infer_kind(summary)
        attributes: dict = {"provider": "local-demo", "classification": "work"}
        if len(local_hints) > 1:
            attributes["project_candidates"] = local_hints
        relations = explicit_relations(quote)
        if relations:
            attributes["relations"] = relations
        facts.append(WorkFact(
            id=stable_fact_id(message, kind.value, quote, summary),
            kind=kind,
            summary=summary,
            project_hint=local_hints[0] if len(local_hints) == 1 else None,
            entity_key=entity.group(1).strip() if entity else None,
            actor=message.sender,
            status=infer_status(summary),
            occurred_at=message.timestamp,
            evidence=[EvidenceReference(message_id=message.id, source_id=message.source_id, quote=quote)],
            confidence=0.75,
            attributes=attributes,
        ))
    return facts
