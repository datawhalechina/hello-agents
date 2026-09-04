"""hr_stream_store.py

已保存训练的 1Hz 心率流旁挂存储（DATA-05）。

为什么要单独一个 store
----------------------
心率流有两个互相冲突的约束：

1. **不能进 `daily_records.json`**。`query_daily_records` 会把整条 record 交给
   ReAct 观察，一段 64 分钟的训练就是 1802 个采样点——足以把上下文撑爆。
   项目一贯的原则是"脏活留 Python、决策交 LLM"，1Hz 流属于前者。
2. **不能进 `health.db` 的 `heart_rate_samples`**。那张表存的是全天 1 分钟
   级监测数据，日汇总与趋势都按"每个采样点等权"来算均值。把 1Hz 训练流灌
   进去，训练那一小时会被加权约 30 倍，当天的日均心率直接失真。

所以流本身按训练记录 id 旁挂成独立文件，`daily_records.json` 里只留一份
体积恒定的摘要（条数、最小/最大/均值、覆盖窗口）。Python 需要重算区间心率
时按 id 取回原始流，LLM 永远只看到摘要。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from fithealth_agent.atomic_json import atomic_write_json
from fithealth_agent.settings import data_path


logger = logging.getLogger(__name__)

def default_stream_dir() -> Path:
    """每次调用都重新解析，便于测试在运行中切换数据目录。"""
    return data_path("hr_streams")


class HRStreamStore:
    def __init__(self, stream_dir: Path | None = None) -> None:
        self.stream_dir = stream_dir or default_stream_dir()
        self.stream_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 路径归属
    # ------------------------------------------------------------------

    def resolve(self, record_id: str) -> Path | None:
        """把记录 id 映射到流文件路径，并强制目录归属校验。

        沿用 DATA-02 的做法：只取 basename，且解析后的父目录必须就是
        stream_dir，避免任何形式的路径穿越把读写引到数据目录之外。
        """
        name = Path(str(record_id or "")).name
        if not name or name in {".", ".."}:
            return None
        path = self.stream_dir / f"{name}.json"
        try:
            if path.resolve().parent != self.stream_dir.resolve():
                logger.warning("拒绝越界的心率流路径：%s", path)
                return None
        except OSError:
            return None
        return path

    # ------------------------------------------------------------------
    # 写入与摘要
    # ------------------------------------------------------------------

    @staticmethod
    def summarize(samples: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """算出体积恒定的摘要——这是唯一允许进入 LLM 上下文的部分。"""
        values: list[int] = []
        stamps: list[str] = []
        for item in samples:
            if not isinstance(item, dict):
                continue
            bpm = item.get("heart_rate")
            timestamp = item.get("timestamp")
            if bpm is None or not isinstance(timestamp, str):
                continue
            try:
                values.append(int(bpm))
            except (TypeError, ValueError):
                continue
            stamps.append(timestamp)
        if not values:
            return {"samples": 0}
        return {
            "samples": len(values),
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 1),
            "start": min(stamps),
            "end": max(stamps),
        }

    def save(self, record_id: str, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """落盘 1Hz 流，返回可以安全塞进训练记录的摘要（含 file 指针）。"""
        summary = self.summarize(samples)
        if not summary.get("samples"):
            return summary
        path = self.resolve(record_id)
        if path is None:
            logger.warning("心率流未保存：记录 id 无法解析为合法路径（%s）", record_id)
            return summary
        payload = {
            "record_id": str(record_id),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "samples": samples,
        }
        atomic_write_json(path, payload, indent=None)
        return {**summary, "file": path.name}

    # ------------------------------------------------------------------
    # 读取与删除
    # ------------------------------------------------------------------

    def load(self, record_id: str) -> list[dict[str, Any]]:
        path = self.resolve(record_id)
        if path is None or not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("心率流 %s 读取失败：%s", record_id, exc)
            return []
        samples = payload.get("samples") if isinstance(payload, dict) else None
        return samples if isinstance(samples, list) else []

    def get_summary(self, record_id: str) -> dict[str, Any] | None:
        path = self.resolve(record_id)
        if path is None or not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        summary = payload.get("summary") if isinstance(payload, dict) else None
        return summary if isinstance(summary, dict) else None

    def delete(self, record_id: str) -> bool:
        path = self.resolve(record_id)
        if path is None or not path.exists():
            return False
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("删除心率流 %s 失败：%s", record_id, exc)
            return False
        return True

    @staticmethod
    def _references(records: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
        references: dict[str, list[str]] = {}
        for item in records:
            if not isinstance(item, dict):
                continue
            record = item.get("record")
            stream = record.get("hr_stream") if isinstance(record, dict) else None
            filename = stream.get("file") if isinstance(stream, dict) else None
            if not isinstance(filename, str) or Path(filename).name != filename:
                continue
            references.setdefault(filename, []).append(str(item.get("id") or ""))
        return references

    def audit(self, records: Iterable[dict[str, Any]]) -> dict[str, list[Any]]:
        """Compare sidecar files with the pointers stored in training records."""
        references = self._references(records)
        present = {path.name for path in self.stream_dir.glob("*.json") if path.is_file()}
        return {
            "orphans": sorted(present - references.keys()),
            "missing": [
                {"file": name, "record_ids": sorted(record_ids)}
                for name, record_ids in sorted(references.items())
                if name not in present
            ],
        }

    def delete_orphan(self, name: str, records: Iterable[dict[str, Any]]) -> bool:
        safe_name = Path(str(name or "")).name
        if safe_name != str(name or "") or not safe_name.endswith(".json"):
            raise ValueError("心率流文件名无效")
        if safe_name not in self.audit(records)["orphans"]:
            return False
        path = self.stream_dir / safe_name
        try:
            if path.resolve().parent != self.stream_dir.resolve() or not path.is_file():
                return False
            path.unlink()
        except OSError as exc:
            logger.warning("删除孤立心率流 %s 失败：%s", safe_name, exc)
            return False
        return True

    def clear(self) -> int:
        removed = 0
        for path in self.stream_dir.glob("*.json"):
            try:
                path.unlink()
                removed += 1
            except OSError as exc:
                logger.warning("删除心率流文件 %s 失败：%s", path.name, exc)
        return removed
