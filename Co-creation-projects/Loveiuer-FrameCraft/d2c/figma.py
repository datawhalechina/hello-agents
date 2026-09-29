"""Read a selected Figma node without treating input URLs as fetch targets."""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse

import httpx

MAX_BYTES = 8 * 1024 * 1024
NODE_ID = re.compile(r"^[0-9]+:[0-9]+$")


def parse_figma_url(url: str, node_id: str | None = None) -> tuple[str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in {"www.figma.com", "figma.com"}:
        raise ValueError("请输入 https://www.figma.com/design/… 格式的 Figma 链接。")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Figma 链接不能包含登录信息或自定义端口。")
    match = re.fullmatch(r"/(?:design|file|proto)/([a-zA-Z0-9]+)(?:/[^/]*)?/?", parsed.path)
    if not match:
        raise ValueError("链接中缺少合法的 Figma file key。")
    selected = (node_id or parse_qs(parsed.query).get("node-id", [""])[0]).replace("-", ":")
    if not NODE_ID.fullmatch(selected):
        raise ValueError("请在 Figma 选中一个 Frame，复制带 node-id 的链接，或填写节点 ID（如 1:2）。")
    return match.group(1), selected


def fetch_figma(url: str, token: str, node_id: str | None = None, *, client=None) -> tuple[dict, str]:
    file_key, selected = parse_figma_url(url, node_id)
    if not token.strip():
        raise ValueError("缺少 FIGMA_ACCESS_TOKEN，请在项目 .env 中配置有 file_content:read 权限的 Token。")
    owned = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        with client.stream(
            "GET", f"https://api.figma.com/v1/files/{file_key}/nodes",
            params={"ids": selected}, headers={"X-Figma-Token": token},
        ) as response:
            if response.status_code in (401, 403):
                raise ValueError("Figma 拒绝访问：请检查 Token 是否有效，以及是否有目标文件的读取权限。")
            if response.status_code == 404:
                raise ValueError("Figma 文件不存在或当前账号不可访问。")
            if response.status_code == 429:
                retry = response.headers.get("retry-after", "稍后")
                retry = retry if retry.isdigit() else "稍后"
                raise ValueError(f"Figma 请求达到限流，请稍后重试（Retry-After: {retry}）。")
            if response.status_code != 200:
                raise ValueError(f"Figma API 返回 HTTP {response.status_code}，未生成代码。")
            chunks, total = [], 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("Figma 节点数据超过 8 MB，请选择更小的 Frame。")
                chunks.append(chunk)
            try:
                payload = json.loads(b"".join(chunks))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("Figma 返回的数据不是有效 JSON。") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), dict):
                raise ValueError("Figma 返回的数据缺少 nodes。")
            if not payload["nodes"].get(selected):
                raise ValueError(f"Figma 中找不到节点 {selected}，请重新复制 Frame 链接。")
            return payload, selected
    except httpx.TimeoutException as exc:
        raise ValueError("Figma 请求超时，请检查网络后重试。") from exc
    except httpx.HTTPError as exc:
        raise ValueError("无法连接 Figma API，请检查网络后重试。") from exc
    finally:
        if owned:
            client.close()
