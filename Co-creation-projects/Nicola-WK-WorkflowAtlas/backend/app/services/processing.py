"""Scoped model batches, observable jobs and atomic evidence-backed commits."""
from __future__ import annotations
import hashlib
import logging
import threading
import time
from uuid import uuid4
from ..config import Settings
from ..schemas import AgentTaskResult, Job, WorkFact, utcnow
from ..storage import Repository, dump
from .model_settings import ModelSettingsService

logger = logging.getLogger(__name__)

class ProcessingInputError(ValueError):
    pass

def _message_signature(messages) -> str:
    return hashlib.sha256(dump([m.model_dump(mode="json") for m in messages]).encode()).hexdigest()


def _cache_key(batch, effective: Settings) -> str:
    from ..agents import prompts
    policies = {name: value for name, value in vars(prompts).items() if name.endswith('PROMPT') and isinstance(value, str)}
    signature = dump({'version': 'economy-v1', 'messages': _message_signature(batch),
                      'model': effective.llm_model, 'url': effective.llm_base_url,
                      'key_hash': hashlib.sha256(effective.llm_api_key.encode()).hexdigest(), 'policies': policies})
    return 'analysis_cache:' + hashlib.sha256(signature.encode()).hexdigest()


def _holistic_cache_key(messages, effective: Settings) -> str:
    from ..extraction.holistic import REPORT_PROMPT
    return 'holistic_cache:' + hashlib.sha256(dump([_message_signature(messages), effective.llm_model, effective.llm_base_url,
        hashlib.sha256(effective.llm_api_key.encode()).hexdigest(), REPORT_PROMPT]).encode()).hexdigest()


def _direct_cache_key(messages, effective: Settings) -> str:
    from ..extraction.direct import DIRECT_PROMPT
    return 'direct_cache:' + hashlib.sha256(dump([_message_signature(messages), effective.llm_model, effective.llm_base_url,
        hashlib.sha256(effective.llm_api_key.encode()).hexdigest(), effective.llm_thinking, DIRECT_PROMPT]).encode()).hexdigest()


def _answer_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode('utf-8')).hexdigest()


def _diagram_cache_key(source_id: str, markdown: str, effective: Settings) -> str:
    from ..extraction.direct import DIAGRAM_PROMPT
    return 'diagram_cache:' + hashlib.sha256(dump([source_id, markdown, effective.llm_model, effective.llm_base_url,
        hashlib.sha256(effective.llm_api_key.encode()).hexdigest(), effective.llm_thinking, DIAGRAM_PROMPT]).encode()).hexdigest()


def _fact_graph_cache_key(messages, markdown: str, effective: Settings) -> str:
    from ..extraction.fact_graph import FACT_GRAPH_PROMPT
    signature = [_message_signature(messages), _answer_hash(markdown), effective.llm_model, effective.llm_base_url,
                 hashlib.sha256(effective.llm_api_key.encode()).hexdigest(), effective.llm_thinking, FACT_GRAPH_PROMPT]
    return 'fact_graph_cache:' + hashlib.sha256(dump(signature).encode()).hexdigest()

