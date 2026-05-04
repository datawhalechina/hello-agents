from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import RemoteDisconnected
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from xml.etree import ElementTree as ET
import html


USER_AGENT = "rss-digest-bot/0.1"


@dataclass(slots=True)
class FeedEntry:
    title: str
    link: str
    published_at: str
    summary: str


def fetch_text(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def normalize_datetime(value: str) -> str:
    if not value:
        return ""

    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return value


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _find_text(node: ET.Element, tag_name: str) -> str:
    for child in node.iter():
        if _strip_namespace(child.tag) == tag_name and child.text:
            return child.text.strip()
    return ""


def _find_link(node: ET.Element) -> str:
    fallback = ""
    for child in node.iter():
        if _strip_namespace(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "").strip().lower()
        if href and rel == "alternate":
            return href.strip()
        if href:
            if not fallback or rel not in {"self", "hub"}:
                fallback = href.strip()
            continue
        if child.text and not fallback:
            fallback = child.text.strip()
    return fallback


def _find_summary(node: ET.Element) -> str:
    for tag_name in ("summary", "description", "content", "content:encoded"):
        text = _find_text(node, tag_name)
        if text:
            return html.unescape(text)
    return ""


def parse_feed(xml_text: str) -> list[FeedEntry]:
    root = ET.fromstring(xml_text)
    entries: list[FeedEntry] = []

    for node in root.iter():
        local_name = _strip_namespace(node.tag)
        if local_name not in {"item", "entry"}:
            continue

        title = html.unescape(_find_text(node, "title") or "Untitled")
        link = _find_link(node)
        published = normalize_datetime(
            _find_text(node, "published")
            or _find_text(node, "updated")
            or _find_text(node, "pubDate")
        )
        summary = _find_summary(node)

        if link:
            entries.append(
                FeedEntry(
                    title=title,
                    link=link,
                    published_at=published,
                    summary=summary,
                )
            )
    return entries


def fetch_feed_entries(feed_url: str, timeout: int) -> list[FeedEntry]:
    try:
        xml_text = fetch_text(feed_url, timeout)
        entries = parse_feed(xml_text)
        entries.sort(key=lambda item: item.published_at or "", reverse=True)
        return entries
    except (ET.ParseError, URLError, HTTPError, TimeoutError, RemoteDisconnected, ConnectionResetError):
        return []
