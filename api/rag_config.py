"""Small, explicit RAG contract. No database or provider access at import time."""
from dataclasses import dataclass
import math
import os

DIMENSIONS = 768
EMBEDDING_MODEL = 'gemini-embedding-001'


@dataclass(frozen=True)
class Settings:
    database_url: str
    collection: str
    api_key: str
    model: str
    min_similarity: float
    top_k: int

    @classmethod
    def load(cls):
        database = os.getenv('RAG_DATABASE_URL', '')
        key = os.getenv('GEMINI_API_KEY', '')
        threshold = float(os.getenv('RAG_MIN_SIMILARITY', '0.55'))
        top_k = int(os.getenv('RAG_TOP_K', '3'))
        collection = os.getenv('RAG_COLLECTION', 'claims-project-v1')
        if not database or not key or not collection:
            raise ValueError('Missing RAG configuration')
        if not math.isfinite(threshold) or not -1 <= threshold <= 1 or not 1 <= top_k <= 8:
            raise ValueError('Invalid retrieval configuration')
        return cls(database, collection, key, os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'), threshold, top_k)


def normalize(values):
    if values is None or len(values) != DIMENSIONS or not all(math.isfinite(v) for v in values):
        raise ValueError('Invalid embedding shape or values')
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0 or not math.isfinite(norm):
        raise ValueError('Invalid embedding norm')
    return [v / norm for v in values]
