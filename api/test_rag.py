import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from google.genai import errors, types
import httpx
import psycopg
import pytest
import main
import rag
from rag_config import normalize

CLAIM = {'claim_id': 'PRIVATE-CLAIM-1', 'claim_amount': 150, 'claim_status': 'PENDING', 'service_date': '2025-12-01'}
HEADERS = {'X-API-Key': 'test-key'}
CHUNK = {'chunk_id': 'pending-source', 'source': 'repo://status', 'title': 'Estado',
         'content': 'PENDING significa pendiente.', 'similarity': 0.9}
ANSWER = {'supported': True, 'explanation': 'El estado indica que está pendiente.',
          'evidence': [{'chunk_id': 'pending-source', 'quote': 'PENDING significa pendiente.'}]}


def response(answer=ANSWER, finish=types.FinishReason.STOP):
    return types.GenerateContentResponse(candidates=[types.Candidate(finish_reason=finish,
        content=types.Content(parts=[types.Part(text=json.dumps(answer))]))])


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'test-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-key')
    monkeypatch.setenv('RAG_DATABASE_URL', 'postgresql://fixture-only')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    monkeypatch.delenv('RAG_ENABLED', raising=False)
    embedding = AsyncMock(return_value=types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[1.0] + [0.0] * 767)]))
    generate = AsyncMock(return_value=response())
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=SimpleNamespace(models=SimpleNamespace(
        embed_content=embedding, generate_content=generate)))
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(rag.genai, 'Client', MagicMock(return_value=SimpleNamespace(aio=context)))
    search = MagicMock(return_value=[CHUNK])
    monkeypatch.setattr(rag.rag_store, 'search', search)
    with TestClient(main.app) as client:
        yield client, embedding, generate, search


def test_rag_retrieves_before_generation_and_returns_verified_source(configured):
    client, embedding, generate, search = configured
    result = client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body['retrieval_status'] == 'context_used'
    assert body['sources'][0]['source'] == 'repo://status'
    assert body['sources'][0]['quote'] in CHUNK['content']
    assert '150.00' in body['summary'] and '2025-12-01' in body['summary']
    assert embedding.await_count == 1 and search.call_count == 1
    assert embedding.await_args.kwargs['config'].task_type == 'RETRIEVAL_QUERY'
    assert CLAIM['claim_id'] not in generate.await_args.kwargs['contents']
    assert CHUNK['content'] in generate.await_args.kwargs['contents']


def test_no_context_does_not_call_generator(configured):
    client, _, generate, search = configured
    search.return_value = []
    result = client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS)
    assert result.status_code == 200
    assert result.json()['retrieval_status'] == 'insufficient_context'
    assert result.json()['sources'] == []
    generate.assert_not_awaited()


@pytest.mark.parametrize('evidence', [[], [{'chunk_id': 'invented', 'quote': 'made up'}],
    [{'chunk_id': 'pending-source', 'quote': 'No está en el documento'}]])
def test_invented_citations_are_rejected(configured, evidence):
    client, _, generate, _ = configured
    generate.return_value = response(ANSWER | {'evidence': evidence})
    assert client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS).status_code == 502


def test_unsupported_answer_is_explicit(configured):
    client, _, generate, _ = configured
    generate.return_value = response({'supported': False, 'explanation': '', 'evidence': []})
    result = client.post('/claims/rag-summary', json=CLAIM | {'question': '¿Por qué se denegó?'}, headers=HEADERS)
    assert result.json()['retrieval_status'] == 'insufficient_context'


@pytest.mark.parametrize('headers', [{}, {'X-API-Key': 'wrong'}])
def test_rag_auth_precedes_provider(configured, headers):
    client, embedding, generate, search = configured
    assert client.post('/claims/rag-summary', json=CLAIM, headers=headers).status_code == 401
    embedding.assert_not_awaited()
    search.assert_not_called()
    generate.assert_not_awaited()


def test_rag_rejects_invalid_payload_before_provider(configured):
    client, embedding, _, _ = configured
    result = client.post('/claims/rag-summary', json=CLAIM | {'question': 'x' * 501}, headers=HEADERS)
    assert result.status_code == 422
    embedding.assert_not_awaited()


@pytest.mark.parametrize('variable,value', [('RAG_DATABASE_URL',''), ('GEMINI_API_KEY',''),
    ('RAG_TOP_K','999'), ('RAG_MIN_SIMILARITY','nan')])
def test_missing_or_invalid_rag_configuration(configured, monkeypatch, variable, value):
    client, embedding, _, _ = configured
    monkeypatch.setenv(variable, value)
    assert client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS).status_code == 503
    embedding.assert_not_awaited()


def test_store_failure_is_sanitized(configured):
    client, _, generate, search = configured
    search.side_effect = psycopg.OperationalError('postgresql://private:password@host')
    result = client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS)
    assert result.status_code == 503 and 'password' not in result.text
    generate.assert_not_awaited()


@pytest.mark.parametrize('failure,code', [(httpx.ReadTimeout('private'),504),
    (httpx.ConnectError('private'),502), (errors.APIError(429, {'error': {'code':429,'message':'private'}}),429)])
def test_embedding_failures_are_sanitized(configured, failure, code):
    client, embedding, _, search = configured
    embedding.side_effect = failure
    result = client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS)
    assert result.status_code == code and 'private' not in result.text
    search.assert_not_called()


def test_original_endpoint_can_be_switched_to_rag(configured, monkeypatch):
    client, embedding, _, _ = configured
    monkeypatch.setenv('RAG_ENABLED', 'true')
    result = client.post('/claims/llm-summary', json=CLAIM, headers=HEADERS)
    assert result.status_code == 200 and result.json()['retrieval_status'] == 'context_used'
    embedding.assert_awaited_once()


@pytest.mark.parametrize('values', [[0.0]*768, [1.0], [float('nan')]*768, [float('inf')]*768])
def test_bad_vectors_fail(values):
    with pytest.raises(ValueError):
        normalize(values)


def test_real_sdk_serializes_embedding_and_structured_generation(monkeypatch):
    monkeypatch.setenv('APP_API_KEY', 'test-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-key')
    monkeypatch.setenv('RAG_DATABASE_URL', 'postgresql://fixture')
    captured = []
    real_client = rag.genai.Client
    def handle(request):
        captured.append(request)
        if ':batchEmbedContents' in request.url.path:
            return httpx.Response(200, json={'embeddings': [{'values': [1.0]+[0.0]*767}]})
        return httpx.Response(200, json={'candidates': [{'finishReason':'STOP',
            'content':{'role':'model','parts':[{'text':json.dumps(ANSWER)}]}}]})
    def factory(**kwargs):
        kwargs['http_options'].httpx_client = httpx.Client(transport=httpx.MockTransport(handle))
        kwargs['http_options'].httpx_async_client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        return real_client(**kwargs)
    monkeypatch.setattr(rag.genai, 'Client', factory)
    monkeypatch.setattr(rag.rag_store, 'search', lambda settings, vector: [CHUNK])
    with TestClient(main.app) as client:
        result = client.post('/claims/rag-summary', json=CLAIM, headers=HEADERS)
    assert result.status_code == 200, result.text
    assert len(captured) == 2
    first = json.loads(captured[0].content)['requests'][0]
    assert first['taskType'] == 'RETRIEVAL_QUERY' and first['outputDimensionality'] == 768
    assert CLAIM['claim_id'] not in captured[0].content.decode()
    assert json.loads(captured[1].content)['generationConfig']['responseMimeType'] == 'application/json'
