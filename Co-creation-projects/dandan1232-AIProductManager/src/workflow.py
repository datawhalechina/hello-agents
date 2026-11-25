"""Application workflow. Confirmed input is stored separately from generated suggestions."""
from __future__ import annotations

import copy
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import AppError
from .prompts import BRIEF_KEYS, BRIEF_LABELS

MAX_ROUNDS = 6
REVIEW_DECISIONS = {"pending": "待确认", "first_release": "首版做", "later": "以后做"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def string(value, limit=6000) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise AppError("字段需要是文本，且不能超过允许的长度。")
    return value.strip()


def strings(value, limit=12) -> list[str]:
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(x, str) or len(x) > 6000 for x in value):
        raise AppError("模型列表字段格式异常，请重试。", 502)
    return [x.strip() for x in value if x.strip()]


def brief(value) -> dict:
    if not isinstance(value, dict):
        raise AppError("需求内容应为对象。")
    return {key: string(value.get(key, "")) for key in BRIEF_KEYS}


def pending_questions(state: dict, value=None) -> list[str]:
    if value is None:
        return list(state.get("pending_questions", state.get("assumptions", [])))
    if not isinstance(value, list) or len(value) > 12:
        raise AppError("待确认事项最多填写 12 条，每行一条。")
    return [question for question in map(string, value) if question]


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.lock = threading.RLock()
        with self.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, updated TEXT, data TEXT)")
            # A killed server cannot continue an old in-flight request.
            for project_id, payload in conn.execute("SELECT id, data FROM projects").fetchall():
                state = json.loads(payload)
                if state.get("busy"):
                    state.update(busy=False, error="上次任务因服务中断未完成，可以重试。")
                    conn.execute("UPDATE projects SET data=? WHERE id=?", (json.dumps(state, ensure_ascii=False), project_id))

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save(self, state: dict) -> None:
        state["updated_at"] = now()
        with self.lock, self.connect() as conn:
            conn.execute("INSERT OR REPLACE INTO projects VALUES (?, ?, ?)",
                         (state["id"], state["updated_at"], json.dumps(state, ensure_ascii=False)))

    def get(self, project_id: str) -> dict:
        with self.lock, self.connect() as conn:
            row = conn.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise AppError("未找到这个项目，请从项目列表重新打开。", 404)
        return json.loads(row[0])

    def list(self) -> list[dict]:
        with self.lock, self.connect() as conn:
            rows = conn.execute("SELECT data FROM projects ORDER BY updated DESC LIMIT 50").fetchall()
        return [{k: state.get(k) for k in ("id", "title", "stage", "updated_at", "busy")}
                for state in (json.loads(row[0]) for row in rows)]


