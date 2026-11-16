"""Read-only Feishu history with explicit durable page acknowledgement.

No token acquisition, messages sends or other enterprise mutation exists here.
The consumer must atomically persist a SyncPage's messages and next checkpoint.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, replace
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.connectors.local import normalize_record
from app.schemas import StandardMessage


class FeishuReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    payload: dict[str, Any]
    headers: Mapping[str, str] | None = None


@dataclass(frozen=True)
class SyncCheckpoint:
    source_id: str
    chat_id: str
    start_time: int | None = None  # Unix seconds, fixed for a pagination run
    end_time: int | None = None
    page_token: str | None = None
    high_watermark_ms: int = 0
    complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SyncCheckpoint":
        return cls(**value)


@dataclass(frozen=True)
class SyncPage:
    messages: list[StandardMessage]
    checkpoint: SyncCheckpoint


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a bearer token to a redirect destination.
        return None


def _http_get(url: str, headers: Mapping[str, str]) -> HttpResponse:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with build_opener(_NoRedirect).open(request, timeout=30) as response:
            data = response.read(12 * 1024 * 1024 + 1)
            if len(data) > 12 * 1024 * 1024:
                raise FeishuReadError("Feishu response exceeds size limit")
            payload = json.loads(data)
            if not isinstance(payload, dict):
                raise FeishuReadError("Feishu returned an invalid response object")
            return HttpResponse(response.status, payload, dict(response.headers))
    except HTTPError as exc:
        # Error response content may be sensitive and is intentionally not reflected.
        return HttpResponse(exc.code, {}, dict(exc.headers))
    except (URLError, TimeoutError) as exc:
        raise FeishuReadError("Feishu network read failed") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FeishuReadError("Feishu returned malformed JSON") from exc


class FeishuHistoryClient:
    """GET-only adapter; authorization must be supplied by the application owner."""

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = "https://open.feishu.cn",
        page_size: int = 50,
        max_attempts: int = 3,
        transport: Callable[[str, Mapping[str, str]], HttpResponse] = _http_get,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        if not access_token or "\n" in access_token or "\r" in access_token:
            raise ValueError("a valid access token is required")
        if base_url not in {"https://open.feishu.cn", "https://open.larksuite.com"}:
            raise ValueError("only official Feishu/Lark API hosts are allowed")
        if not 1 <= page_size <= 50 or not 1 <= max_attempts <= 6:
            raise ValueError("page_size must be 1–50 and max_attempts 1–6")
        self._token = access_token
        self._base_url = base_url
        self.page_size = page_size
        self.max_attempts = max_attempts
        self._transport = transport
        self._sleep = sleeper

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        url = self._base_url + "/open-apis/im/v1/messages?" + urlencode(params)
        for attempt in range(self.max_attempts):
            try:
                response = self._transport(url, {"Authorization": "Bearer " + self._token})
            except FeishuReadError:
                if attempt + 1 == self.max_attempts:
                    raise
                self._sleep(min(2**attempt, 30))
                continue
            code = response.payload.get("code")
            retryable = response.status == 429 or response.status >= 500 or code in {99991400, 99991401}
            if retryable and attempt + 1 < self.max_attempts:
                try:
                    delay = float((response.headers or {}).get("Retry-After", 2**attempt))
                except (ValueError, TypeError):
                    delay = 2**attempt
                self._sleep(max(0, min(delay, 30)))
                continue
            if response.status != 200 or code != 0:
                raise FeishuReadError(f"Feishu read failed (HTTP {response.status}, code {code})")
            data = response.payload.get("data")
            if not isinstance(data, dict):
                raise FeishuReadError("Feishu response is missing data")
            return data
        raise FeishuReadError("Feishu retry budget exhausted")

    def fetch_page(self, checkpoint: SyncCheckpoint) -> SyncPage:
        """Input state never mutates; returned checkpoint is tentative until committed."""
        if not checkpoint.source_id.strip() or not checkpoint.chat_id.strip():
            raise ValueError("checkpoint requires source_id and chat_id")
        if checkpoint.complete:
            return SyncPage([], checkpoint)
        if checkpoint.start_time is not None and checkpoint.end_time is not None:
            if checkpoint.start_time > checkpoint.end_time:
                raise ValueError("start_time must not exceed end_time")
        params: dict[str, Any] = {
            "container_id_type": "chat",
            "container_id": checkpoint.chat_id,
            "sort_type": "ByCreateTimeAsc",
            "page_size": self.page_size,
        }
        for key in ("start_time", "end_time", "page_token"):
            value = getattr(checkpoint, key)
            if value is not None:
                params[key] = value
        data = self._request(params)
        items = data.get("items", [])
        if not isinstance(items, list) or not isinstance(data.get("has_more"), bool):
            raise FeishuReadError("invalid Feishu pagination response")
        has_more = data["has_more"]
        next_token = data.get("page_token") if has_more else None
        if has_more and (not isinstance(next_token, str) or not next_token or next_token == checkpoint.page_token):
            raise FeishuReadError("Feishu pagination did not advance")
        unique: dict[str, StandardMessage] = {}
        watermark = checkpoint.high_watermark_ms
        for raw in items:
            try:
                if not isinstance(raw, dict):
                    raise ValueError("message must be an object")
                if raw.get("chat_id", checkpoint.chat_id) != checkpoint.chat_id:
                    raise ValueError("message chat identity mismatch")
                message = normalize_record({**raw, "chat_id": checkpoint.chat_id}, checkpoint.source_id)
            except (ValueError, TypeError, OverflowError, OSError) as exc:
                raise FeishuReadError("invalid Feishu history item; checkpoint unchanged") from exc
            if message.id in unique and unique[message.id] != message:
                raise FeishuReadError("conflicting duplicate message in Feishu page")
            unique[message.id] = message
            watermark = max(watermark, int(message.timestamp.timestamp() * 1000))
        return SyncPage(
            list(unique.values()),
            replace(checkpoint, page_token=next_token, high_watermark_ms=watermark, complete=not has_more),
        )

    def sync(
        self,
        checkpoint: SyncCheckpoint,
        commit_page: Callable[[list[StandardMessage], SyncCheckpoint], None],
        *,
        max_pages: int = 100,
    ) -> SyncCheckpoint:
        """Read bounded pages, committing evidence and state through the caller's sink.

        Sink must persist duplicates idempotently. An exception leaves the current page
        unacknowledged. Previous successful pages remain recoverable from the sink.
        """
        if not 1 <= max_pages <= 1000:
            raise ValueError("max_pages must be 1–1000")
        state = checkpoint
        seen_cursors: set[str] = set()
        if state.page_token:
            seen_cursors.add(state.page_token)
        for _ in range(max_pages):
            if state.complete:
                break
            page = self.fetch_page(state)
            cursor = page.checkpoint.page_token
            if cursor and cursor in seen_cursors:
                raise FeishuReadError("Feishu cursor cycle detected")
            commit_page(page.messages, page.checkpoint)
            state = page.checkpoint
            if cursor:
                seen_cursors.add(cursor)
            if not state.complete:
                self._sleep(0.2)
        return state


def incremental_checkpoint(
    previous: SyncCheckpoint,
    *,
    end_time: int | None = None,
    overlap_seconds: int = 2,
) -> SyncCheckpoint:
    """Start a new run with overlap, retaining equal-time records via sink deduplication."""
    if not previous.complete:
        raise ValueError("resume unfinished pagination before incremental sync")
    if overlap_seconds < 1:
        raise ValueError("overlap_seconds must be positive")
    start = max(0, previous.high_watermark_ms // 1000 - overlap_seconds)
    return SyncCheckpoint(
        source_id=previous.source_id,
        chat_id=previous.chat_id,
        start_time=start,
        end_time=end_time,
        high_watermark_ms=previous.high_watermark_ms,
    )
