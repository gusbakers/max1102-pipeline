import json
import logging
import re

from fastapi.testclient import TestClient
import main


def records(caplog):
    return [json.loads(r.message) for r in caplog.records
            if r.name == 'uvicorn.error' and r.message.startswith('{')]


def test_version_and_request_id(caplog, monkeypatch):
    monkeypatch.delenv('APP_API_KEY', raising=False)
    with caplog.at_level(logging.INFO, logger='uvicorn.error'), TestClient(main.app) as client:
        response = client.get('/version')
    assert response.status_code == 200
    assert 'commit' in response.json()
    assert re.fullmatch(r'[0-9a-f]{32}', response.headers['X-Request-ID'])
    event = records(caplog)[-1]
    assert event['request_id'] == response.headers['X-Request-ID']
    assert event['route'] == '/version' and event['status'] == 200
    assert event['duration_ms'] >= 0


def test_logs_exclude_body_headers_and_query(caplog, monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'expected-test-key')
    with caplog.at_level(logging.INFO, logger='uvicorn.error'), TestClient(main.app) as client:
        response = client.post('/claims/llm-summary?secret=private-query',
                               json={'claim_id': 'private-body'}, headers={'X-API-Key': 'private-header'})
        missing = client.get('/private-unmatched-path?secret=private-query')
    assert response.status_code == 401 and missing.status_code == 404
    logs = records(caplog)
    assert [event['status'] for event in logs] == [401, 404]
    assert logs[-1]['route'] == 'unmatched'
    assert 'private-' not in json.dumps(logs)


def test_validation_failure_is_observable(caplog, monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'local-test-only')
    with caplog.at_level(logging.INFO, logger='uvicorn.error'), TestClient(main.app) as client:
        response = client.post('/claims/llm-summary', json={}, headers={'X-API-Key': 'local-test-only'})
    assert response.status_code == 422
    assert records(caplog)[-1]['status'] == 422
