"""将带 _mx_meta 的妙想服务结果转换为统一 HTTP 响应"""

from __future__ import annotations

import copy
from typing import Any

from app.utils.mx_quota import MX_QUOTA_HINT
from app.utils.response import error_response, success_response


def mx_result_to_http(result: dict, *, http_error_code: int = 500) -> dict:
    """
    result 可含 _mx_meta:
      from_cache, quota_exhausted, cache_ttl_seconds, channel, hint
    """
    payload = copy.deepcopy(result)
    meta = payload.pop("_mx_meta", None)

    if not payload.get("success"):
        err = payload.get("error") or "请求失败"
        return error_response(code=http_error_code, message=err)

    msg = "success"
    if isinstance(meta, dict) and meta.get("quota_exhausted"):
        msg = meta.get("hint") or MX_QUOTA_HINT

    return success_response(data=payload, message=msg, meta=meta)
