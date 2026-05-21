
from __future__ import annotations

import asyncio
from typing import Any

def _run_loop_until_complete(loop: asyncio.AbstractEventLoop, coro: Any) -> Any:
    try:
        return loop.run_until_complete(coro)
    except asyncio.CancelledError as e:
        raise RuntimeError("search_cancelled") from e

def run_coroutine_sync(coro: Any, *, op_name: str) -> Any:
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None
    if running_loop is not None:
        raise RuntimeError(f"{op_name} called inside running event loop")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        if loop.is_running():
            try:
                import nest_asyncio

                nest_asyncio.apply()
            except Exception as e:
                raise RuntimeError(
                    f"{op_name} called inside running event loop; "
                    "install nest_asyncio or refactor call path to await the async call."
                ) from e
        return _run_loop_until_complete(loop, coro)

    new_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(new_loop)
        return _run_loop_until_complete(new_loop, coro)
    finally:
        try:
            new_loop.close()
        finally:
            asyncio.set_event_loop(None)
