"""示范作答的材料边界、冻结上下文和按题保存。"""

from fastapi import HTTPException
from . import demo
from .schemas import DemonstrationAnswer


def prepare(store, workspace_id, session_id, question_id):
    item = store.get(workspace_id)
    session = next((s for s in item["sessions"] if s["id"] == session_id), None)
    if session is None:
        raise KeyError(session_id)
    eligible = (
        item.get("demo_role") == "development"
        and session.get("workflow_version") == 2
        and session["snapshot"]["resume"] == demo.RESUME
        and session["snapshot"]["job"] == demo.JOB
    )
    if not eligible or session["mode"] != "live":
        raise HTTPException(409, "此功能仅用于真实模型示范，不代答个人面试。")
    if session["status"] != "active":
        raise HTTPException(409, "本场示范已结束。")
    question = session["questions"][len(session["turns"])]
    if question["id"] != question_id:
        raise HTTPException(409, "题目已变化，请刷新后重试。")
    return {
        "resume": session["snapshot"]["resume"],
        "job": session["snapshot"]["job"],
        "scenario_notes": demo.DEVELOPMENT_SCENARIO,
        "question": {"text": question["text"], "topic": question["topic"]},
        "history": [
            {"question": t["question"]["text"], "answer": t["answer"]}
            for t in session["turns"]
        ],
    }, session.get("demonstration_drafts", {}).get(question_id)


def save(store, workspace_id, session_id, question_id, text):
    answer = DemonstrationAnswer(answer=text.strip()).answer
    item = store.get(workspace_id)
    session = next((s for s in item["sessions"] if s["id"] == session_id), None)
    if session is None:
        raise KeyError(session_id)
    if (
        session["status"] != "active"
        or session["questions"][len(session["turns"])]["id"] != question_id
    ):
        raise HTTPException(409, "题目已变化，生成结果未填入新题。")
    draft = {"question_id": question_id, "answer": answer}
    session.setdefault("demonstration_drafts", {})[question_id] = draft
    session["demonstration"] = True
    store.save(item, item["revision"])
    return draft
