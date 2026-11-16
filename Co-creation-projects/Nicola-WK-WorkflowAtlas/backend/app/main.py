"""FastAPI entry point, serving the built React UI from the same origin."""
from __future__ import annotations

import hmac
import importlib.metadata
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError

from .config import ROOT, Settings
from .schemas import DeleteSourceRequest, FeishuSyncRequest, ImportFormat, ImportPreview, ImportReport, ImportRequest, Job, ModelConnectionRequest, ModelConnectionResult, ModelSettingsUpdate, ModelSettingsView, ProcessRequest, Project, ReviewRequest, SourceAnalysis, SourceDeletionPreview, SourceDeletionResult, SourceInfo, StandardMessage, WorkFact, WorkflowView, WorkspaceStats
from .services.processing import ProcessingService
from .services.model_settings import ModelSettingsService
from .services.query import facts_in_source, project_context, scoped_graph, source_analysis
from .storage import ConflictError, Repository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    repository = Repository(settings.database_path)
    models = ModelSettingsService(repository, settings)
    service = ProcessingService(repository, settings, models)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        repository.close()

    app = FastAPI(title="Workflow Atlas", version="0.1.0", lifespan=lifespan)
    app.state.repository = repository
    app.state.settings = settings
    app.state.processing = service
    app.state.models = models
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if request.url.path.startswith("/api"):
            if settings.api_token and request.url.path != "/api/health":
                expected = f"Bearer {settings.api_token}"
                if not hmac.compare_digest(request.headers.get("authorization", "").encode(), expected.encode()):
                    return JSONResponse(status_code=401, content={"detail": "A valid bearer token is required"})
            if request.method in {"POST", "PUT", "DELETE"}:
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > settings.max_body_bytes:
                        return JSONResponse(status_code=413, content={"detail": "Import exceeds configured request size limit"})
                request._body = bytes(body)
        return await call_next(request)

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, error: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(KeyError)
    async def missing_handler(request: Request, error: KeyError):
        return JSONResponse(status_code=404, content={"detail": str(error.args[0])})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, error: RequestValidationError):
        if request.url.path in {"/api/model/settings", "/api/model/test"}:
            # FastAPI normally includes rejected inputs in validation errors.
            # Invalid credential types/extra fields must remain write-only too.
            details = [{key: item[key] for key in ("loc", "msg", "type") if key in item} for item in error.errors()]
            return JSONResponse(status_code=422, content={"detail": details})
        return await request_validation_exception_handler(request, error)

    @app.get("/api/health")
    def health():
        try:
            framework = importlib.metadata.version("hello-agents")
        except importlib.metadata.PackageNotFoundError:
            framework = "missing"
        view = models.view()
        return {"status": "ok" if framework != "missing" else "degraded", "provider": view.provider, "helloagents": framework, "external_llm_enabled": view.provider == "helloagents-llm" and view.external_data_authorized and view.api_key_configured and not view.storage_error}

    @app.get("/api/model/settings", response_model=ModelSettingsView)
    def model_settings():
        return models.view()

    @app.get('/api/model/report')
    def model_report(source_id: str = Query(min_length=1, max_length=300)):
        from .services.processing import _answer_hash, _diagram_cache_key, _direct_cache_key, _fact_graph_cache_key
        with repository.lock:
            saved = repository.read_state('holistic_report:' + source_id)
            selected = [m for m in repository.messages() if m.source_id == source_id]
            diagram = repository.read_state('model_diagram:' + source_id)
            fact_graph = repository.read_state('fact_graph:' + source_id)
            try:
                stale = bool(saved and (saved.get('format') != 'direct' or saved.get('cache_key') != _direct_cache_key(selected, models.effective())))
                body = saved.get('report', {}).get('markdown', '') if saved else ''
                diagram_stale = bool(diagram and (not body or diagram.get('answer_hash') != _answer_hash(body) or diagram.get('cache_key') != _diagram_cache_key(source_id, body, models.effective())))
                facts_stale = bool(fact_graph and (not body or fact_graph.get('cache_key') != _fact_graph_cache_key(selected, body, models.effective())))
            except ValueError:
                stale = bool(saved)
                diagram_stale = bool(diagram)
                facts_stale = bool(fact_graph)
            return {'source_id': source_id, 'report': saved['report'] if saved else None,
                    'version': saved.get('version') if saved else None,
                    'created_at': saved.get('created_at') if saved else None,
                    'stale': stale, 'format': saved.get('format', 'structured') if saved else 'direct', 'cached': bool(saved and saved.get('cached')),
                    'diagram': diagram.get('answer') if diagram else None, 'diagram_stale': diagram_stale,
                    'diagram_cached': bool(diagram and diagram.get('cached')),
                    'fact_graph': {'version': fact_graph.get('version'), 'cached': bool(fact_graph.get('cached')),
                                   'stale': facts_stale} if fact_graph else None}

    def enqueue_model_graph(background_tasks, source_id, purpose):
        from .services.processing import _answer_hash, _message_signature
        with repository.lock:
            if not any(m.source_id == source_id for m in repository.messages()):
                raise HTTPException(404, '数据源不存在')
            values = models.effective()
            if values.provider != 'helloagents-llm' or not values.external_llm_enabled or not values.external_data_authorized:
                raise HTTPException(403, '请先启用并授权大模型，再生成图谱。')
            saved = repository.read_state('holistic_report:' + source_id)
            if not saved or saved.get('format') != 'direct' or not saved.get('report', {}).get('markdown', '').strip():
                raise HTTPException(400, '请先生成并保存文字回答，再生成所选图谱。')
            if any(job.status in {'queued', 'running'} for job in repository.jobs()):
                raise ConflictError('已有任务正在进行，请等待完成后再生成图谱。')
            job = service.enqueue(source_id, purpose=purpose)
            job.progress['answer_hash'] = _answer_hash(saved['report']['markdown'])
            if purpose == 'facts':
                job.progress['message_signature'] = _message_signature([m for m in repository.messages() if m.source_id == source_id])
            repository.save_job(job)
        background_tasks.add_task(service.run, job.id, source_id)
        return job

    @app.post('/api/model/diagram', response_model=Job, status_code=202)
    def generate_model_diagram(background_tasks: BackgroundTasks, source_id: str = Query(min_length=1, max_length=300)):
        return enqueue_model_graph(background_tasks, source_id, 'diagram')

    @app.post('/api/model/facts', response_model=Job, status_code=202)
    def generate_model_facts(background_tasks: BackgroundTasks, source_id: str = Query(min_length=1, max_length=300)):
        return enqueue_model_graph(background_tasks, source_id, 'facts')

    @app.post("/api/model/test", response_model=ModelConnectionResult)
    def test_model(body: ModelConnectionRequest):
        try:
            return models.test(body)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.put("/api/model/settings", response_model=ModelSettingsView)
    def save_model(body: ModelSettingsUpdate):
        try:
            return models.update(body)
        except ConflictError:
            raise
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/stats", response_model=WorkspaceStats)
    def stats(source_id: str | None = None):
        _, graph = repository.latest()
        graph = scoped_graph(graph, source_id)
        facts = graph.facts
        return {"messages": sum(source_id is None or m.source_id == source_id for m in repository.messages()), "facts": len(facts), "projects": len(graph.projects), "nodes": len(graph.nodes), "edges": len(graph.edges), "pending_review": sum(f.review_status == "pending" for f in facts), "versions": len(repository.versions()) if source_id is None else sum(any(e.source_id == source_id for f in repository.latest(v['version'])[1].facts for e in f.evidence) for v in repository.versions())}

    @app.get("/api/sources", response_model=list[SourceInfo])
    def sources():
        result = {}
        for message in repository.messages():
            entry = result.setdefault(message.source_id, {"id": message.source_id, "type": message.source_type, "message_count": 0, "last_timestamp": message.timestamp.isoformat()})
            entry["message_count"] += 1
            entry["last_timestamp"] = message.timestamp.isoformat()
        return list(result.values())

    @app.get("/api/sources/analysis", response_model=SourceAnalysis)
    def analysis(source_id: str):
        messages = repository.messages()
        if not any(m.source_id == source_id for m in messages):
            raise KeyError("Source not found")
        return source_analysis(source_id, messages, repository.latest()[1])

    @app.get("/api/sources/delete-preview", response_model=SourceDeletionPreview)
    def delete_preview(source_id: str = Query(min_length=1, max_length=300)):
        return repository.source_delete_preview(source_id)

    @app.delete("/api/sources", response_model=SourceDeletionResult)
    def delete_source(body: DeleteSourceRequest, source_id: str = Query(min_length=1, max_length=300)):
        return repository.delete_source(source_id, body)

    @app.post("/api/import", response_model=ImportReport)
    def import_records(body: ImportRequest):
        try:
            return repository.import_messages(body.messages, body.source_id)
        except ConflictError:
            raise
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/import/file", response_model=ImportReport)
    async def import_file(request: Request, source_id: str = Query(min_length=1, max_length=300), format: ImportFormat = "auto", naive_timezone: Literal['UTC', 'UTC+08:00'] = 'UTC+08:00'):
        from .connectors.local import parse_messages
        from .connectors.formats import source_contexts
        try:
            from .services.import_preflight import decode_import, import_warnings
            content = decode_import(await request.body())
            messages = await run_in_threadpool(parse_messages, content, source_id, format, naive_timezone)
            contexts = await run_in_threadpool(source_contexts, content, format)
            result = repository.import_messages(messages, source_id, contexts)
            result.warnings.extend(import_warnings(messages))
            return result
        except ConflictError:
            raise
        except (ValueError, ValidationError, UnicodeError) as error:
            raise HTTPException(400, str(error)) from error

    @app.post('/api/import/preview', response_model=ImportPreview)
    async def import_preview(request: Request, source_id: str = Query(min_length=1, max_length=300), format: ImportFormat = 'auto', naive_timezone: Literal['UTC', 'UTC+08:00'] = 'UTC+08:00'):
        from .services.import_preflight import decode_import, preview_import
        try:
            preview = await run_in_threadpool(preview_import, repository, decode_import(await request.body()), source_id, format, naive_timezone)
            return preview.model_dump(mode='json')
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.post('/api/import/commit', response_model=ImportReport)
    async def import_commit(request: Request, source_id: str = Query(min_length=1, max_length=300), format: ImportFormat = 'auto', naive_timezone: Literal['UTC', 'UTC+08:00'] = 'UTC+08:00', fingerprint: str = Query(min_length=64, max_length=64, pattern='^[0-9a-f]{64}$')):
        from .connectors.formats import source_contexts
        from .services.import_preflight import decode_import, import_warnings, preview_import
        try:
            content = decode_import(await request.body())
            def commit_checked():
                with repository.lock:
                    preview = preview_import(repository, content, source_id, format, naive_timezone)
                    if not hmac.compare_digest(fingerprint, preview.fingerprint):
                        raise ConflictError('文件、导入选项或已有数据发生变化，请重新检查后再导入。')
                    if not preview.messages:
                        raise HTTPException(400, '没有可导入的消息，请先修复问题记录。')
                    result = repository.import_messages(preview.messages, source_id, source_contexts(content, format))
                    result.warnings.extend(import_warnings(preview.messages))
                    if preview.duplicates:
                        result.warnings.append(f'预检发现 {preview.duplicates} 条重复记录；确认结果按去重后的消息标识计数。')
                    if preview.issues:
                        result.warnings.append('仅导入已确认的可识别消息，问题记录未导入，请下载并保留问题清单。')
                    return result
            return await run_in_threadpool(commit_checked)
        except ConflictError:
            raise
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/process", response_model=Job)
    def process(body: ProcessRequest):
        return service.run(service.enqueue(body.source_id).id, body.source_id)

    @app.get("/api/feishu/status")
    def feishu_status():
        return {"enabled": settings.feishu_sync_enabled, "credential_configured": bool(settings.feishu_access_token), "mode": "read-only", "sources": [{"source_id": source["id"], "checkpoint": repository.checkpoint(source["id"])} for source in sources() if repository.checkpoint(source["id"])]}

    @app.post("/api/feishu/sync")
    def feishu_sync(body: FeishuSyncRequest):
        from time import time
        from .connectors.feishu import FeishuHistoryClient, FeishuReadError, SyncCheckpoint, incremental_checkpoint
        if not settings.feishu_sync_enabled or not settings.feishu_access_token:
            raise HTTPException(403, "Read-only Feishu sync requires explicit enablement and a server-side access token")
        imported = duplicates = 0
        try:
            # Serialize cursor owners to prevent concurrent resume races.
            with repository.lock:
                saved = repository.checkpoint(body.source_id)
                if saved:
                    checkpoint = SyncCheckpoint.from_dict(saved)
                    if checkpoint.chat_id != body.chat_id:
                        raise ConflictError("A source cannot change its Feishu chat identity")
                    if body.incremental and checkpoint.complete:
                        checkpoint = incremental_checkpoint(checkpoint, end_time=body.end_time if body.end_time is not None else int(time()))
                else:
                    checkpoint = SyncCheckpoint(source_id=body.source_id, chat_id=body.chat_id, start_time=body.start_time, end_time=body.end_time if body.end_time is not None else int(time()))
                def commit(messages, state):
                    nonlocal imported, duplicates
                    report = repository.commit_sync_page(messages, state)
                    imported += report.imported
                    duplicates += report.duplicates
                checkpoint = FeishuHistoryClient(settings.feishu_access_token).sync(checkpoint, commit, max_pages=body.max_pages)
            return {"imported": imported, "duplicates": duplicates, "checkpoint": checkpoint.to_dict()}
        except ConflictError:
            raise
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        except FeishuReadError as error:
            raise HTTPException(502, str(error)) from error

    @app.post("/api/jobs", status_code=202, response_model=Job)
    def queue_job(body: ProcessRequest, background: BackgroundTasks):
        job = service.enqueue(body.source_id)
        background.add_task(service.run, job.id, body.source_id)
        return job

    @app.get("/api/jobs/{job_id}", response_model=Job)
    def get_job(job_id: str):
        job = repository.job(job_id)
        if job is None:
            raise KeyError("Job not found")
        return job

    @app.post("/api/jobs/{job_id}/cancel", response_model=Job)
    def cancel_job(job_id: str):
        return service.cancel(job_id)

    @app.post("/api/demo")
    def demo():
        from .connectors.local import parse_messages
        fixture = ROOT / "data" / "fixtures" / "demo_messages.json"
        if not fixture.exists():
            raise HTTPException(503, "Demo fixture is not installed")
        messages = parse_messages(fixture.read_text(encoding="utf-8"), "demo-feishu", "json")
        report = repository.import_messages(messages, "demo-feishu")
        return {"import": report, "job": service.run(service.enqueue().id, force_local=True)}

    @app.get("/api/messages", response_model=list[StandardMessage])
    def messages(source_id: str | None = None, q: str = "", limit: int = Query(default=100, ge=1, le=1000), offset: int = Query(default=0, ge=0)):
        return [m for m in repository.messages() if (source_id is None or m.source_id == source_id) and q.casefold() in m.text.casefold()][offset:offset + limit]

    @app.get("/api/facts", response_model=list[WorkFact])
    def facts(project_id: str | None = None, q: str = "", review_status: Literal["pending", "accepted", "rejected"] | None = None, source_id: str | None = None):
        from .retrieval.search import search_facts
        items = [f for f in facts_in_source(repository.facts(), source_id) if (project_id is None or f.project_id == project_id) and (review_status is None or f.review_status == review_status)]
        return search_facts(q, items, limit=1000) if q else items

    @app.get("/api/projects", response_model=list[Project])
    def projects(source_id: str | None = None):
        return repository.projects() if source_id is None else scoped_graph(repository.latest()[1], source_id).projects

    @app.get("/api/projects/{project_id}", response_model=Project)
    def project(project_id: str):
        found = next((p for p in repository.projects() if p.id == project_id), None)
        if found is None:
            raise KeyError("Project not found")
        return found

    @app.get("/api/projects/{project_id}/workflow", response_model=WorkflowView)
    def workflow(project_id: str, version: int | None = Query(default=None, ge=1), source_id: str | None = None):
        number, graph = repository.latest(version)
        graph = scoped_graph(graph, source_id)
        found = next((p for p in graph.projects if p.id == project_id), None)
        if found is None:
            raise KeyError("Project not found in this workflow version")
        project_facts = [f for f in graph.facts if f.project_id == project_id]
        warnings = [warning for warning in graph.warnings if not warning.startswith("Fact ") or any(f.id in warning for f in project_facts)]
        nodes = [n for n in graph.nodes if n.project_id == project_id]
        node_ids = {n.id for n in nodes}
        related_nodes, related_edges, related_facts = project_context(graph, project_id)
        return {"project": found, "nodes": nodes,
                "edges": [e for e in graph.edges if e.source in node_ids and e.target in node_ids],
                "facts": project_facts, "version": number, "warnings": warnings,
                "related_nodes": related_nodes, "related_edges": related_edges, "related_facts": related_facts}

    @app.get("/api/projects/{project_id}/versions")
    def versions(project_id: str, source_id: str | None = None):
        project(project_id)
        versions = repository.versions(project_id)
        if source_id is None:
            return versions
        return [entry for entry in versions if any(f.project_id == project_id for f in scoped_graph(repository.latest(entry['version'])[1], source_id).facts)]

    @app.get("/api/evidence/{source_id}/{message_id}", response_model=StandardMessage)
    def evidence(source_id: str, message_id: str):
        message = repository.evidence(source_id, message_id)
        if message is None:
            raise KeyError("Evidence message not found")
        return message

    # Query form preserves source/message identities that contain slash characters.
    @app.get("/api/evidence", response_model=StandardMessage)
    def evidence_query(source_id: str, message_id: str):
        return evidence(source_id, message_id)

    @app.get("/api/projects/{project_id}/memory")
    def memory(project_id: str, source_id: str | None = None):
        from .retrieval.memory import build_working_memory
        project(project_id)
        return build_working_memory([f for f in facts_in_source(repository.facts(), source_id) if f.project_id == project_id and f.verified and f.review_status != "rejected"])

    @app.post("/api/facts/{fact_id}/review", response_model=WorkFact)
    def review(fact_id: str, body: ReviewRequest):
        return repository.review(fact_id, body)

    @app.get("/api/reviews")
    def reviews():
        return repository.reviews()

    @app.get("/api/export")
    def export(format: Literal["json", "jsonl", "training"] = "json", project_id: str | None = None, source_id: str | None = None):
        _, graph = repository.latest()
        graph = scoped_graph(graph, source_id)
        facts = [fact for fact in facts_in_source(repository.facts(), source_id) if project_id is None or fact.project_id == project_id]
        if project_id is not None:
            project(project_id)
        if format == "training":
            rows = []
            for fact in facts:
                if fact.review_status == "accepted" and fact.verified:
                    sources = [repository.evidence(e.source_id, e.message_id) for e in fact.evidence]
                    rows.append({"messages": [{"role": "system", "content": "Extract a work fact supported by the provided source evidence."}, {"role": "user", "content": "\n".join(m.text for m in sources if m is not None)}, {"role": "assistant", "content": json.dumps(fact.model_dump(mode="json"), ensure_ascii=False)}], "provenance": [e.model_dump() for e in fact.evidence], "review_status": "accepted", "verified": True})
            payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        elif format == "jsonl":
            payload = "".join(fact.model_dump_json() + "\n" for fact in facts)
        else:
            nodes, edges, projects = graph.nodes, graph.edges, graph.projects
            if project_id is not None:
                related_nodes, related_edges, related_facts = project_context(graph, project_id)
                nodes = [n for n in nodes if n.project_id == project_id] + related_nodes
                own_ids = {n.id for n in nodes if n.project_id == project_id}
                edges = [e for e in edges if e.source in own_ids and e.target in own_ids] + related_edges
                facts = facts + related_facts
                project_ids = {n.project_id for n in nodes} | {project_id}
                projects = [p for p in projects if p.id in project_ids]
            payload = json.dumps({"projects": [p.model_dump(mode="json") for p in projects],
                "facts": [f.model_dump(mode="json") for f in facts], "nodes": [n.model_dump(mode="json") for n in nodes],
                "edges": [e.model_dump(mode="json") for e in edges], "warnings": graph.warnings}, ensure_ascii=False, indent=2)
        extension = "json" if format == "json" else "jsonl"
        return Response(payload, media_type="application/json" if format == "json" else "application/x-ndjson", headers={"Content-Disposition": f'attachment; filename="workflow-{format}.{extension}"'})

    @app.get("/api/runtime")
    def runtime():
        from .agents.orchestrator import WorkflowOrchestrator
        try:
            description = service._orchestrator(WorkflowOrchestrator).describe()
            modes = description["agents"]
            limitations = description["limitations"]
        except (ValueError, PermissionError) as error:
            modes = [{"name": name, "mode": "disabled"} for name in WorkflowOrchestrator.agent_names]
            limitations = [str(error)]
        latest = repository.runtime()
        if models.view().provider == 'helloagents-llm':
            modes = [{'name': 'Direct Chat Answer', 'mode': 'llm'}]
            limitations = ['模型一次通读消息并直接返回Markdown正文和表格，不要求JSON结构或逐行证据字段，也不自动重试。',
                          '正文是模型回答，未经逐项引文核验或人工采纳；不自动改写事实图谱或训练标签。附件和链接正文未自动读取。']
        return {"provider": models.view().provider, "framework": health()["helloagents"], "agents": [a["name"] for a in modes], "agent_modes": modes, "limitations": limitations, "agent_results": latest.get("agent_results", []), "last_run_provider": latest.get("provider")}

    dist = ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str):
            if path.startswith("api/") or path in {"api", "docs", "openapi.json"}:
                raise HTTPException(404, "Not found")
            return FileResponse(dist / "index.html")

    def openapi_contract():
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            if settings.api_token:
                schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {"type": "http", "scheme": "bearer"}
                for path, operations in schema["paths"].items():
                    if path.startswith("/api/") and path != "/api/health":
                        for operation in operations.values():
                            operation["security"] = [{"BearerAuth": []}]
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi_contract
    return app
