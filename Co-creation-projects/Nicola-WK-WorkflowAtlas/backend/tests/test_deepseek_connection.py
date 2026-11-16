import httpx
from app.extraction.remote import test_model_connection as connect
from test_model_adapter import native_transport,completion

def test_deepseek_fixed_connection_probe_disables_thinking(monkeypatch):
    def handler(request):
        import json
        payload=json.loads(request.content)
        answer='OK' if payload.get('thinking')=={'type':'disabled'} else ''
        return httpx.Response(200,json=completion(answer))
    requests,clients,adapters=native_transport(monkeypatch,handler)
    result=connect('deepseek-flash','synthetic','https://api.deepseek.com/v1')
    assert result['ok'] is True
    assert len(requests)==1 and requests[0]['thinking']=={'type':'disabled'}
    assert clients[0][0].is_closed()


def test_empty_body_keeps_reported_usage_in_job(client, monkeypatch):
    from app.extraction import direct
    settings=client.app.state.settings
    settings.provider='helloagents-llm'
    settings.external_llm_enabled=settings.external_data_authorized=True
    settings.llm_model='synthetic'
    class EmptyAnalyzer:
        def __init__(self, settings): pass
        def analyze(self, messages, **kwargs):
            raise direct.EmptyDirectAnswer({'prompt_tokens':20,'completion_tokens':100,'total_tokens':120,'reasoning_tokens':100},'length',500)
    monkeypatch.setattr(direct,'DirectAnalyzer',EmptyAnalyzer)
    client.post('/api/import',json={'source_id':'synthetic','messages':[{'id':'m','source_id':'synthetic','sender':'测试','text':'讨论任务','timestamp':'2026-11-10T09:00:00+08:00'}]})
    job=client.post('/api/process',json={'source_id':'synthetic'}).json()
    assert job['status']=='failed'
    assert job['progress']['usage']['reasoning_tokens']==100
    assert job['progress']['finish_reason']=='length'
    assert client.get('/api/model/report?source_id=synthetic').json()['report'] is None
