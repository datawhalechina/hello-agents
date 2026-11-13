"""Discover model IDs without saving the draft connection or returning credentials."""
from __future__ import annotations

import asyncio
import json
from time import perf_counter
from urllib.parse import urlparse

import httpx

from .settings import Settings


class ModelListingUnavailable(ValueError):
    """The service responded, but its optional model-list endpoint is unavailable."""


async def discover_models(base_url: str, api_key: str, settings: Settings,
                          connection_id: str | None = None, use_saved_key: bool = True) -> list[str]:
    endpoint = base_url.strip().rstrip("/")
    try:
        parsed = urlparse(endpoint)
    except ValueError:
        raise ValueError("请填写有效的 HTTP(S) API 地址。") from None
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or
            parsed.username or parsed.password or parsed.query or parsed.fragment or
            any(character.isspace() for character in endpoint)):
        raise ValueError("请填写有效的 HTTP(S) API 地址，不要包含用户名、密码或查询参数。")
    # A saved key belongs to its saved endpoint, never to a newly typed provider.
    key = api_key.strip() or (settings.key_for(endpoint, connection_id) if use_saved_key else "")
    if any(character in key for character in "\r\n"):
        raise ValueError("API Key 不能包含换行，请检查后重试。")
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}

    async def fetch():
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=not local) as client:
            async with client.stream("GET", endpoint + "/models", headers=headers) as response:
                status = response.status_code
                if status in {401, 403}:
                    raise ValueError("获取模型失败，请检查 API Key 和模型服务的访问权限。")
                if status in {404, 405, 501}:
                    raise ModelListingUnavailable("此地址不支持获取模型列表，请检查 API 地址，或手动填写模型名称。")
                if status == 429:
                    raise ValueError("模型服务请求过于频繁或额度不足，请稍后重试。")
                if 300 <= status < 400:
                    raise ValueError("模型服务地址发生跳转，请填写实际 API 地址后重试。")
                if not 200 <= status < 300:
                    raise ValueError(f"获取模型失败（HTTP {status}），请稍后重试或手动填写。")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise ValueError("模型列表响应过大，请手动填写模型名称。")
                try:
                    payload = json.loads(body)
                except (ValueError, UnicodeError):
                    raise ValueError("模型服务未返回有效的模型列表，请检查 API 地址或手动填写。") from None
                entries = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(entries, list):
                    raise ValueError("此服务的模型列表格式无法识别，请手动填写模型名称。")
                names = {entry["id"].strip() for entry in entries
                         if isinstance(entry, dict) and isinstance(entry.get("id"), str)
                         and 0 < len(entry["id"].strip()) <= 200}
                return sorted(names, key=str.casefold)

    try:
        return await asyncio.wait_for(fetch(), timeout=15)
    except (asyncio.TimeoutError, httpx.TimeoutException):
        raise ValueError("获取模型列表超时，请检查网络或 API 地址后重试。") from None
    except httpx.RequestError:
        raise ValueError("无法连接模型服务，请检查网络、API 地址或本地服务是否启动。") from None
    except (httpx.InvalidURL, UnicodeError):
        raise ValueError("API 地址或密钥格式无效，请检查后重试。") from None


async def test_connection(base_url: str, api_key: str, settings: Settings,
                          connection_id: str | None = None, use_saved_key: bool = True) -> dict:
    """Probe access via model discovery; never start generation or save draft settings."""
    started = perf_counter()
    try:
        names = await discover_models(base_url, api_key, settings, connection_id, use_saved_key)
    except ModelListingUnavailable:
        return {"status": "warning", "latency_ms": round((perf_counter() - started) * 1000),
                "message": "服务已响应，但不支持模型列表检测，尚未确认调用权限。请检查地址或手动配置模型。"}
    except ValueError as error:
        raise ValueError(str(error).replace("获取模型失败", "连接测试失败")
                         .replace("获取模型列表超时", "连接测试超时")) from None
    return {"status": "success", "latency_ms": round((perf_counter() - started) * 1000),
            "message": "连接成功，模型列表接口可访问。" if names else "连接成功，但服务未返回可用模型。"}