class ProcessingService:
    def __init__(self, repository: Repository, settings: Settings, models: ModelSettingsService | None = None):
        self.repository = repository
        self.settings = settings
        self.models = models or ModelSettingsService(repository, settings)
        self.run_lock = threading.Lock()

    def enqueue(self, source_id: str | None = None, *, purpose: str = 'answer') -> Job:
        job = Job(id=uuid4().hex, source_id=source_id, purpose=purpose)
        self.repository.save_job(job)
        return job

    def cancel(self, job_id: str) -> Job:
        with self.repository.lock:
            job = self.repository.job(job_id)
            if job is None:
                raise KeyError("Job not found")
            if job.status in {"queued", "running"}:
                job.cancel_requested = True
                self.repository.save_job(job)
            return job

    def _cancelled(self, job_id: str) -> bool:
        stored = self.repository.job(job_id)
        return stored is not None and stored.cancel_requested

    def _save_progress(self, job: Job, **progress) -> None:
        with self.repository.lock:
            job.cancel_requested = self._cancelled(job.id)
            job.progress.update(progress)
            self.repository.save_job(job)

    def run(self, job_id: str, source_id: str | None = None, *, force_local: bool = False) -> Job:
        with self.run_lock:
            job = self.repository.job(job_id)
            if job is not None and job.purpose == 'facts' and not force_local:
                return self._run_fact_graph(job_id, source_id)
            if job is not None and job.purpose == 'diagram' and not force_local:
                return self._run_diagram(job_id, source_id)
            return self._run(job_id, source_id, force_local=force_local)

    def _run_diagram(self, job_id: str, source_id: str | None = None) -> Job:
        return self._run_direct(job_id, source_id, diagram=True)

    def _run_fact_graph(self, job_id: str, source_id: str | None = None) -> Job:
        from ..extraction.direct import EmptyDirectAnswer
        from ..extraction.fact_graph import FactGraphAnalyzer, FactGraphOutputError
        from ..extraction.holistic import validate_report
        from ..extraction.remote import ModelResponseError
        from ..schemas import DirectModelAnswer, ModelWorkflowReport, WorkflowUpdateProposal
        from .model_reports import report_proposal

        job = self.repository.job(job_id)
        if job is None:
            raise KeyError('Job not found')
        source_id = source_id or job.source_id
        job.status = 'running'
        self._save_progress(job, stage='正在生成可交互事实图谱', markdown='')
        draft, last_saved = '', 0.0

        def on_delta(delta):
            nonlocal draft, last_saved
            draft += delta
            if time.monotonic() - last_saved >= 0.4:
                self._save_progress(job, markdown=draft)
                last_saved = time.monotonic()

        def check_snapshot():
            current = self.repository.read_state('holistic_report:' + source_id)
            messages = [m for m in self.repository.messages() if m.source_id == source_id]
            if (not current or current.get('format') != 'direct' or
                    _answer_hash(current.get('report', {}).get('markdown', '')) != job.progress.get('answer_hash') or
                    _message_signature(messages) != job.progress.get('message_signature')):
                raise ProcessingInputError('回答或原始消息已变化，请根据最新内容生成事实图谱。')
            if self._cancelled(job.id):
                raise ProcessingInputError('任务已取消')
            return messages, current['report']['markdown']

        try:
            effective = self.models.effective()
            if effective.provider != 'helloagents-llm' or not effective.external_llm_enabled or not effective.external_data_authorized:
                raise ProcessingInputError('请先启用并授权模型分析')
            with self.repository.lock:
                selected, body = check_snapshot()
            if not selected or not body.strip():
                raise ProcessingInputError('请先保存此来源的模型回答')
            self._save_progress(job, total_messages=len(selected), model=effective.llm_model)
            cache_key = _fact_graph_cache_key(selected, body, effective)
            self._save_progress(job, cache_key=cache_key)
            cached = self.repository.read_state(cache_key)
            if cached is None:
                report, answer = FactGraphAnalyzer(effective).analyze(selected, body,
                    cancel_check=lambda: self._cancelled(job.id), on_delta=on_delta)
            else:
                report = ModelWorkflowReport.model_validate(cached['report'])
                answer = DirectModelAnswer.model_validate(cached['answer'])
                if cached.get('recovered_from_job'):
                    job.progress['recovered_from_job'] = cached['recovered_from_job']
            validate_report(report, selected, require_tables=False)
            if not answer.complete:
                raise FactGraphOutputError('图谱输出未完整，已保留任务输出。', answer)
            self._save_progress(job, markdown=answer.markdown, usage=answer.usage, model=answer.model,
                thinking=answer.thinking, thinking_controlled=answer.thinking_controlled,
                finish_reason=answer.finish_reason, elapsed_ms=answer.elapsed_ms,
                processed_messages=len(selected), cached_messages=len(selected) if cached else 0)
            if self._cancelled(job.id):
                raise ProcessingInputError('任务已取消')
            if cached is None:
                self.repository.write_state(cache_key, {'source_id': source_id,
                    'report': report.model_dump(mode='json'), 'answer': answer.model_dump(mode='json')})
            proposal = report_proposal(report, selected, source_id)
            with self.repository.lock:
                check_snapshot()
                _, current = self.repository.latest()
                retained = [f for f in self.repository.facts() if all(e.source_id != source_id for e in f.evidence)]
                fact_ids = {f.id for f in retained}
                nodes = [n for n in current.nodes if n.fact_ids and all(key in fact_ids for key in n.fact_ids)]
                node_ids = {n.id for n in nodes}
                project_ids = {f.project_id for f in retained if f.project_id}
                merged = WorkflowUpdateProposal(
                    projects=[p for p in current.projects if p.source_id != source_id and
                              (p.id in project_ids or p.analysis_mode == 'model')] + proposal.projects,
                    facts=retained + proposal.facts, nodes=nodes + proposal.nodes,
                    edges=[e for e in current.edges if e.source in node_ids and e.target in node_ids] + proposal.edges,
                    warnings=proposal.warnings)
                state = {'source_id': source_id, 'answer_hash': job.progress['answer_hash'],
                         'cache_key': cache_key, 'cached': cached is not None, 'created_at': utcnow().isoformat()}
                if job.progress.get('recovered_from_job'):
                    state['recovered_from_job'] = job.progress['recovered_from_job']
                job.status, job.completed_at = 'completed', utcnow()
                job.progress['stage'] = '事实图谱已保存'
                job.result = {'complete': True, 'source_id': source_id, 'analysis_mode': 'interactive-facts',
                              'facts': len(proposal.facts), 'projects': len(proposal.projects),
                              'warnings': proposal.warnings}
                self.repository.apply(merged, self.repository.runtime(), preserve_model_semantics=True,
                    extra_state=('fact_graph:' + source_id, state), terminal_job=job)
            return job
        except Exception as error:
            if isinstance(error, FactGraphOutputError):
                answer = error.answer
                job.progress.update(markdown=answer.markdown, usage=answer.usage, model=answer.model,
                    thinking=answer.thinking, thinking_controlled=answer.thinking_controlled,
                    finish_reason=answer.finish_reason, elapsed_ms=answer.elapsed_ms)
            elif isinstance(error, EmptyDirectAnswer):
                job.progress.update(usage=error.usage, finish_reason=error.finish_reason, elapsed_ms=error.elapsed_ms)
            elif draft:
                job.progress['markdown'] = draft
            if self._cancelled(job.id):
                job.status, job.error = 'cancelled', None
            else:
                job.status = 'failed'
                job.error = (error.public_detail if isinstance(error, ModelResponseError) else
                             str(error) if isinstance(error, ProcessingInputError) else
                             '事实图谱生成或保存失败，任务输出已保留。')
                logger.error('Fact graph generation failed (%s)', type(error).__name__)
            job.result = None
            job.completed_at = utcnow()
            job.progress['stage'] = '已停止' if job.status == 'cancelled' else '事实图谱未保存'
            self.repository.save_job(job)
            return job

    def _run(self, job_id: str, source_id: str | None, *, force_local: bool) -> Job:
        if not force_local and self.models.view().provider == 'helloagents-llm':
            return self._run_direct(job_id, source_id)
        return self._run_legacy(job_id, source_id, force_local=force_local)

    def _run_direct(self, job_id: str, source_id: str | None, *, diagram: bool = False) -> Job:
        from ..extraction.direct import DiagramAnalyzer, DirectAnalyzer, EmptyDirectAnswer
        from ..extraction.remote import ModelResponseError
        from ..schemas import DirectModelAnswer
        job = self.repository.job(job_id)
        if job is None:
            raise KeyError('Job not found')
        source_id = source_id or job.source_id
        job.source_id, job.status = source_id, 'running'
        self._save_progress(job, stage='正在生成图谱' if diagram else '正在生成回答', batch_index=1, total_batches=1,
                            processed_messages=0, cached_messages=0, markdown='')
        draft, last_saved = '', 0.0

        def on_delta(delta):
            nonlocal draft, last_saved
            draft += delta
            if time.monotonic() - last_saved >= 0.4:
                self._save_progress(job, markdown=draft)
                last_saved = time.monotonic()

        try:
            effective = self.models.effective()
            if not effective.external_llm_enabled or not effective.external_data_authorized:
                raise ProcessingInputError('请先配置并授权模型分析')
            with self.repository.lock:
                selected = [m for m in self.repository.messages() if m.source_id == source_id]
            if not source_id or not selected:
                raise ProcessingInputError('请选择一个有消息的数据源')
            if self._cancelled(job.id):
                raise ProcessingInputError('任务已取消')
            signature = _message_signature(selected)
            saved = self.repository.read_state('holistic_report:' + source_id) if diagram else None
            if diagram:
                if not saved or saved.get('format') != 'direct' or not saved.get('report', {}).get('markdown', '').strip():
                    raise ProcessingInputError('请先生成并保存文字回答，再根据回答生成图谱。')
                body = saved['report']['markdown']
                base_hash = _answer_hash(body)
                if job.progress.get('answer_hash') != base_hash:
                    raise ProcessingInputError('保存的回答已变化，请基于最新回答重新生成图谱。')
                cache_key = _diagram_cache_key(source_id, body, effective)
            else:
                cache_key = _direct_cache_key(selected, effective)
            self._save_progress(job, total_messages=len(selected), model=effective.llm_model, thinking=effective.llm_thinking)
            cached = self.repository.read_state(cache_key)
            if cached is not None:
                answer = DirectModelAnswer.model_validate(cached['report'])
            elif diagram:
                answer = DiagramAnalyzer(effective).analyze(body, source_id=source_id, cancel_check=lambda: self._cancelled(job.id), on_delta=on_delta)
            else:
                answer = DirectAnalyzer(effective).analyze(selected, cancel_check=lambda: self._cancelled(job.id), on_delta=on_delta)
            if not answer.markdown.strip():
                raise ProcessingInputError('模型尚未返回正文；不会将空回答保存为报告。')
            if self._cancelled(job.id):
                raise ProcessingInputError('任务已取消')
            self._save_progress(job, markdown=answer.markdown, usage=answer.usage, model=answer.model, thinking=answer.thinking, thinking_controlled=answer.thinking_controlled,
                finish_reason=answer.finish_reason, elapsed_ms=answer.elapsed_ms,
                processed_messages=len(selected), cached_messages=len(selected) if cached is not None else 0)
            if cached is None and answer.complete:
                self.repository.write_state(cache_key, {'source_id': source_id, 'report': answer.model_dump(mode='json')})
            with self.repository.lock, self.repository.connection:
                latest_answer = self.repository.read_state('holistic_report:' + source_id) if diagram else None
                if diagram and (not latest_answer or _answer_hash(latest_answer.get('report', {}).get('markdown', '')) != base_hash):
                    raise ProcessingInputError('生成期间文字回答发生变化，未覆盖图谱；已生成内容保留在任务中。')
                if not diagram and signature != _message_signature([m for m in self.repository.messages() if m.source_id == source_id]):
                    raise ProcessingInputError('生成期间消息发生变化，回答已保留在本次任务中，请核对后重新分析。')
                if self._cancelled(job.id):
                    raise ProcessingInputError('任务已取消')
                wrapper = {'source_id': source_id, 'format': 'direct', 'report': answer.model_dump(mode='json'), 'cached': cached is not None,
                    'created_at': utcnow().isoformat(), 'version': None, 'cache_key': cache_key}
                if diagram:
                    wrapper['answer'] = wrapper.pop('report')
                    wrapper['answer_hash'] = base_hash
                self.repository.connection.execute('INSERT OR REPLACE INTO state VALUES(?,?)', (('model_diagram:' if diagram else 'holistic_report:') + source_id, dump(wrapper)))
                if not diagram:
                    self.repository.connection.execute("INSERT OR REPLACE INTO state VALUES('runtime',?)", (dump({'provider': 'helloagents-llm', 'analysis_mode': 'direct-chat', 'agent_results': []}),))
                job.result = {'provider': 'helloagents-llm', 'analysis_mode': 'model-diagram' if diagram else 'direct-chat', 'source_id': source_id,
                    'messages': len(selected), 'facts': 0, 'projects': 0, 'complete': answer.complete,
                    'warnings': [] if answer.complete else ['回答尚未完整，已保留正文；不会自动重试。']}
                job.status = 'completed'
                job.progress['stage'] = '已完成' if answer.complete else '回答未完整，已保留正文'
                # Publish terminal status under the same transaction, without
                # save_job's nested connection context committing early.
                self.repository.connection.execute('UPDATE jobs SET payload=? WHERE id=?', (dump(job), job.id))
        except Exception as error:
            if isinstance(error, EmptyDirectAnswer):
                job.progress.update(usage=error.usage, finish_reason=error.finish_reason, elapsed_ms=error.elapsed_ms)
            if draft:
                job.progress['markdown'] = draft
            if self._cancelled(job.id):
                job.status, job.error = 'cancelled', None
                job.cancel_requested = True
                job.progress['stage'] = '已停止，已生成正文保留在任务中'
            else:
                job.status = 'failed'
                job.error = error.public_detail if isinstance(error, ModelResponseError) else str(error) if isinstance(error, ProcessingInputError) else '模型请求或回答存储失败；已生成的正文保留在本次任务中。'
                job.progress['stage'] = '失败，已生成正文仍可查看'
                logger.error('Direct model request failed (%s)', type(error).__name__)
        job.completed_at = utcnow()
        self.repository.save_job(job)
        return job

    def _run_holistic(self, job_id: str, source_id: str | None) -> Job:
        from ..extraction.holistic import HolisticAnalyzer, validate_report
        from ..extraction.remote import ModelResponseError
        from ..schemas import ModelWorkflowReport, WorkflowUpdateProposal
        from .model_reports import report_proposal
        job = self.repository.job(job_id)
        if job is None:
            raise KeyError('Job not found')
        source_id = source_id or job.source_id
        job.source_id, job.status = source_id, 'running'
        self._save_progress(job, stage='大模型全局还原', batch_index=1, total_batches=1, processed_messages=0, cached_messages=0)
        try:
            effective = self.models.effective()
            if not effective.external_llm_enabled or not effective.external_data_authorized:
                raise ProcessingInputError('请先配置并授权模型分析')
            with self.repository.lock:
                selected = [m for m in self.repository.messages() if m.source_id == source_id]
            if not source_id or not selected:
                raise ProcessingInputError('请选择一个有消息的数据源')
            if self._cancelled(job.id):
                raise ProcessingInputError('任务已取消')
            signature = _message_signature(selected)
            cache_key = _holistic_cache_key(selected, effective)
            self._save_progress(job, total_messages=len(selected))
            cached = self.repository.read_state(cache_key)
            report = ModelWorkflowReport.model_validate(cached['report']) if cached is not None else HolisticAnalyzer(effective).analyze(selected, cancel_check=lambda: self._cancelled(job.id))
            validate_report(report, selected)
            if self._cancelled(job.id):
                raise ProcessingInputError('任务已取消')
            if cached is None:
                self.repository.write_state(cache_key, {'source_id': source_id, 'report': report.model_dump(mode='json')})
            self._save_progress(job, stage='核对原文依据并保存', processed_messages=len(selected), cached_messages=len(selected) if cached is not None else 0)
            proposal = report_proposal(report, selected, source_id)
            with self.repository.lock:
                if signature != _message_signature([m for m in self.repository.messages() if m.source_id == source_id]):
                    raise ProcessingInputError('分析期间消息发生变化，结果未写入；请重新分析')
                if self._cancelled(job.id):
                    raise ProcessingInputError('任务已取消')
                _, current = self.repository.latest()
                retained_facts = [f for f in self.repository.facts() if all(e.source_id != source_id for e in f.evidence)]
                retained_ids = {f.id for f in retained_facts}
                retained_nodes = [n for n in current.nodes if n.fact_ids and all(f in retained_ids for f in n.fact_ids)]
                node_ids = {n.id for n in retained_nodes}
                old_project_ids = {f.project_id for f in retained_facts if f.project_id}
                merged = WorkflowUpdateProposal(
                    projects=[p for p in current.projects if p.source_id != source_id and (p.id in old_project_ids or p.analysis_mode == 'model')] + proposal.projects,
                    facts=retained_facts + proposal.facts, nodes=retained_nodes + proposal.nodes,
                    edges=[e for e in current.edges if e.source in node_ids and e.target in node_ids] + proposal.edges,
                    warnings=proposal.warnings)
                runtime = {'provider': 'helloagents-llm', 'analysis_mode': 'full-model', 'agent_results': []}
                wrapper = {'source_id': source_id, 'report': report.model_dump(mode='json'), 'created_at': utcnow().isoformat(), 'signature': signature, 'cache_key': cache_key}
                version = self.repository.apply(merged, runtime, preserve_model_semantics=True, extra_state=('holistic_report:' + source_id, wrapper))
                job.result = {'version': version, 'messages': len(selected), 'facts': len(proposal.facts), 'projects': len(proposal.projects),
                              'nodes': len(proposal.nodes), 'edges': len(proposal.edges), 'warnings': proposal.warnings, 'source_id': source_id, **runtime}
                job.status, job.progress['stage'] = 'completed', '已完成'
                self.repository.save_job(job)
        except Exception as error:
            if self._cancelled(job.id):
                job.status, job.error, job.progress['stage'] = 'cancelled', None, '已停止，结果未写入'
                job.cancel_requested = True
            else:
                job.status = 'failed'
                job.error = (error.public_detail if isinstance(error, ModelResponseError) else str(error) if isinstance(error, ProcessingInputError)
                             else '模型报告未通过格式或原文依据校验，本次结果未写入。')
                job.progress['stage'] = '失败，结果未写入'
                logger.error('Full model analysis failed (%s)', type(error).__name__)
        job.completed_at = utcnow()
        self.repository.save_job(job)
        return job

    def _run_legacy(self, job_id: str, source_id: str | None, *, force_local: bool) -> Job:
        job = self.repository.job(job_id)
        if job is None:
            raise KeyError("Job not found")
        source_id = source_id if source_id is not None else job.source_id
        job.source_id = source_id
        job.status = "running"
        self._save_progress(job, stage="准备分析", processed_messages=0, cached_messages=0)
        try:
            from ..agents.orchestrator import WorkflowOrchestrator
            from ..workflow.builder import build_workflow
            from ..workflow.verifier import fact_verification_errors, message_index, verify_references
            if self._cancelled(job.id):
                raise ProcessingInputError("任务已取消")
            effective = self.settings.model_copy(update={"provider": "local-demo"}) if force_local else self.models.effective()
            with self.repository.lock:
                all_messages = self.repository.messages()
                if source_id and not any(m.source_id == source_id for m in all_messages):
                    raise ProcessingInputError("所选数据源没有导入消息")
                remote = effective.provider == "helloagents-llm"
                if remote and not source_id:
                    raise ProcessingInputError("使用大模型前请选择一个明确的数据源")
                selected = [m for m in all_messages if m.source_id == source_id] if remote else all_messages
                signature = _message_signature(selected)
                existing_projects = self.repository.projects()
            if remote:
                size = effective.llm_batch_size
                batches = [selected[index:index + size] for index in range(0, len(selected), size)]
                collected = []
                aggregate = {}
                cached_messages = 0
                for index, batch in enumerate(batches, 1):
                    if self._cancelled(job.id):
                        raise ProcessingInputError("任务已取消")
                    self._save_progress(job, stage="模型筛选与提取", total_messages=len(selected), batch_index=index, total_batches=len(batches))
                    cache_key = _cache_key(batch, effective)
                    cached = self.repository.read_state(cache_key)
                    if cached is not None:
                        try:
                            batch_facts = [WorkFact.model_validate(f) for f in cached['facts']]
                            stages = [AgentTaskResult.model_validate(s) for s in cached['agent_results']]
                        except (ValueError, KeyError, TypeError) as error:
                            raise ProcessingInputError('分析缓存损坏，本次结果未写入') from error
                        cached_messages += len(batch)
                    else:
                        orchestrator = self._orchestrator(WorkflowOrchestrator, effective, remote_max_seconds=600, economy_mode=True, cancel_check=lambda: self._cancelled(job.id))
                        result = orchestrator.analyze(batch, existing_projects)
                        batch_facts, stages = result.proposal.facts, result.agent_results
                    # Cached facts are proposals, never trusted labels. Reverify
                    # against this exact immutable batch on every use.
                    evidence_index = message_index(batch)
                    if any(f.review_status != 'pending' or fact_verification_errors(f, evidence_index) for f in batch_facts):
                        raise ProcessingInputError('分析结果或缓存的原文证据未通过核验，本次结果未写入')
                    if self._cancelled(job.id):
                        raise ProcessingInputError('任务已取消')
                    if cached is None:
                        self.repository.write_state(cache_key, {'source_id': source_id,
                            'facts': [f.model_dump(mode='json') for f in batch_facts],
                            'agent_results': [s.model_dump(mode='json') for s in stages]})
                    collected.extend(batch_facts)
                    for stage in stages:
                        combined = aggregate.setdefault(stage.agent, AgentTaskResult(agent=stage.agent, status="completed", detail="分批处理结果合计"))
                        combined.input_count += stage.input_count
                        combined.output_count += stage.output_count
                        combined.duration_ms += stage.duration_ms
                    self._save_progress(job, processed_messages=min(index * size, len(selected)), cached_messages=cached_messages)
                results, provider = list(aggregate.values()), "helloagents-llm"
            else:
                self._save_progress(job, stage="本地分析", total_messages=len(selected), batch_index=1, total_batches=1)
                result = self._orchestrator(WorkflowOrchestrator, effective).analyze(selected, existing_projects)
                collected, results, provider = result.proposal.facts, result.agent_results, result.provider
                self._save_progress(job, processed_messages=len(selected))
            if self._cancelled(job.id):
                raise ProcessingInputError("任务已取消")
            self._save_progress(job, stage="核验并保存")
            with self.repository.lock:
                current_messages = self.repository.messages()
                current_selection = [m for m in current_messages if m.source_id == source_id] if remote else current_messages
                if _message_signature(current_selection) != signature:
                    raise ProcessingInputError("分析期间消息发生变化，结果未写入；请重新分析")
                if self._cancelled(job.id):
                    raise ProcessingInputError("任务已取消")
                if remote:
                    retained = [f for f in self.repository.facts() if f.evidence[0].source_id != source_id]
                    proposal = build_workflow([*retained, *collected], current_messages, self.repository.projects())
                else:
                    proposal = result.proposal
                evidence_index = message_index(current_messages)
                for fact in proposal.facts:
                    if fact_verification_errors(fact, evidence_index):
                        fact.verified = False
                facts = {fact.id: fact for fact in proposal.facts}
                proposal.nodes = [n for n in proposal.nodes if n.verified and n.fact_ids and all(key in facts and facts[key].verified and facts[key].project_id == n.project_id for key in n.fact_ids) and verify_references(n.evidence, evidence_index)]
                nodes = {n.id: n for n in proposal.nodes}
                proposal.edges = [e for e in proposal.edges if e.source in nodes and e.target in nodes and nodes[e.source].project_id == nodes[e.target].project_id == e.project_id and e.verified and verify_references(e.evidence, evidence_index)]
                runtime = {"provider": provider, "agent_results": [stage.model_dump(mode="json") for stage in results]}
                version = self.repository.apply(proposal, runtime)
                job.result = {"version": version, "messages": len(selected), "facts": len(proposal.facts), "projects": len(proposal.projects), "nodes": len(proposal.nodes), "edges": len(proposal.edges), "warnings": proposal.warnings, "source_id": source_id, **runtime}
                job.status = "completed"
                job.progress["stage"] = "已完成"
                # Publish completion while the commit lock still excludes a
                # late cancellation request for an already saved graph.
                self.repository.save_job(job)
        except Exception as error:
            if self._cancelled(job.id):
                job.status = "cancelled"
                job.cancel_requested = True
                job.error = None
                job.progress["stage"] = "已停止，结果未写入"
            else:
                logger.error("Processing job %s failed (%s)", job.id, type(error).__name__)
                job.status = "failed"
                from ..agents.orchestrator import AnalysisError
                job.error = (f"{error.stage}：{error.public_detail}" if isinstance(error, AnalysisError) and error.public_detail
                             else str(error) if isinstance(error, ProcessingInputError)
                             else f"分析失败（{type(error).__name__}），请检查模型连接或输入格式。")
                job.progress["stage"] = "失败，结果未写入"
        job.completed_at = utcnow()
        self.repository.save_job(job)
        return job

    def _orchestrator(self, constructor, effective: Settings | None = None, **kwargs):
        values = effective or self.models.effective()
        if values.provider == 'helloagents-llm':
            kwargs.setdefault('economy_mode', True)
        return constructor(provider=values.provider, external_llm_enabled=values.external_llm_enabled, external_data_authorized=values.external_data_authorized, llm_model=values.llm_model, llm_api_key=values.llm_api_key, llm_base_url=values.llm_base_url, **kwargs)