class Workflow:
    def __init__(self, store: Store, backend, search):
        self.store, self.backend, self.search = store, backend, search

    def create(self, idea: str) -> dict:
        idea = string(idea, 12000)
        if len(idea) < 5:
            raise AppError("请用至少 5 个字描述你想做的产品。")
        state = {"id": uuid.uuid4().hex, "title": idea[:28], "idea": idea,
                 "messages": [{"role": "user", "content": idea}], "round": 0,
                 "brief": dict.fromkeys(BRIEF_KEYS, ""), "assumptions": [],
                 "question": "", "options": [], "ready": False, "confirmed_brief": None,
                 "sources": [], "competitors": [], "research_summary": "", "notices": [],
                 "assessment": None, "prd": None, "conflicts": [], "report": "",
                 "stage": "interview", "activity": "正在理解你的想法", "busy": False, "error": "",
                 "created_at": now(), "updated_at": now()}
        self.store.save(state)
        return state

    def checkpoint(self, state: dict, stage: str, activity: str):
        state.update(stage=stage, activity=activity)
        self.store.save(state)

    def update_draft(self, state: dict, edits: dict, questions=None) -> None:
        if state["confirmed_brief"] is not None:
            raise AppError("请先选择修改已确认需求。", 409)
        if not isinstance(edits, dict) or any(key not in BRIEF_KEYS for key in edits):
            raise AppError("草稿修改包含未知的需求字段。")
        changes = {key: string(value) for key, value in edits.items()}
        if questions is not None:
            state["pending_questions"] = pending_questions(state, questions)
        state.setdefault("manual_brief", {}).update(changes)
        state["brief"].update(changes)
        for key in changes:
            state.get("draft_suggestions", {}).pop(key, None)
        state["title"] = state["brief"]["title"] or state["idea"][:28]

    def save_draft(self, state: dict, edits: dict, questions=None) -> None:
        self.update_draft(state, edits, questions)
        self.store.save(state)

    def interview(self, state: dict) -> None:
        if state["confirmed_brief"] is not None:
            raise AppError("这份需求已经确认，请先选择修改需求。", 409)
        if state["round"] >= MAX_ROUNDS:
            raise AppError("已达到六轮访谈上限，请检查并确认右侧需求。", 409)
        self.checkpoint(state, "interview", "正在整理回答并选择下一个问题")
        manual = state.get("manual_brief", {})
        result = self.backend.run("interview", {"conversation": state["messages"], "draft": state["brief"],
                                               "manual_brief": manual,
                                               "round": state["round"] + 1, "max_rounds": MAX_ROUNDS})
        new_brief = brief(result.get("brief"))
        assumptions = strings(result.get("assumptions", []))
        question = string(result.get("question", ""), 2000)
        reply = string(result.get("reply", ""), 3000)
        if not isinstance(result.get("ready", False), bool):
            raise AppError("模型的访谈完成标记格式异常，请重试。", 502)
        options = strings(result.get("options", []), 3)
        state["round"] += 1
        ready = bool(result.get("ready")) or not question or state["round"] >= MAX_ROUNDS
        if ready:
            question, options = "", []
        suggestions = {key: new_brief[key] for key, value in manual.items()
                       if new_brief[key] and new_brief[key] != value}
        new_brief.update(manual)
        state.update(brief=new_brief, assumptions=assumptions, ready=ready,
                     draft_suggestions=suggestions, question=question, options=options,
                     title=new_brief["title"] or state["title"])
        content = "\n\n".join(x for x in (reply, question) if x)
        if ready:
            content += "\n\n请检查右侧草稿，补充或修改后确认。未确定的信息可以保留为空。"
        state["messages"].append({"role": "assistant", "content": content})
        self.checkpoint(state, "confirm" if ready else "interview", "等待确认需求" if ready else "等待你的回答")

    def add_answer(self, state: dict, answer: str, edits=None, questions=None) -> None:
        if state["confirmed_brief"] is not None or state["ready"] or state["round"] >= MAX_ROUNDS:
            raise AppError("访谈已结束，请在需求草稿中修改内容。", 409)
        answer = string(answer, 8000)
        if not answer:
            raise AppError("请先填写你的回答。")
        if state["messages"][-1]["role"] == "user":
            raise AppError("上一条回答还未处理成功，请使用重试。", 409)
        if edits is not None or questions is not None:
            self.update_draft(state, {} if edits is None else edits, questions)
        state["messages"].append({"role": "user", "content": answer})
        self.store.save(state)

    def confirm(self, state: dict, value: dict, questions=None) -> None:
        confirmed = brief(value)
        if not confirmed["title"] or not confirmed["problem"]:
            raise AppError("至少填写产品名称和要解决的问题，再确认需求。")
        confirmed_questions = pending_questions(state, questions)
        state.update(brief=confirmed, confirmed_brief=copy.deepcopy(confirmed), title=confirmed["title"],
                     confirmed_questions=confirmed_questions, draft_suggestions={},
                     ready=True, question="", options=[], report="", report_id=None, prd=None, prd_reviews={}, assessment=None,
                     sources=[], competitors=[], research_summary="", notices=[], conflicts=[], error="")
        self.checkpoint(state, "confirmed", "需求已确认，可以开始分析")

    def reopen(self, state: dict) -> None:
        # Remove stale deliverables after changing the decision baseline.
        questions = state.get("confirmed_questions", pending_questions(state))
        state.update(confirmed_brief=None, pending_questions=questions, report="", report_id=None,
                     prd=None, prd_reviews={}, assessment=None, sources=[], competitors=[],
                     notices=[], conflicts=[], research_summary="", error="", ready=True)
        self.checkpoint(state, "confirm", "请修改并重新确认需求；旧分析结果已失效")

    def generate(self, state: dict, online: bool) -> None:
        if state["confirmed_brief"] is None:
            raise AppError("请先检查并确认需求，再生成分析。", 409)
        confirmed = copy.deepcopy(state["confirmed_brief"])
        # Keep the last complete report readable while this run collects its results.
        generated = {"sources": [], "competitors": [], "notices": [], "research_summary": "", "prd_reviews": {}}
        state["online"] = online
        self.checkpoint(state, "research", "正在查询相关产品" if online else "已跳过联网竞品研究")
        if online:
            query = f"{confirmed['title']} {confirmed['target_users']} {confirmed['problem'][:200]} 同类产品 功能 官网"
            try:
                generated["sources"] = self.search.search(query)
            except AppError as exc:
                generated["notices"].append(str(exc))
            if generated["sources"]:
                result = self.backend.run("research", {"confirmed_brief": confirmed, "evidence": generated["sources"]})
                competitors = result.get("competitors", [])
                if not isinstance(competitors, list) or len(competitors) > 3:
                    raise AppError("竞品结果格式异常，请重新生成。", 502)
                valid_ids = {s["id"] for s in generated["sources"]}
                for item in competitors:
                    if not isinstance(item, dict):
                        raise AppError("竞品条目格式异常，请重新生成。", 502)
                    ids = strings(item.get("source_ids", []), 6)
                    if not ids or not set(ids).issubset(valid_ids):
                        generated["notices"].append("已移除一条缺少有效来源的竞品结论。")
                        continue
                    generated["competitors"].append({**{k: string(item.get(k, "")) for k in
                                                         ("name", "positioning", "features", "difference")}, "source_ids": ids})
                generated["research_summary"] = string(result.get("summary", ""))
            else:
                generated["notices"].append("未获得竞品资料；文档中会明确标记，本次不生成竞品事实。")
        else:
            generated["notices"].append("本次未进行联网竞品研究。")
        context = {"confirmed_brief": confirmed, "confirmed_questions": state.get("confirmed_questions", pending_questions(state)),
                   "competitors": generated["competitors"], "evidence": generated["sources"],
                   "research_limitations": generated["notices"]}
        self.checkpoint(state, "assess", "正在评估实现条件和首版范围")
        assessment = self.backend.run("assess", context)
        if assessment.get("verdict") not in ("可先做原型", "需先解决依赖", "信息不足"):
            raise AppError("可行性结论格式异常，请重新生成。", 502)
        generated["assessment"] = {"verdict": assessment["verdict"], "reason": string(assessment.get("reason", "")),
                                   **{k: strings(assessment.get(k, [])) for k in
                                      ("technical_path", "dependencies", "risks", "validation_steps")}}
        self.checkpoint(state, "writing", "正在编写 PRD 草稿和验收条件")
        result = self.backend.run("writer", {**context, "assessment": generated["assessment"]})
        requirements = result.get("requirements", [])
        if not isinstance(requirements, list) or not requirements or len(requirements) > 20:
            raise AppError("PRD 缺少有效功能条目，请重新生成。", 502)
        cleaned = []
        for item in requirements:
            if not isinstance(item, dict):
                raise AppError("PRD 功能条目格式异常，请重新生成。", 502)
            row = {k: string(item.get(k, "")) for k in ("name", "description", "acceptance")}
            if not all(row.values()):
                raise AppError("PRD 功能条目缺少描述或验收条件，请重新生成。", 502)
            cleaned.append(row)
        generated["prd"] = {"requirements": cleaned, **{k: strings(result.get(k, [])) for k in
                            ("user_stories", "nonfunctional", "milestones", "open_questions")}}
        self.checkpoint(state, "audit", "正在核对 PRD 是否遵守已确认的需求")
        audit = self.backend.run("audit", {"confirmed_brief": confirmed, "draft": generated["prd"]})
        generated["conflicts"] = strings(audit.get("conflicts", []))
        generated.update(report_id=uuid.uuid4().hex, report_generated_at=now())
        completed = {**state, **generated}
        completed["report"] = render_report(completed)
        activity = "草稿存在待修正的冲突，请检查" if completed["conflicts"] else "PRD 草稿已生成，请检查建议内容"
        self.checkpoint(completed, "done", activity)
        state.update(completed)

    def review_requirement(self, state: dict, index, decision, acceptance, report_id) -> None:
        if not state["report"] or not state.get("prd") or state.get("report_id") != report_id:
            raise AppError("文档已更新，请重新打开当前版本再评审。", 409)
        requirements = state["prd"]["requirements"]
        if type(index) is not int or not 0 <= index < len(requirements):
            raise AppError("未找到要评审的功能条目。")
        if not isinstance(decision, str) or decision not in REVIEW_DECISIONS:
            raise AppError("请选择首版做、以后做或待确认。")
        acceptance = string(acceptance)
        if not acceptance:
            raise AppError("请填写这项功能的验收条件。")
        state.setdefault("prd_reviews", {})[str(index)] = {"decision": decision, "acceptance": acceptance}
        state.setdefault("report_generated_at", state["updated_at"])
        state["report"] = render_report(state)
        self.store.save(state)


