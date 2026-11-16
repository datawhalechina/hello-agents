import json
import pytest
from app.connectors.local import parse_messages

@pytest.mark.parametrize('text',['123','00123','-12','1.20','1e3','true','false','null','[1,2]','"quoted"','{"other":1}'])
def test_rendered_cli_text_keeps_exact_json_like_characters(text):
    record={'message_id':'synthetic','msg_type':'text','create_time':'2026-11-10T09:00:00+08:00','content':text}
    item=parse_messages(json.dumps([record]),'s')[0]
    assert item.text==text and item.metadata['raw']==record

@pytest.mark.parametrize('text',['123','true','null','[1,2]','"quoted"'])
def test_official_text_envelope_still_decodes(text):
    record={'message_id':'synthetic','msg_type':'text','create_time':'2026-11-10T09:00:00+08:00','body':{'content':json.dumps({'text':text})}}
    item=parse_messages(json.dumps([record]),'s')[0]
    assert item.text==text and item.metadata['raw']==record

def test_numeric_message_at_position29_imports_and_deduplicates(client):
    records=[{'message_id':f'm-{i}','msg_type':'text','create_time':'2026-11-10 09:00:00','content':'123' if i==29 else '虚构测试消息'} for i in range(1,51)]
    response=client.post('/api/import/file?source_id=synthetic-numeric',content=json.dumps({'items':records}))
    assert response.status_code==200,response.text
    assert response.json()['imported']==50
    assert client.app.state.repository.evidence('synthetic-numeric','m-29').text=='123'
    assert client.post('/api/import/file?source_id=synthetic-numeric',content=json.dumps(records)).json()['duplicates']==50

def test_missing_body_still_explained_and_batch_atomic(client):
    records=[{'message_id':'good','msg_type':'text','create_time':'2026-11-10 09:00:00','content':'123'}, {'message_id':'bad','msg_type':'text','create_time':'2026-11-10 09:00:00','body':{'content':'{"secret":"SHOULD_NOT_ECHO"}'}}]
    response=client.post('/api/import/file?source_id=synthetic-bad',content=json.dumps(records))
    assert response.status_code==400 and 'position 2' in response.text
    assert 'content' in response.json()['detail'] and 'SHOULD_NOT_ECHO' not in response.text
    assert client.app.state.repository.messages()==[]
