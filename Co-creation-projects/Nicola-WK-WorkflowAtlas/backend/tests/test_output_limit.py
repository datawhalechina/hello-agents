import json
import httpx
import pytest
from openai import OpenAI
from hello_agents.core.llm_adapters import OpenAIAdapter
from app.extraction.remote import RemoteReasoner
from app.schemas import StandardMessage

@pytest.mark.parametrize('always_truncated', [False, True])
def test_truncated_native_completion_retries_with_larger_budget(monkeypatch, always_truncated):
    sent=[]
    def handler(request):
        payload=json.loads(request.content); sent.append(payload)
        enough=payload['max_tokens']>=12000 and not always_truncated
        content=json.dumps({'facts':[{'kind':'task','summary':'开始开发','quote':'开始开发'}]},ensure_ascii=False) if enough else ''
        return httpx.Response(200,json={'id':'fixture','object':'chat.completion','created':0,'model':'synthetic','choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop' if enough else 'length'}],'usage':{'prompt_tokens':10,'completion_tokens':3000,'total_tokens':3010}})
    def client(adapter):
        return OpenAI(api_key='synthetic',base_url='https://synthetic.invalid/v1',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(OpenAIAdapter,'create_client',client)
    reasoner=RemoteReasoner(external_llm_enabled=True,external_data_authorized=True,model='synthetic',api_key='synthetic',base_url='https://synthetic.invalid/v1')
    m=StandardMessage(id='1',source_id='synthetic',sender='测试',timestamp='2026-11-10T09:00:00+08:00',text='开始开发')
    try:
        if always_truncated:
            from app.extraction.remote import ModelResponseError
            with pytest.raises(ModelResponseError) as caught:
                reasoner.extract(m)
            assert '长度上限' in caught.value.public_detail
        else:
            facts=reasoner.extract(m)
            assert len(facts)==1 and facts[0].evidence[0].quote=='开始开发'
        assert len(sent)==2 and sent[0]['max_tokens']<sent[1]['max_tokens']<=12000
        assert reasoner.llm.max_tokens == 3000
    finally: reasoner.close()


def test_job_preserves_safe_model_error_and_does_not_commit(monkeypatch):
    from app.agents import orchestrator
    from app.config import Settings
    from app.extraction.remote import ModelResponseError
    from app.services.processing import ProcessingService
    from app.storage import Repository

    class TruncatedReasoner:
        def __init__(self, **kwargs): pass
        def classify(self, message): return 'work'
        def extract(self, message):
            raise ModelResponseError('PRIVATE_PROVIDER_BODY', '模型输出达到长度上限')
        def close(self): pass

    monkeypatch.setattr(orchestrator, 'RemoteReasoner', TruncatedReasoner)
    settings = Settings(database_path=':memory:', provider='helloagents-llm', external_llm_enabled=True,
                        external_data_authorized=True, llm_model='synthetic', llm_api_key='synthetic', _env_file=None)
    repo = Repository(':memory:')
    m = StandardMessage(id='1',source_id='synthetic',sender='测试',timestamp='2026-11-10T09:00:00+08:00',text='开始开发')
    try:
        repo.import_messages([m], 'synthetic')
        service = ProcessingService(repo, settings)
        monkeypatch.setattr(ProcessingService, "_run", ProcessingService._run_legacy)
        job = service.run(service.enqueue('synthetic').id)
        assert job.status == 'failed' and job.result is None
        assert job.error == 'Fact Extractor：模型输出达到长度上限'
        assert 'PRIVATE_PROVIDER_BODY' not in job.model_dump_json()
        assert repo.facts() == [] and repo.versions() == []
    finally:
        repo.close()
