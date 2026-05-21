from __future__ import annotations

import os
import threading

from app.core.search import PaperSearcher
from app.core.storage import PaperDatabase

from ..settings import get_settings

_singleton_lock = threading.Lock()
_searcher: PaperSearcher | None = None
_database: PaperDatabase | None = None

def get_searcher() -> PaperSearcher:
    global _searcher
    if _searcher is not None:
        return _searcher
    with _singleton_lock:
        if _searcher is not None:
            return _searcher
        s = get_settings()
        _searcher = PaperSearcher(
            email=(s.openalex_mailto or s.ncbi_email) or None,
            api_key=s.ncbi_api_key or None,
            download_dir=s.downloads_dir,
            httpx_trust_env=s.papergraph_httpx_trust_env,
        )
        return _searcher

def get_database() -> PaperDatabase:
    global _database
    if _database is not None:
        return _database
    with _singleton_lock:
        if _database is not None:
            return _database
        s = get_settings()
        db_path = os.path.join(s.data_dir, "papers.db")
        _database = PaperDatabase(db_path)
        return _database

def get_db_path() -> str:
    return get_database().db_path
