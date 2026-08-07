from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import re


USER_AGENT = "rss-digest-bot/0.1"
NOISE_PATTERNS = [
    r"subscribe",
    r"sign in",
    r"sign up",
    r"cookie",
    r"all rights reserved",
    r"previous post",
    r"next post",
    r"related posts?",
    r"table of contents",
    r"share this",
]


class _HTMLToTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attr_text = " ".join(f"{key}={value}" for key, value in attrs)
        attr_text_lower = attr_text.lower()

        if tag in {"script", "style", "noscript", "svg", "form"}:
            self._skip_depth += 1
            return

        if any(flag in attr_text_lower for flag in ["nav", "footer", "sidebar", "comment", "share", "promo", "subscribe"]):
            self._skip_depth += 1
            return

        if tag in {"p", "div", "article", "section", "br", "li", "h1", "h2", "h3", "h4", "blockquote", "pre"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "form"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return

        if tag in {"p", "div", "article", "section", "li", "blockquote", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return

        text = data.strip()
        if not text:
            return
        self.parts.append(text + " ")


def fetch_html(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def _extract_candidate_html(html_text: str) -> str:
    patterns = [
        r"<article\b[^>]*>(.*?)</article>",
        r"<main\b[^>]*>(.*?)</main>",
        r"<body\b[^>]*>(.*?)</body>",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return html_text


def _clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    if len(line) < 30:
        return ""
    lower = line.lower()
    if any(re.search(pattern, lower) for pattern in NOISE_PATTERNS):
        return ""
    return line


def _dedupe_preserve_order(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        output.append(line)
    return output


def html_to_text(html_text: str) -> str:
    candidate = _extract_candidate_html(html_text)
    parser = _HTMLToTextParser()
    parser.feed(candidate)
    text = "".join(parser.parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    raw_lines = [segment.strip() for segment in text.splitlines()]
    cleaned_lines = [_clean_line(line) for line in raw_lines]
    filtered_lines = [line for line in cleaned_lines if line]
    filtered_lines = _dedupe_preserve_order(filtered_lines)
    return "\n\n".join(filtered_lines).strip()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def fetch_and_extract(url: str, timeout: int) -> tuple[str, str]:
    try:
        html_text = fetch_html(url, timeout)
    except (URLError, HTTPError, TimeoutError):
        return "", ""
    return html_text, html_to_text(html_text)
