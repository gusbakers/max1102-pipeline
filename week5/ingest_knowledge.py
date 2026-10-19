"""Atomically replace a named knowledge collection after embedding all changed chunks."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from google import genai
from google.genai import types
from api.rag import embed
from api.rag_config import EMBEDDING_MODEL, Settings
from api.rag_store import connect


def chunks_from_file(path):
    chunks, seen = [], set()
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        source, title, text = (record[k].strip() for k in ('source', 'title', 'text'))
        if not source or not title or not text or source in seen:
            raise ValueError('Knowledge records require unique sources and nonempty title/text')
        seen.add(source)
        # Bound prompt size; overlap keeps context at chunk boundaries.
        for index, start in enumerate(range(0, len(text), 900)):
            content = text[start:start + 1050]
            digest = hashlib.sha256((title + '\n' + content).encode()).hexdigest()
            chunk_id = hashlib.sha256(f'{source}:{index}:{digest}'.encode()).hexdigest()[:32]
            chunks.append(dict(chunk_id=chunk_id, source=source, title=title,
                               content=content, content_hash=digest))
    if not chunks:
        raise ValueError('Refusing to replace knowledge with an empty collection')
    return chunks


async def ingest(path):
    settings = Settings.load()
    chunks = chunks_from_file(path)
    with connect(settings.database_url) as conn:
        cached = {row['chunk_id']: row['embedding'] for row in conn.execute('''
            SELECT chunk_id, embedding::text AS embedding FROM week5_knowledge.chunks
            WHERE collection=%s AND embedding_model=%s''',
            (settings.collection, EMBEDDING_MODEL)).fetchall()}
    generated = 0
    async with genai.Client(api_key=settings.api_key, vertexai=False,
        http_options=types.HttpOptions(timeout=20000,
            retry_options=types.HttpRetryOptions(attempts=1))).aio as client:
        for chunk in chunks:
            if chunk['chunk_id'] in cached:
                chunk['embedding'] = cached[chunk['chunk_id']]
            else:
                vector = await embed(client, chunk['title'] + '\n' + chunk['content'], 'RETRIEVAL_DOCUMENT')
                chunk['embedding'] = json.dumps(vector, allow_nan=False)
                generated += 1
    # Readers see the old or the new collection, never a partially indexed corpus.
    with connect(settings.database_url) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (settings.collection,))
        conn.execute('DELETE FROM week5_knowledge.chunks WHERE collection=%s', (settings.collection,))
        with conn.cursor() as cursor:
            cursor.executemany('''INSERT INTO week5_knowledge.chunks
                (collection, chunk_id, source, title, content, content_hash, embedding_model, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)''',
                [(settings.collection, c['chunk_id'], c['source'], c['title'], c['content'],
                  c['content_hash'], EMBEDDING_MODEL, c['embedding']) for c in chunks])
    return {'chunks': len(chunks), 'new_embeddings': generated, 'collection': settings.collection}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default='knowledge/claims_reference.jsonl')
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(ingest(args.file)), indent=2))
    except Exception as exc:
        # SDK/database exception strings may contain connection details.
        raise SystemExit(f'Indexing failed ({type(exc).__name__}); check configuration and connectivity.') from None
