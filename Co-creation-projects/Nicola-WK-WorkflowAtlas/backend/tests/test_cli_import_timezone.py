import json
import pytest
from app.connectors.local import parse_messages

def test_cli_export_timezone_is_explicit_and_raw_preserved(client):
    raw={'message_id':'synthetic-1','msg_type':'text','create_time':'2026-11-10 09:30:00','sender':{'id':'synthetic-user','name':'测试人'},'content':'完成测试'}
    response=client.post('/api/import/file?source_id=synthetic&format=json&naive_timezone=UTC%2B08%3A00',content=json.dumps({'data':{'items':[raw]}}))
    assert response.status_code==200,response.text
    stored=client.app.state.repository.messages()[0]
    assert stored.timestamp.isoformat()=='2026-11-10T09:30:00+08:00'
    assert stored.metadata['raw']==raw
    assert client.post('/api/import/file?source_id=synthetic&format=json&naive_timezone=UTC%2B08%3A00',content=json.dumps([raw])).json()['duplicates']==1

def test_cli_timezone_error_explains_field_without_echoing_input(client):
    raw={'message_id':'synthetic-2','msg_type':'text','create_time':'PRIVATE_INVALID_VALUE','content':'private enterprise content'}
    response=client.post('/api/import/file?source_id=synthetic&format=json',content=json.dumps([raw]))
    assert response.status_code==400
    assert '时间' in response.json()['detail']
    assert 'PRIVATE_INVALID_VALUE' not in response.text and 'private enterprise' not in response.text
    assert client.app.state.repository.messages()==[]


@pytest.mark.parametrize('stamp,zone,offset', [
    ('2026-11-10 09:30:00', 'UTC', 0),
    ('2026-11-10T09:30:00+08:00', 'UTC', 28800),
    ('1700000000123', 'UTC+08:00', 0),
])
def test_import_timezone_does_not_override_explicit_or_epoch_time(stamp, zone, offset):
    raw={'message_id':'synthetic','msg_type':'text','create_time':stamp,'content':'测试'}
    message=parse_messages(json.dumps([raw]), 's', naive_timezone=zone)[0]
    assert message.timestamp.utcoffset().total_seconds()==offset
    assert message.metadata['raw']==raw


def test_direct_parser_remains_strict_and_invalid_batch_is_atomic(client):
    from app.connectors.local import ImportValidationError
    valid={'message_id':'valid','msg_type':'text','create_time':'2026-11-10 09:30:00','content':'测试'}
    with pytest.raises(ImportValidationError,match='时区'):
        parse_messages(json.dumps([valid]), 's')
    response=client.post('/api/import/file?source_id=s',content=json.dumps([valid,{**valid,'message_id':'bad','create_time':'invalid'}]))
    assert response.status_code==400 and 'position 2' in response.json()['detail']
    assert client.app.state.repository.messages()==[]
