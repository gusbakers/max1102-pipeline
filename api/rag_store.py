"""Parameterized SQL with exact cosine search for the small Week 5 corpus."""
import json
import psycopg
from psycopg.rows import dict_row

try:
    from .rag_config import EMBEDDING_MODEL, normalize
except ImportError:
    from rag_config import EMBEDDING_MODEL, normalize


def connect(url):
    return psycopg.connect(url, connect_timeout=5, options='-c statement_timeout=5000', row_factory=dict_row)


def search(settings, vector):
    encoded = json.dumps(normalize(vector), allow_nan=False)
    with connect(settings.database_url) as conn:
        return conn.execute('''
            SELECT chunk_id, source, title, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM week5_knowledge.chunks
            WHERE collection = %s AND embedding_model = %s
              AND 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector, chunk_id
            LIMIT %s
        ''', (encoded, settings.collection, EMBEDDING_MODEL, encoded,
              settings.min_similarity, encoded, settings.top_k)).fetchall()


def readiness(settings):
    with connect(settings.database_url) as conn:
        row = conn.execute('''SELECT count(*) AS chunks FROM week5_knowledge.chunks
            WHERE collection = %s AND embedding_model = %s''',
            (settings.collection, EMBEDDING_MODEL)).fetchone()
    return {'ready': row['chunks'] > 0, 'chunks': row['chunks'], 'embedding_model': EMBEDDING_MODEL}
