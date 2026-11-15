import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import demo
from .demonstration import prepare as prepare_demonstration, save as save_demonstration
from .streaming import sse, stream_answer
from .config import ModelConfigInput, save_config
from .engine import Engine, ModelError, fingerprint, report, settings
from .interview import answer_turn, end_interview, judge, new_session, reference_answers
from .files import MAX_BYTES, extract_text
from .schemas import (
    AnswerInput,
    ConfirmInput,
    DemonstrationInput,
    DemonstrationAnswer,
    MaterialsInput,
    ModeInput,
    SessionInput,
    WorkspaceInput,
)
from .store import Conflict, Store, now

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", interpolate=False)


def get_session(workspace: dict, session_id: str) -> dict:
    for session in workspace["sessions"]:
        if session["id"] == session_id:
            return session
    raise KeyError(session_id)


def current_analysis(workspace: dict) -> dict:
    analysis = workspace["analysis"]
    if not analysis or analysis["fingerprint"] != fingerprint(
        workspace["resume"], workspace["job"]
    ):
        raise HTTPException(409, "请先保存材料并重新生成证据分析。")
    return analysis


def create_app(database: str | None = None, env_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="OfferNote 求职面试工作台", version="0.2.0")
    store = Store(
        database or os.getenv("OFFERNOTE_DB", str(ROOT / "data" / "offer-note.sqlite3"))
    )
    store.ensure_demos()
    engine = Engine(store)
    app.state.store, app.state.engine = store, engine
    grading = set()
    grading_lock = threading.Lock()
    demonstrating = set()
    demonstration_lock = threading.Lock()

    def generate_report(workspace_id, session_id):
        # Background jobs are recoverable via /finish. A running session is graded once per process.
        with grading_lock:
            if session_id in grading:
                return
            grading.add(session_id)
        try:
            item = store.get(workspace_id)
            session = get_session(item, session_id)
            if session["status"] != "awaiting_report":
                return
            result, error = None, None
            try:
                result = judge(engine, session)
            except ModelError as exc:
                error = str(exc)
            except Exception:
                error = "评审生成异常，回答已保存，请重试评审。"
            for _attempt in range(3):
                current = store.get(workspace_id)
                stored = get_session(current, session_id)
                if stored["status"] != "awaiting_report":
                    return
                stored["report_error"] = error
                if result is not None:
                    stored.update(report=result, status="completed", completed_at=now())
                try:
                    store.save(current, current["revision"])
                    return
                except Conflict:
                    continue
        except KeyError:
            return  # The user deleted the workspace while grading.
        finally:
            with grading_lock:
                grading.discard(session_id)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(KeyError)
    def missing(_request, _exc):
        return JSONResponse(
            {"detail": "工作区、问题或面试记录不存在。"}, status_code=404
        )

    @app.exception_handler(Conflict)
    def conflict(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ModelError)
    def model_error(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.exception_handler(RequestValidationError)
    def invalid_request(_request, exc):
        return JSONResponse(
            {
                "detail": [
                    {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
                    for e in exc.errors()
                ]
            },
            status_code=422,
        )

    @app.put("/api/settings")
    def update_settings(body: ModelConfigInput, request: Request):
        origin = request.headers.get("origin")
        allowed = {
            str(request.base_url).rstrip("/"),
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
        if origin and origin not in allowed:
            raise HTTPException(403, "配置只接受本机工作台的请求。")
        try:
            return save_config(body, env_path or ROOT / ".env")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except OSError:
            raise HTTPException(500, "无法写入项目 .env，请检查文件权限。") from None

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": "0.2.0",
            "storage": "SQLite",
            "local_only": True,
        }

    @app.get("/api/settings")
    def model_settings():
        return settings()

    @app.post("/api/model-check")
    def model_check():
        return engine.probe()

    @app.get("/api/workspaces")
    def workspaces():
        return [
            {
                key: item[key]
                for key in ["id", "name", "role", "updated_at", "created_at"]
            }
            | {
                "demo_role": item.get("demo_role"),
                "session_count": len(item["sessions"]),
                "has_analysis": item["analysis"] is not None,
            }
            for item in store.list()
        ]

    @app.post("/api/workspaces", status_code=201)
    def create_workspace(body: WorkspaceInput):
        return store.create(body.name, body.role)

    @app.post("/api/workspaces/demo", status_code=201)
    def create_demo(role: str = "development"):
        if role not in demo.PROFILES:
            raise HTTPException(422, "演示工作区仅支持 Agent 开发。")
        store.ensure_demos()
        return store.get("demo-" + role)

    @app.get("/api/workspaces/{workspace_id}")
    def workspace(workspace_id: str):
        return store.get(workspace_id)

    @app.delete("/api/workspaces/{workspace_id}", status_code=204)
    def delete_workspace(workspace_id: str):
        store.delete(workspace_id)
        return Response(status_code=204)

    @app.put("/api/workspaces/{workspace_id}/materials")
    def update_materials(workspace_id: str, body: MaterialsInput):
        item = store.get(workspace_id)
        if item["resume"] == body.resume and item["job"] == body.job:
            return item
        item.update(resume=body.resume, job=body.job, analysis=None)
        return store.save(item, item["revision"])

    @app.post("/api/extract")
    async def extract(file: UploadFile):
        try:
            if file.size and file.size > MAX_BYTES:
                raise ValueError("文件不得超过 5 MB。")
            content = await file.read(MAX_BYTES + 1)
            text = await run_in_threadpool(extract_text, file.filename or "", content)
            return {
                "filename": file.filename,
                "text": text,
                "chars": len(text),
                "notice": "请核对提取文字，尤其是双栏顺序、日期和数字。",
            }
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        finally:
            await file.close()

    @app.post("/api/workspaces/{workspace_id}/analyze")
    def analyze(workspace_id: str, body: ModeInput):
        item = store.get(workspace_id)
        if len(item["resume"].strip()) < 30 or len(item["job"].strip()) < 20:
            raise HTTPException(422, "请先保存至少 30 字符的简历和 20 字符的岗位要求。")
        item["analysis"] = engine.analyze(item, body.mode)
        return store.save(item, item["revision"])

    @app.put("/api/workspaces/{workspace_id}/claims/{claim_id}")
    def confirm_claim(workspace_id: str, claim_id: str, body: ConfirmInput):
        item = store.get(workspace_id)
        analysis = current_analysis(item)
        for claim in analysis["claims"]:
            if claim["id"] == claim_id:
                claim["confirmed"] = body.confirmed
                return store.save(item, item["revision"])
        raise KeyError(claim_id)

    @app.post("/api/workspaces/{workspace_id}/sessions", status_code=201)
    def start_session(workspace_id: str, body: SessionInput):
        item = store.get(workspace_id)
        analysis = current_analysis(item)
        if item.get("demo_role") == "development" and body.mode == "live":
            body = body.model_copy(update={"demonstration": True})
        if body.demonstration:
            if (
                item.get("demo_role") != "development"
                or item["resume"] != demo.RESUME
                or item["job"] != demo.JOB
            ):
                raise HTTPException(
                    409, "模型示范仅适用于未修改的 Agent 开发虚构材料。"
                )
            if body.mode != "live" or analysis["mode"] != "live":
                raise HTTPException(409, "真实示范需要先使用真实模型分析材料。")
        if (
            sum(
                s["status"] == "active" and s.get("workflow_version") == 2
                for s in item["sessions"]
            )
            >= 3
        ):
            raise HTTPException(409, "已有三场进行中的面试，请先结束其中一场。")
        weak_topics = []
        if body.focus == "weak":
            for previous in reversed(item["sessions"]):
                if body.source_session_id and previous["id"] != body.source_session_id:
                    continue
                if (
                    previous["analysis_id"] == analysis["id"]
                    and previous["status"] == "completed"
                ):
                    weak_topics = previous["report"]["weak_topics"]
                    break
            if not weak_topics:
                raise HTTPException(409, "当前分析暂无可复练的已完成面试。")
        item["sessions"].append(new_session(engine, item, body, weak_topics))
        return store.save(item, item["revision"])

    @app.post(
        "/api/workspaces/{workspace_id}/sessions/{session_id}/demonstration-answer"
    )
    def demonstration_answer(
        workspace_id: str, session_id: str, body: DemonstrationInput
    ):
        with demonstration_lock:
            if session_id in demonstrating:
                raise HTTPException(409, "正在生成本题示范回答，请稍后读取。")
            demonstrating.add(session_id)
        try:
            context, draft = prepare_demonstration(
                store, workspace_id, session_id, body.question_id
            )
            if draft:
                return draft
            result = engine.call(
                workspace_id,
                "live",
                "demonstration_answer",
                context,
                DemonstrationAnswer,
                lambda: {},
            )
            return save_demonstration(
                store, workspace_id, session_id, body.question_id, result["answer"]
            )
        finally:
            with demonstration_lock:
                demonstrating.discard(session_id)

    @app.post(
        "/api/workspaces/{workspace_id}/sessions/{session_id}/demonstration-answer/stream"
    )
    async def demonstration_answer_stream(
        workspace_id: str, session_id: str, body: DemonstrationInput
    ):
        context, draft = prepare_demonstration(
            store, workspace_id, session_id, body.question_id
        )
        with demonstration_lock:
            if session_id in demonstrating:
                raise HTTPException(409, "正在生成本题示范回答，请稍后读取。")
            demonstrating.add(session_id)

        async def generate():
            source = None
            try:
                if draft:
                    yield sse("done", **draft)
                    return
                yield sse("start", question_id=body.question_id)
                text = ""
                source = stream_answer(engine, workspace_id, context)
                async for delta in source:
                    text += delta
                    yield sse("delta", question_id=body.question_id, text=delta)
                saved = await run_in_threadpool(
                    save_demonstration,
                    store,
                    workspace_id,
                    session_id,
                    body.question_id,
                    text,
                )
                yield sse("done", **saved)
            except (ModelError, HTTPException) as exc:
                yield sse(
                    "error",
                    message=exc.detail if isinstance(exc, HTTPException) else str(exc),
                )
            except Exception:
                yield sse(
                    "error", message="流式回答未完成保存，请重试；已有问答仍保留。"
                )
            finally:
                if source is not None:
                    await source.aclose()
                with demonstration_lock:
                    demonstrating.discard(session_id)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/workspaces/{workspace_id}/sessions/{session_id}/answers")
    def answer(
        workspace_id: str,
        session_id: str,
        body: AnswerInput,
        background: BackgroundTasks,
    ):
        item = store.get(workspace_id)
        session = get_session(item, session_id)
        for turn in session["turns"]:
            if turn["request_id"] == body.request_id:
                if (
                    turn["answer"] != body.answer
                    or turn["question"]["id"] != body.question_id
                ):
                    raise HTTPException(409, "同一请求标识不能用于不同回答。")
                return item
        if session.get("workflow_version") != 2:
            raise HTTPException(409, "旧版面试已保留。请结束旧面试并新建 Agent 面试。")
        if session["status"] != "active":
            raise HTTPException(409, "本场面试已结束，请查看或重试评审。")
        question = session["questions"][len(session["turns"])]
        if question["id"] != body.question_id:
            raise HTTPException(409, "题目已变化，请刷新并回答当前问题。")
        answer_turn(engine, session, body)
        if session.get("demonstration"):
            draft = session.get("demonstration_drafts", {}).get(body.question_id)
            session["turns"][-1]["answer_source"] = (
                "model_demonstration"
                if draft and draft["answer"] == body.answer
                else "edited_demonstration"
            )
        saved = store.save(item, item["revision"])
        if session["status"] == "awaiting_report":
            background.add_task(generate_report, workspace_id, session_id)
        return saved

    @app.post("/api/workspaces/{workspace_id}/sessions/{session_id}/finish")
    def finish_session(workspace_id: str, session_id: str, background: BackgroundTasks):
        item = store.get(workspace_id)
        session = get_session(item, session_id)
        if session["status"] == "completed":
            return item
        if not session["turns"]:
            raise HTTPException(409, "至少回答一题后才能生成复盘。")
        if session.get("workflow_version") != 2:
            session.update(
                status="completed", completed_at=now(), report=report(session)
            )
            return store.save(item, item["revision"])
        if session["status"] == "active":
            end_interview(
                session, "user_finish", "用户提前结束，仅评估实际作答的内容。"
            )
        session["report_error"] = None
        saved = store.save(item, item["revision"])
        background.add_task(generate_report, workspace_id, session_id)
        return saved

    @app.post("/api/workspaces/{workspace_id}/sessions/{session_id}/reference-answers")
    def regenerate_answers(workspace_id: str, session_id: str):
        item = store.get(workspace_id)
        session = get_session(item, session_id)
        if (
            session["status"] != "completed"
            or not session.get("report")
            or session.get("workflow_version") != 2
        ):
            raise HTTPException(409, "完成 Agent 面试后才能生成参考答案。")
        answers = reference_answers(engine, session)
        # 模型执行期间可能有其他工作区更新，重新读取后仅更新参考答案。
        current = store.get(workspace_id)
        stored = get_session(current, session_id)
        stored["report"].update(reference_answers=answers, reference_answers_error=None)
        stored["report"]["warnings"] = [
            w
            for w in stored["report"].get("warnings", [])
            if not w.startswith("评分已完成，参考答案")
        ]
        return store.save(current, current["revision"])

    @app.get("/api/workspaces/{workspace_id}/events")
    def events(workspace_id: str, model_only: bool = False):
        return store.events(workspace_id, model_only=model_only)

    @app.get("/api/workspaces/{workspace_id}/sessions/{session_id}/export")
    def export(workspace_id: str, session_id: str):
        item = store.get(workspace_id)
        session = get_session(item, session_id)
        if session["status"] != "completed":
            raise HTTPException(409, "请先结束面试并生成复盘。")
        result = session["report"]
        text = [
            f"# {item['name']} · 面试复盘",
            f"岗位：{item['role']}",
            f"模式：{session['mode']}",
            f"已回答 {result['answered']} / 预算 {result['planned']} 题",
            result["scope"],
            result["demo_notice"],
            "",
        ]
        if session.get("demonstration"):
            text.append("模型示范面试：虚构材料与示范作答，不评价使用者本人能力。")
        if session.get("workflow_version") == 2:
            text.extend(
                [
                    "## 独立模型评审",
                    result["summary"],
                    f"参考综合分：{result['total_score'] if result['total_score'] is not None else '未形成有效综合分'}；已评估权重：{result['covered_weight']}%",
                    f"评分契约：{result['rubric_version']}",
                    *result["warnings"],
                ]
            )
            for score in result["scores"]:
                text.extend(
                    [
                        f"### {score['label']}：{str(score['score']) + '/4' if score['score'] is not None else '未评估'}",
                        score["reason"],
                    ]
                )
                text.extend(
                    f"> 回答 {ref['turn_id'][:8]}：{ref['quote']}"
                    for ref in score["evidence"]
                )
            for title, key in [("优点", "strengths"), ("待改进部分", "weaknesses")]:
                text.append(f"## {title}")
                for finding in result[key]:
                    text.append(finding["text"])
                    text.extend(
                        f"> 回答 {ref['turn_id'][:8]}：{ref['quote']}"
                        for ref in finding["evidence"]
                    )
            text.append("## 改进计划")
            for improvement in result["improvements"]:
                text.extend(
                    [
                        f"### {improvement['title']}",
                        improvement["detail"],
                        improvement["exercise"],
                    ]
                )
            text.append("## 主题结束依据")
            text.extend(
                f"{topic['title']}：{topic['reason']}"
                for topic in session["topics"]
                if topic["status"] == "closed"
            )
        for index, turn in enumerate(session["turns"], 1):
            text.extend(
                [
                    f"## {index}. {turn['question']['text']}",
                    "### 我的回答",
                    turn["answer"],
                ]
            )
            reference = next(
                (
                    a
                    for a in result.get("reference_answers", [])
                    if a["turn_id"] == turn.get("id")
                ),
                None,
            )
            if reference:
                text.extend(
                    [
                        "### 模型参考答案（学习示范，请结合实际核对）",
                        reference["answer"],
                        *[f"- {p}" for p in reference["key_points"]],
                        *[f"- 注意：{p}" for p in reference["pitfalls"]],
                    ]
                )
            if session.get("workflow_version") != 2:
                feedback = turn["feedback"]
                verdict = {
                    "supported": "证据充分",
                    "partial": "待补充",
                    "unverified": "未验证",
                }[feedback["verdict"]]
                text.extend(
                    [
                        f"证据状态：{verdict}",
                        *feedback["gaps"],
                        f"下一步：{feedback['next_step']}",
                    ]
                )
        return Response(
            "\n\n".join(text),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="interview-{session_id[:8]}.md"'
            },
        )

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
