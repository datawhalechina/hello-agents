"""NoteOrganizer - 笔记自动整理器

为 Agent 提供笔记自动整理能力，支持：
- 自动检测临时笔记积累情况
- 智能分析内容重要性并评分
- 自动将重要笔记升级为任务笔记或项目笔记
- 自动清理冗余、过时、重复的临时笔记
- 相似内容检测与合并

使用场景：
- 长时程任务的笔记自动整理
- 知识沉淀与结构化
- 存储空间优化
"""

import re
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from difflib import SequenceMatcher


class NoteOrganizerPolicy:
    """笔记自动整理策略配置"""

    def __init__(
        self,
        temp_notes_threshold: int = 10,
        check_interval_minutes: int = 30,
        importance_threshold_promote: float = 0.7,
        importance_threshold_project: float = 0.85,
        importance_threshold_delete: float = 0.2,
        max_temp_age_days: int = 7,
        max_task_notes_per_task: int = 20,
        auto_promote_enabled: bool = True,
        auto_cleanup_enabled: bool = True,
        auto_merge_enabled: bool = True,
    ):
        self.temp_notes_threshold = temp_notes_threshold
        self.check_interval_minutes = check_interval_minutes
        self.importance_threshold_promote = importance_threshold_promote
        self.importance_threshold_project = importance_threshold_project
        self.importance_threshold_delete = importance_threshold_delete
        self.max_temp_age_days = max_temp_age_days
        self.max_task_notes_per_task = max_task_notes_per_task
        self.auto_promote_enabled = auto_promote_enabled
        self.auto_cleanup_enabled = auto_cleanup_enabled
        self.auto_merge_enabled = auto_merge_enabled


class NoteClassifier:
    """笔记分类器 - 重要性评分"""

    DECISION_KEYWORDS = {
        "决定",
        "选择",
        "结论",
        "方案",
        "最终",
        "采用",
        "确定",
        "决定使用",
    }
    PROBLEM_KEYWORDS = {
        "问题",
        "错误",
        "bug",
        "失败",
        "异常",
        "失败原因",
        "修复",
        "解决",
    }
    TASK_KEYWORDS = {"目标", "待办", "下一步", "计划", "任务", "完成", "实现"}
    LEARNING_KEYWORDS = {"学会", "发现", "学到了", "掌握", "理解", "注意到"}

    def __init__(self, current_task_context: Optional[str] = None):
        self.current_task_context = current_task_context or ""

    def calculate_importance(self, note: Dict[str, Any]) -> float:
        """计算笔记重要性分数 (0-1)"""
        content = note.get("content", "")
        title = note.get("title", "")
        text = f"{title} {content}"

        content_score = self._calc_content_score(text, content)
        context_score = self._calc_context_score(text, note)
        time_score = self._calc_time_score(note)

        return content_score * 0.6 + context_score * 0.3 + time_score * 0.1

    def _calc_content_score(self, text: str, content: str) -> float:
        """计算内容质量分 (0-1)"""
        score = 0.0

        text_lower = text.lower()

        if any(kw in text_lower for kw in self.DECISION_KEYWORDS):
            score += 0.3
        if any(kw in text_lower for kw in self.PROBLEM_KEYWORDS):
            score += 0.15
        if any(kw in text_lower for kw in self.TASK_KEYWORDS):
            score += 0.2
        if any(kw in text_lower for kw in self.LEARNING_KEYWORDS):
            score += 0.25

        length = len(content)
        if 50 <= length <= 500:
            score += 0.1
        elif length > 1000:
            score += 0.05

        has_structure = bool(re.search(r"[0-9]+\.|\-|•|\*|##", content))
        if has_structure:
            score += 0.1

        return min(1.0, score)

    def _calc_context_score(self, text: str, note: Dict[str, Any]) -> float:
        """计算上下文相关分 (0-1)"""
        score = 0.0

        if self.current_task_context:
            context_lower = self.current_task_context.lower()
            text_lower = text.lower()

            context_words = set(context_lower.split())
            text_words = set(text_lower.split())
            overlap = len(context_words & text_words)
            if overlap > 0:
                score += min(0.3, overlap * 0.05)

        tags = note.get("tags", [])
        if tags and isinstance(tags, list):
            score += min(0.1, len(tags) * 0.02)

        return min(1.0, score)

    def _calc_time_score(self, note: Dict[str, Any]) -> float:
        """计算时效分 (0-1)"""
        created_at = note.get("created_at", "")
        if not created_at:
            return 0.5

        try:
            created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now()

            if created_time.tzinfo:
                now = datetime.now(created_time.tzinfo)

            days_old = (now - created_time).days

            if days_old <= 1:
                return 1.0
            elif days_old <= 7:
                return 0.8
            elif days_old <= 14:
                return 0.6
            elif days_old <= 30:
                return 0.4
            else:
                return 0.2
        except Exception:
            return 0.5

    def compute_similarity(self, note1: Dict[str, Any], note2: Dict[str, Any]) -> float:
        """计算两条笔记的相似度 (0-1)"""
        content1 = note1.get("content", "")
        content2 = note2.get("content", "")

        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = intersection / union if union > 0 else 0.0

        title1 = note1.get("title", "")
        title2 = note2.get("title", "")
        title_sim = 1.0 if title1 and title1 == title2 else 0.0

        matcher = SequenceMatcher(None, content1, content2)
        edit_sim = matcher.ratio()

        return jaccard * 0.4 + title_sim * 0.2 + edit_sim * 0.4


