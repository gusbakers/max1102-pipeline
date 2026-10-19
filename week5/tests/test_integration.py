"""Real PostgreSQL/pgvector and Kafka. Gemini HTTP is intercepted, never billed."""
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest
from confluent_kafka import Producer
from fastapi.testclient import TestClient
from google import genai

from api import main, rag_store
from api.rag_config import EMBEDDING_MODEL, Settings
from streaming.consumer import consume
from streaming.events import ClaimEvent
from streaming.producer import ensure_topic, publish
from week5 import ingest_knowledge

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Real PostgreSQL required')
ROOT = Path(__file__).resolve().parents[2]
VECTOR = [1.0] + [0.0] * 767


@pytest.fixture
def database():
    url = os.environ['TEST_DATABASE_URL']
    with psycopg.connect(url) as conn:
        conn.execute((ROOT / 'week5/sql/001_init.sql').read_text())
    return url


@pytest.fixture
def indexed(database, monkeypatch):
    collection = 'integration-' + uuid4().hex
    monkeypatch.setenv('RAG_DATABASE_URL', database)
    monkeypatch.setenv('RAG_COLLECTION', collection)
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-integration-key')
    monkeypatch.setenv('APP_API_KEY', 'integration-key')
    monkeypatch.setenv('RAG_MIN_SIMILARITY', '0.8')
    calls = []
    async def embed(client, text, task):
        calls.append(task)
        return VECTOR
    monkeypatch.setattr(ingest_knowledge, 'embed', embed)
    result = asyncio.run(ingest_knowledge.ingest(ROOT / 'knowledge/claims_reference.jsonl'))
    assert result['chunks'] == 5 and result['new_embeddings'] == 5
    yield Settings.load(), calls
    with psycopg.connect(database) as conn:
        conn.execute('DELETE FROM week5_knowledge.chunks WHERE collection=%s', (collection,))


def test_real_cosine_search_model_and_collection_isolation(indexed, database):
    settings, _ = indexed
    hits = rag_store.search(settings, VECTOR)
    assert len(hits) == 3 and all(abs(h['similarity'] - 1.0) < 1e-6 for h in hits)
    assert rag_store.search(settings, [0.0, 1.0]+[0.0]*766) == []
    assert rag_store.search(replace(settings, collection="absent' OR true --"), VECTOR) == []
    with psycopg.connect(database) as conn:
        conn.execute('UPDATE week5_knowledge.chunks SET embedding_model=%s WHERE collection=%s',
                     ('different-model', settings.collection))
    assert rag_store.search(settings, VECTOR) == []
    assert rag_store.readiness(settings)['ready'] is False


def test_ingestion_cache_and_failed_reindex_preserve_collection(indexed, monkeypatch, tmp_path):
    settings, calls = indexed
    result = asyncio.run(ingest_knowledge.ingest(ROOT / 'knowledge/claims_reference.jsonl'))
    assert result['new_embeddings'] == 0 and len(calls) == 5
    before = rag_store.search(settings, VECTOR)
    corpus = tmp_path / 'new.jsonl'
    corpus.write_text('\n'.join(json.dumps({'source':f'new:{i}', 'title':'New', 'text':str(i)}) for i in range(2)))
    attempted = []
    async def fail(client, text, task):
        attempted.append(text)
        if len(attempted) == 2:
            raise RuntimeError('Provider unavailable')
        return VECTOR
    monkeypatch.setattr(ingest_knowledge, 'embed', fail)
    with pytest.raises(RuntimeError):
        asyncio.run(ingest_knowledge.ingest(corpus))
    assert rag_store.search(settings, VECTOR) == before


