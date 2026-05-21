
from __future__ import annotations

import email.utils
import hashlib
import os
import re
from typing import Any

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from ...settings import get_settings

def _iter_file(path: str):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 256)
            if not chunk:
                break
            yield chunk

def build_library_pdf_response(*, paper_id: int, request: Request, db_path: str, logger: Any) -> Response:
    from ...core.storage import PaperDatabase
    path = PaperDatabase(db_path).get_library_pdf_abspath(paper_id)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="本地 PDF 不存在")

    data_root = os.path.realpath(os.path.abspath(get_settings().data_dir))
    real_path = os.path.realpath(os.path.abspath(path))
    if real_path != data_root and not real_path.startswith(data_root + os.sep):
        logger.warning(
            "PDF 路径安全检查失败: paper_id=%d, path=%s, data_root=%s",
            int(paper_id),
            path,
            data_root,
        )
        raise HTTPException(status_code=403, detail="非法文件路径")

    st = os.stat(path)
    file_size = int(st.st_size)
    mtime = int(st.st_mtime)
    range_header = request.headers.get("range") or request.headers.get("Range")
    if_none_match = (request.headers.get("if-none-match") or request.headers.get("If-None-Match") or "").strip()
    if_modified_since = (
        request.headers.get("if-modified-since") or request.headers.get("If-Modified-Since") or ""
    ).strip()
    if_range = (request.headers.get("if-range") or request.headers.get("If-Range") or "").strip()

    etag_raw = f"{path}|{mtime}|{file_size}".encode("utf-8", "ignore")
    etag = 'W/"' + hashlib.sha1(etag_raw).hexdigest() + '"'
    last_modified = email.utils.formatdate(mtime, usegmt=True)

    common_headers: dict[str, str] = {
        "Content-Disposition": f"inline; filename=paper-{int(paper_id)}.pdf",
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "Accept-Ranges, Content-Range, Content-Length, ETag, Last-Modified",
        "Cache-Control": "public, max-age=3600",
        "ETag": etag,
        "Last-Modified": last_modified,
    }

    if not range_header:
        try:
            if if_none_match and if_none_match == etag:
                return Response(status_code=304, headers=common_headers)
            if if_modified_since:
                ims_ts = email.utils.parsedate_to_datetime(if_modified_since).timestamp()
                if int(ims_ts) >= mtime:
                    return Response(status_code=304, headers=common_headers)
        except Exception:
            pass

    if not range_header:
        return StreamingResponse(
            _iter_file(path),
            media_type="application/pdf",
            headers={**common_headers, "Content-Length": str(file_size)},
        )

    if if_range:
        ok = if_range in (etag, last_modified)
        if not ok:
            return StreamingResponse(
                _iter_file(path),
                media_type="application/pdf",
                headers={**common_headers, "Content-Length": str(file_size)},
            )

    m = re.match(r"bytes=(\d+)-(\d*)", range_header.strip())
    if not m:
        return Response(status_code=416, headers={**common_headers, "Content-Range": f"bytes */{file_size}"})
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else file_size - 1
    if start >= file_size:
        return Response(status_code=416, headers={**common_headers, "Content-Range": f"bytes */{file_size}"})
    end = min(end, file_size - 1)
    if end < start:
        return Response(status_code=416, headers={**common_headers, "Content-Range": f"bytes */{file_size}"})

    length = end - start + 1

    def iter_range():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1024 * 256, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        **common_headers,
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(length),
    }
    return StreamingResponse(iter_range(), status_code=206, media_type="application/pdf", headers=headers)