class OrganizeResult:
    """整理结果"""

    def __init__(
        self,
        promoted: List[Dict[str, Any]] = None,
        elevated: List[Dict[str, Any]] = None,
        deleted: List[Dict[str, Any]] = None,
        merged: List[Dict[str, Any]] = None,
    ):
        self.promoted = promoted or []
        self.elevated = elevated or []
        self.deleted = deleted or []
        self.merged = merged or []

    @property
    def total_changes(self) -> int:
        return (
            len(self.promoted)
            + len(self.elevated)
            + len(self.deleted)
            + len(self.merged)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promoted": self.promoted,
            "elevated": self.elevated,
            "deleted": self.deleted,
            "merged": self.merged,
            "total_changes": self.total_changes,
            "timestamp": datetime.now().isoformat(),
        }

    def __str__(self) -> str:
        lines = ["📊 笔记整理结果\n"]
        if self.promoted:
            lines.append(f"  ✅ 升级为任务笔记: {len(self.promoted)} 条")
        if self.elevated:
            lines.append(f"  🏆 升级为项目笔记: {len(self.elevated)} 条")
        if self.deleted:
            lines.append(f"  🗑️  删除: {len(self.deleted)} 条")
        if self.merged:
            lines.append(f"  🔗 合并: {len(self.merged)} 条")
        if self.total_changes == 0:
            lines.append("  无需整理")
        return "\n".join(lines)


