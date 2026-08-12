"""
将 SQLite 历史文本记忆回填到 Milvus。
运行：
  cd backend && .venv/bin/python scripts/reindex_milvus.py
"""

from __future__ import annotations

from memory.store import list_all_user_ids
from rag.indexers import reindex_user


def main() -> None:
    users = list_all_user_ids(limit=5000)
    total = 0
    for uid in users:
        n = reindex_user(uid, limit=500)
        total += n
        print(f"user={uid} indexed={n}")
    print(f"done users={len(users)} total_chunks={total}")


if __name__ == "__main__":
    main()
