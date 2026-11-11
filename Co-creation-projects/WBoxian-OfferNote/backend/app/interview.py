"""持久化面试状态机：模型提议动作，程序核验后原子提交。"""

import copy
import re

from .agent_tools import InterviewTools, allowed_actions
from .engine import ModelError
from .prompts import PROMPT_VERSION
from .rubric import RUBRIC
from .schemas import InterviewDecision, JudgeOutput, ReferenceAnswersOutput
from .store import now, uid


def new_session(engine, workspace, body, weak_topics):
    topics = []
    for claim in workspace["analysis"]["claims"]:
        title = claim["topic"]
        if weak_topics and title not in weak_topics:
            continue
        topic = next((t for t in topics if t["title"] == title), None)
        if topic:
            topic["claim_ids"].append(claim["id"])
        elif len(topics) < 6:
            topics.append(
                {
                    "id": uid(),
                    "title": title,
                    "claim_ids": [claim["id"]],
                    "status": "unvisited",
                    "covered": [],
                    "gaps": [],
                    "contradictions": [],
                    "evidence": [],
                    "closure": None,
                    "reason": "",
                }
            )
    if not topics:
        raise ModelError("当前材料中没有可核对的复练主题，请重新分析材料。")
    session = {
        "id": uid(),
        "workspace_id": workspace["id"],
        "workflow_version": 2,
        "created_at": now(),
        "mode": body.mode,
        "demonstration": body.demonstration,
        "focus": body.focus,
        "source_session_id": body.source_session_id,
        "analysis_id": workspace["analysis"]["id"],
        "material_fingerprint": workspace["analysis"]["fingerprint"],
        "snapshot": copy.deepcopy(
            {
                "role": workspace["role"],
                "resume": workspace["resume"],
                "job": workspace["job"],
                "analysis": workspace["analysis"],
            }
        ),
        "rubric": copy.deepcopy(RUBRIC),
        "prompt_version": PROMPT_VERSION,
        "budget": {"total_turns": body.count, "max_topic_turns": body.max_topic_turns},
        "status": "active",
        "topics": topics,
        "current_topic_id": None,
        "questions": [],
        "turns": [],
        "trace": [],
        "report": None,
        "report_error": None,
    }
    decide(engine, session)
    return session


def valid_refs(refs, session, topic_id=None):
    turns = {t["id"]: t for t in session["turns"]}
    return bool(refs) and all(
        ref["turn_id"] in turns
        and ref["quote"].strip()
        and ref["quote"] in turns[ref["turn_id"]]["answer"]
        and (
            topic_id is None
            or turns[ref["turn_id"]]["question"]["topic_id"] == topic_id
        )
        for ref in refs
    )


def normalized(text):
    return re.sub(r"[\W_]+", "", text.casefold())


def close_topic(session, closure, reason):
    current = next(
        (t for t in session["topics"] if t["id"] == session["current_topic_id"]), None
    )
    if current:
        current.update(status="closed", closure=closure, reason=reason)


def end_interview(session, closure, reason):
    close_topic(session, closure, reason)
    session.update(
        status="awaiting_report", ended_at=now(), end_reason=reason, report_error=None
    )
    session["trace"].append(
        {
            "action": "finish",
            "topic_id": session["current_topic_id"],
            "reason": reason,
            "closure": closure,
            "tools": [],
            "created_at": now(),
        }
    )


def demo_decision(engine, session):
    tools = InterviewTools(engine, session)
    current = next(
        (t for t in session["topics"] if t["id"] == session["current_topic_id"]), None
    )
    count = (
        sum(t["question"]["topic_id"] == current["id"] for t in session["turns"])
        if current
        else 0
    )
    if current:
        tools.invoke("read_topic_history", {"topic_id": current["id"]})
    available = [t for t in session["topics"] if t["status"] == "unvisited"]
    action = (
        "ask_followup"
        if current and count < min(3, session["budget"]["max_topic_turns"])
        else "switch_topic"
        if available
        else "finish"
    )
    target = available[0] if action == "switch_topic" else current
    progress = {"covered": [], "gaps": [], "contradictions": [], "evidence": []}
    if current and session["turns"]:
        turn = session["turns"][-1]
        progress.update(
            gaps=["演示模式不判断实际技术水平。"],
            evidence=[{"turn_id": turn["id"], "quote": turn["answer"][:160]}],
        )
    question = None
    if action != "finish":
        tools.invoke("read_material_evidence", {"topic_id": target["id"]})
        claim = next(
            c
            for c in session["snapshot"]["analysis"]["claims"]
            if c["id"] in target["claim_ids"]
        )
        templates = [
            f"围绕“{target['title']}”，请选一个真实场景，说明你亲自实现的部分。",
            f"围绕“{target['title']}”刚才的场景，请从一次输入进入系统开始，说明关键调用和数据如何流转。",
            f"围绕“{target['title']}”刚才的实现，哪个失败场景最值得验证？请说明触发方式、预期结果和实际证据。",
        ]
        question = {
            "text": templates[0 if action == "switch_topic" else count],
            "topic": target["title"],
            "source_quote": claim["quote"],
            "intent": "逐步核对真实实现与能力边界。",
            "criteria": ["具体个人动作", "实现与验证证据"],
        }
    session["_step_tool_events"] = tools.events
    return {
        "action": action,
        "topic_id": target["id"],
        "reason": "演示规则继续核实细节。"
        if action == "ask_followup"
        else "演示主题达到轮次阈值，转向其他主题或结束。",
        "closure": None if action == "ask_followup" else "no_progress",
        "question": question,
        "progress": progress,
    }


