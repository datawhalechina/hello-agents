"""连接已有 Chromium 一次，读取公开页；云 Session 由创建方结束。"""

import asyncio
import json
import os
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

TARGET = "https://example.com/"


async def read_page(endpoint: str, target: str = TARGET) -> dict:
    """不创建、重连或替换云运行，只关闭本例创建的页面并断开连接。"""
    address = urlsplit(endpoint)
    local_fixture = address.scheme == "ws" and address.hostname in {"127.0.0.1", "::1"}
    if (address.scheme != "wss" and not local_fixture) or not address.hostname or address.username or address.password:
        raise ValueError("invalid_endpoint")
    # Do not let inherited Playwright debug settings print the control URL.
    os.environ.pop("DEBUG", None)
    os.environ.pop("PWDEBUG", None)
    result = {"page_task": "failed", "client_cleanup": "pending", "cloud_release": "not_checked"}
    async with async_playwright() as playwright:
        browser = None
        page = None
        cleanup_ok = True
        try:
            browser = await playwright.chromium.connect_over_cdp(endpoint, timeout=10000)
            if not browser.contexts:
                raise RuntimeError("default_context_missing")
            page = await browser.contexts[0].new_page()
            response = await page.goto(target, wait_until="domcontentloaded", timeout=15000)
            if response is None or not response.ok:
                raise RuntimeError("page_response_failed")
            title = await page.title()
            heading = await page.locator("h1").first.inner_text(timeout=5000)
            if not title.strip() or not heading.strip():
                raise RuntimeError("empty_page_result")
            result.update(page_task="passed", title=title[:200], heading=heading[:300])
        finally:
            if page is not None:
                try:
                    await asyncio.wait_for(page.close(), 5)
                except Exception:
                    cleanup_ok = False
            if browser is not None:
                try:
                    await asyncio.wait_for(browser.close(), 5)
                except Exception:
                    cleanup_ok = False
            result["client_cleanup"] = "completed" if cleanup_ok else "unconfirmed"
    return result


def main() -> int:
    try:
        result = asyncio.run(asyncio.wait_for(
            read_page(os.environ.get("CAPY_CDP_ENDPOINT", "")), 45
        ))
    except (Exception, KeyboardInterrupt):
        print(json.dumps({"page_task": "failed", "cloud_release": "not_checked",
                          "next_action": "The Session owner must stop and inspect the original Session."}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["page_task"] == "passed" and result["client_cleanup"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