def test_rag_sdk_http_and_real_database_together(indexed, monkeypatch):
    settings, _ = indexed
    hit = rag_store.search(settings, VECTOR)[0]
    real_client = genai.Client
    def handle(request):
        if ':batchEmbedContents' in request.url.path:
            return httpx.Response(200, json={'embeddings':[{'values':VECTOR}]})
        answer = {'supported':True, 'explanation':'La documentación recuperada describe el contrato del proyecto.',
                  'evidence':[{'chunk_id':hit['chunk_id'], 'quote':hit['content'][:100]}]}
        return httpx.Response(200, json={'candidates':[{'finishReason':'STOP',
            'content':{'role':'model','parts':[{'text':json.dumps(answer)}]}}]})
    def factory(**kwargs):
        kwargs['http_options'].httpx_client = httpx.Client(transport=httpx.MockTransport(handle))
        kwargs['http_options'].httpx_async_client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        return real_client(**kwargs)
    monkeypatch.setattr(genai, 'Client', factory)
    with TestClient(main.app) as client:
        ready = client.get('/rag/health', headers={'X-API-Key':'integration-key'})
        assert ready.status_code == 200 and ready.json()['chunks'] == 5
        result = client.post('/claims/rag-summary', headers={'X-API-Key':'integration-key'}, json={
            'claim_id':'INTEGRATION-1', 'claim_amount':120, 'claim_status':'PAID', 'service_date':'2025-12-10'})
    assert result.status_code == 200, result.text
    assert result.json()['sources'][0]['chunk_id'] == hit['chunk_id']


@pytest.mark.skipif(os.getenv('RUN_KAFKA_INTEGRATION') != '1', reason='Real Kafka required')
def test_kafka_acknowledgement_restart_replay_and_rejection(database):
    bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    suffix = uuid4().hex
    topic = 'claims-test-' + suffix
    group = 'claims-group-' + suffix
    ensure_topic(bootstrap, topic)
    now = datetime.now(timezone.utc)
    events = [ClaimEvent(event_id=uuid4(), occurred_at=now, claim={
        'claim_id':f'TEST-{suffix}-{i}', 'claim_amount':100+i,
        'claim_status':'PAID', 'service_date':now.date()}) for i in range(3)]
    try:
        assert publish(events, bootstrap, topic) == 3
        assert consume(database, bootstrap, group, topic, max_messages=3) == {
            'inserted':3, 'duplicate':0, 'rejected':0}
        conflict = events[0].model_copy(update={'claim':events[0].claim.model_copy(update={'claim_amount':999})})
        assert publish([events[0], conflict], bootstrap, topic) == 2
        producer = Producer({'bootstrap.servers':bootstrap})
        producer.produce(topic, key=b'bad', value=b'{invalid json')
        producer.produce(topic, key=b'wrong-key', value=events[1].canonical().encode())
        assert producer.flush(30) == 0
        # A new consumer instance resumes at the committed offset for this group.
        assert consume(database, bootstrap, group, topic, max_messages=4) == {
            'inserted':0, 'duplicate':1, 'rejected':3}
        # Replay simulates delivery after a crash between DB commit and broker commit.
        assert consume(database, bootstrap, 'replay-' + suffix, topic, max_messages=7) == {
            'inserted':0, 'duplicate':4, 'rejected':3}
        with psycopg.connect(database) as conn:
            saved = conn.execute('SELECT event_id,payload_hash FROM week5_stream.events WHERE event_id=ANY(%s)',
                                 ([e.event_id for e in events],)).fetchall()
            rejected = conn.execute('SELECT reason FROM week5_stream.rejections WHERE topic=%s', (topic,)).fetchall()
        assert dict(saved) == {e.event_id:e.digest() for e in events}
        assert sorted(r[0] for r in rejected) == ['EVENT_ID_CONFLICT','INVALID_EVENT_SCHEMA','KEY_MISMATCH']
    finally:
        with psycopg.connect(database) as conn:
            conn.execute('DELETE FROM week5_stream.events WHERE event_id=ANY(%s)', ([e.event_id for e in events],))
            conn.execute('DELETE FROM week5_stream.rejections WHERE topic=%s', (topic,))
        from confluent_kafka.admin import AdminClient
        for future in AdminClient({'bootstrap.servers':bootstrap}).delete_topics([topic]).values():
            future.result(timeout=20)
