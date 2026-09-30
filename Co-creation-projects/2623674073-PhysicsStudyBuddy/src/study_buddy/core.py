"""Deterministic study workflow; language models supply bounded content only."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


TOPICS = {
    "牛顿第二定律": {
        "objectives": ["受力分析", "规律理解", "公式应用"],
        "prerequisites": ["合力与受力分析", "加速度的含义"],
    },
    "匀变速直线运动": {
        "objectives": ["运动量辨析", "图像理解", "公式应用"],
        "prerequisites": ["速度与加速度"],
    },
    "功与动能定理": {
        "objectives": ["功的计算", "动能变化", "综合应用"],
        "prerequisites": ["力与位移", "动能"],
    },
}


class Backend(Protocol):
    def make_quiz(self, context: dict[str, Any]) -> list[dict[str, Any]]: ...

    def grade_short(self, question: dict[str, Any], answer: str) -> dict[str, Any]: ...

    def make_plan(self, context: dict[str, Any]) -> list[dict[str, Any]]: ...

    def answer(self, context: dict[str, Any], question: str) -> str: ...

    def search(self, query: str) -> list[dict[str, str]]: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_quiz(questions: list[dict[str, Any]]) -> None:
    if not isinstance(questions, list) or len(questions) != 5:
        raise ValueError("诊断题必须恰好包含 5 题")
    if any(not isinstance(q, dict) for q in questions):
        raise ValueError("每道诊断题必须是对象")
    if [q.get("type") for q in questions].count("choice") != 3:
        raise ValueError("诊断题必须包含 3 道选择题")
    if [q.get("type") for q in questions].count("short") != 2:
        raise ValueError("诊断题必须包含 2 道简答题")
    ids = [q.get("id") for q in questions]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != 5:
        raise ValueError("题目 ID 缺失或重复")
    for q in questions:
        for field in ("skill", "stem", "explanation"):
            if not isinstance(q.get(field), str) or not q[field].strip():
                raise ValueError(f"题目 {q['id']} 缺少 {field}")
        if q["type"] == "choice":
            if not isinstance(q.get("options"), dict) or set(q["options"]) != set("ABCD"):
                raise ValueError(f"题目 {q['id']} 的选项不完整")
            if any(not isinstance(option, str) or not option.strip() for option in q["options"].values()):
                raise ValueError(f"题目 {q['id']} 存在空选项")
            if not isinstance(q.get("correct_answer"), str) or q["correct_answer"] not in "ABCD":
                raise ValueError(f"题目 {q['id']} 的答案无效")
        elif (not isinstance(q.get("rubric"), list) or len(q["rubric"]) != 2
              or any(not isinstance(point, str) or not point.strip() for point in q["rubric"])):
            raise ValueError(f"题目 {q['id']} 需要两个有效评分要点")
    if len({q["skill"] for q in questions}) < 2:
        raise ValueError("诊断题至少覆盖两个能力点")


def validate_plan(tasks: list[dict[str, Any]]) -> None:
    if not isinstance(tasks, list) or not 3 <= len(tasks) <= 6:
        raise ValueError("计划必须包含 3 到 6 个任务")
    if any(not isinstance(task, dict) for task in tasks):
        raise ValueError("每项计划任务必须是对象")
    ids: set[str] = set()
    for task in tasks:
        for field in ("id", "title", "why", "done_when"):
            if not isinstance(task.get(field), str) or not task[field].strip():
                raise ValueError(f"计划任务缺少 {field}")
        if task["id"] in ids:
            raise ValueError("计划任务 ID 重复")
        ids.add(task["id"])
        if not isinstance(task.get("minutes"), int) or not 5 <= task["minutes"] <= 120:
            raise ValueError("任务预计用时须为 5 到 120 分钟")
        if not isinstance(task.get("resource_query", ""), str):
            raise ValueError("resource_query 必须为文本")


def score_round(
    questions: list[dict[str, Any]], answers: dict[str, str], backend: Backend
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    expected = {q["id"] for q in questions}
    if set(answers) != expected:
        raise ValueError("请完成全部五道题再提交")
    results: list[dict[str, Any]] = []
    totals: dict[str, dict[str, Any]] = defaultdict(lambda: {"earned": 0, "possible": 0, "items": 0})
    for q in questions:
        answer = str(answers[q["id"]]).strip()
        if q["type"] == "choice":
            earned = 2 if answer.upper() == q["correct_answer"] else 0
            feedback = "回答正确。" if earned else f"正确答案：{q['correct_answer']}。{q['explanation']}"
        elif not answer:
            earned, feedback = 0, "未作答；请对照评分要点复习。"
        else:
            grading = backend.grade_short(q, answer)
            earned = grading.get("score")
            feedback = grading.get("feedback")
            if type(earned) is not int or earned not in (0, 1, 2):
                raise ValueError(f"题目 {q['id']} 的简答评分无效")
            if not isinstance(feedback, str) or not feedback.strip():
                raise ValueError(f"题目 {q['id']} 的简答反馈为空")
        results.append({"question_id": q["id"], "skill": q["skill"], "answer": answer,
                        "earned": earned, "possible": 2, "feedback": feedback})
        bucket = totals[q["skill"]]
        bucket["earned"] += earned
        bucket["possible"] += 2
        bucket["items"] += 1
    mastery = {}
    for skill, value in totals.items():
        ratio = value["earned"] / value["possible"]
        label = "需要补基础" if ratio < 0.5 else "需要练习" if ratio < 0.8 else "掌握较好"
        mastery[skill] = {**value, "level": label}
    return results, mastery


class StudyBuddy:
    def __init__(self, backend: Backend, progress_dir: Path):
        self.backend = backend
        self.progress_dir = Path(progress_dir)

    def _path(self, learner: str, subject: str, topic: str) -> Path:
        key = json.dumps([learner, subject, topic], ensure_ascii=False)
        return self.progress_dir / (hashlib.sha256(key.encode("utf-8")).hexdigest()[:24] + ".json")

    def open(self, learner: str, subject: str, topic: str, grade: str = "高一") -> dict[str, Any]:
        learner, subject, topic, grade = (x.strip() for x in (learner, subject, topic, grade))
        if not learner or not topic:
            raise ValueError("学习者名称和知识点不能为空")
        if subject not in ("物理", "高中物理"):
            raise ValueError("首版支持高中物理；请输入“物理”或“高中物理”")
        if grade not in ("高一", "高二", "高三"):
            raise ValueError("年级请选择高一、高二或高三")
        path = self._path(learner, subject, topic)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        catalog = TOPICS.get(topic, {})
        session = {"learner": learner, "subject": subject, "topic": topic, "grade": grade,
                   "reviewed_topic": bool(catalog), "objectives": catalog.get("objectives", []),
                   "prerequisites": catalog.get("prerequisites", []), "rounds": [], "plan": [],
                   "pending_quiz": None, "created_at": _now(), "updated_at": _now()}
        self._save(session)
        return session

    def _save(self, session: dict[str, Any]) -> None:
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        session["updated_at"] = _now()
        path = self._path(session["learner"], session["subject"], session["topic"])
        temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            temp.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
            for attempt in range(5):
                try:
                    os.replace(temp, path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def begin_quiz(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        if session["pending_quiz"] is not None:
            return session["pending_quiz"]
        context = {key: session[key] for key in ("subject", "topic", "grade", "objectives", "prerequisites")}
        context["round_number"] = len(session["rounds"]) + 1
        context["previous_questions"] = [q["stem"] for rnd in session["rounds"] for q in rnd["questions"]]
        context["latest_mastery"] = session["rounds"][-1]["mastery"] if session["rounds"] else {}
        questions = self.backend.make_quiz(context)
        validate_quiz(questions)
        session["pending_quiz"] = questions
        self._save(session)
        return questions

    def submit(self, session: dict[str, Any], answers: dict[str, str]) -> dict[str, Any]:
        questions = session.get("pending_quiz")
        if not questions:
            raise ValueError("没有待提交的测验，请先开始诊断或复测")
        results, mastery = score_round(questions, answers, self.backend)
        completed = [task for task in session["plan"] if task.get("completed")]
        context = {key: session[key] for key in ("subject", "topic", "grade", "prerequisites")}
        context.update({"mastery": mastery, "results": results, "completed_tasks": completed,
                        "round_number": len(session["rounds"]) + 1})
        tasks = self.backend.make_plan(context)
        validate_plan(tasks)
        for task in tasks:
            task["completed"] = False
            task["resources"] = []
        notices = []
        for task in tasks[:2]:
            query = task.get("resource_query", "").strip()
            if query:
                try:
                    task["resources"] = self.backend.search(query)[:2]
                    if not task["resources"]:
                        notices.append("本次未找到可展示的外部学习资源。")
                except Exception as exc:
                    notices.append(f"资源搜索暂不可用：{exc}")
        round_result = {"number": len(session["rounds"]) + 1, "at": _now(), "questions": questions,
                        "results": results, "mastery": mastery}
        session["rounds"].append(round_result)
        session["pending_quiz"] = None
        session["plan"] = tasks
        session["notices"] = notices
        self._save(session)
        return round_result

    def complete_task(self, session: dict[str, Any], task_id: str) -> None:
        for task in session["plan"]:
            if task["id"] == task_id:
                task["completed"] = True
                self._save(session)
                return
        raise ValueError("未找到该计划任务")

    def ask(self, session: dict[str, Any], question: str) -> str:
        if not question.strip():
            raise ValueError("问题不能为空")
        context = {"subject": session["subject"], "topic": session["topic"],
                   "grade": session["grade"], "plan": session["plan"],
                   "mastery": session["rounds"][-1]["mastery"] if session["rounds"] else {}}
        return self.backend.answer(context, question.strip())