def decide(engine, session):
    raw = engine.call(
        session["workspace_id"],
        session["mode"],
        "interview",
        {"session": session},
        InterviewDecision,
        lambda: demo_decision(engine, session),
    )
    tools = session.pop("_step_tool_events", [])
    action, target_id = raw["action"], raw["topic_id"]
    topics = {t["id"]: t for t in session["topics"]}
    if action not in allowed_actions(session) or target_id not in topics:
        raise ModelError(
            "面试 Agent 返回了当前状态不允许的动作，本次回答未保存，请重试。"
        )
    current_id = session["current_topic_id"]
    progress = raw["progress"]
    if progress["evidence"] and not valid_refs(
        progress["evidence"], session, current_id
    ):
        raise ModelError("Agent 的主题判断引用了不存在的回答，本次结果未保存。")
    if progress["covered"] and not progress["evidence"]:
        raise ModelError("Agent 未提供已核实维度的回答证据。")
    if action == "ask_followup" and target_id != current_id:
        raise ModelError("继续追问必须留在当前主题。")
    if action == "switch_topic" and topics[target_id]["status"] != "unvisited":
        raise ModelError("Agent 试图重新打开已访问的主题，请重试。")
    if current_id and action != "ask_followup" and raw["closure"] is None:
        raise ModelError("Agent 未提供主题结束依据。")
    if action == "finish" and (target_id != current_id or raw["question"] is not None):
        raise ModelError("结束动作不能生成下一道问题。")
    question = raw["question"]
    if action != "finish":
        if question is None:
            raise ModelError("Agent 未返回下一道问题。")
        if (
            question["source_quote"]
            and question["source_quote"] not in session["snapshot"]["resume"]
        ):
            raise ModelError("问题引用了冻结简历中不存在的内容。")
        if any(
            normalized(q["text"]) == normalized(question["text"])
            for q in session["questions"]
        ):
            raise ModelError("Agent 重复了已经问过的问题，本次结果未保存，请重试。")
        if (
            session["mode"] == "live"
            and action == "switch_topic"
            and not any(
                e["name"] == "read_material_evidence"
                and e["topic_id"] == target_id
                and e["status"] == "success"
                for e in tools
            )
        ):
            raise ModelError(
                "Agent 未成功读取新主题材料。请检查模型的原生工具调用能力。"
            )
    if current_id:
        current = topics[current_id]
        current.update(gaps=progress["gaps"], contradictions=progress["contradictions"])
        if progress["evidence"]:
            current["covered"] = list(
                dict.fromkeys(current["covered"] + progress["covered"])
            )
            current["evidence"] = (current["evidence"] + progress["evidence"])[-12:]
    if action != "ask_followup":
        close_topic(session, raw["closure"], raw["reason"])
    if action == "finish":
        session.update(
            status="awaiting_report", ended_at=now(), end_reason=raw["reason"]
        )
    else:
        topics[target_id]["status"] = "active"
        session["current_topic_id"] = target_id
        question.update(
            id=uid(),
            topic_id=target_id,
            topic=topics[target_id]["title"],
            follow_up_depth=sum(
                t["question"]["topic_id"] == target_id for t in session["turns"]
            ),
        )
        session["questions"].append(question)
    session["trace"].append(
        {
            "action": action,
            "topic_id": target_id,
            "reason": raw["reason"],
            "closure": raw["closure"],
            "tools": tools,
            "created_at": now(),
        }
    )


