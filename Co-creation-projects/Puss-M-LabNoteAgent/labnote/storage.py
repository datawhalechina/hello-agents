# -*- coding: utf-8 -*-
"""实验笔记的结构化存储层（纯 Python，不依赖 LLM）

记录模型：每条实验记录为一个 dict
{
  "id": "20261115-001",
  "date": "2026-11-15",
  "title": "双目立体匹配基线实验",
  "params": {"baseline_cm": 12, "method": "SGM"},
  "results": {"err_px": 0.8},
  "tags": ["stereo", "reconstruction"],
  "raw": "原始输入文本",
  "created_at": "ISO时间戳"
}
"""
import json
import os
import re
import threading
from datetime import datetime


class NoteStore:
    """基于 JSON 文件的实验笔记库（线程安全，支持并发工具调用）"""

    def __init__(self, path: str = None):
        self.path = path or os.path.join(os.getcwd(), "labnote_data.json")
        self._lock = threading.Lock()
        if not os.path.exists(self.path):
            self._write({"notes": [], "counter": 0})

    def _read(self) -> dict:
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

    # ---------- 增 ----------
    def add(self, title: str, date: str = None, params: dict = None,
            results: dict = None, tags: list = None, raw: str = "") -> dict:
        """新增一条实验记录，返回完整记录。"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            data = self._read()
            data["counter"] += 1
            rec = {
                "id": f"{date.replace('-', '')}-{data['counter']:03d}",
                "date": date,
                "title": title,
                "params": params or {},
                "results": results or {},
                "tags": tags or [],
                "raw": raw,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            data["notes"].append(rec)
            self._write(data)
        return rec

    # ---------- 查 ----------
    def search(self, keyword: str = None, tag: str = None, date: str = None,
               limit: int = 5) -> list:
        """按关键词（标题/参数/结果/原文模糊匹配）、标签、日期检索，最新优先。"""
        data = self._read()
        kw = (keyword or "").lower()
        hits = []
        for rec in reversed(data["notes"]):
            if date and not rec["date"].startswith(date):
                continue
            if tag and tag.lower() not in [t.lower() for t in rec["tags"]]:
                continue
            if kw:
                haystack = json.dumps(
                    {k: rec[k] for k in ("title", "params", "results", "raw", "tags")},
                    ensure_ascii=False).lower()
                if kw not in haystack:
                    continue
            hits.append(rec)
            if len(hits) >= limit:
                break
        return hits

    def get(self, note_id: str) -> dict:
        for rec in self._read()["notes"]:
            if rec["id"] == note_id:
                return rec
        return {}

    # ---------- 对比 ----------
    @staticmethod
    def diff(a: dict, b: dict) -> dict:
        """对比两条记录的参数差异：仅在一侧存在 / 两侧值不同。"""
        keys = set(a.get("params", {})) | set(b.get("params", {}))
        diffs = {}
        for k in keys:
            va, vb = a.get("params", {}).get(k, "—"), b.get("params", {}).get(k, "—")
            if va != vb:
                diffs[k] = {"a": va, "b": vb}
        res_keys = set(a.get("results", {})) | set(b.get("results", {}))
        res = {}
        for k in res_keys:
            va, vb = a.get("results", {}).get(k, "—"), b.get("results", {}).get(k, "—")
            if va != vb:
                res[k] = {"a": va, "b": vb}
        return {"params_diff": diffs, "results_diff": res}

    # ---------- 统计 ----------
    def stats(self) -> dict:
        data = self._read()
        notes = data["notes"]
        tags = {}
        for rec in notes:
            for t in rec["tags"]:
                tags[t] = tags.get(t, 0) + 1
        return {"total": len(notes),
                "dates": sorted({r["date"] for r in notes}, reverse=True)[:10],
                "top_tags": sorted(tags.items(), key=lambda x: -x[1])[:10]}