class NoteOrganizer:
    """笔记自动整理器

    自动分析临时笔记，将重要信息升级为任务/项目笔记，清理冗余内容。

    用法示例：
    ```python
    from tools.builtin.note_organizer import NoteOrganizer, NoteOrganizerPolicy

    policy = NoteOrganizerPolicy(
        temp_notes_threshold=10,
        auto_promote_enabled=True,
        auto_cleanup_enabled=True
    )
    organizer = NoteOrganizer(note_tool, policy=policy)

    # 手动整理
    result = organizer.organize()

    # 启动自动调度
    organizer.start_auto_organize()
    ```
    """

    def __init__(
        self,
        note_tool: "NoteTool",  # noqa: F821
        policy: Optional[NoteOrganizerPolicy] = None,
    ):
        self.note_tool = note_tool
        self.policy = policy or NoteOrganizerPolicy()
        self.classifier = NoteClassifier()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def organize(self, force: bool = False) -> OrganizeResult:
        """执行笔记整理

        Args:
            force: 是否强制执行（忽略阈值检查）

        Returns:
            OrganizeResult: 整理结果
        """
        if not force and not self._should_organize():
            return OrganizeResult()

        temp_notes = self._get_temp_notes()
        if not temp_notes:
            return OrganizeResult()

        for note in temp_notes:
            note["importance_score"] = self.classifier.calculate_importance(note)

        promoted = []
        elevated = []
        deleted = []
        merged = []

        if self.policy.auto_promote_enabled:
            promoted, elevated = self._promote_notes(temp_notes)

        if self.policy.auto_cleanup_enabled:
            deleted = self._cleanup_notes(temp_notes)

        if self.policy.auto_merge_enabled:
            merged = self._merge_similar_notes(temp_notes)

        return OrganizeResult(
            promoted=promoted,
            elevated=elevated,
            deleted=deleted,
            merged=merged,
        )

    def _should_organize(self) -> bool:
        """检查是否应该触发整理"""
        temp_notes = self._get_temp_notes()
        return len(temp_notes) >= self.policy.temp_notes_threshold

    def _get_temp_notes(self) -> List[Dict[str, Any]]:
        """获取所有临时笔记"""
        notes = []
        for note_info in self.note_tool.notes_index.get("notes", []):
            note_id = note_info.get("id")
            if not note_id:
                continue

            note_path = self.note_tool._get_note_path(note_id)
            if not note_path.exists():
                continue

            try:
                with open(note_path, "r", encoding="utf-8") as f:
                    markdown_text = f.read()
                note = self.note_tool._markdown_to_note(markdown_text)
                note["id"] = note_id
                note["note_type"] = note_info.get("type", "general")

                if note.get("tags") and "temp" in note["tags"]:
                    notes.append(note)
                elif note.get("type") == "general":
                    notes.append(note)
            except Exception as e:
                print(f"⚠️ 读取笔记失败 {note_id}: {e}")

        return notes

    def _promote_notes(
        self, notes: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """升级笔记"""
        promoted = []
        elevated = []

        for note in notes:
            score = note.get("importance_score", 0)

            if score >= self.policy.importance_threshold_project:
                new_type = "conclusion"
                new_title = f"[项目] {note.get('title', '无标题')}"
                action = "elevate"
            elif score >= self.policy.importance_threshold_promote:
                new_type = "task_state"
                new_title = note.get("title", "无标题")
                action = "promote"
            else:
                continue

            self.note_tool.run(
                {
                    "action": "create",
                    "title": new_title,
                    "content": note.get("content", ""),
                    "note_type": new_type,
                    "tags": note.get("tags", []) + ["organized"],
                }
            )

            promoted_item = {
                "note_id": note["id"],
                "original_title": note.get("title"),
                "new_type": new_type,
                "score": score,
                "action": action,
            }

            if action == "promote":
                promoted.append(promoted_item)
            else:
                elevated.append(promoted_item)

            self.note_tool.run({"action": "delete", "note_id": note["id"]})

        return promoted, elevated

    def _cleanup_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """清理过期/低价值笔记"""
        deleted = []
        now = datetime.now()
        max_age = timedelta(days=self.policy.max_temp_age_days)

        for note in notes:
            score = note.get("importance_score", 0)

            if score >= self.policy.importance_threshold_delete:
                continue

            created_at = note.get("created_at", "")
            if not created_at:
                continue

            try:
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_time.tzinfo:
                    created_time = created_time.replace(tzinfo=None)

                if now - created_time > max_age:
                    self.note_tool.run({"action": "delete", "note_id": note["id"]})
                    deleted.append(
                        {
                            "note_id": note["id"],
                            "title": note.get("title"),
                            "score": score,
                            "reason": f"超过{self.policy.max_temp_age_days}天且重要性低",
                        }
                    )
            except Exception as e:
                print(f"⚠️ 清理笔记失败 {note.get('id')}: {e}")

        return deleted

    def _merge_similar_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并相似笔记"""
        merged = []
        merged_ids: Set[str] = set()

        for i, note1 in enumerate(notes):
            if note1["id"] in merged_ids:
                continue

            similar_notes = []
            for j, note2 in enumerate(notes):
                if i == j or note2["id"] in merged_ids:
                    continue

                sim = self.classifier.compute_similarity(note1, note2)
                if sim >= 0.6:
                    similar_notes.append((note2, sim))

            if len(similar_notes) >= 2:
                merged_content = note1.get("content", "")
                for similar_note, _ in similar_notes:
                    merged_content += f"\n\n---\n\n{similar_note.get('content', '')}"
                    merged_ids.add(similar_note["id"])

                    self.note_tool.run(
                        {"action": "delete", "note_id": similar_note["id"]}
                    )

                self.note_tool.run(
                    {
                        "action": "update",
                        "note_id": note1["id"],
                        "content": merged_content,
                        "tags": note1.get("tags", []) + ["merged"],
                    }
                )

                merged.append(
                    {
                        "note_id": note1["id"],
                        "merged_count": len(similar_notes),
                        "similar_ids": [n["id"] for n, _ in similar_notes],
                    }
                )

        return merged

    def start_auto_organize(self):
        """启动自动整理调度"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._auto_organize_loop, daemon=True
        )
        self._scheduler_thread.start()

    def stop_auto_organize(self):
        """停止自动整理调度"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

    def _auto_organize_loop(self):
        """自动整理后台循环"""
        interval_seconds = self.policy.check_interval_minutes * 60

        while not self._stop_event.is_set():
            try:
                self.organize()
            except Exception as e:
                print(f"⚠️ 自动整理失败: {e}")

            self._stop_event.wait(interval_seconds)

    def get_status(self) -> Dict[str, Any]:
        """获取整理器状态"""
        temp_notes = self._get_temp_notes()
        return {
            "enabled": self.policy.auto_promote_enabled
            or self.policy.auto_cleanup_enabled,
            "temp_notes_count": len(temp_notes),
            "threshold": self.policy.temp_notes_threshold,
            "is_running": self._scheduler_thread.is_alive()
            if self._scheduler_thread
            else False,
        }


class NoteToolOrganizeMixin:
    """NoteTool 的自动整理混入"""

    def _organize_notes(self, mode: str = "auto", force: bool = False) -> str:
        """执行笔记整理

        Args:
            mode: "auto" 自动模式 或 "manual" 手动模式
            force: 是否强制执行

        Returns:
            整理结果
        """
        if mode == "manual" and not force:
            return "请使用 force=True 强制执行手动整理"

        policy = NoteOrganizerPolicy(
            temp_notes_threshold=self.notes_index.get("metadata", {}).get(
                "temp_threshold", 10
            ),
            auto_promote_enabled=(mode == "auto"),
            auto_cleanup_enabled=(mode == "auto"),
        )

        organizer = NoteOrganizer(self, policy=policy)
        result = organizer.organize(force=force)

        return str(result)