def answer_turn(engine, session, body):
    question = session["questions"][len(session["turns"])]
    session["turns"].append(
        {
            "id": uid(),
            "request_id": body.request_id,
            "question": copy.deepcopy(question),
            "answer": body.answer,
            "created_at": now(),
        }
    )
    if len(session["turns"]) >= session["budget"]["total_turns"]:
        end_interview(session, "budget", "本场题目预算已达到，仅评估实际作答内容。")
    else:
        decide(engine, session)


def demo_judgement(session):
    turns = session["turns"]
    ref = {"turn_id": turns[0]["id"], "quote": turns[0]["answer"][:120]}
    visited = [
        t
        for t in session["topics"]
        if any(x["question"]["topic_id"] == t["id"] for x in turns)
    ]
    return {
        "summary": "离线演示已完成。评分与技术优缺点需切换真实模型后验证。",
        "scores": [
            {
                "dimension": d["id"],
                "score": None,
                "reason": "演示规则不评判实际能力。",
                "evidence": [],
            }
            for d in session["rubric"]["dimensions"]
        ],
        "topics": [
            {
                "topic_id": t["id"],
                "score": None,
                "reason": "演示模式未评分。",
                "evidence": [],
            }
            for t in visited
        ],
        "strengths": [],
        "weaknesses": [],
        "improvements": [
            {
                "topic_id": turns[0]["question"]["topic_id"],
                "priority": "medium",
                "title": "用真实模型重新核验本轮表达",
                "detail": "此条仅为演示行动项，不判断真实薄弱点。",
                "exercise": "保留问题和原始回答，配置模型后重新面试并检查评审引用。",
                "evidence": [ref],
            }
        ],
    }


def reference_answers(engine, session):
    if session["mode"] == "demo":
        return []
    answers = []
    for offset in range(0, len(session["turns"]), 4):
        turns = session["turns"][offset : offset + 4]
        result = engine.call(
            session["workspace_id"],
            "live",
            "reference_answers",
            {
                "role": session["snapshot"]["role"],
                "turns": [
                    {
                        "turn_id": t["id"],
                        "question": t["question"]["text"],
                        "answer": t["answer"],
                    }
                    for t in turns
                ],
            },
            ReferenceAnswersOutput,
            lambda: {},
        )
        if len(result["answers"]) != len(turns) or {
            a["turn_id"] for a in result["answers"]
        } != {t["id"] for t in turns}:
            raise ModelError("参考答案未覆盖对应题目，请重新生成。")
        answers.extend(result["answers"])
    return answers


def invalid_judge_evidence(raw, session):
    """只返回错误字段位置，不把无效引用当作已核实证据。"""
    errors = []
    for key in ["scores", "topics", "strengths", "weaknesses", "improvements"]:
        for index, item in enumerate(raw[key]):
            if (
                key in ("scores", "topics")
                and item["score"] is None
                and not item["evidence"]
            ):
                continue
            if not valid_refs(item["evidence"], session, item.get("topic_id")):
                errors.append(f"{key}.{index}.evidence")
    return errors


