"""Read-only context projections over immutable imported message evidence.

These helpers never repair or rewrite a StandardMessage. Display text is not an
evidence quote: every quote is an exact slice of the already-stored text.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
import re
from typing import Any

from app.schemas import StandardMessage


IdentityMap = Mapping[tuple[str, str], str]


def _raw(message: StandardMessage) -> dict[str, Any]:
    value = message.metadata.get("raw", {})
    return value if isinstance(value, dict) else {}


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def reply_references(message: StandardMessage) -> list[str]:
    """Ordered parent, root and thread IDs; caller verifies source/chat/time.

    A root/thread ID alone is a context candidate, not evidence that every
    message in that thread belongs to one project. Self references are omitted.
    """
    raw = _raw(message)
    result: list[str] = []
    imported = message.metadata.get("import")
    if isinstance(imported, dict) and imported.get("reply_to_message_id") is not None:
        values = (imported["reply_to_message_id"], message.thread_id)
    else:
        values = (raw.get("parent_id"), raw.get("root_id"), message.thread_id, raw.get("thread_id"))
    for value in values:
        if _nonblank(value) and value != message.id and value not in result:
            result.append(value)
    return result


def build_identity_map(messages: Sequence[StandardMessage]) -> dict[tuple[str, str], str]:
    """Resolve source-local IDs only when all observed names agree.

    Names come from explicit sender/mention fields, never fuzzy body matching.
    An ID with conflicting names is excluded, rather than choosing input order.
    This projection is for display/attribution and does not merge user identities.
    """
    candidates: dict[tuple[str, str], set[str]] = defaultdict(set)
    for message in messages:
        raw = _raw(message)
        sender = raw.get("sender")
        identities = [sender] if isinstance(sender, dict) else []
        mentions = raw.get("mentions")
        if isinstance(mentions, list):
            identities.extend(item for item in mentions if isinstance(item, dict))
        for identity in identities:
            user_id = identity.get("id")
            if not _nonblank(user_id):
                continue
            for field in ("name", "sender_name"):
                name = identity.get(field)
                if _nonblank(name) and len(name) <= 200:
                    candidates[(message.source_id, user_id)].add(name.strip())
    return {key: next(iter(names)) for key, names in candidates.items() if len(names) == 1}


def resolve_sender_name(message: StandardMessage, identities: IdentityMap) -> str:
    """Return a source-supported display name, otherwise the original sender."""
    sender = _raw(message).get("sender")
    user_id = sender.get("id") if isinstance(sender, dict) else message.sender
    if _nonblank(user_id):
        name = identities.get((message.source_id, user_id))
        if name:
            return name
    return message.sender


@dataclass(frozen=True, slots=True)
class TextSegment:
    start: int
    end: int
    quote: str
    display_text: str


class _DisplayText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style"}:
            self.hidden.append(tag)

    def handle_endtag(self, tag: str):
        if self.hidden and self.hidden[-1] == tag:
            self.hidden.pop()

    def handle_data(self, data: str):
        if not self.hidden:
            self.parts.append(data)


def display_text(text: str) -> str:
    """Plain presentation/analysis projection; never use this as an exact quote."""
    parser = _DisplayText()
    parser.feed(text)
    parser.close()
    return " ".join("".join(parser.parts).split())


# Entire non-visible blocks precede structural markers so markup inside a script
# or comment cannot be reinterpreted as a visible work paragraph.
_BOUNDARY = re.compile(
    r"<!--.*?(?:-->|$)|"
    r"<(?P<hidden>script|style)\b[^>]*>.*?(?:</(?P=hidden)\s*>|$)|"
    r"</?(?:p|div|li|ul|ol|h[1-6]|br|tr|td|th|table|blockquote|section|article)\b[^>]*>|"
    r"\r\n|\r|\n",
    re.IGNORECASE | re.DOTALL,
)


def message_segments(text: str) -> list[TextSegment]:
    """Split line/HTML block boundaries while retaining exact source offsets.

    Inline tags and encoded entities remain in quote; only display_text renders
    them. No links, scripts, attachments or external resources are followed.
    """
    result: list[TextSegment] = []

    def append(start: int, end: int) -> None:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            quote = text[start:end]
            plain = display_text(quote)
            if plain:
                result.append(TextSegment(start, end, quote, plain))

    cursor = 0
    for boundary in _BOUNDARY.finditer(text):
        append(cursor, boundary.start())
        cursor = boundary.end()
    append(cursor, len(text))
    return result


def iter_text_segments(text: str) -> list[str]:
    """Convenience list of literal evidence quotes for paragraph-level analysis."""
    return [segment.quote for segment in message_segments(text)]