def render_report(state: dict) -> str:
    b, a, p = state["confirmed_brief"], state["assessment"], state["prd"]
    lines = [f"# {b['title']} · 产品需求文档", "", f"生成时间：{state['report_generated_at']}", "",
             "> 待评审草稿。第一节记录用户确认的需求。分析与未评审的功能为 AI 建议。", "",
             "## 1. 已确认需求", ""]
    for key, label in zip(BRIEF_KEYS, BRIEF_LABELS):
        lines.extend([f"### {label}", b[key] or "尚未确定", ""])
    if state["conflicts"]:
        lines.extend(["## 需要优先修正的需求冲突", "", *["- " + x for x in state["conflicts"]], ""])
    lines.extend(["## 2. 竞品研究", "", *["> " + x for x in state["notices"]], "", state["research_summary"], ""])
    for item in state["competitors"]:
        lines.extend([f"### {item['name']}", f"- 定位：{item['positioning']}", f"- 功能：{item['features']}",
                      f"- 差异与局限：{item['difference']}", f"- 来源编号：{', '.join(item['source_ids'])}", ""])
    lines.extend(["## 3. 可行性建议", "", f"**{a['verdict']}**", a["reason"], ""])
    for key, label in (("technical_path", "实现路径"), ("dependencies", "依赖条件"),
                       ("risks", "风险"), ("validation_steps", "待验证的用户需求")):
        lines.extend([f"### {label}", *["- " + x for x in a[key]], ""])
    lines.extend(["## 4. 功能设计建议", "", "以下为待评审建议，需由用户确认后再进入开发。", "",
                  "### 用户故事", *["- " + x for x in p["user_stories"]], ""])
    reviews = state.get("prd_reviews", {})
    for index, item in enumerate(p["requirements"]):
        lines.extend([f"### F{index + 1:02d} {item['name']}", item["description"], ""])
        review = reviews.get(str(index))
        if review:
            lines.extend(["评审决定：" + REVIEW_DECISIONS[review["decision"]], "",
                          "验收条件（用户评审）：" + review["acceptance"], ""])
        else:
            lines.extend(["验收条件：" + item["acceptance"], ""])
    for label, key in (("5. 非功能需求建议", "nonfunctional"), ("6. 实施顺序建议", "milestones"),
                       ("7. 待确认问题", "open_questions")):
        lines.extend(["## " + label, ""])
        if key == "open_questions":
            questions = state.get("confirmed_questions", pending_questions(state))
            if questions:
                lines.extend(["### 需求确认时保留的事项", "", *["- " + x for x in questions], ""])
            suggestions = [q for q in p[key] if q not in questions]
            if suggestions:
                lines.extend(["### AI 补充的问题", "", *["- " + x for x in suggestions], ""])
        else:
            lines.extend([*["- " + x for x in p[key]], ""])
    lines.extend(["## 8. 资料来源", ""])
    for source in state["sources"]:
        lines.extend([f"- [{source['id']}] {source['title']}", f"  {source['url']}", f"  查询时间：{source['retrieved_at']}"])
    if not state["sources"]:
        lines.append("本次没有可列出的联网资料。")
    return "\n".join(lines).strip() + "\n"