def judge(engine, session):
    visited_ids = {t["question"]["topic_id"] for t in session["turns"]}
    visited = [t for t in session["topics"] if t["id"] in visited_ids]
    context = {
        "role": session["snapshot"]["role"],
        "job": session["snapshot"]["job"],
        "resume": session["snapshot"]["resume"],
        "rubric": session["rubric"],
        "topics": [{"id": t["id"], "title": t["title"]} for t in visited],
        "turns": [
            {
                "turn_id": t["id"],
                "question": {
                    "text": t["question"]["text"],
                    "topic_id": t["question"]["topic_id"],
                    "topic": t["question"]["topic"],
                },
                "answer": t["answer"],
            }
            for t in session["turns"]
        ],
    }
    raw = engine.call(
        session["workspace_id"],
        session["mode"],
        "judge",
        context,
        JudgeOutput,
        lambda: demo_judgement(session),
    )
    dimensions = session["rubric"]["dimensions"]
    if {s["dimension"] for s in raw["scores"]} != {d["id"] for d in dimensions}:
        raise ModelError("评审维度缺失或重复，请重试评审。")
    if (
        len(raw["topics"]) != len(visited)
        or {t["topic_id"] for t in raw["topics"]} != visited_ids
    ):
        raise ModelError("评审覆盖了未作答主题或遗漏实际作答主题，请重试。")
    warnings = []
    evidence_repaired = False
    invalid_fields = invalid_judge_evidence(raw, session)
    if session["mode"] == "live" and invalid_fields:
        try:
            candidate = engine.call(
                session["workspace_id"],
                "live",
                "judge",
                {
                    **context,
                    "previous_review": raw,
                    "evidence_corrections": {
                        "invalid_fields": invalid_fields,
                        "allowed_turn_ids": [t["id"] for t in session["turns"]],
                        "instruction": "前次评审中的引用未通过核验。依据原始 turns 重新评审并返回完整 JSON。"
                        "turn_id 只能使用 turns 中的回答 ID，不能使用问题 ID 或 topic_id；"
                        "quote 必须是对应回答中连续的原文短句，优先选 20–80 字符，不改写、不拼接、不加省略号。"
                        "previous_review 只是待修正候选，不是事实；不要求保留原评分。"
                        "确无依据时该评分用 null，或删除对应优缺点和建议，不得编造引用。",
                    },
                },
                JudgeOutput,
                lambda: {},
            )
            if (
                {s["dimension"] for s in candidate["scores"]}
                == {d["id"] for d in dimensions}
                and len(candidate["topics"]) == len(visited)
                and {t["topic_id"] for t in candidate["topics"]} == visited_ids
            ):
                raw = candidate
                evidence_repaired = not invalid_judge_evidence(raw, session)
            warnings.append("评分证据已自动修正一次，展示内容仍经原文核验。")
        except ModelError:
            warnings.append("评分证据修正未完成，已按原文核验结果保留有效部分。")
    for score in raw["scores"] + raw["topics"]:
        topic_id = score.get("topic_id")
        if score["score"] is not None and not valid_refs(
            score["evidence"], session, topic_id
        ):
            score.update(
                score=None, reason="评分引文未通过核对，本项暂不计分。", evidence=[]
            )
            warnings.append("部分评分缺少有效回答引文，已改为未评估。")
        elif score["evidence"] and not valid_refs(score["evidence"], session, topic_id):
            score["evidence"] = []
    for key in ["strengths", "weaknesses", "improvements"]:
        validated = []
        for item in raw[key]:
            topic_id = item.get("topic_id")
            if (topic_id is not None and topic_id not in visited_ids) or not valid_refs(
                item["evidence"], session, topic_id
            ):
                warnings.append("已隐藏无法核对回答依据的评审结论或建议。")
            else:
                validated.append(item)
        raw[key] = validated
    score_map = {s["dimension"]: s for s in raw["scores"]}
    covered_weight = sum(
        d["weight"] for d in dimensions if score_map[d["id"]]["score"] is not None
    )
    total = (
        round(
            sum(
                score_map[d["id"]]["score"] / 4 * d["weight"]
                for d in dimensions
                if score_map[d["id"]]["score"] is not None
            )
            / covered_weight
            * 100
        )
        if covered_weight >= 60
        else None
    )
    for dimension in dimensions:
        score_map[dimension["id"]].update(
            label=dimension["label"], weight=dimension["weight"]
        )
    weak = [
        t["title"]
        for t in visited
        if next(x["score"] for x in raw["topics"] if x["topic_id"] == t["id"])
        in (0, 1, 2)
    ]
    if session["mode"] == "demo":
        weak = [t["title"] for t in visited]
    references, reference_error = [], None
    try:
        references = reference_answers(engine, session)
    except ModelError as exc:
        reference_error = str(exc)
        warnings.append("评分已完成，参考答案生成失败，可在复盘页单独重试。")
    return {
        **raw,
        "evidence_repaired": evidence_repaired,
        "reference_answers": references,
        "reference_answers_error": reference_error,
        "scores": [score_map[d["id"]] for d in dimensions],
        "total_score": total,
        "covered_weight": covered_weight,
        "rubric_version": session["rubric"]["version"],
        "prompt_version": PROMPT_VERSION,
        "answered": len(session["turns"]),
        "planned": session["budget"]["total_turns"],
        "warnings": list(dict.fromkeys(warnings)),
        "actions": [i["title"] + "：" + i["exercise"] for i in raw["improvements"]],
        "weak_topics": weak,
        "groups": {"supported": [], "partial": [], "unverified": []},
        "scope": "仅评估已作答内容。引文校验只证明原文存在，技术正确性与实际贡献仍需人工复核。",
        "demo_notice": "离线规则演示不评分；演示复练主题不代表真实薄弱点。"
        if session["mode"] == "demo"
        else "模型参考评分，需结合实际代码、产物与人工审核。",
    }
